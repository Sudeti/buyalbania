import logging
from django.db.models import Avg, Count, Min, Max, Q, F
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from .models import PropertyAnalysis

logger = logging.getLogger(__name__)

class PropertyAnalytics:
    """Comprehensive property market analytics service"""
    
    def __init__(self):
        self.now = timezone.now()
        self.six_months_ago = self.now - timedelta(days=180)
        self.one_year_ago = self.now - timedelta(days=365)
    
    def get_location_market_stats(self, location: str, property_type: str = None) -> Dict:
        """Get comprehensive market statistics for a location"""
        try:
            # Base query for location
            base_query = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                status='completed',
                asking_price__gt=0,
                created_at__gte=self.six_months_ago
            )
            
            if property_type:
                base_query = base_query.filter(property_type=property_type)
            
            # Calculate key metrics
            stats = base_query.aggregate(
                total_properties=Count('id'),
                avg_price=Avg('asking_price'),
                min_price=Min('asking_price'),
                max_price=Max('asking_price'),
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area')),
                avg_investment_score=Avg('investment_score'),
                high_score_count=Count('id', filter=Q(investment_score__gte=80)),
                strong_buy_count=Count('id', filter=Q(recommendation='strong_buy')),
            )
            
            # Calculate price ranges
            if stats['total_properties'] > 0:
                price_range = stats['max_price'] - stats['min_price']
                stats['price_range'] = price_range
                stats['price_volatility'] = (price_range / stats['avg_price']) * 100 if stats['avg_price'] else 0
                
                            # Calculate success rates
            if stats['total_properties'] > 0:
                stats['high_score_rate'] = (stats['high_score_count'] / stats['total_properties']) * 100
                stats['strong_buy_rate'] = (stats['strong_buy_count'] / stats['total_properties']) * 100
            else:
                stats['high_score_rate'] = 0
                stats['strong_buy_rate'] = 0
                
                # Market sentiment
                if stats['avg_investment_score']:
                    if stats['avg_investment_score'] >= 75:
                        stats['market_sentiment'] = 'bullish'
                    elif stats['avg_investment_score'] >= 60:
                        stats['market_sentiment'] = 'neutral'
                    else:
                        stats['market_sentiment'] = 'bearish'
                else:
                    stats['market_sentiment'] = 'unknown'
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating location market stats for {location}: {e}")
            return {}
    
    def get_price_trends(self, location: str, property_type: str = None, months: int = 6) -> List[Dict]:
        """Get price trends over time for a location"""
        try:
            start_date = self.now - timedelta(days=months * 30)
            
            base_query = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                status='completed',
                asking_price__gt=0,
                created_at__gte=start_date
            )
            
            if property_type:
                base_query = base_query.filter(property_type=property_type)
            
            # Group by month and calculate averages
            trends = base_query.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                avg_price=Avg('asking_price'),
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area')),
                property_count=Count('id'),
                avg_investment_score=Avg('investment_score')
            ).order_by('month')
            
            return list(trends)
            
        except Exception as e:
            logger.error(f"Error calculating price trends for {location}: {e}")
            return []
    
    def get_comparable_analysis(self, property_analysis: PropertyAnalysis) -> Dict:
        """Get detailed comparable property analysis"""
        try:
            location = property_analysis.property_location.split(',')[0]
            property_type = property_analysis.property_type
            price = float(property_analysis.asking_price)
            area = property_analysis.usable_area
            
            # Get comparable properties
            comparables = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                property_type=property_type,
                status='completed',
                asking_price__gt=0
            ).exclude(id=property_analysis.id)
            
            # Filter by size if available
            if area:
                size_range = area * 0.4  # ±40% size difference
                comparables = comparables.filter(
                    Q(total_area__range=(area - size_range, area + size_range)) |
                    Q(internal_area__range=(area - size_range, area + size_range))
                )
            
            # Get recent comparables (last 6 months)
            comparables = comparables.filter(
                created_at__gte=self.six_months_ago
            ).order_by('-created_at')[:10]
            
            if not comparables.exists():
                return {}
            
            # Calculate comparable statistics
            comp_stats = comparables.aggregate(
                avg_price=Avg('asking_price'),
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area')),
                min_price=Min('asking_price'),
                max_price=Max('asking_price'),
                avg_investment_score=Avg('investment_score'),
                total_count=Count('id')
            )
            
            # Calculate price position
            avg_comp_price = comp_stats['avg_price']
            avg_comp_price_per_sqm = comp_stats['avg_price_per_sqm']
            
            if avg_comp_price and price > 0:
                price_position = ((price - avg_comp_price) / avg_comp_price) * 100
                price_percentile = self._calculate_price_percentile(price, comparables)
            else:
                price_position = 0
                price_percentile = 50
            
            # Calculate area-adjusted price comparison
            if area and avg_comp_price_per_sqm:
                current_price_per_sqm = price / area
                price_per_sqm_position = ((current_price_per_sqm - avg_comp_price_per_sqm) / avg_comp_price_per_sqm) * 100
            else:
                price_per_sqm_position = 0
            
            return {
                'comparable_count': comp_stats['total_count'],
                'avg_comparable_price': avg_comp_price,
                'avg_comparable_price_per_sqm': avg_comp_price_per_sqm,
                'price_position_percentage': price_position,
                'price_percentile': price_percentile,
                'price_per_sqm_position': price_per_sqm_position,
                'price_range': {
                    'min': comp_stats['min_price'],
                    'max': comp_stats['max_price'],
                    'current': price
                },
                'avg_comparable_score': comp_stats['avg_investment_score'],
                'comparable_properties': list(comparables.values(
                    'property_title', 'asking_price', 'total_area', 
                    'investment_score', 'recommendation', 'created_at'
                )[:5])
            }
            
        except Exception as e:
            logger.error(f"Error calculating comparable analysis: {e}")
            return {}
    
    def get_market_opportunity_score(self, property_analysis: PropertyAnalysis) -> Dict:
        """Calculate market opportunity score based on multiple factors"""
        try:
            location = property_analysis.property_location.split(',')[0]
            price = float(property_analysis.asking_price)
            area = property_analysis.usable_area
            
            # Get market stats
            market_stats = self.get_location_market_stats(location, property_analysis.property_type)
            comparable_analysis = self.get_comparable_analysis(property_analysis)
            
            if not market_stats or not comparable_analysis:
                return {'opportunity_score': 50, 'factors': []}
            
            factors = []
            opportunity_score = 50  # Base score
            
            # Factor 1: Price vs Market Average (30% weight)
            if comparable_analysis.get('avg_comparable_price'):
                avg_price = comparable_analysis['avg_comparable_price']
                price_diff = ((price - avg_price) / avg_price) * 100
                
                if price_diff <= -10:  # 10% or more below average
                    factors.append({
                        'factor': 'price_below_market',
                        'description': f'Price is {abs(price_diff):.1f}% below market average',
                        'impact': 'positive',
                        'weight': 30
                    })
                    opportunity_score += 20
                elif price_diff >= 10:  # 10% or more above average
                    factors.append({
                        'factor': 'price_above_market',
                        'description': f'Price is {price_diff:.1f}% above market average',
                        'impact': 'negative',
                        'weight': 30
                    })
                    opportunity_score -= 15
            
            # Factor 2: Market Sentiment (20% weight)
            market_sentiment = market_stats.get('market_sentiment', 'unknown')
            if market_sentiment == 'bullish':
                factors.append({
                    'factor': 'bullish_market',
                    'description': 'Market shows bullish sentiment',
                    'impact': 'positive',
                    'weight': 20
                })
                opportunity_score += 15
            elif market_sentiment == 'bearish':
                factors.append({
                    'factor': 'bearish_market',
                    'description': 'Market shows bearish sentiment',
                    'impact': 'negative',
                    'weight': 20
                })
                opportunity_score -= 10
            
            # Factor 3: Location Tier (20% weight)
            location_tier = property_analysis.location_tier
            if location_tier == 'prime':
                factors.append({
                    'factor': 'prime_location',
                    'description': 'Prime location with high demand',
                    'impact': 'positive',
                    'weight': 20
                })
                opportunity_score += 15
            elif location_tier == 'emerging':
                factors.append({
                    'factor': 'emerging_location',
                    'description': 'Emerging location with growth potential',
                    'impact': 'positive',
                    'weight': 20
                })
                opportunity_score += 10
            
            # Factor 4: Property Type Demand (15% weight)
            type_demand = self._get_property_type_demand(property_analysis.property_type, location)
            if type_demand == 'high':
                factors.append({
                    'factor': 'high_type_demand',
                    'description': 'High demand for this property type',
                    'impact': 'positive',
                    'weight': 15
                })
                opportunity_score += 10
            elif type_demand == 'low':
                factors.append({
                    'factor': 'low_type_demand',
                    'description': 'Low demand for this property type',
                    'impact': 'negative',
                    'weight': 15
                })
                opportunity_score -= 10
            
            # Factor 5: Days on Market (15% weight)
            days_on_market = property_analysis.days_on_market
            if days_on_market > 90:
                factors.append({
                    'factor': 'long_market_time',
                    'description': f'Property on market for {days_on_market} days',
                    'impact': 'positive',
                    'weight': 15
                })
                opportunity_score += 10  # Negotiation opportunity
            
            # Normalize score to 0-100 range
            opportunity_score = max(0, min(100, opportunity_score))
            
            return {
                'opportunity_score': round(opportunity_score, 1),
                'factors': factors,
                'market_stats': market_stats,
                'comparable_analysis': comparable_analysis
            }
            
        except Exception as e:
            logger.error(f"Error calculating market opportunity score: {e}")
            return {'opportunity_score': 50, 'factors': []}
    
    def get_negotiation_insights(self, property_analysis: PropertyAnalysis) -> Dict:
        """Provide negotiation insights based on market analysis"""
        try:
            comparable_analysis = self.get_comparable_analysis(property_analysis)
            market_stats = self.get_location_market_stats(
                property_analysis.property_location.split(',')[0],
                property_analysis.property_type
            )
            
            insights = {
                'recommended_offer_range': {},
                'negotiation_factors': [],
                'market_conditions': {},
                'timing_recommendations': []
            }
            
            # Calculate recommended offer range
            if comparable_analysis.get('avg_comparable_price'):
                avg_price = comparable_analysis['avg_comparable_price']
                current_price = float(property_analysis.asking_price)
                
                # Base recommendation on price position
                if current_price > avg_price:
                    # Above market - room for negotiation
                    discount_range = min(15, (current_price - avg_price) / avg_price * 100)
                    recommended_min = current_price * (1 - discount_range / 100)
                    recommended_max = current_price * 0.95  # 5% below asking
                    
                    insights['recommended_offer_range'] = {
                        'min': round(recommended_min, 0),
                        'max': round(recommended_max, 0),
                        'discount_percentage': round(discount_range, 1)
                    }
                    
                    insights['negotiation_factors'].append({
                        'factor': 'above_market_price',
                        'description': f'Property priced {((current_price - avg_price) / avg_price * 100):.1f}% above market average',
                        'leverage': 'high'
                    })
                else:
                    # Below or at market - less room for negotiation
                    recommended_min = current_price * 0.98  # 2% below asking
                    recommended_max = current_price * 0.95  # 5% below asking
                    
                    insights['recommended_offer_range'] = {
                        'min': round(recommended_min, 0),
                        'max': round(recommended_max, 0),
                        'discount_percentage': 2.5
                    }
            
            # Add market condition insights
            if market_stats.get('market_sentiment'):
                sentiment = market_stats['market_sentiment']
                if sentiment == 'bullish':
                    insights['market_conditions']['sentiment'] = 'bullish'
                    insights['negotiation_factors'].append({
                        'factor': 'bullish_market',
                        'description': 'Market is bullish - sellers have leverage',
                        'leverage': 'low'
                    })
                elif sentiment == 'bearish':
                    insights['market_conditions']['sentiment'] = 'bearish'
                    insights['negotiation_factors'].append({
                        'factor': 'bearish_market',
                        'description': 'Market is bearish - buyers have leverage',
                        'leverage': 'high'
                    })
            
            # Add timing recommendations
            days_on_market = property_analysis.days_on_market
            if days_on_market > 60:
                insights['timing_recommendations'].append({
                    'timing': 'immediate',
                    'description': f'Property on market for {days_on_market} days - seller may be motivated',
                    'urgency': 'high'
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error calculating negotiation insights: {e}")
            return {}
    
    def _calculate_price_percentile(self, price: float, comparables) -> float:
        """Calculate price percentile among comparable properties"""
        try:
            prices = list(comparables.values_list('asking_price', flat=True))
            if not prices:
                return 50
            
            prices.append(price)
            prices.sort()
            
            position = prices.index(price)
            percentile = (position / (len(prices) - 1)) * 100
            
            return round(percentile, 1)
            
        except Exception as e:
            logger.error(f"Error calculating price percentile: {e}")
            return 50
    
    def _get_property_type_demand(self, property_type: str, location: str) -> str:
        """Determine demand level for property type in location"""
        try:
            # Get recent properties of this type
            recent_properties = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                property_type=property_type,
                status='completed',
                created_at__gte=self.six_months_ago
            )
            
            if not recent_properties.exists():
                return 'unknown'
            
            # Calculate average investment score
            avg_score = recent_properties.aggregate(
                avg_score=Avg('investment_score')
            )['avg_score']
            
            if avg_score >= 75:
                return 'high'
            elif avg_score >= 60:
                return 'medium'
            else:
                return 'low'
                
        except Exception as e:
            logger.error(f"Error determining property type demand: {e}")
            return 'unknown'
    
    def get_market_summary(self, location: str = None) -> Dict:
        """Get comprehensive market summary"""
        try:
            base_query = PropertyAnalysis.objects.filter(
                status='completed',
                asking_price__gt=0,
                created_at__gte=self.six_months_ago
            )
            
            if location:
                base_query = base_query.filter(property_location__icontains=location)
            
            # Overall market stats
            total_count = base_query.count()
            if total_count > 0:
                market_stats = base_query.aggregate(
                    total_properties=Count('id'),
                    avg_price=Avg('asking_price'),
                    avg_investment_score=Avg('investment_score'),
                    high_score_count=Count('id', filter=Q(investment_score__gte=80)),
                    strong_buy_count=Count('id', filter=Q(recommendation='strong_buy'))
                )
                
                # Calculate rates
                market_stats['high_score_rate'] = (market_stats['high_score_count'] / total_count) * 100
                market_stats['strong_buy_rate'] = (market_stats['strong_buy_count'] / total_count) * 100
            else:
                market_stats = {
                    'total_properties': 0,
                    'avg_price': 0,
                    'avg_investment_score': 0,
                    'high_score_rate': 0,
                    'strong_buy_rate': 0
                }
            
            # Price trends by month
            monthly_trends = base_query.annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                avg_price=Avg('asking_price'),
                property_count=Count('id')
            ).order_by('month')
            
            # Property type distribution
            type_distribution = base_query.values('property_type').annotate(
                count=Count('id'),
                avg_price=Avg('asking_price'),
                avg_score=Avg('investment_score')
            ).order_by('-count')
            
            return {
                'market_stats': market_stats,
                'monthly_trends': list(monthly_trends),
                'type_distribution': list(type_distribution),
                'analysis_period': {
                    'start': self.six_months_ago,
                    'end': self.now,
                    'months': 6
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating market summary: {e}")
            return {}

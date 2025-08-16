import logging
import statistics
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.db.models import Avg, Count, Min, Max, Q, F, Variance
from django.utils import timezone
from datetime import timedelta
from .models import PropertyAnalysis
from django.core.cache import cache

logger = logging.getLogger(__name__)

class MarketPositionEngine:
    """Real-time market position analysis based on actual comparable data with caching"""
    
    def calculate_property_advantage(self, property_analysis: PropertyAnalysis) -> Optional[Dict]:
        """Calculate real market position using actual comparable properties with caching"""
        try:
            location = property_analysis.property_location.split(',')[0]
            prop_type = property_analysis.property_type
            price_per_sqm = property_analysis.price_per_sqm
            
            if not price_per_sqm or not property_analysis.total_area:
                logger.warning(f"Missing price or area data for analysis {property_analysis.id}")
                return None
            
            # Create cache key
            cache_key = f"market_position_{location}_{prop_type}_{price_per_sqm}_{property_analysis.total_area}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for market position: {location}")
                return cached_result
            
            # Get real comparables from database
            comparables = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                property_type=prop_type,
                total_area__range=(
                    property_analysis.total_area * 0.8, 
                    property_analysis.total_area * 1.2
                ),
                status='completed',
                asking_price__gt=0
            ).exclude(id=property_analysis.id)
            
            if comparables.count() < 3:
                logger.info(f"Insufficient comparables ({comparables.count()}) for analysis {property_analysis.id}")
                return None
            
            # Calculate price per sqm for all comparables
            prices_per_sqm = []
            for comp in comparables:
                if comp.total_area and comp.total_area > 0:
                    comp_price_per_sqm = float(comp.asking_price) / comp.total_area
                    prices_per_sqm.append(comp_price_per_sqm)
            
            if len(prices_per_sqm) < 3:
                return None
            
            # Calculate percentile ranking
            percentile = self._calculate_percentile(price_per_sqm, prices_per_sqm)
            
            # Calculate savings potential
            median_price = statistics.median(prices_per_sqm)
            savings_amount = (median_price - price_per_sqm) * property_analysis.total_area
            price_advantage_percent = ((median_price - price_per_sqm) / median_price) * 100
            
            # Determine market position category
            if percentile <= 25:
                position_category = "bottom_quartile"
                advantage_description = f"Priced in bottom 25% of market"
            elif percentile <= 50:
                position_category = "below_median"
                advantage_description = f"Priced below market median"
            elif percentile <= 75:
                position_category = "above_median"
                advantage_description = f"Priced above market median"
            else:
                position_category = "top_quartile"
                advantage_description = f"Priced in top 25% of market"
            
            result = {
                'market_percentile': percentile,
                'position_category': position_category,
                'advantage_description': advantage_description,
                'potential_savings': savings_amount,
                'sample_size': comparables.count(),
                'price_advantage_percent': price_advantage_percent,
                'median_market_price': median_price,
                'price_range': {
                    'min': min(prices_per_sqm),
                    'max': max(prices_per_sqm),
                    'current': price_per_sqm
                }
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, 3600)
            logger.debug(f"Cache set for market position: {location}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating property advantage: {e}")
            return None
    
    def _calculate_percentile(self, value: float, data: List[float]) -> float:
        """Calculate percentile of value in dataset"""
        try:
            sorted_data = sorted(data)
            position = 0
            for i, item in enumerate(sorted_data):
                if value <= item:
                    position = i
                    break
            else:
                position = len(sorted_data)
            
            percentile = (position / len(sorted_data)) * 100
            return round(percentile, 1)
        except Exception as e:
            logger.error(f"Error calculating percentile: {e}")
            return 50.0


class AgentPerformanceAnalyzer:
    """Analyze agent performance patterns from scraped data with caching"""
    
    def get_agent_insights(self, property_analysis: PropertyAnalysis) -> Optional[Dict]:
        """Get agent performance insights based on historical data with caching"""
        try:
            agent_name = property_analysis.agent_name
            if not agent_name:
                return None
            
            # Create cache key
            cache_key = f"agent_insights_{agent_name}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for agent insights: {agent_name}")
                return cached_result
            
            # Analyze agent's portfolio from scraped data
            agent_properties = PropertyAnalysis.objects.filter(
                agent_name=agent_name,
                status='completed',
                asking_price__gt=0,
                total_area__gt=0
            )
            
            if agent_properties.count() < 3:
                logger.info(f"Insufficient agent data for {agent_name}")
                return None
            
            # Calculate agent metrics
            agent_stats = agent_properties.aggregate(
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area')),
                avg_days_market=Avg('days_on_market'),
                total_properties=Count('id'),
                price_variance=Variance(F('asking_price') / F('total_area'))
            )
            
            # Compare to market average
            location = property_analysis.property_location.split(',')[0]
            market_stats = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                status='completed',
                asking_price__gt=0,
                total_area__gt=0
            ).aggregate(
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area'))
            )
            
            if not market_stats['avg_price_per_sqm']:
                return None
            
            agent_avg = agent_stats['avg_price_per_sqm']
            market_avg = market_stats['avg_price_per_sqm']
            
            # Calculate agent vs market pricing
            agent_vs_market_percent = ((agent_avg - market_avg) / market_avg) * 100
            
            # Calculate consistency score
            consistency_score = 100
            if agent_stats['price_variance'] and agent_avg:
                variance_percent = (agent_stats['price_variance'] / (agent_avg ** 2)) * 100
                consistency_score = max(0, 100 - variance_percent)
            
            # Determine negotiation potential
            negotiation_potential = self._calculate_negotiation_potential(
                agent_vs_market_percent, 
                agent_stats['avg_days_market'],
                consistency_score
            )
            
            result = {
                'agent_portfolio_size': agent_stats['total_properties'],
                'agent_avg_price_vs_market': agent_vs_market_percent,
                'agent_consistency_score': consistency_score,
                'agent_velocity': agent_stats['avg_days_market'],
                'negotiation_potential': negotiation_potential,
                'agent_pricing_style': self._categorize_pricing_style(agent_vs_market_percent),
                'market_comparison': {
                    'agent_avg': agent_avg,
                    'market_avg': market_avg,
                    'difference_percent': agent_vs_market_percent
                }
            }
            
            # Cache the result for 2 hours (agent data changes less frequently)
            cache.set(cache_key, result, 7200)
            logger.debug(f"Cache set for agent insights: {agent_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing agent performance: {e}")
            return None
    
    def _calculate_negotiation_potential(self, agent_vs_market: float, avg_days: float, consistency: float) -> str:
        """Calculate negotiation potential based on agent patterns"""
        score = 0
        
        # Agent pricing factor (higher above market = more negotiation room)
        if agent_vs_market > 10:
            score += 40
        elif agent_vs_market > 5:
            score += 25
        elif agent_vs_market < -5:
            score -= 20
        
        # Market velocity factor (longer on market = more negotiation room)
        if avg_days and avg_days > 60:
            score += 30
        elif avg_days and avg_days > 30:
            score += 15
        
        # Consistency factor (less consistent = more negotiation room)
        if consistency < 70:
            score += 20
        
        if score >= 60:
            return 'high'
        elif score >= 30:
            return 'medium'
        else:
            return 'low'
    
    def _categorize_pricing_style(self, agent_vs_market: float) -> str:
        """Categorize agent's pricing style"""
        if agent_vs_market > 15:
            return 'aggressive'
        elif agent_vs_market > 5:
            return 'premium'
        elif agent_vs_market > -5:
            return 'market_rate'
        elif agent_vs_market > -15:
            return 'competitive'
        else:
            return 'discount'


class NeighborhoodVelocityTracker:
    """Track market momentum using time-series data with caching"""
    
    def analyze_market_momentum(self, property_analysis: PropertyAnalysis) -> Dict:
        """Analyze market momentum and timing intelligence with caching"""
        try:
            location = property_analysis.property_location.split(',')[0]
            now = timezone.now()
            
            # Create cache key
            cache_key = f"market_momentum_{location}_{now.strftime('%Y-%m-%d')}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for market momentum: {location}")
                return cached_result
            
            # Get properties by time periods
            last_30_days = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                created_at__gte=now - timedelta(days=30),
                asking_price__gt=0,
                total_area__gt=0
            )
            
            last_90_days = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                created_at__gte=now - timedelta(days=90),
                asking_price__gt=0,
                total_area__gt=0
            )
            
            # Calculate listing velocity
            velocity_30d = last_30_days.count()
            velocity_90d = last_90_days.count() / 3  # Average per month
            
            # Price momentum analysis
            recent_avg = last_30_days.aggregate(
                avg=Avg(F('asking_price') / F('total_area'))
            )['avg']
            
            older_avg = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                created_at__range=[
                    now - timedelta(days=120), 
                    now - timedelta(days=90)
                ],
                asking_price__gt=0,
                total_area__gt=0
            ).aggregate(
                avg=Avg(F('asking_price') / F('total_area'))
            )['avg']
            
            # Calculate momentum
            momentum = 0
            if older_avg and recent_avg:
                momentum = ((recent_avg - older_avg) / older_avg) * 100
            
            # Supply pressure analysis
            active_listings = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                is_active=True
            ).count()
            
            # Market temperature calculation
            market_temperature = self._calculate_market_temperature(
                velocity_30d, velocity_90d, momentum, active_listings
            )
            
            result = {
                'listing_velocity_trend': velocity_30d - velocity_90d,
                'velocity_30d': velocity_30d,
                'velocity_90d': velocity_90d,
                'price_momentum_30d': momentum,
                'supply_pressure': active_listings,
                'market_temperature': market_temperature,
                'timing_recommendation': self._get_timing_recommendation(market_temperature, momentum),
                'market_phase': self._determine_market_phase(momentum, velocity_30d, active_listings)
            }
            
            # Cache the result for 6 hours (market momentum changes daily)
            cache.set(cache_key, result, 21600)
            logger.debug(f"Cache set for market momentum: {location}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing market momentum: {e}")
            return {}
    
    def _calculate_market_temperature(self, velocity_30d: int, velocity_90d: float, momentum: float, supply: int) -> str:
        """Calculate market temperature based on multiple factors"""
        score = 0
        
        # Velocity factor
        if velocity_30d > velocity_90d * 1.5:
            score += 30  # High activity
        elif velocity_30d < velocity_90d * 0.5:
            score -= 20  # Low activity
        
        # Momentum factor
        if momentum > 10:
            score += 25  # Strong upward momentum
        elif momentum > 5:
            score += 15  # Moderate upward momentum
        elif momentum < -10:
            score -= 25  # Strong downward momentum
        elif momentum < -5:
            score -= 15  # Moderate downward momentum
        
        # Supply factor
        if supply < 10:
            score += 20  # Low supply
        elif supply > 50:
            score -= 20  # High supply
        
        if score >= 40:
            return 'hot'
        elif score >= 20:
            return 'warm'
        elif score >= -20:
            return 'moderate'
        else:
            return 'cool'
    
    def _get_timing_recommendation(self, temperature: str, momentum: float) -> str:
        """Get timing recommendation based on market conditions"""
        if temperature == 'hot' and momentum > 5:
            return 'act_fast'
        elif temperature == 'warm' and momentum > 0:
            return 'good_timing'
        elif temperature == 'cool' and momentum < 0:
            return 'wait_better'
        else:
            return 'neutral'
    
    def _determine_market_phase(self, momentum: float, velocity: int, supply: int) -> str:
        """Determine current market phase"""
        if momentum > 10 and velocity > 10 and supply < 20:
            return 'expansion'
        elif momentum > 5 and velocity > 5:
            return 'growth'
        elif momentum < -10 and velocity < 5 and supply > 30:
            return 'contraction'
        elif momentum < -5 and supply > 20:
            return 'decline'
        else:
            return 'stable'


class PropertyScarcityAnalyzer:
    """Analyze property scarcity and uniqueness with caching"""
    
    def calculate_scarcity_score(self, property_analysis: PropertyAnalysis) -> Dict:
        """Calculate property scarcity score based on market supply with caching"""
        try:
            # Create cache key
            cache_key = f"scarcity_score_{property_analysis.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for scarcity score: {property_analysis.id}")
                return cached_result
            
            # Define search criteria for "similar" properties
            location = property_analysis.property_location.split(',')[0]
            filters = {
                'property_location__icontains': location,
                'property_type': property_analysis.property_type,
                'total_area__range': (
                    float(property_analysis.total_area) * 0.85, 
                    float(property_analysis.total_area) * 1.15
                ) if property_analysis.total_area else (0, float('inf')),
                'asking_price__range': (
                    float(property_analysis.asking_price) * 0.8,
                    float(property_analysis.asking_price) * 1.2
                )
            }
            
            # Count similar active properties
            similar_active = PropertyAnalysis.objects.filter(
                **filters,
                is_active=True
            ).exclude(id=property_analysis.id).count()
            
            # Count similar sold in last 6 months
            similar_sold = PropertyAnalysis.objects.filter(
                **filters,
                is_active=False,
                removed_date__gte=timezone.now() - timedelta(days=180)
            ).count()
            
            # Special features scoring
            special_features_score = self._calculate_special_features_score(property_analysis)
            
            # Calculate base scarcity score
            base_scarcity = max(0, 100 - (similar_active * 15))  # Fewer similar = higher score
            demand_indicator = min(similar_sold * 8, 40)  # Historical demand
            
            final_score = min(100, base_scarcity + special_features_score + demand_indicator)
            
            # Identify unique features
            unique_features = self._identify_unique_features(property_analysis)
            
            # Market gap analysis
            market_gap = 'high_demand_low_supply' if similar_active < 3 and similar_sold > 5 else 'normal'
            
            result = {
                'scarcity_score': final_score,
                'similar_active_count': similar_active,
                'historical_demand': similar_sold,
                'special_features_score': special_features_score,
                'uniqueness_factors': unique_features,
                'market_gap_analysis': market_gap,
                'scarcity_category': self._categorize_scarcity(final_score),
                'demand_supply_ratio': similar_sold / max(similar_active, 1)
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, 3600)
            logger.debug(f"Cache set for scarcity score: {property_analysis.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating scarcity score: {e}")
            return {'scarcity_score': 50, 'similar_active_count': 0, 'historical_demand': 0}
    
    def _calculate_special_features_score(self, property_analysis: PropertyAnalysis) -> int:
        """Calculate score based on special property features"""
        score = 0
        
        if property_analysis.has_elevator:
            score += 15
        if property_analysis.floor_level == 'ground_floor' and property_analysis.property_type == 'commercial':
            score += 25
        if property_analysis.property_condition == 'new':
            score += 20
        if property_analysis.furnished:
            score += 10
        if property_analysis.bedrooms and property_analysis.bedrooms >= 3:
            score += 10
        if property_analysis.bathrooms and property_analysis.bathrooms >= 2:
            score += 5
        
        return score
    
    def _identify_unique_features(self, property_analysis: PropertyAnalysis) -> List[str]:
        """Identify unique features of the property"""
        features = []
        
        if property_analysis.has_elevator:
            features.append("Elevator access")
        if property_analysis.property_condition == 'new':
            features.append("New construction")
        if property_analysis.furnished:
            features.append("Furnished")
        if property_analysis.floor_level == 'ground_floor' and property_analysis.property_type == 'commercial':
            features.append("Ground floor commercial")
        if property_analysis.neighborhood:
            features.append(f"Prime {property_analysis.neighborhood} location")
        
        return features
    
    def _categorize_scarcity(self, score: float) -> str:
        """Categorize scarcity level"""
        if score >= 80:
            return 'extremely_rare'
        elif score >= 60:
            return 'rare'
        elif score >= 40:
            return 'uncommon'
        else:
            return 'common'


class ROICalculator:
    """Calculate investment ROI based on real market data with caching"""
    
    def calculate_investment_potential(self, property_analysis: PropertyAnalysis) -> Dict:
        """Calculate investment potential with real market data and caching"""
        try:
            location = property_analysis.property_location.split(',')[0]
            
            # Create cache key
            cache_key = f"roi_calculation_{property_analysis.id}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for ROI calculation: {property_analysis.id}")
                return cached_result
            
            # Estimate monthly rent from market data
            estimated_monthly_rent = self._estimate_rent_from_market_data(property_analysis)
            
            # Calculate purchase costs
            purchase_price = float(property_analysis.asking_price)
            notary_fees = purchase_price * 0.03  # 3% in Albania
            total_investment = purchase_price + notary_fees
            
            # Calculate annual yields
            annual_rental_income = estimated_monthly_rent * 12
            gross_yield = (annual_rental_income / total_investment) * 100
            
            # Operating costs (estimate based on Albanian market)
            annual_costs = annual_rental_income * 0.25  # 25% for maintenance, management, taxes
            net_yield = ((annual_rental_income - annual_costs) / total_investment) * 100
            
            # Appreciation potential based on price trend data
            location_appreciation = self._calculate_location_appreciation_rate(location)
            
            # 5-year projection
            year_5_value = total_investment * (1 + location_appreciation/100) ** 5
            total_rental_income_5y = annual_rental_income * 5
            total_return_5y = (year_5_value + total_rental_income_5y - total_investment) / total_investment * 100
            
            # Break-even analysis
            break_even_months = total_investment / estimated_monthly_rent if estimated_monthly_rent > 0 else None
            break_even_years = break_even_months / 12 if break_even_months else None
            
            # Compare to market average
            market_comparison = self._compare_to_market_averages(gross_yield, location)
            
            result = {
                'gross_annual_yield': gross_yield,
                'net_annual_yield': net_yield,
                'estimated_monthly_rent': estimated_monthly_rent,
                'total_investment_required': total_investment,
                'location_appreciation_rate': location_appreciation,
                'projected_5y_total_return': total_return_5y,
                'break_even_months': break_even_months,
                'break_even_years': break_even_years,
                'market_comparison': market_comparison,
                'investment_category': self._categorize_investment(gross_yield, total_return_5y),
                'risk_adjusted_return': self._calculate_risk_adjusted_return(gross_yield, location_appreciation)
            }
            
            # Cache the result for 1 hour
            cache.set(cache_key, result, 3600)
            logger.debug(f"Cache set for ROI calculation: {property_analysis.id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating investment potential: {e}")
            return {}
    
    def _estimate_rent_from_market_data(self, property_analysis: PropertyAnalysis) -> float:
        """Estimate rent based on property characteristics and market data"""
        try:
            # Base estimate using rule of thumb: 0.5-0.8% of property value per month
            conservative_estimate = float(property_analysis.asking_price) * 0.005  # 0.5%
            optimistic_estimate = float(property_analysis.asking_price) * 0.008   # 0.8%
            
            # Adjust based on location
            location_multipliers = {
                'tirana': 1.2,
                'vlorë': 1.0,
                'vlore': 1.0,
                'durrës': 0.9,
                'durres': 0.9,
                'saranda': 1.1
            }
            
            location_key = property_analysis.property_location.lower().split(',')[0]
            location_multiplier = location_multipliers.get(location_key, 1.0)
            
            # Adjust based on property type
            type_multipliers = {
                'apartment': 1.0,
                'villa': 1.3,
                'commercial': 1.1,
                'office': 0.9,
                'studio': 0.8
            }
            
            type_multiplier = type_multipliers.get(property_analysis.property_type, 1.0)
            
            base_estimate = (conservative_estimate + optimistic_estimate) / 2
            adjusted_estimate = base_estimate * location_multiplier * type_multiplier
            
            return round(adjusted_estimate, 0)
            
        except Exception as e:
            logger.error(f"Error estimating rent: {e}")
            return float(property_analysis.asking_price) * 0.006  # Default 0.6%
    
    def _calculate_location_appreciation_rate(self, location: str) -> float:
        """Calculate location appreciation rate based on historical data with caching"""
        try:
            # Create cache key
            cache_key = f"appreciation_rate_{location}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Get price trends for location
            six_months_ago = timezone.now() - timedelta(days=180)
            
            recent_prices = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                created_at__gte=six_months_ago,
                status='completed',
                asking_price__gt=0,
                total_area__gt=0
            ).aggregate(
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area'))
            )['avg_price_per_sqm']
            
            older_prices = PropertyAnalysis.objects.filter(
                property_location__icontains=location,
                created_at__range=[six_months_ago - timedelta(days=90), six_months_ago],
                status='completed',
                asking_price__gt=0,
                total_area__gt=0
            ).aggregate(
                avg_price_per_sqm=Avg(F('asking_price') / F('total_area'))
            )['avg_price_per_sqm']
            
            if recent_prices and older_prices and older_prices > 0:
                appreciation = ((recent_prices - older_prices) / older_prices) * 100
                result = round(appreciation, 1)
            else:
                # Default appreciation rates by location
                default_rates = {
                    'tirana': 8.0,
                    'vlorë': 6.0,
                    'vlore': 6.0,
                    'durrës': 5.0,
                    'durres': 5.0,
                    'saranda': 7.0
                }
                
                location_key = location.lower()
                result = default_rates.get(location_key, 5.0)
            
            # Cache the result for 24 hours (appreciation rates change slowly)
            cache.set(cache_key, result, 86400)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating appreciation rate: {e}")
            return 5.0
    
    def _compare_to_market_averages(self, gross_yield: float, location: str) -> Dict:
        """Compare yields to market averages"""
        try:
            # Market average yields by location
            market_averages = {
                'tirana': 6.0,
                'vlorë': 5.5,
                'vlore': 5.5,
                'durrës': 5.0,
                'durres': 5.0,
                'saranda': 6.5
            }
            
            location_key = location.lower()
            market_avg = market_averages.get(location_key, 5.5)
            
            yield_difference = gross_yield - market_avg
            
            return {
                'market_average': market_avg,
                'yield_difference': yield_difference,
                'vs_market_percent': (yield_difference / market_avg) * 100 if market_avg > 0 else 0,
                'performance': 'above_market' if yield_difference > 0 else 'below_market'
            }
            
        except Exception as e:
            logger.error(f"Error comparing to market averages: {e}")
            return {}
    
    def _categorize_investment(self, gross_yield: float, total_return_5y: float) -> str:
        """Categorize investment based on returns"""
        if gross_yield >= 7.0 and total_return_5y >= 50:
            return 'excellent'
        elif gross_yield >= 6.0 and total_return_5y >= 35:
            return 'good'
        elif gross_yield >= 5.0 and total_return_5y >= 25:
            return 'moderate'
        else:
            return 'poor'
    
    def _calculate_risk_adjusted_return(self, gross_yield: float, appreciation: float) -> float:
        """Calculate risk-adjusted return"""
        # Simple risk adjustment based on yield stability and appreciation potential
        risk_score = min(100, gross_yield * 10 + appreciation * 2)
        return round(risk_score, 1)

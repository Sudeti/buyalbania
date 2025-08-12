# apps/property_ai/market_analytics.py
from django.db.models import Avg, Count, Q
from decimal import Decimal
from .models import PropertyAnalysis

class MarketAnalytics:
    """Calculate market averages and identify opportunities"""
    
    @staticmethod
    def get_market_averages(property_type=None, location=None, neighborhood=None):
        """Get average prices per sqm for market segments"""
        queryset = PropertyAnalysis.objects.filter(
            status='completed',
            asking_price__gt=0,
            total_area__gt=0  # Only properties with area data
        )
        
        # Apply filters
        if property_type:
            queryset = queryset.filter(property_type=property_type)
        if location:
            queryset = queryset.filter(property_location__icontains=location)
        if neighborhood:
            queryset = queryset.filter(neighborhood__icontains=neighborhood)
        
        # Calculate averages
        if queryset.exists():
            total_properties = queryset.count()
            avg_price = queryset.aggregate(avg=Avg('asking_price'))['avg']
            avg_area = queryset.aggregate(avg=Avg('total_area'))['avg']
            
            # Calculate price per sqm for each property, then average
            price_per_sqm_values = []
            for prop in queryset:
                if prop.price_per_sqm:
                    price_per_sqm_values.append(prop.price_per_sqm)
            
            avg_price_per_sqm = sum(price_per_sqm_values) / len(price_per_sqm_values) if price_per_sqm_values else 0
            
            return {
                'total_properties': total_properties,
                'avg_price': float(avg_price or 0),
                'avg_area': float(avg_area or 0),
                'avg_price_per_sqm': float(avg_price_per_sqm),
                'filters': {
                    'property_type': property_type,
                    'location': location,
                    'neighborhood': neighborhood
                }
            }
        
        return None
    
    @staticmethod
    def get_all_market_segments():
        """Get averages for all major market segments"""
        segments = {}
        
        # Major cities
        cities = ['Tirana', 'Durrës', 'Vlorë', 'Shkodër']
        
        # Property types
        property_types = ['apartment', 'villa', 'commercial', 'office']
        
        for city in cities:
            segments[city] = {}
            
            for prop_type in property_types:
                avg_data = MarketAnalytics.get_market_averages(
                    property_type=prop_type, 
                    location=city
                )
                if avg_data and avg_data['total_properties'] >= 3:  # Min 3 properties for reliable average
                    segments[city][prop_type] = avg_data
        
        return segments
    
    @staticmethod
    def get_neighborhood_averages(city):
        """Get averages by neighborhood within a city"""
        neighborhoods = PropertyAnalysis.objects.filter(
            property_location__icontains=city,
            neighborhood__isnull=False,
            status='completed'
        ).values_list('neighborhood', flat=True).distinct()
        
        neighborhood_data = {}
        
        for neighborhood in neighborhoods:
            if neighborhood:  # Skip empty neighborhoods
                for prop_type in ['apartment', 'villa', 'commercial']:
                    avg_data = MarketAnalytics.get_market_averages(
                        property_type=prop_type,
                        location=city,
                        neighborhood=neighborhood
                    )
                    if avg_data and avg_data['total_properties'] >= 2:  # Min 2 properties
                        if neighborhood not in neighborhood_data:
                            neighborhood_data[neighborhood] = {}
                        neighborhood_data[neighborhood][prop_type] = avg_data
        
        return neighborhood_data
    
    @staticmethod
    def identify_below_market_properties(threshold_percentage=15):
        """Find properties priced below market average"""
        opportunities = []
        
        # Get all completed properties
        properties = PropertyAnalysis.objects.filter(
            status='completed',
            asking_price__gt=0,
            total_area__gt=0
        )
        
        for prop in properties:
            # Get market average for this property's segment
            market_avg = MarketAnalytics.get_market_averages(
                property_type=prop.property_type,
                location=prop.property_location,
                neighborhood=prop.neighborhood
            )
            
            if market_avg and prop.price_per_sqm:
                market_price_per_sqm = market_avg['avg_price_per_sqm']
                property_price_per_sqm = prop.price_per_sqm
                
                # Calculate percentage below market
                if market_price_per_sqm > 0:
                    percentage_below = ((market_price_per_sqm - property_price_per_sqm) / market_price_per_sqm) * 100
                    
                    if percentage_below >= threshold_percentage:
                        opportunities.append({
                            'property': prop,
                            'property_price_per_sqm': property_price_per_sqm,
                            'market_avg_per_sqm': market_price_per_sqm,
                            'percentage_below_market': percentage_below,
                            'potential_savings': (market_price_per_sqm - property_price_per_sqm) * prop.total_area
                        })
        
        # Sort by percentage below market (highest savings first)
        opportunities.sort(key=lambda x: x['percentage_below_market'], reverse=True)
        
        return opportunities
    
    @staticmethod
    def get_property_market_position(property_analysis):
        """Get specific property's position vs market"""
        if not property_analysis.price_per_sqm:
            return None
        
        # City-level comparison
        city_avg = MarketAnalytics.get_market_averages(
            property_type=property_analysis.property_type,
            location=property_analysis.property_location
        )
        
        # Neighborhood-level comparison (if available)
        neighborhood_avg = None
        if property_analysis.neighborhood:
            neighborhood_avg = MarketAnalytics.get_market_averages(
                property_type=property_analysis.property_type,
                location=property_analysis.property_location,
                neighborhood=property_analysis.neighborhood
            )
        
        result = {
            'property_price_per_sqm': property_analysis.price_per_sqm,
            'city_comparison': None,
            'neighborhood_comparison': None
        }
        
        # City comparison
        if city_avg:
            city_market_price = city_avg['avg_price_per_sqm']
            if city_market_price > 0:
                city_diff_percentage = ((property_analysis.price_per_sqm - city_market_price) / city_market_price) * 100
                result['city_comparison'] = {
                    'market_avg_per_sqm': city_market_price,
                    'difference_percentage': city_diff_percentage,
                    'is_below_market': city_diff_percentage < 0,
                    'sample_size': city_avg['total_properties']
                }
        
        # Neighborhood comparison
        if neighborhood_avg:
            neighborhood_market_price = neighborhood_avg['avg_price_per_sqm']
            if neighborhood_market_price > 0:
                neighborhood_diff_percentage = ((property_analysis.price_per_sqm - neighborhood_market_price) / neighborhood_market_price) * 100
                result['neighborhood_comparison'] = {
                    'market_avg_per_sqm': neighborhood_market_price,
                    'difference_percentage': neighborhood_diff_percentage,
                    'is_below_market': neighborhood_diff_percentage < 0,
                    'sample_size': neighborhood_avg['total_properties']
                }
        
        return result
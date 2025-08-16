# apps/property_ai/views/admin_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from ..models import PropertyAnalysis
import logging

logger = logging.getLogger(__name__)

def is_superuser(user):
    """Check if user is superuser"""
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def agent_analytics(request):
    """Superuser-only view for agent analytics dashboard"""
    
    # Get all agents with their properties
    agents_data = PropertyAnalysis.objects.filter(
        agent_name__isnull=False
    ).exclude(
        agent_name=''
    ).values('agent_name').annotate(
        total_listings=Count('id'),
        avg_price=Avg('asking_price'),
        avg_investment_score=Avg('investment_score'),
        avg_price_per_sqm=Avg(
            ExpressionWrapper(
                F('asking_price') / Coalesce(F('internal_area'), F('total_area'), 1),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        premium_listings=Count('id', filter=Q(asking_price__gte=200000)),
        high_score_listings=Count('id', filter=Q(investment_score__gte=80)),
        completed_analyses=Count('id', filter=Q(status='completed')),
        active_listings=Count('id', filter=Q(is_active=True)),
    ).order_by('-total_listings')
    
    # Calculate additional metrics for each agent
    for agent in agents_data:
        # Difficulty coefficient (lower is easier to work with)
        if agent['total_listings'] > 0:
            # Calculate actual price consistency from agent's properties
            agent_properties = PropertyAnalysis.objects.filter(
                agent_name=agent['agent_name'],
                asking_price__gt=0
            )
            
            if agent_properties.count() > 1:
                # Calculate price variance as a measure of consistency
                prices = [float(p) for p in agent_properties.values_list('asking_price', flat=True)]
                avg_price = sum(prices) / len(prices)
                variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
                price_consistency = max(0, 1 - (variance / (avg_price ** 2)))  # Normalize variance
            else:
                price_consistency = 1.0  # Single property is considered consistent
            
            response_rate = agent['completed_analyses'] / agent['total_listings']
            listing_quality = agent['high_score_listings'] / agent['total_listings']
            
            # Calculate difficulty coefficient (0-1 scale, lower is easier)
            difficulty_coefficient = (
                (1 - price_consistency) * 0.3 +  # Price consistency weight
                (1 - response_rate) * 0.4 +      # Response rate weight (higher importance)
                (1 - listing_quality) * 0.3      # Listing quality weight
            )
            agent['difficulty_coefficient'] = round(difficulty_coefficient, 2)
        else:
            agent['difficulty_coefficient'] = 1.0
        
        # Agent rank based on multiple factors
        rank_score = (
            agent['total_listings'] * 0.3 +
            (agent['avg_investment_score'] or 0) * 0.2 +
            agent['high_score_listings'] * 0.3 +
            agent['completed_analyses'] * 0.2
        )
        agent['rank_score'] = round(rank_score, 2)
        
        # Contact info (get from first property)
        first_property = PropertyAnalysis.objects.filter(
            agent_name=agent['agent_name']
        ).first()
        agent['agent_email'] = first_property.agent_email if first_property else None
        agent['agent_phone'] = first_property.agent_phone if first_property else None
    
    # Sort by rank score
    agents_data = sorted(agents_data, key=lambda x: x['rank_score'], reverse=True)
    
    # Add rank numbers
    for i, agent in enumerate(agents_data):
        agent['rank'] = i + 1
    
    # Overall statistics
    total_agents = len(agents_data)
    total_listings = sum(agent['total_listings'] for agent in agents_data)
    avg_listings_per_agent = total_listings / total_agents if total_agents > 0 else 0
    
    context = {
        'agents': agents_data,
        'stats': {
            'total_agents': total_agents,
            'total_listings': total_listings,
            'avg_listings_per_agent': round(avg_listings_per_agent, 1),
            'top_agent': agents_data[0] if agents_data else None,
        }
    }
    
    return render(request, 'property_ai/admin/agent_analytics.html', context)

@login_required
@user_passes_test(is_superuser)
def property_rankings(request):
    """Superuser-only view for property rankings by various metrics"""
    
    # Get filter parameters
    location_filter = request.GET.get('location', '')
    property_type_filter = request.GET.get('property_type', '')
    ranking_type = request.GET.get('ranking_type', 'price_per_sqm')
    
    # Base queryset
    properties = PropertyAnalysis.objects.filter(
        status='completed',
        asking_price__gt=0
    )
    
    # Apply filters
    if location_filter:
        properties = properties.filter(property_location__icontains=location_filter)
    if property_type_filter:
        properties = properties.filter(property_type=property_type_filter)
    
    # Calculate rankings based on type
    if ranking_type == 'price_per_sqm':
        # Rank by price per square meter (ascending - best deals first)
        properties = properties.annotate(
            price_per_sqm=ExpressionWrapper(
                F('asking_price') / Coalesce(F('internal_area'), F('total_area'), 1),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).filter(
            price_per_sqm__gt=0
        ).order_by('price_per_sqm')
        
        ranking_title = "Best Price per Square Meter Deals"
        ranking_subtitle = "Properties with lowest €/m² (best value)"
        
    elif ranking_type == 'investment_score':
        # Rank by investment score (descending - highest scores first)
        properties = properties.filter(
            investment_score__isnull=False
        ).order_by('-investment_score')
        
        ranking_title = "Highest Investment Score Properties"
        ranking_subtitle = "Properties with best AI investment recommendations"
        
    elif ranking_type == 'market_position':
        # Rank by market position percentage (ascending - below market first)
        properties = properties.filter(
            market_position_percentage__isnull=False
        ).order_by('market_position_percentage')
        
        ranking_title = "Best Market Position Properties"
        ranking_subtitle = "Properties priced below market average"
        
    elif ranking_type == 'opportunity_score':
        # Rank by market opportunity score (descending - highest opportunity first)
        properties = properties.filter(
            market_opportunity_score__isnull=False
        ).order_by('-market_opportunity_score')
        
        ranking_title = "Highest Market Opportunity Properties"
        ranking_subtitle = "Properties with best market timing"
        
    else:
        # Default to price per sqm
        properties = properties.annotate(
            price_per_sqm=ExpressionWrapper(
                F('asking_price') / Coalesce(F('internal_area'), F('total_area'), 1),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).filter(
            price_per_sqm__gt=0
        ).order_by('price_per_sqm')
        
        ranking_title = "Best Price per Square Meter Deals"
        ranking_subtitle = "Properties with lowest €/m² (best value)"
    
    # Add rank numbers and limit to top 100
    ranked_properties = []
    for i, prop in enumerate(properties[:100]):
        prop_data = {
            'rank': i + 1,
            'id': prop.id,
            'title': prop.property_title,
            'location': prop.property_location,
            'neighborhood': prop.neighborhood,
            'price': prop.asking_price,
            'area': prop.internal_area or prop.total_area,
            'property_type': prop.property_type,
            'investment_score': prop.investment_score,
            'recommendation': prop.recommendation,
            'agent_name': prop.agent_name,
            'agent_email': prop.agent_email,
            'agent_phone': prop.agent_phone,
            'created_at': prop.created_at,
        }
        
        # Add ranking-specific data
        if ranking_type == 'price_per_sqm':
            prop_data['price_per_sqm'] = prop.price_per_sqm
        elif ranking_type == 'market_position':
            prop_data['market_position'] = prop.market_position_percentage
        elif ranking_type == 'opportunity_score':
            prop_data['opportunity_score'] = prop.market_opportunity_score
        
        # Calculate price per sqm for display if not already calculated
        if 'price_per_sqm' not in prop_data and prop_data['area']:
            try:
                prop_data['price_per_sqm'] = round(float(prop_data['price']) / float(prop_data['area']), 0)
            except (ValueError, ZeroDivisionError):
                prop_data['price_per_sqm'] = None
        
        ranked_properties.append(prop_data)
    
    # Get available locations and property types for filters
    locations = PropertyAnalysis.objects.values_list('property_location', flat=True).distinct()
    property_types = PropertyAnalysis.objects.values_list('property_type', flat=True).distinct()
    
    context = {
        'properties': ranked_properties,
        'ranking_title': ranking_title,
        'ranking_subtitle': ranking_subtitle,
        'ranking_type': ranking_type,
        'location_filter': location_filter,
        'property_type_filter': property_type_filter,
        'available_locations': sorted(set(locations)),
        'available_property_types': sorted(set(property_types)),
        'stats': {
            'total_ranked': len(ranked_properties),
            'location_count': len(locations),
            'property_type_count': len(property_types),
        }
    }
    
    return render(request, 'property_ai/admin/property_rankings.html', context)

@login_required
@user_passes_test(is_superuser)
def agent_api(request):
    """API endpoint for agent data (for AJAX requests)"""
    agent_name = request.GET.get('agent_name')
    
    if not agent_name:
        return JsonResponse({'error': 'Agent name required'}, status=400)
    
    # Get agent's properties
    agent_properties = PropertyAnalysis.objects.filter(
        agent_name=agent_name,
        status='completed'
    ).order_by('-created_at')
    
    # Calculate detailed stats
    stats = {
        'total_properties': agent_properties.count(),
        'avg_price': agent_properties.aggregate(avg=Avg('asking_price'))['avg'],
        'avg_investment_score': agent_properties.aggregate(avg=Avg('investment_score'))['avg'],
        'high_score_count': agent_properties.filter(investment_score__gte=80).count(),
        'strong_buy_count': agent_properties.filter(recommendation='strong_buy').count(),
        'buy_count': agent_properties.filter(recommendation='buy').count(),
        'hold_count': agent_properties.filter(recommendation='hold').count(),
        'avoid_count': agent_properties.filter(recommendation='avoid').count(),
    }
    
    # Get recent properties
    recent_properties = agent_properties[:10].values(
        'id', 'property_title', 'property_location', 'asking_price', 
        'investment_score', 'recommendation', 'created_at'
    )
    
    return JsonResponse({
        'agent_name': agent_name,
        'stats': stats,
        'recent_properties': list(recent_properties)
    })

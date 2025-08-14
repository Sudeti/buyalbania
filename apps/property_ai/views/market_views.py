# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from ..models import PropertyAnalysis
from django.utils import timezone
from ..market_analytics import MarketAnalytics

@login_required
def market_overview(request):
    """Market overview with tier restrictions - PRESERVING ALL EXISTING FEATURES"""
    
    # Get ALL market statistics first (same as before)
    total_properties = PropertyAnalysis.objects.filter(status='completed').count()
    
    # By location (keep existing)
    location_stats = PropertyAnalysis.objects.filter(status='completed').values('property_location').annotate(
        count=Count('id'),
        avg_price=Avg('asking_price'),
        avg_score=Avg('investment_score')
    ).order_by('-count')[:10]
    
    # By property type (keep existing)
    type_stats = PropertyAnalysis.objects.filter(status='completed').values('property_type').annotate(
        count=Count('id'),
        avg_price=Avg('asking_price'),
        avg_score=Avg('investment_score')
    ).order_by('-count')
    
    # Simple removal analytics (keep existing)
    removed_properties = PropertyAnalysis.objects.filter(is_active=False)
    
    # Average days on market (keep existing)
    if removed_properties.exists():
        avg_days_on_market = sum(prop.days_on_market for prop in removed_properties) / removed_properties.count()
    else:
        avg_days_on_market = 0
    
    # Recently removed (keep existing)
    recently_removed = removed_properties.filter(
        removed_date__gte=timezone.now() - timezone.timedelta(days=30)
    ).count()

    # Keep all existing market analytics
    market_segments = MarketAnalytics.get_all_market_segments()
    opportunities = MarketAnalytics.identify_below_market_properties(threshold_percentage=10)[:20]
    tirana_neighborhoods = MarketAnalytics.get_neighborhood_averages('Tirana')

    # NOW ADD: Tier-based filtering for what user can actually see
    if not request.user.is_authenticated:
        # Anonymous users see aggregate stats but no individual properties
        visible_opportunities = []
        user_tier = 'anonymous'
        tier_message = 'Sign up to see individual property analyses!'
        user_can_see_count = 0
    elif not hasattr(request.user, 'profile'):
        # User without profile - redirect them
        messages.error(request, 'Please complete your profile.')
        return redirect('accounts:user_profile')
    else:
        profile = request.user.profile
        user_tier = profile.subscription_tier
        
        if profile.subscription_tier == 'free':
            # Free users see their own analyses only in the opportunities list
            visible_opportunities = [opp for opp in opportunities if opp['property'].user == request.user]
            user_can_see_count = PropertyAnalysis.objects.filter(user=request.user, status='completed').count()
            tier_message = f"You have {profile.remaining_analyses} free analysis remaining this month. Showing your {user_can_see_count} properties."
        elif profile.subscription_tier == 'basic':
            # Basic users see good properties (60+) in opportunities
            visible_opportunities = [opp for opp in opportunities if (opp['property'].investment_score or 0) >= 60 or opp['property'].user == request.user]
            user_can_see_count = PropertyAnalysis.objects.filter(
                Q(investment_score__gte=60) | Q(user=request.user),
                status='completed'
            ).distinct().count()
            tier_message = f"Showing {len(visible_opportunities)} good investment opportunities. {profile.remaining_analyses} analyses remaining."
        else:  # premium
            # Premium sees everything
            visible_opportunities = opportunities
            user_can_see_count = total_properties
            tier_message = f"Premium access: Showing all {len(visible_opportunities)} investment opportunities. Unlimited analyses."

    # Also filter top_opportunities for display based on tier
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile
        if profile.subscription_tier == 'free':
            top_opportunities = PropertyAnalysis.objects.filter(
                user=request.user,
                status='completed',
                investment_score__gte=75
            ).order_by('-investment_score')[:10]
        elif profile.subscription_tier == 'basic':
            top_opportunities = PropertyAnalysis.objects.filter(
                status='completed',
                investment_score__gte=75
            ).filter(
                Q(investment_score__gte=60) | Q(user=request.user)
            ).order_by('-investment_score')[:10]
        else:
            top_opportunities = PropertyAnalysis.objects.filter(
                status='completed',
                investment_score__gte=75
            ).order_by('-investment_score')[:10]
    else:
        # Anonymous users see no individual properties
        top_opportunities = PropertyAnalysis.objects.none()

    # Build context with ALL existing data PLUS tier info
    context = {
        # KEEP ALL EXISTING ANALYTICS
        'total_properties': total_properties,
        'location_stats': location_stats,
        'type_stats': type_stats,
        'total_removed': removed_properties.count(),
        'avg_days_on_market': round(avg_days_on_market, 1),
        'recently_removed': recently_removed,
        'market_segments': market_segments,
        'tirana_neighborhoods': tirana_neighborhoods,
        
        # TIER-FILTERED DATA
        'top_opportunities': top_opportunities,
        'opportunities': visible_opportunities,
        
        # NEW TIER INFO
        'user_tier': user_tier,
        'tier_message': tier_message,
        'user_can_see_count': user_can_see_count,
        'remaining_analyses': getattr(request.user, 'profile', None) and request.user.profile.remaining_analyses or 0,
    }
    
    return render(request, 'property_ai/market_overview.html', context)


def market_analytics_api(request):
    """API endpoint for market analytics"""
    property_type = request.GET.get('type')
    location = request.GET.get('location')
    neighborhood = request.GET.get('neighborhood')
    
    market_data = MarketAnalytics.get_market_averages(
        property_type=property_type,
        location=location,
        neighborhood=neighborhood
    )
    
    return JsonResponse(market_data or {'error': 'No data available'})
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from ..models import PropertyAnalysis
from ..analytics import PropertyAnalytics
import logging

logger = logging.getLogger(__name__)

@login_required
def analytics_dashboard(request):
    """Comprehensive analytics dashboard for users"""
    # Check if user has access to analytics
    user_tier = request.user.profile.subscription_tier
    if user_tier == 'free':
        # Get subscription plans for upgrade buttons
        from apps.payments.models import SubscriptionPlan
        subscription_plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
        
        return render(request, 'property_ai/analytics_locked.html', {
            'user_tier': user_tier,
            'subscription_plans': subscription_plans,
        })
    
    try:
        analytics = PropertyAnalytics()
        
        # Get user's analyses - include all properties, not just completed ones
        user_analyses = PropertyAnalysis.objects.filter(
            user=request.user
        ).order_by('-created_at')
        
        # Portfolio analytics - handle both analyzed and unanalyzed properties
        portfolio_stats = {
            'total_analyses': user_analyses.count(),
            'completed_analyses': user_analyses.filter(status='completed').count(),
            'analyzing_count': user_analyses.filter(status='analyzing').count(),
            'failed_count': user_analyses.filter(status='failed').count(),
            'avg_investment_score': user_analyses.filter(status='completed').aggregate(avg=Avg('investment_score'))['avg'],
            'avg_opportunity_score': user_analyses.filter(status='completed').aggregate(avg=Avg('market_opportunity_score'))['avg'],
            'strong_buys': user_analyses.filter(status='completed', recommendation='strong_buy').count(),
            'high_leverage_count': user_analyses.filter(status='completed', negotiation_leverage='high').count(),
            'below_market_count': user_analyses.filter(status='completed', market_position_percentage__lt=0).count(),
        }
        
        # Calculate basic opportunity indicators for unanalyzed properties
        unanalyzed_properties = user_analyses.filter(status__in=['analyzing', 'failed'])
        basic_opportunity_count = 0
        
        for prop in unanalyzed_properties[:10]:  # Check first 10 for performance
            basic_metrics = analytics.get_basic_property_metrics(prop)
            if basic_metrics.get('opportunity_indicators'):
                basic_opportunity_count += 1
        
        portfolio_stats['basic_opportunity_count'] = basic_opportunity_count
        
        # Market summary - include unanalyzed properties
        market_summary = analytics.get_market_summary(include_unanalyzed=True)
        
        # Location breakdown - include all properties
        location_stats = user_analyses.values('property_location').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed')),
            avg_score=Avg('investment_score'),
            avg_opportunity=Avg('market_opportunity_score'),
            avg_price=Avg('asking_price')
        ).order_by('-count')[:5]
        
        # Property type breakdown - include all properties
        type_stats = user_analyses.values('property_type').annotate(
            count=Count('id'),
            completed_count=Count('id', filter=Q(status='completed')),
            avg_score=Avg('investment_score'),
            avg_opportunity=Avg('market_opportunity_score'),
            avg_price=Avg('asking_price')
        ).order_by('-count')
        
        # Recent market trends - include unanalyzed properties
        recent_analyses = user_analyses[:10]
        recent_trends = []
        for analysis in recent_analyses:
            location = analysis.property_location.split(',')[0]
            trends = analytics.get_price_trends(location, analysis.property_type, months=3, include_unanalyzed=True)
            if trends:
                recent_trends.append({
                    'property': analysis.property_title,
                    'location': location,
                    'status': analysis.status,
                    'trends': trends
                })
        
        # Analysis status breakdown
        status_breakdown = {
            'completed': portfolio_stats['completed_analyses'],
            'analyzing': portfolio_stats['analyzing_count'],
            'failed': portfolio_stats['failed_count'],
            'completion_rate': (portfolio_stats['completed_analyses'] / portfolio_stats['total_analyses']) * 100 if portfolio_stats['total_analyses'] > 0 else 0
        }
        
        context = {
            'portfolio_stats': portfolio_stats,
            'market_summary': market_summary,
            'location_stats': location_stats,
            'type_stats': type_stats,
            'recent_trends': recent_trends[:5],
            'status_breakdown': status_breakdown,
            'user_tier': request.user.profile.subscription_tier,
        }
        
        return render(request, 'property_ai/analytics_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in analytics dashboard: {e}")
        return render(request, 'property_ai/analytics_dashboard.html', {
            'error': 'Unable to load analytics data'
        })

@login_required
def market_insights_api(request):
    """API endpoint for market insights data"""
    # Check if user has access to analytics
    if request.user.profile.subscription_tier == 'free':
        return JsonResponse({'error': 'Analytics access requires a paid plan'}, status=403)
    
    try:
        location = request.GET.get('location', '')
        property_type = request.GET.get('property_type', '')
        include_unanalyzed = request.GET.get('include_unanalyzed', 'true').lower() == 'true'
        
        analytics = PropertyAnalytics()
        
        if location:
            # Get location-specific insights
            market_stats = analytics.get_location_market_stats(location, property_type, include_unanalyzed=include_unanalyzed)
            price_trends = analytics.get_price_trends(location, property_type, months=6, include_unanalyzed=include_unanalyzed)
            
            data = {
                'market_stats': market_stats,
                'price_trends': price_trends,
                'location': location,
                'property_type': property_type,
                'include_unanalyzed': include_unanalyzed
            }
        else:
            # Get general market summary
            data = analytics.get_market_summary(include_unanalyzed=include_unanalyzed)
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error in market insights API: {e}")
        return JsonResponse({'error': 'Unable to load market insights'}, status=500)

@login_required
def opportunity_analysis_api(request, analysis_id):
    """API endpoint for detailed opportunity analysis"""
    # Check if user has access to analytics
    if request.user.profile.subscription_tier == 'free':
        return JsonResponse({'error': 'Analytics access requires a paid plan'}, status=403)
    
    try:
        analysis = PropertyAnalysis.objects.get(id=analysis_id, user=request.user)
        analytics = PropertyAnalytics()
        
        # Get opportunity analysis (works for both analyzed and unanalyzed properties)
        opportunity_analysis = analytics.get_market_opportunity_score(analysis)
        
        # Get basic metrics for unanalyzed properties
        basic_metrics = {}
        if analysis.status != 'completed':
            basic_metrics = analytics.get_basic_property_metrics(analysis)
        
        # Get comparable analysis (include unanalyzed properties)
        comparable_analysis = analytics.get_comparable_analysis(analysis, include_unanalyzed=True)
        
        # Get negotiation insights (only for completed analyses)
        negotiation_insights = {}
        if analysis.status == 'completed':
            negotiation_insights = analytics.get_negotiation_insights(analysis)
        
        data = {
            'opportunity_analysis': opportunity_analysis,
            'basic_metrics': basic_metrics,
            'comparable_analysis': comparable_analysis,
            'negotiation_insights': negotiation_insights,
            'property_id': analysis_id,
            'analysis_status': analysis.status
        }
        
        return JsonResponse(data)
        
    except PropertyAnalysis.DoesNotExist:
        return JsonResponse({'error': 'Analysis not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in opportunity analysis API: {e}")
        return JsonResponse({'error': 'Unable to load opportunity analysis'}, status=500)

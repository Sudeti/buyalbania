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
    try:
        analytics = PropertyAnalytics()
        
        # Get user's analyses
        user_analyses = PropertyAnalysis.objects.filter(
            user=request.user, 
            status='completed'
        ).order_by('-created_at')
        
        # Portfolio analytics
        portfolio_stats = {
            'total_analyses': user_analyses.count(),
            'avg_investment_score': user_analyses.aggregate(avg=Avg('investment_score'))['avg'],
            'avg_opportunity_score': user_analyses.aggregate(avg=Avg('market_opportunity_score'))['avg'],
            'strong_buys': user_analyses.filter(recommendation='strong_buy').count(),
            'high_leverage_count': user_analyses.filter(negotiation_leverage='high').count(),
            'below_market_count': user_analyses.filter(market_position_percentage__lt=0).count(),
        }
        
        # Market summary
        market_summary = analytics.get_market_summary()
        
        # Location breakdown
        location_stats = user_analyses.values('property_location').annotate(
            count=Count('id'),
            avg_score=Avg('investment_score'),
            avg_opportunity=Avg('market_opportunity_score'),
            avg_price=Avg('asking_price')
        ).order_by('-count')[:5]
        
        # Property type breakdown
        type_stats = user_analyses.values('property_type').annotate(
            count=Count('id'),
            avg_score=Avg('investment_score'),
            avg_opportunity=Avg('market_opportunity_score'),
            avg_price=Avg('asking_price')
        ).order_by('-count')
        
        # Recent market trends
        recent_analyses = user_analyses[:10]
        recent_trends = []
        for analysis in recent_analyses:
            location = analysis.property_location.split(',')[0]
            trends = analytics.get_price_trends(location, analysis.property_type, months=3)
            if trends:
                recent_trends.append({
                    'property': analysis.property_title,
                    'location': location,
                    'trends': trends
                })
        
        context = {
            'portfolio_stats': portfolio_stats,
            'market_summary': market_summary,
            'location_stats': location_stats,
            'type_stats': type_stats,
            'recent_trends': recent_trends[:5],
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
    try:
        location = request.GET.get('location', '')
        property_type = request.GET.get('property_type', '')
        
        analytics = PropertyAnalytics()
        
        if location:
            # Get location-specific insights
            market_stats = analytics.get_location_market_stats(location, property_type)
            price_trends = analytics.get_price_trends(location, property_type, months=6)
            
            data = {
                'market_stats': market_stats,
                'price_trends': price_trends,
                'location': location,
                'property_type': property_type
            }
        else:
            # Get general market summary
            data = analytics.get_market_summary()
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error in market insights API: {e}")
        return JsonResponse({'error': 'Unable to load market insights'}, status=500)

@login_required
def opportunity_analysis_api(request, analysis_id):
    """API endpoint for detailed opportunity analysis"""
    try:
        analysis = PropertyAnalysis.objects.get(id=analysis_id, user=request.user)
        analytics = PropertyAnalytics()
        
        opportunity_analysis = analytics.get_market_opportunity_score(analysis)
        negotiation_insights = analytics.get_negotiation_insights(analysis)
        comparable_analysis = analytics.get_comparable_analysis(analysis)
        
        data = {
            'opportunity_analysis': opportunity_analysis,
            'negotiation_insights': negotiation_insights,
            'comparable_analysis': comparable_analysis,
            'property_id': analysis_id
        }
        
        return JsonResponse(data)
        
    except PropertyAnalysis.DoesNotExist:
        return JsonResponse({'error': 'Analysis not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in opportunity analysis API: {e}")
        return JsonResponse({'error': 'Unable to load opportunity analysis'}, status=500)

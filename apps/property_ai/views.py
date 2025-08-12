# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from .models import PropertyAnalysis
from .ai_engine import PropertyAI
from .scrapers import Century21AlbaniaScraper
import logging
from django.http import FileResponse
import os
from django.utils import timezone
from .market_analytics import MarketAnalytics

logger = logging.getLogger(__name__)

def home(request):
    """Property analysis home page with sale focus"""
    # Get some stats for the homepage
    total_analyses = PropertyAnalysis.objects.filter(status='completed').count()
    avg_score = PropertyAnalysis.objects.filter(
        status='completed', 
        investment_score__isnull=False
    ).aggregate(avg_score=Avg('investment_score'))['avg_score']
    
    # Recent high-scoring properties
    featured_properties = PropertyAnalysis.objects.filter(
        status='completed',
        investment_score__gte=75
    ).order_by('-investment_score')[:3]
    
    context = {
        'features': [
            'AI-powered investment analysis for sale properties',
            'Albanian real estate market insights',
            'Rental yield calculations',
            'Risk assessment & ROI projections',
            'Instant property evaluation',
            'Investment recommendations'
        ],
        'stats': {
            'total_analyses': total_analyses,
            'avg_score': round(avg_score or 0, 1),
        },
        'featured_properties': featured_properties,
    }
    return render(request, 'property_ai/home.html', context)

@require_http_methods(["GET", "POST"])
def analyze_property(request):
    """Analyze property with strict quota enforcement"""
    if request.method == 'GET':
        # Show quota info on the form
        quota_info = {}
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            profile = request.user.profile
            quota_info = {
                'tier': profile.subscription_tier,
                'remaining': profile.remaining_analyses,
                'can_analyze': profile.can_analyze_property()
            }
        
        return render(request, 'property_ai/analyze_form.html', {'quota_info': quota_info})
    
    # Require login for ANY analysis
    if not request.user.is_authenticated:
        messages.error(request, 'Please create an account to analyze properties.')
        return redirect('accounts:register')
    
    # Check quota BEFORE scraping
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'Please complete your profile setup.')
        return redirect('accounts:user_profile')
    
    profile = request.user.profile
    if not profile.can_analyze_property():
        tier_info = {
            'free': 'You\'ve used your 1 free analysis this month. Upgrade to Basic (€5) for 10 analyses per month!',
            'basic': 'You\'ve used all 10 analyses this month. Upgrade to Premium (€15) for unlimited analyses!',
        }
        messages.error(request, tier_info.get(profile.subscription_tier, 'Analysis quota exceeded.'))
        return redirect('property_ai:analyze_property')
    
    property_url = request.POST.get('property_url', '').strip()
    
    if not property_url:
        messages.error(request, 'Please provide a property URL')
        return redirect('property_ai:analyze_property')
    
    # Check if user has already analyzed this property
    existing_user_analysis = PropertyAnalysis.objects.filter(
        property_url=property_url, 
        user=request.user
    ).first()
    
    if existing_user_analysis:
        messages.info(request, 'You have already analyzed this property.')
        return redirect('property_ai:analysis_detail', analysis_id=existing_user_analysis.id)
    
    # Check if property exists globally (but user can't see others' analyses)
    existing_global_analysis = PropertyAnalysis.objects.filter(property_url=property_url).first()
    
    try:
        # If property exists globally, create a new user-specific analysis
        if existing_global_analysis:
            # Use existing scraped data but create new analysis for this user
            analysis = PropertyAnalysis.objects.create(
                user=request.user,
                scraped_by=request.user,
                property_url=property_url,
                property_title=existing_global_analysis.property_title,
                property_location=existing_global_analysis.property_location,
                neighborhood=existing_global_analysis.neighborhood,
                asking_price=existing_global_analysis.asking_price,
                property_type=existing_global_analysis.property_type,
                total_area=existing_global_analysis.total_area,
                property_condition=existing_global_analysis.property_condition,
                floor_level=existing_global_analysis.floor_level,
                status='analyzing'
            )
            
            messages.info(request, 'Using existing property data. Running your personalized analysis...')
        else:
            # Scrape new property
            scraper = Century21AlbaniaScraper()
            property_data = scraper.scrape_property(property_url)
            
            if not property_data:
                messages.error(request, 'Could not access this property.')
                return redirect('property_ai:analyze_property')
            
            analysis = PropertyAnalysis.objects.create(
                user=request.user,
                scraped_by=request.user,
                property_url=property_url,
                property_title=property_data['title'],
                property_location=property_data['location'],
                neighborhood=property_data.get('neighborhood', ''),
                asking_price=property_data['price'],
                property_type=property_data['property_type'],
                total_area=property_data.get('square_meters'),
                property_condition=property_data.get('condition', ''),
                floor_level=property_data.get('floor_level', ''),
                status='analyzing'
            )
        
        # CONSUME QUOTA BEFORE RUNNING ANALYSIS
        if not profile.use_analysis_quota():
            messages.error(request, 'Could not consume analysis quota. Please try again.')
            analysis.delete()  # Clean up
            return redirect('property_ai:analyze_property')
        
        # Run AI analysis
        ai = PropertyAI()
        comparable_properties = get_comparable_properties(analysis)
        
        analysis_data = {
            'title': analysis.property_title,
            'location': analysis.property_location,
            'neighborhood': analysis.neighborhood,
            'price': float(analysis.asking_price),
            'property_type': analysis.property_type,
            'square_meters': analysis.total_area,
            'condition': analysis.property_condition,
            'floor_level': analysis.floor_level,
        }
        
        result = ai.analyze_property(analysis_data, comparable_properties)
        
        if result.get('status') == 'success':
            analysis.analysis_result = result
            analysis.ai_summary = result.get('summary', '')
            analysis.investment_score = result.get('investment_score')
            analysis.recommendation = result.get('recommendation')
            analysis.status = 'completed'
            analysis.save()
            
            messages.success(request, f'Analysis complete! You have {profile.remaining_analyses} analyses remaining this month.')
            return redirect('property_ai:analysis_detail', analysis_id=analysis.id)
        else:
            analysis.status = 'failed'
            analysis.save()
            messages.error(request, 'Analysis failed. Your quota has not been consumed.')
            # Refund the quota since analysis failed
            profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
            profile.save()
            return redirect('property_ai:analyze_property')
            
    except Exception as e:
        logger.error(f"Error analyzing property {property_url}: {e}")
        messages.error(request, 'Error accessing property. Please try again.')
        return redirect('property_ai:analyze_property')

# apps/property_ai/views.py - Update my_analyses view
@login_required
def my_analyses(request):
    """Show analyses based on user tier"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'Please complete your profile.')
        return redirect('accounts:user_profile')
    
    profile = request.user.profile
    
    if profile.subscription_tier == 'free':
        analyses = PropertyAnalysis.objects.filter(user=request.user).order_by('-created_at')
        available_count = analyses.count()
    elif profile.subscription_tier == 'basic':
        all_good_analyses = PropertyAnalysis.objects.filter(
            status='completed',
            investment_score__gte=60
        )
        own_analyses = PropertyAnalysis.objects.filter(user=request.user)
        analyses = (all_good_analyses | own_analyses).distinct().order_by('-created_at')
        available_count = analyses.count()
    else:  # premium
        analyses = PropertyAnalysis.objects.filter(status='completed').order_by('-created_at')
        available_count = analyses.count()
    
    # ADD: Calculate stats
    completed_analyses = analyses.filter(status='completed')
    stats = {
        'total': analyses.count(),
        'completed': completed_analyses.count(),
        'avg_score': completed_analyses.aggregate(avg=Avg('investment_score'))['avg'],
        'strong_buys': completed_analyses.filter(investment_score__gte=80).count(),
    }
    
    context = {
        'analyses': analyses[:50],  # Paginate
        'user_tier': profile.subscription_tier,
        'remaining_analyses': profile.remaining_analyses,
        'total_available': available_count,
        'quota_used': profile.monthly_analyses_used,
        'stats': stats,  # ADD this
    }
    return render(request, 'property_ai/my_analyses.html', context)

def get_comparable_properties(analysis):
    """Get comparable properties for analysis context"""
    try:
        # Find similar properties in same location and type
        comparables = PropertyAnalysis.objects.filter(
            property_location__icontains=analysis.property_location.split(',')[0],  # Main city
            property_type=analysis.property_type,
            status='completed',
            asking_price__gt=0
        ).exclude(id=analysis.id)
        
        # Filter by similar size if available
        if analysis.usable_area:
            size_range = analysis.usable_area * 0.3  # ±30% size difference
            comparables = comparables.filter(
                Q(total_area__range=(analysis.usable_area - size_range, analysis.usable_area + size_range)) |
                Q(internal_area__range=(analysis.usable_area - size_range, analysis.usable_area + size_range))
            )
        
        # Get top 5 most recent comparables
        comparables = comparables.order_by('-created_at')[:5]
        
        comparable_data = []
        for comp in comparables:
            comparable_data.append({
                'title': comp.property_title,
                'location': comp.property_location,
                'price': float(comp.asking_price),
                'area': comp.usable_area,
                'price_per_sqm': comp.price_per_sqm,
                'investment_score': comp.investment_score,
                'recommendation': comp.recommendation,
            })
        
        return comparable_data
        
    except Exception as e:
        logger.error(f"Error getting comparable properties: {e}")
        return []

# apps/property_ai/views.py - UPDATE analysis_detail:
def analysis_detail(request, analysis_id):
    """Display investment analysis results with access control"""
    analysis = get_object_or_404(PropertyAnalysis, id=analysis_id)
    
    # CHECK ACCESS CONTROL
    if request.user.is_authenticated:
        if not analysis.is_available_to_user(request.user):
            messages.error(request, 'You do not have access to this analysis. Upgrade your account for more access!')
            return redirect('property_ai:home')
    else:
        # Anonymous users can't see any analysis
        messages.error(request, 'Please log in to view property analyses.')
        return redirect('accounts:login')
    
    # Get similar properties for comparison (also filtered by tier)
    similar_properties = PropertyAnalysis.objects.filter(
        property_location__icontains=analysis.property_location.split(',')[0],
        property_type=analysis.property_type,
        status='completed'
    ).exclude(id=analysis.id)
    
    # Filter similar properties by user tier too
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        accessible_similar = [prop for prop in similar_properties if prop.is_available_to_user(request.user)]
        similar_properties = accessible_similar[:3]
    else:
        similar_properties = []
    
    context = {
        'analysis': analysis,
        'property_analysis': analysis,  # For template compatibility
        'similar_properties': similar_properties,
        'show_comparison': len(similar_properties) > 0,
    }
    
    return render(request, 'property_ai/analysis_detail.html', context)

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

# NEW: Market analytics API endpoint
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

@login_required
def download_report(request, analysis_id):
    """Download PDF report"""
    analysis = get_object_or_404(PropertyAnalysis, id=analysis_id, user=request.user)
    
    if analysis.report_generated and analysis.report_file_path:
        if os.path.exists(analysis.report_file_path):
            return FileResponse(
                open(analysis.report_file_path, 'rb'),
                as_attachment=True,
                filename=f"PropertyReport_{analysis_id[:8]}.pdf"
            )
    
    messages.error(request, 'Report not available for download.')
    return redirect('property_ai:analysis_detail', analysis_id=analysis_id)
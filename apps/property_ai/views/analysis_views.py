# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from ..models import PropertyAnalysis
from ..ai_engine import PropertyAI
from ..scrapers import Century21AlbaniaScraper
import logging



logger = logging.getLogger(__name__)


@login_required
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

                agent_name=existing_global_analysis.agent_name,
                agent_email=existing_global_analysis.agent_email,
                agent_phone=existing_global_analysis.agent_phone,
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

                agent_name=property_data.get('agent_name', ''),
                agent_email=property_data.get('agent_email', ''),
                agent_phone=property_data.get('agent_phone', ''),
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

@login_required
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
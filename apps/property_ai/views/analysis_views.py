# Updated views.py - Sale properties workflow
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import timedelta
from ..models import PropertyAnalysis
from ..ai_engine import PropertyAI
from ..scrapers import Century21AlbaniaScraper
from ..utils import standardize_property_url
import logging
from decimal import Decimal


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
    property_url = request.POST.get('property_url', '').strip()
    
    if not property_url:
        messages.error(request, 'Please provide a property URL')
        return redirect('property_ai:analyze_property')
    
    # Standardize the URL to avoid duplicates (remove /en prefix, etc.)
    original_url = property_url
    property_url = standardize_property_url(property_url)
    
    if original_url != property_url:
        logger.info(f"URL standardized: {original_url} -> {property_url}")
    
    # Check if user has already analyzed this property (using standardized URL)
    existing_user_analysis = PropertyAnalysis.objects.filter(
        property_url=property_url, 
        user=request.user
    ).first()

    if existing_user_analysis:
        if existing_user_analysis.status == 'completed':
            messages.info(request, 'You have already analyzed this property.')
            return redirect('property_ai:analysis_detail', analysis_id=existing_user_analysis.id)
        elif existing_user_analysis.status == 'failed':
            # Allow retry of failed analysis - but need to check quota first
            if not profile.can_analyze_property():
                logger.debug(f"User {request.user.username} quota exceeded for retry. Tier: {profile.subscription_tier}, Used: {profile.monthly_analyses_used}")
                tier_info = {
                    'free': 'You\'ve used your 1 free analysis this month. You can still access existing analyses without using quota. Upgrade to Basic (€5) for 10 analyses per month!',
                    'basic': 'You\'ve used all 10 analyses this month. You can still access existing analyses without using quota. Upgrade to Premium (€15) for unlimited analyses!',
                }
                messages.error(request, tier_info.get(profile.subscription_tier, 'Analysis quota exceeded.'))
                return redirect('property_ai:analyze_property')
            
            messages.info(request, 'Retrying failed analysis...')
            existing_user_analysis.status = 'analyzing'  # Reset status
            existing_user_analysis.save()
            analysis = existing_user_analysis  # Reuse the existing record
            # Continue with the analysis flow below
        elif existing_user_analysis.status == 'analyzing':
            messages.warning(request, 'Analysis already in progress. Please wait.')
            return redirect('property_ai:analysis_detail', analysis_id=existing_user_analysis.id)
    
    # Check if property exists globally (using standardized URL)
    existing_global_analysis = PropertyAnalysis.objects.filter(property_url=property_url).first()
    
    logger.debug(f"User {request.user.username} (tier: {profile.subscription_tier}) analyzing {property_url}")
    logger.debug(f"Existing global analysis: {existing_global_analysis is not None}")
    if existing_global_analysis:
        logger.debug(f"Global analysis status: {existing_global_analysis.status}, created: {existing_global_analysis.created_at}")
    
    # If there's a completed analysis globally, handle it properly
    if existing_global_analysis and existing_global_analysis.status == 'completed':
        logger.debug(f"User {request.user.username} accessing existing global analysis")
        
        # Check if user has access to this analysis based on their tier
        if existing_global_analysis.is_available_to_user(request.user):
            
            # Check if analysis is older than 2 weeks
            analysis_age = timezone.now() - existing_global_analysis.created_at
            if analysis_age.days > 14:
                # Analysis is old, check if user has quota to regenerate
                if profile.can_analyze_property():
                    messages.info(request, 'Analysis is older than 2 weeks. Regenerating with fresh data...')
                    existing_global_analysis.user = request.user
                    existing_global_analysis.status = 'analyzing'
                    existing_global_analysis.save()
                    analysis = existing_global_analysis
                    # Continue with analysis flow below
                else:
                    messages.warning(request, 'Analysis is older than 2 weeks, but you\'ve used your quota. You can still view the existing analysis.')
                    return redirect('property_ai:analysis_detail', analysis_id=existing_global_analysis.id)
            else:
                # Analysis is recent, send PDF report
                from ..tasks import generate_property_report_task
                try:
                    # Create a copy for this user to get PDF
                    user_analysis = PropertyAnalysis.objects.create(
                        user=request.user,
                        scraped_by=existing_global_analysis.scraped_by,
                        property_url=existing_global_analysis.property_url,
                        property_title=existing_global_analysis.property_title,
                        property_location=existing_global_analysis.property_location,
                        neighborhood=existing_global_analysis.neighborhood,
                        asking_price=existing_global_analysis.asking_price,
                        property_type=existing_global_analysis.property_type,
                        total_area=existing_global_analysis.total_area,
                        internal_area=existing_global_analysis.internal_area,
                        bedrooms=existing_global_analysis.bedrooms,
                        bathrooms=existing_global_analysis.bathrooms,
                        floor_level=existing_global_analysis.floor_level,
                        ceiling_height=existing_global_analysis.ceiling_height,
                        facade_length=existing_global_analysis.facade_length,
                        property_condition=existing_global_analysis.property_condition,
                        furnished=existing_global_analysis.furnished,
                        has_elevator=existing_global_analysis.has_elevator,
                        description=existing_global_analysis.description,
                        agent_name=existing_global_analysis.agent_name,
                        agent_email=existing_global_analysis.agent_email,
                        agent_phone=existing_global_analysis.agent_phone,
                        status='completed',
                        analysis_result=existing_global_analysis.analysis_result,
                        ai_summary=existing_global_analysis.ai_summary,
                        investment_score=existing_global_analysis.investment_score,
                        recommendation=existing_global_analysis.recommendation,
                        market_opportunity_score=existing_global_analysis.market_opportunity_score,
                        price_percentile=existing_global_analysis.price_percentile,
                        market_position_percentage=existing_global_analysis.market_position_percentage,
                        negotiation_leverage=existing_global_analysis.negotiation_leverage,
                        market_sentiment=existing_global_analysis.market_sentiment,
                    )
                    
                    generate_property_report_task.delay(user_analysis.id)
                    messages.success(request, 'Analysis found! A PDF report will be sent to your email shortly.')
                    
                except Exception as e:
                    logger.error(f"Error creating user analysis copy for PDF: {e}")
                    messages.success(request, 'Analysis found! You can access this property analysis without using your quota.')
                
                return redirect('property_ai:analysis_detail', analysis_id=existing_global_analysis.id)
        else:
            messages.error(request, 'This analysis exists but you need to upgrade your account to access it.')
            return redirect('property_ai:analyze_property')
    
    # If no existing analysis, inform user that a new analysis will be created
    if not existing_global_analysis:
        messages.info(request, 'No existing analysis found. Creating a new analysis for this property...')
    
    # Only check quota if we need to create a new analysis
    if not profile.can_analyze_property():
        logger.debug(f"User {request.user.username} quota exceeded. Tier: {profile.subscription_tier}, Used: {profile.monthly_analyses_used}")
        tier_info = {
            'free': 'You\'ve used your 1 free analysis this month. You can still access existing analyses without using quota. Upgrade to Basic (€5) for 10 analyses per month!',
            'basic': 'You\'ve used all 10 analyses this month. You can still access existing analyses without using quota. Upgrade to Premium (€15) for unlimited analyses!',
        }
        messages.error(request, tier_info.get(profile.subscription_tier, 'Analysis quota exceeded.'))
        return redirect('property_ai:analyze_property')
    
    logger.debug(f"User {request.user.username} can analyze. Proceeding with new analysis.")
    
    try:
        logger.debug(f"Starting analysis process for {request.user.username}")
        
        # Check if we're retrying a failed analysis
        is_retry = existing_user_analysis and existing_user_analysis.status == 'analyzing'
        
        if is_retry:
            # We're retrying - use the existing analysis object
            analysis = existing_user_analysis
            logger.debug(f"Retrying analysis for {request.user.username}")
        elif existing_global_analysis:
            # If property exists globally but analysis is incomplete, update the existing record
            logger.debug(f"Updating existing global analysis for {request.user.username}")
            analysis = existing_global_analysis
            analysis.user = request.user  # Set the current user as the requester
            analysis.status = 'analyzing'
            analysis.save()
            
            messages.info(request, 'Using existing property data. Running your personalized analysis...')
        else:
            # Create new analysis by scraping property data
            logger.debug(f"Scraping new property data for {request.user.username}")
            try:
                scraper = Century21AlbaniaScraper()
                property_data = scraper.scrape_property(property_url)
            except Exception as e:
                logger.error(f"Error creating scraper or scraping property: {e}")
                messages.error(request, 'Error accessing property website. Please try again.')
                return redirect('property_ai:analyze_property')
            
            if not property_data:
                logger.error(f"Failed to scrape property data for {property_url}")
                messages.error(request, 'Could not access this property.')
                return redirect('property_ai:analyze_property')
            
            logger.debug(f"Successfully scraped property data for {request.user.username}")
            try:
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
                    internal_area=property_data.get('internal_area'),
                    bedrooms=property_data.get('bedrooms'),
                    bathrooms=property_data.get('bathrooms'),
                    floor_level=property_data.get('floor_level', ''),
                    ceiling_height=property_data.get('ceiling_height'),
                    facade_length=property_data.get('facade_length'),
                    property_condition=property_data.get('condition', ''),
                    furnished=property_data.get('furnished'),
                    has_elevator=property_data.get('has_elevator'),
                    description=property_data.get('description', ''),

                    agent_name=property_data.get('agent_name', ''),
                    agent_email=property_data.get('agent_email', ''),
                    agent_phone=property_data.get('agent_phone', ''),
                    status='analyzing'
                )
            except Exception as e:
                logger.error(f"Error creating PropertyAnalysis record: {e}")
                messages.error(request, 'Error saving property data. Please try again.')
                return redirect('property_ai:analyze_property')
        
        # CONSUME QUOTA BEFORE RUNNING ANALYSIS
        logger.debug(f"Attempting to consume quota for {request.user.username}. Current usage: {profile.monthly_analyses_used}")
        try:
            if not profile.use_analysis_quota():
                logger.error(f"Failed to consume quota for {request.user.username}")
                messages.error(request, 'Could not consume analysis quota. Please try again.')
                analysis.delete()  # Clean up
                return redirect('property_ai:analyze_property')
        except Exception as e:
            logger.error(f"Error consuming quota: {e}")
            messages.error(request, 'Error with analysis quota. Please try again.')
            analysis.delete()  # Clean up
            return redirect('property_ai:analyze_property')
        
        logger.debug(f"Successfully consumed quota for {request.user.username}. New usage: {profile.monthly_analyses_used}")
        
        # Run AI analysis with enhanced analytics
        logger.debug(f"Starting AI analysis for {request.user.username}")
        
        try:
            ai = PropertyAI()
        except Exception as e:
            logger.error(f"Error creating AI engine: {e}")
            messages.error(request, 'Error initializing AI analysis. Please try again.')
            # Refund the quota since we couldn't even start
            profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
            profile.save()
            analysis.status = 'failed'
            analysis.save()
            return redirect('property_ai:analyze_property')
        
        try:
            comparable_properties = get_comparable_properties(analysis)
        except Exception as e:
            logger.error(f"Error getting comparable properties: {e}")
            comparable_properties = []  # Use empty list as fallback
        
        analysis_data = {
            'title': getattr(analysis, 'property_title', ''),
            'location': getattr(analysis, 'property_location', ''),
            'neighborhood': getattr(analysis, 'neighborhood', ''),
            'price': float(getattr(analysis, 'asking_price', 0)),
            'property_type': getattr(analysis, 'property_type', ''),
            'square_meters': getattr(analysis, 'total_area', 0),
            'condition': getattr(analysis, 'property_condition', ''),
            'floor_level': getattr(analysis, 'floor_level', ''),
        }
        
        # Pass the property_analysis object for enhanced analytics
        try:
            result = ai.analyze_property(analysis_data, comparable_properties, property_analysis=analysis)
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            result = {"status": "error", "message": f"AI analysis failed: {str(e)}"}
        
        logger.debug(f"AI analysis result for {request.user.username}: {result.get('status')}")
        logger.debug(f"AI analysis details: {result}")
        
        if result.get('status') == 'success':
            logger.debug(f"AI analysis successful for {request.user.username}")
            try:
                analysis.analysis_result = result
                analysis.ai_summary = result.get('summary', '')
                
                # Convert investment_score to integer
                investment_score = result.get('investment_score')
                if investment_score is not None:
                    try:
                        analysis.investment_score = int(investment_score)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid investment_score value: {investment_score}")
                        analysis.investment_score = None
                
                analysis.recommendation = result.get('recommendation')
                
                # Validate recommendation field
                valid_recommendations = ['strong_buy', 'buy', 'hold', 'avoid']
                if analysis.recommendation not in valid_recommendations:
                    logger.warning(f"Invalid recommendation value: {analysis.recommendation}")
                    analysis.recommendation = 'hold'  # Default to hold
                
                # Store enhanced analytics data with proper type conversion
                market_opportunity_score = result.get('market_opportunity_score')
                if market_opportunity_score is not None:
                    analysis.market_opportunity_score = Decimal(str(market_opportunity_score))
                
                price_analysis = result.get('price_analysis', {})
                price_percentile = price_analysis.get('price_percentile')
                if price_percentile is not None:
                    analysis.price_percentile = Decimal(str(price_percentile))
                
                market_position_percentage = price_analysis.get('market_position_percentage')
                if market_position_percentage is not None:
                    analysis.market_position_percentage = Decimal(str(market_position_percentage))
                
                analysis.negotiation_leverage = result.get('negotiation_leverage')
                
                # Validate negotiation_leverage field
                valid_leverage = ['high', 'medium', 'low']
                leverage_value = analysis.negotiation_leverage
                
                # Handle various edge cases
                if leverage_value:
                    leverage_lower = leverage_value.lower().strip()
                    if 'high' in leverage_lower or 'strong' in leverage_lower:
                        analysis.negotiation_leverage = 'high'
                    elif 'medium' in leverage_lower or 'moderate' in leverage_lower:
                        analysis.negotiation_leverage = 'medium'
                    elif 'low' in leverage_lower or 'weak' in leverage_lower:
                        analysis.negotiation_leverage = 'low'
                    elif leverage_lower not in valid_leverage:
                        logger.warning(f"Invalid negotiation_leverage value: {leverage_value}")
                        analysis.negotiation_leverage = 'medium'  # Default to medium
                else:
                    analysis.negotiation_leverage = 'medium'  # Default to medium
                
                # Fix market_sentiment - it should be a string, not a list
                market_sentiment = result.get('market_sentiment')
                if market_sentiment and market_sentiment in ['bullish', 'neutral', 'bearish']:
                    analysis.market_sentiment = market_sentiment
                
                analysis.status = 'completed'
                analysis.save()
                
                # 🆕 ADD THIS: Trigger PDF generation and email
                from ..tasks import generate_property_report_task
                try:
                    generate_property_report_task.delay(analysis.id)
                    logger.info(f"Queued PDF report generation for analysis {analysis.id}")
                except Exception as e:
                    logger.error(f"Failed to queue PDF generation for analysis {analysis.id}: {e}")
                
                logger.debug(f"Analysis completed successfully for {request.user.username}")
                messages.success(request, f'Analysis complete! You have {profile.remaining_analyses} analyses remaining this month.')
                return redirect('property_ai:analysis_detail', analysis_id=analysis.id)
            except Exception as e:
                logger.error(f"Error saving analysis results: {e}")
                logger.error(f"Result data: {result}")
                messages.error(request, 'Error saving analysis results. Please try again.')
                # Refund the quota since we couldn't save
                profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
                profile.save()
                analysis.status = 'failed'
                analysis.save()
                return redirect('property_ai:analyze_property')
        else:
            error_message = result.get('message', 'Unknown error')
            logger.error(f"AI analysis failed for {request.user.username}: {error_message}")
            try:
                analysis.status = 'failed'
                analysis.save()
                
                # Provide more specific error messages
                if 'timeout' in error_message.lower():
                    messages.error(request, 'Analysis timed out. Please try again.')
                elif 'api' in error_message.lower():
                    messages.error(request, 'AI service temporarily unavailable. Please try again.')
                elif 'quota' in error_message.lower():
                    messages.error(request, 'AI service quota exceeded. Please try again later.')
                else:
                    messages.error(request, f'Analysis failed: {error_message}')
                
                # Refund the quota since analysis failed
                profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
                profile.save()
                logger.debug(f"Refunded quota for {request.user.username}. New usage: {profile.monthly_analyses_used}")
            except Exception as e:
                logger.error(f"Error saving failed analysis status: {e}")
                messages.error(request, 'Analysis failed and there was an error processing the result.')
            return redirect('property_ai:analyze_property')
            
    except Exception as e:
        logger.error(f"Error analyzing property {property_url}: {e}")
        # Add more specific error handling
        if 'scraper' in str(e).lower() or 'scrape' in str(e).lower():
            messages.error(request, 'Error accessing property website. The property may no longer be available.')
        elif 'quota' in str(e).lower():
            messages.error(request, 'Error with analysis quota. Please try again.')
        elif 'ai' in str(e).lower() or 'analysis' in str(e).lower():
            messages.error(request, 'Error running AI analysis. Please try again.')
        else:
            messages.error(request, 'Error accessing property. Please try again.')
        return redirect('property_ai:analyze_property')


@login_required
def my_analyses(request):
    """Show only user's own analyses for all tiers"""
    if not hasattr(request.user, 'profile'):
        messages.error(request, 'Please complete your profile.')
        return redirect('accounts:user_profile')
    
    profile = request.user.profile
    
    # ALL TIERS: Show only user's own analyses
    analyses = PropertyAnalysis.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate enhanced stats
    completed_analyses = analyses.filter(status='completed')
    stats = {
        'total': analyses.count(),
        'completed': completed_analyses.count(),
        'avg_score': completed_analyses.aggregate(avg=Avg('investment_score'))['avg'],
        'strong_buys': completed_analyses.filter(investment_score__gte=80).count(),
        'avg_opportunity_score': completed_analyses.aggregate(avg=Avg('market_opportunity_score'))['avg'],
        'high_leverage_count': completed_analyses.filter(negotiation_leverage='high').count(),
        'below_market_count': completed_analyses.filter(market_position_percentage__lt=0).count(),
    }
    
    # Get portfolio analytics
    from ..analytics import PropertyAnalytics
    analytics = PropertyAnalytics()
    
    portfolio_analytics = {}
    if completed_analyses.exists():
        # Get unique locations from user's analyses
        locations = completed_analyses.values_list('property_location', flat=True).distinct()
        if locations:
            # Get market summary for user's portfolio
            portfolio_analytics = analytics.get_market_summary()
    
    context = {
        'analyses': analyses[:50],
        'user_tier': profile.subscription_tier,
        'remaining_analyses': profile.remaining_analyses,
        'stats': stats,
        'portfolio_analytics': portfolio_analytics,
    }
    return render(request, 'property_ai/my_analyses.html', context)


def get_comparable_properties(analysis):
    """Get comparable properties for analysis context"""
    try:
        logger.debug(f"Getting comparable properties for analysis {analysis.id}")
        
        # Safely get location and property type
        location = getattr(analysis, 'property_location', '')
        property_type = getattr(analysis, 'property_type', '')
        
        if not location:
            logger.warning(f"No location found for analysis {analysis.id}")
            return []
        
        # Find similar properties in same location and type
        comparables = PropertyAnalysis.objects.filter(
            property_location__icontains=location.split(',')[0],  # Main city
            status='completed',
            asking_price__gt=0
        ).exclude(id=analysis.id)
        
        # Add property type filter if available
        if property_type:
            comparables = comparables.filter(property_type=property_type)
        
        # Filter by similar size if available
        try:
            usable_area = getattr(analysis, 'usable_area', None)
            if usable_area and usable_area > 0:
                size_range = usable_area * 0.3  # ±30% size difference
                comparables = comparables.filter(
                    Q(total_area__range=(usable_area - size_range, usable_area + size_range)) |
                    Q(internal_area__range=(usable_area - size_range, usable_area + size_range))
                )
        except Exception as e:
            logger.warning(f"Error filtering by size: {e}")
        
        # Get top 5 most recent comparables
        comparables = comparables.order_by('-created_at')[:5]
        
        comparable_data = []
        for comp in comparables:
            try:
                comparable_data.append({
                    'title': getattr(comp, 'property_title', ''),
                    'location': getattr(comp, 'property_location', ''),
                    'price': float(getattr(comp, 'asking_price', 0)),
                    'area': getattr(comp, 'usable_area', 0),
                    'price_per_sqm': getattr(comp, 'price_per_sqm', 0),
                    'investment_score': getattr(comp, 'investment_score', 0),
                    'recommendation': getattr(comp, 'recommendation', ''),
                })
            except Exception as e:
                logger.warning(f"Error processing comparable property {comp.id}: {e}")
                continue
        
        logger.debug(f"Found {len(comparable_data)} comparable properties")
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
    
    # Get enhanced analytics data
    from ..analytics import PropertyAnalytics
    analytics = PropertyAnalytics()
    
    market_analytics = {}
    if analysis.status == 'completed':
        try:
            location = analysis.property_location.split(',')[0]
            market_analytics = {
                'market_stats': analytics.get_location_market_stats(location, analysis.property_type),
                'comparable_analysis': analytics.get_comparable_analysis(analysis),
                'opportunity_analysis': analytics.get_market_opportunity_score(analysis),
                'negotiation_insights': analytics.get_negotiation_insights(analysis),
                'price_trends': analytics.get_price_trends(location, analysis.property_type, months=6)
            }
        except Exception as e:
            logger.error(f"Error getting market analytics: {e}")
            market_analytics = {}
    
    context = {
        'analysis': analysis,
        'property_analysis': analysis,  # For template compatibility
        'similar_properties': similar_properties,
        'show_comparison': len(similar_properties) > 0,
        'market_analytics': market_analytics,
    }
    
    return render(request, 'property_ai/analysis_detail.html', context)
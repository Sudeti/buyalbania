# Component Interaction Guide - Property AI System

## Overview

This guide provides detailed examples of how different components interact with each other, showing actual code patterns and data flow between modules.

## 1. Property Analysis Workflow

### Complete Analysis Flow Example

```python
# User submits property URL → analysis_views.py:analyze_property()

# Step 1: Quota Check
profile = request.user.profile
if not profile.can_analyze_property():
    messages.error(request, 'Analysis quota exceeded.')
    return redirect('property_ai:analyze_property')

# Step 2: Check for existing analysis
existing_analysis = PropertyAnalysis.objects.filter(
    property_url=property_url, 
    user=request.user
).first()

# Step 3: Data Scraping (if new property)
if not existing_global_analysis:
    scraper = Century21AlbaniaScraper()
    property_data = scraper.scrape_property(property_url)
    
    # scraper.scrape_property() internally calls:
    # - _extract_title(soup)
    # - _extract_price(text, soup)
    # - _extract_location(text)
    # - _extract_agent_name(soup, text)
    # etc.

# Step 4: Create PropertyAnalysis record
analysis = PropertyAnalysis.objects.create(
    user=request.user,
    scraped_by=request.user,
    property_url=property_url,
    property_title=property_data['title'],
    # ... other fields
)

# Step 5: AI Analysis
ai = PropertyAI()
comparable_properties = get_comparable_properties(analysis)

analysis_data = {
    'title': analysis.property_title,
    'location': analysis.property_location,
    'price': float(analysis.asking_price),
    # ... other fields
}

result = ai.analyze_property(analysis_data, comparable_properties)

# Step 6: Store Results
if result.get('status') == 'success':
    analysis.analysis_result = result
    analysis.investment_score = result.get('investment_score')
    analysis.recommendation = result.get('recommendation')
    analysis.status = 'completed'
    analysis.save()
    
    # Consume quota
    profile.use_analysis_quota()
```

### Data Flow Between Components

```python
# 1. User Input → Views
property_url = request.POST.get('property_url', '').strip()

# 2. Views → Models (Quota Check)
profile = request.user.profile
can_analyze = profile.can_analyze_property()  # UserProfile method

# 3. Views → Scrapers (Data Extraction)
scraper = Century21AlbaniaScraper()
property_data = scraper.scrape_property(property_url)

# 4. Views → Models (Data Storage)
analysis = PropertyAnalysis.objects.create(
    user=request.user,
    property_url=property_url,
    # ... scraped data
)

# 5. Views → AI Engine (Analysis)
ai = PropertyAI()
result = ai.analyze_property(analysis_data, comparable_properties)

# 6. Views → Models (Result Storage)
analysis.analysis_result = result
analysis.save()

# 7. Views → Models (Quota Consumption)
profile.use_analysis_quota()
```

## 2. AI Engine Integration

### AI Analysis Process

```python
# ai_engine.py:PropertyAI.analyze_property()

def analyze_property(self, property_data, comparable_properties=None):
    # 1. Calculate metrics
    price = property_data.get('price', 0)
    area = property_data.get('square_meters', 0)
    price_per_sqm = (price / area) if area > 0 else 0
    
    # 2. Build comprehensive prompt
    prompt = f"""
    ROLE: You are an elite Albanian real estate investment analyst.
    
    PROPERTY DATA:
    Title: {property_data.get('title', '')}
    Location: {property_data.get('location', '')}
    Price: €{price:,}
    Price/m²: €{price_per_sqm:.0f}/m²
    
    COMPARABLE PROPERTIES: {json.dumps(comparable_properties or [])}
    
    2025 ALBANIAN MARKET CONTEXT:
    - Tirana center: €3,500-5,000/m²
    - Tirana suburbs: €1,200-1,500/m²
    - Rental yields: 5-8% annually
    
    FORMAT AS JSON:
    {{
        "investment_score": 85,
        "recommendation": "strong_buy",
        "summary": "High-yield investment opportunity",
        "price_analysis": {{...}},
        "rental_analysis": {{...}},
        "market_insights": [...],
        "risk_factors": [...],
        "action_items": [...]
    }}
    """
    
    # 3. Generate analysis with timeout protection
    response = self._generate_with_thread_timeout(prompt)
    
    # 4. Parse and return results
    if response and hasattr(response, 'text'):
        content = response.parts[0].text
        data = self._safe_json_loads(content)
        return {"status": "success", **data}
    
    return {"status": "error", "message": "Failed to generate analysis"}
```

### Comparable Properties Integration

```python
# analysis_views.py:get_comparable_properties()

def get_comparable_properties(analysis):
    # 1. Find similar properties in same location and type
    comparables = PropertyAnalysis.objects.filter(
        property_location__icontains=analysis.property_location.split(',')[0],
        property_type=analysis.property_type,
        status='completed',
        asking_price__gt=0
    ).exclude(id=analysis.id)
    
    # 2. Filter by similar size
    if analysis.usable_area:
        size_range = analysis.usable_area * 0.3  # ±30%
        comparables = comparables.filter(
            Q(total_area__range=(analysis.usable_area - size_range, 
                               analysis.usable_area + size_range)) |
            Q(internal_area__range=(analysis.usable_area - size_range, 
                                  analysis.usable_area + size_range))
        )
    
    # 3. Get top 5 most recent
    comparables = comparables.order_by('-created_at')[:5]
    
    # 4. Format for AI engine
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
```

## 3. Data Scraping Integration

### Scraper Data Extraction

```python
# scrapers.py:Century21AlbaniaScraper.scrape_property()

def scrape_property(self, url):
    # 1. Fetch page content
    response = self.session.get(url, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')
    text = soup.get_text()
    
    # 2. Filter rental vs. sale properties
    rental_keywords = ['qira', 'për qira', 'for rent', 'jepet me qira']
    sale_keywords = ['shesim', 'shitje', 'shitet', 'për shitje', 'for sale']
    
    text_lower = text.lower()
    is_rental = any(keyword in text_lower for keyword in rental_keywords)
    is_sale = any(keyword in text_lower for keyword in sale_keywords)
    
    if is_rental and not is_sale:
        return None  # Skip rental properties
    
    # 3. Extract property data
    extracted_data = {
        'url': url,
        'title': self._extract_title(soup),
        'price': self._extract_price(text, soup),
        'location': self._extract_location(text),
        'neighborhood': self._extract_neighborhood(text),
        'property_type': self._extract_type(text),
        'square_meters': self._extract_area(text),
        'condition': self._extract_condition(text),
        'floor_level': self._extract_floor(text),
        'agent_name': self._extract_agent_name(soup, text),
        'agent_email': self._extract_agent_email(soup, text),
        'agent_phone': self._extract_agent_phone(soup, text),
    }
    
    # 4. Validate essential data
    if extracted_data['price'] > 0 and extracted_data['title']:
        return extracted_data
    return None
```

### Agent Information Extraction

```python
# scrapers.py:Agent extraction methods

def _extract_agent_name(self, soup, text):
    # Method 1: Look for names near email addresses
    email_matches = re.finditer(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    for email_match in email_matches:
        start_pos = max(0, email_match.start() - 100)
        text_before_email = text[start_pos:email_match.start()]
        
        name_match = re.search(r'([A-Z][a-z]{2,15} [A-Z][a-z]{2,15})', text_before_email)
        if name_match:
            cleaned_name = self._clean_agent_name(name_match.group(1))
            if cleaned_name and self._is_valid_agent_name(cleaned_name):
                return cleaned_name
    
    return None

def _extract_agent_phone(self, soup, text):
    # Albanian mobile format: +355676475921
    phone_patterns = [
        r'\+355[6-9][0-9]{8}',  # Albanian mobile with +
        r'355[6-9][0-9]{8}',    # Without +
        r'0[6-9][0-9]{8}',      # Domestic format
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            cleaned = self._clean_phone_number(match)
            if cleaned:
                return cleaned
    
    return None
```

## 4. Access Control Integration

### Tier-Based Access Control

```python
# models.py:PropertyAnalysis.is_available_to_user()

def is_available_to_user(self, user):
    if not user or not user.is_authenticated:
        return False
        
    user_profile = getattr(user, 'profile', None)
    if not user_profile:
        return False
        
    tier = user_profile.subscription_tier
    
    if tier == 'free':
        # Free: Only their own analyses
        return self.user == user
    elif tier == 'basic':
        # Basic: Only their own analyses
        return self.user == user
    elif tier == 'premium':
        # Premium: Own analyses + excellent properties (80+)
        return (self.user == user) or (
            self.status == 'completed' and 
            (self.investment_score or 0) >= 80
        )
    else:
        return False
```

### View-Level Access Control

```python
# analysis_views.py:analysis_detail()

@login_required
def analysis_detail(request, analysis_id):
    analysis = get_object_or_404(PropertyAnalysis, id=analysis_id)
    
    # Check access control
    if request.user.is_authenticated:
        if not analysis.is_available_to_user(request.user):
            messages.error(request, 'You do not have access to this analysis.')
            return redirect('property_ai:home')
    
    # Get similar properties (also filtered by tier)
    similar_properties = PropertyAnalysis.objects.filter(
        property_location__icontains=analysis.property_location.split(',')[0],
        property_type=analysis.property_type,
        status='completed'
    ).exclude(id=analysis.id)
    
    # Filter by user tier
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        accessible_similar = [
            prop for prop in similar_properties 
            if prop.is_available_to_user(request.user)
        ]
        similar_properties = accessible_similar[:3]
    
    return render(request, 'property_ai/analysis_detail.html', {
        'analysis': analysis,
        'similar_properties': similar_properties,
    })
```

## 5. Quota Management Integration

### Quota Check and Consumption

```python
# accounts/models.py:UserProfile quota methods

def can_analyze_property(self):
    """Check if user can analyze a new property"""
    self.reset_monthly_quota_if_needed()
    
    if self.subscription_tier == 'free':
        return self.monthly_analyses_used < 1
    elif self.subscription_tier == 'basic':
        return self.monthly_analyses_used < 10
    else:  # premium
        return True  # unlimited

def use_analysis_quota(self):
    """Consume one analysis from quota"""
    self.reset_monthly_quota_if_needed()
    if self.can_analyze_property():
        self.monthly_analyses_used += 1
        self.save()
        return True
    return False

def reset_monthly_quota_if_needed(self):
    """Reset quota on first of each month"""
    from django.utils import timezone
    today = timezone.now().date()
    
    if (not self.monthly_quota_reset_date or 
        today.month != self.monthly_quota_reset_date.month):
        self.monthly_analyses_used = 0
        self.monthly_quota_reset_date = today
        self.save()
```

### Quota Integration in Views

```python
# analysis_views.py:Quota management in analysis workflow

# Before scraping - check quota
if not profile.can_analyze_property():
    tier_info = {
        'free': 'You\'ve used your 1 free analysis this month. Upgrade to Basic (€5) for 10 analyses per month!',
        'basic': 'You\'ve used all 10 analyses this month. Upgrade to Premium (€15) for unlimited analyses!',
    }
    messages.error(request, tier_info.get(profile.subscription_tier, 'Analysis quota exceeded.'))
    return redirect('property_ai:analyze_property')

# After successful analysis - consume quota
if result.get('status') == 'success':
    # ... store analysis results ...
    
    # Consume quota
    if not profile.use_analysis_quota():
        messages.error(request, 'Could not consume analysis quota.')
        return redirect('property_ai:analyze_property')
    
    messages.success(request, f'Analysis complete! You have {profile.remaining_analyses} analyses remaining this month.')

# On analysis failure - refund quota
else:
    analysis.status = 'failed'
    analysis.save()
    messages.error(request, 'Analysis failed. Your quota has not been consumed.')
    # Refund the quota since analysis failed
    profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
    profile.save()
```

## 6. Report Generation Integration

### PDF Report Generation

```python
# report_generator.py:PropertyReportPDF.generate_pdf_report()

def generate_pdf_report(self, property_analysis, report_content):
    try:
        # 1. Prepare template context
        context = self._prepare_template_context(property_analysis, report_content)
        
        # 2. Render HTML template
        html_content = render_to_string('property_ai/reports/property_report.html', context)
        
        # 3. Generate PDF filename
        pdf_filename = f"property_report_{property_analysis.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)
        
        # 4. Create PDF with WeasyPrint
        html_doc = HTML(string=html_content, base_url=settings.STATIC_URL)
        css = CSS(string=self._get_pdf_css())
        html_doc.write_pdf(pdf_path, stylesheets=[css])
        
        return pdf_path
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        raise
```

### Report Context Preparation

```python
# report_generator.py:Template context preparation

def _prepare_template_context(self, property_analysis, report_content):
    analysis_result = property_analysis.analysis_result or {}
    
    return {
        'property_analysis': property_analysis,
        'user': property_analysis.user,
        'analysis_result': analysis_result,
        'summary': analysis_result.get("summary", ""),
        'investment_score': property_analysis.investment_score,
        'recommendation': property_analysis.recommendation,
        'price_analysis': analysis_result.get('price_analysis', {}),
        'rental_analysis': analysis_result.get('rental_analysis', {}),
        'market_insights': analysis_result.get('market_insights', []),
        'risk_factors': analysis_result.get('risk_factors', []),
        'action_items': analysis_result.get('action_items', []),
        'five_year_projection': analysis_result.get('five_year_projection', {}),
        'generation_date': datetime.now(),
        'report_id': str(property_analysis.id)[:8].upper(),
    }
```

## 7. User Management Integration

### Registration and Email Verification

```python
# accounts/views.py:User registration workflow

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create profile and verification token
            token = secrets.token_urlsafe(32)
            profile = UserProfile.objects.create(
                user=user,
                email_verification_token=token,
                email_verification_sent_at=timezone.now()
            )
            
            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('accounts:verify_email', args=[token])
            )
            
            email = EmailMultiAlternatives(
                subject='Verify your email',
                body=f"Click this link to verify your email: {verification_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
            
            return render(request, 'accounts/register_success.html', {'email': user.email})
```

### Profile Deletion with GDPR Compliance

```python
# accounts/views.py:Profile deletion

@login_required
@require_POST
def delete_profile_execute(request):
    user = request.user
    user_email = user.email
    
    try:
        # Log deletion for audit
        logger.info(f"User {user_email} requested profile deletion")
        
        # Log privacy consents being deleted
        privacy_consents = user.privacy_consents.all()
        if privacy_consents.exists():
            logger.info(f"Deleting {privacy_consents.count()} privacy consent records for user {user_email}")
        
        # Send confirmation email
        send_mail(
            subject='Profile Deletion Confirmed',
            message=f'Your profile and all associated data have been permanently deleted.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=True
        )
        
        # Delete user (cascades to related objects)
        logout(request)
        user.delete()
        
        messages.success(request, 'Your profile has been successfully deleted.')
        return redirect('property_ai:home')
        
    except Exception as e:
        logger.error(f"Profile deletion failed for {user_email}: {e}")
        messages.error(request, 'An error occurred while deleting your profile.')
        return redirect('accounts:user_profile')
```

## 8. Error Handling Integration

### Comprehensive Error Handling

```python
# analysis_views.py:Error handling in analysis workflow

try:
    # Scrape property data
    scraper = Century21AlbaniaScraper()
    property_data = scraper.scrape_property(property_url)
    
    if not property_data:
        messages.error(request, 'Could not access this property.')
        return redirect('property_ai:analyze_property')
    
    # Create analysis record
    analysis = PropertyAnalysis.objects.create(...)
    
    # Run AI analysis
    ai = PropertyAI()
    result = ai.analyze_property(analysis_data, comparable_properties)
    
    if result.get('status') == 'success':
        # Store successful results
        analysis.analysis_result = result
        analysis.status = 'completed'
        analysis.save()
        
        # Consume quota
        profile.use_analysis_quota()
        
        messages.success(request, f'Analysis complete! You have {profile.remaining_analyses} analyses remaining.')
        return redirect('property_ai:analysis_detail', analysis_id=analysis.id)
    else:
        # Handle AI analysis failure
        analysis.status = 'failed'
        analysis.save()
        
        # Refund quota
        profile.monthly_analyses_used = max(0, profile.monthly_analyses_used - 1)
        profile.save()
        
        messages.error(request, 'Analysis failed. Your quota has not been consumed.')
        return redirect('property_ai:analyze_property')
        
except Exception as e:
    logger.error(f"Error analyzing property {property_url}: {e}")
    messages.error(request, 'Error accessing property. Please try again.')
    return redirect('property_ai:analyze_property')
```

## 9. Performance Optimization Integration

### Database Query Optimization

```python
# analysis_views.py:Optimized queries

def my_analyses(request):
    # Use select_related for foreign key relationships
    analyses = PropertyAnalysis.objects.filter(
        user=request.user
    ).select_related('user').order_by('-created_at')
    
    # Use aggregation for statistics
    completed_analyses = analyses.filter(status='completed')
    stats = {
        'total': analyses.count(),
        'completed': completed_analyses.count(),
        'avg_score': completed_analyses.aggregate(
            avg=Avg('investment_score')
        )['avg'],
        'strong_buys': completed_analyses.filter(
            investment_score__gte=80
        ).count(),
    }
    
    # Limit results for performance
    context = {
        'analyses': analyses[:50],  # Only show last 50
        'user_tier': request.user.profile.subscription_tier,
        'remaining_analyses': request.user.profile.remaining_analyses,
        'stats': stats,
    }
    return render(request, 'property_ai/my_analyses.html', context)
```

### Caching Integration

```python
# Example caching implementation (not in current codebase)

from django.core.cache import cache
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def home(request):
    """Cached home page with statistics"""
    cache_key = 'home_stats'
    stats = cache.get(cache_key)
    
    if not stats:
        # Calculate expensive statistics
        total_analyses = PropertyAnalysis.objects.filter(status='completed').count()
        avg_score = PropertyAnalysis.objects.filter(
            status='completed', 
            investment_score__isnull=False
        ).aggregate(avg_score=Avg('investment_score'))['avg_score']
        
        stats = {
            'total_analyses': total_analyses,
            'avg_score': round(avg_score or 0, 1),
        }
        
        # Cache for 15 minutes
        cache.set(cache_key, stats, 60 * 15)
    
    return render(request, 'property_ai/home.html', {'stats': stats})
```

This component interaction guide shows the detailed code patterns and data flow between all major components of the Property AI System, demonstrating how they work together to provide a comprehensive property investment analysis platform.

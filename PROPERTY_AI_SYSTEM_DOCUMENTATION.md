# Property AI System - Comprehensive Documentation

## System Overview

The Property AI System is a Django-based web application that provides AI-powered investment analysis for Albanian real estate properties. The system scrapes property data from Century21 Albania, analyzes properties using Google's Gemini AI, and provides investment recommendations with detailed reports.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Interface│    │   Business Logic│    │   Data Layer    │
│                 │    │                 │    │                 │
│ • Templates     │◄──►│ • Views         │◄──►│ • Models        │
│ • Forms         │    │ • AI Engine     │    │ • Database      │
│ • Static Files  │    │ • Scrapers      │    │ • File Storage  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Data Models (`models.py`)

#### PropertyAnalysis Model
The central model that stores all property and analysis data:

**Key Fields:**
- `property_url`: Unique identifier for each property
- `user`: User who requested the analysis (nullable for scraped properties)
- `scraped_by`: User who initiated the scraping process
- Property details: title, location, price, area, type, condition
- Analysis results: investment score, recommendation, AI summary
- Agent information: name, email, phone

**Access Control:**
```python
def is_available_to_user(self, user):
    """Tier-based access control"""
    if tier == 'free':
        return self.user == user  # Only own analyses
    elif tier == 'basic':
        return self.user == user  # Only own analyses
    elif tier == 'premium':
        return (self.user == user) or (self.investment_score >= 80)  # Own + high-scoring
```

**Computed Properties:**
- `price_per_sqm`: Price per square meter
- `usable_area`: Internal or total area
- `location_tier`: Prime/Good/Emerging based on location
- `investment_category`: High/Moderate/Low potential

#### UserProfile Model (`accounts/models.py`)
Manages user subscriptions and quotas:

**Subscription Tiers:**
- **Free**: 1 analysis per month
- **Basic**: 10 analyses per month (€5/month)
- **Premium**: Unlimited analyses (€15/month)

**Quota Management:**
```python
def can_analyze_property(self):
    if self.subscription_tier == 'free':
        return self.monthly_analyses_used < 1
    elif self.subscription_tier == 'basic':
        return self.monthly_analyses_used < 10
    else:  # premium
        return True  # unlimited
```

### 2. Data Scraping (`scrapers.py`)

#### Century21AlbaniaScraper
Responsible for extracting property data from Century21 Albania website.

**Key Methods:**

1. **`get_sale_property_listings(max_pages=10)`**
   - Scrapes property listing pages
   - Extracts URLs for individual properties
   - Returns list of property URLs

2. **`scrape_property(url)`**
   - Scrapes individual property pages
   - Filters out rental properties (focuses on sales)
   - Extracts comprehensive property data

**Data Extraction:**
```python
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
```

**Albanian Market Focus:**
- Detects Albanian rental vs. sale keywords
- Extracts Albanian phone numbers (+355 format)
- Recognizes Albanian neighborhoods and cities
- Handles Albanian property descriptions

### 3. AI Analysis Engine (`ai_engine.py`)

#### PropertyAI Class
Uses Google's Gemini AI to analyze properties and provide investment recommendations.

**Key Features:**
- **Model**: Gemini 2.5 Pro with JSON response format
- **Timeout Protection**: 120-second timeout for API calls
- **Albanian Market Context**: Uses 2025 Albanian real estate data

**Analysis Process:**
```python
def analyze_property(self, property_data, comparable_properties=None):
    # 1. Calculate key metrics
    price_per_sqm = (price / area) if area > 0 else 0
    
    # 2. Generate comprehensive prompt with market data
    prompt = f"""
    ROLE: Albanian real estate investment analyst
    
    PROPERTY DATA: {property_data}
    COMPARABLE PROPERTIES: {comparable_properties}
    
    2025 ALBANIAN MARKET CONTEXT:
    - Tirana center: €3,500-5,000/m²
    - Tirana suburbs: €1,200-1,500/m²
    - Durrës: €800-1,200/m²
    - Rental yields: 5-8% annually
    """
    
    # 3. Generate analysis with timeout protection
    response = self._generate_with_thread_timeout(prompt)
    
    # 4. Parse JSON response
    return {"status": "success", **data}
```

**Analysis Output:**
```json
{
    "investment_score": 85,
    "recommendation": "strong_buy",
    "summary": "High-yield investment opportunity",
    "price_analysis": {
        "price_per_sqm": 3200,
        "value_assessment": "below_market",
        "market_position_percentage": -15.2,
        "negotiation_potential": "5-10%"
    },
    "rental_analysis": {
        "estimated_monthly_rent": 950,
        "annual_gross_yield": "6.8%",
        "rental_demand": "high"
    },
    "market_insights": [...],
    "risk_factors": [...],
    "action_items": [...]
}
```

### 4. User Interface Views

#### Analysis Views (`analysis_views.py`)

**`analyze_property(request)`**
Main analysis workflow:

1. **Quota Check**: Verify user can analyze properties
2. **URL Validation**: Check if property URL is valid
3. **Duplicate Check**: Check if user already analyzed this property
4. **Data Scraping**: Scrape property data or use existing data
5. **AI Analysis**: Run AI analysis with comparable properties
6. **Quota Consumption**: Consume analysis quota
7. **Result Storage**: Save analysis results

**Key Workflow:**
```python
# Check quota before scraping
if not profile.can_analyze_property():
    messages.error(request, 'Analysis quota exceeded.')
    return redirect('property_ai:analyze_property')

# Check for existing analysis
existing_analysis = PropertyAnalysis.objects.filter(
    property_url=property_url, 
    user=request.user
).first()

# Scrape or use existing data
if existing_global_analysis:
    # Use existing scraped data, create new user analysis
    analysis = PropertyAnalysis.objects.create(...)
else:
    # Scrape new property
    scraper = Century21AlbaniaScraper()
    property_data = scraper.scrape_property(property_url)

# Consume quota and run AI analysis
profile.use_analysis_quota()
ai = PropertyAI()
result = ai.analyze_property(analysis_data, comparable_properties)
```

**`my_analyses(request)`**
Shows user's analysis history with statistics:
- Total analyses completed
- Average investment score
- Number of strong buy recommendations

**`analysis_detail(request, analysis_id)`**
Displays detailed analysis results with access control:
- Investment score and recommendation
- Price analysis and market insights
- Rental yield calculations
- Similar properties (filtered by tier)

#### Home Views (`home_views.py`)

**`home(request)`**
Landing page with:
- System features overview
- Statistics (total analyses, average score)
- Featured high-scoring properties

#### Report Views (`report_views.py`)

**`download_report(request, analysis_id)`**
Generates and downloads PDF reports for completed analyses.

### 5. Report Generation (`report_generator.py`)

#### PropertyReportPDF Class
Generates professional PDF reports using WeasyPrint.

**Report Structure:**
1. **Cover Page**: Property title, analysis date, report ID
2. **Executive Summary**: Investment score and recommendation
3. **Property Details**: Complete property information
4. **Market Analysis**: Price analysis and market position
5. **Rental Analysis**: Yield calculations and demand assessment
6. **Risk Assessment**: Identified risk factors
7. **Action Items**: Recommended next steps

**PDF Generation Process:**
```python
def generate_pdf_report(self, property_analysis, report_content):
    # 1. Prepare template context
    context = self._prepare_template_context(property_analysis, report_content)
    
    # 2. Render HTML template
    html_content = render_to_string('property_ai/reports/property_report.html', context)
    
    # 3. Generate PDF with styling
    html_doc = HTML(string=html_content, base_url=settings.STATIC_URL)
    css = CSS(string=self._get_pdf_css())
    html_doc.write_pdf(pdf_path, stylesheets=[css])
```

### 6. User Management (`accounts/views.py`)

**Registration and Authentication:**
- Email verification required
- Privacy policy consent tracking
- GDPR compliance with data deletion

**Profile Management:**
- Subscription tier management
- Analysis quota tracking
- Profile deletion with data cleanup

## Data Flow

### 1. Property Analysis Workflow

```
User Input URL
       ↓
Quota Check (UserProfile)
       ↓
Duplicate Check (PropertyAnalysis)
       ↓
Data Scraping (Century21AlbaniaScraper)
       ↓
Data Storage (PropertyAnalysis)
       ↓
AI Analysis (PropertyAI)
       ↓
Result Storage (PropertyAnalysis)
       ↓
Quota Consumption (UserProfile)
       ↓
Report Generation (PropertyReportPDF)
```

### 2. User Access Control Flow

```
User Request
       ↓
Authentication Check
       ↓
Tier Verification (UserProfile)
       ↓
Access Control (PropertyAnalysis.is_available_to_user())
       ↓
Content Display (Filtered by Tier)
```

### 3. Data Relationships

```
User (Django Auth)
 ├── UserProfile (Subscription & Quota)
 │    ├── subscription_tier
 │    ├── monthly_analyses_used
 │    └── can_analyze_property()
 │
 └── PropertyAnalysis (User's Analyses)
      ├── property_url (Unique)
      ├── analysis_result (JSON)
      ├── investment_score
      └── recommendation

PropertyAnalysis (Global Database)
 ├── scraped_by (User who scraped)
 ├── agent_name, agent_email, agent_phone
 └── is_available_to_user() (Access Control)
```

## Key Features

### 1. Tier-Based Access Control
- **Free**: Only own analyses
- **Basic**: Only own analyses
- **Premium**: Own analyses + high-scoring properties (80+)

### 2. Quota Management
- Monthly reset on 1st of month
- Automatic quota consumption
- Refund on failed analyses

### 3. Albanian Market Focus
- Albanian property detection
- Local market data integration
- Albanian language support

### 4. Comprehensive Analysis
- Investment scoring (0-100)
- Market position analysis
- Rental yield calculations
- Risk assessment
- Action recommendations

### 5. Professional Reporting
- PDF report generation
- Professional styling
- Comprehensive analysis summary

## Security & Compliance

### 1. GDPR Compliance
- Privacy policy version tracking
- User consent records
- Data deletion capabilities
- Audit logging

### 2. Access Control
- User authentication required
- Tier-based content access
- URL-based property isolation

### 3. Data Protection
- Encrypted sensitive data
- Secure file storage
- Audit trails

## Performance Considerations

### 1. Database Optimization
- Indexed fields for fast queries
- Efficient relationship queries
- Pagination for large datasets

### 2. AI API Management
- Timeout protection
- Error handling
- Rate limiting considerations

### 3. File Storage
- Organized report storage
- Cleanup procedures
- Efficient PDF generation

## Error Handling

### 1. Scraping Errors
- Graceful failure handling
- Logging for debugging
- User-friendly error messages

### 2. AI Analysis Errors
- Timeout protection
- JSON parsing fallbacks
- Quota refund on failure

### 3. User Input Validation
- URL format validation
- Quota enforcement
- Access control validation

## Future Enhancements

### 1. Scalability
- Celery task queues for background processing
- Redis caching for frequent queries
- CDN for static assets

### 2. Advanced Features
- Property alerts and notifications
- Market trend analysis
- Comparative market analysis
- Investment portfolio tracking

### 3. Integration
- Multiple property sources
- Payment gateway integration
- Email marketing integration
- Analytics and reporting

This documentation provides a comprehensive overview of how all components work together to create a robust, scalable property investment analysis system focused on the Albanian real estate market.

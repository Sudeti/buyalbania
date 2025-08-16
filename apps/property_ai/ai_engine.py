import json
import logging
import re
import time
import threading
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

class PropertyAI:
    """AI-powered property investment analysis"""

    def __init__(self, model_name='gpt-5'):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_name = model_name
   
    # Updated ai_engine.py - simplified to match your scraper
    # ai_engine.py - Update the analyze_property method
    def analyze_property(self, property_data, comparable_properties=None, property_analysis=None):
        """Enhanced investment analysis with comprehensive market analytics"""
        try:
            from .analytics import PropertyAnalytics
            
            # Calculate key metrics from simplified data
            price = property_data.get('price', 0)
            area = property_data.get('square_meters', 0)
            price_per_sqm = (price / area) if area > 0 else 0
            
            # Initialize analytics service
            analytics = PropertyAnalytics()
            
            # Get comprehensive market analysis if property_analysis object is provided
            market_analytics = {}
            if property_analysis:
                location = property_analysis.property_location.split(',')[0]
                
                # Get market statistics (include unanalyzed properties for better context)
                market_stats = analytics.get_location_market_stats(location, property_analysis.property_type, include_unanalyzed=True)
                
                # Get comparable analysis (include unanalyzed properties)
                comparable_analysis = analytics.get_comparable_analysis(property_analysis, include_unanalyzed=True)
                
                # Get market opportunity score (works for both analyzed and unanalyzed properties)
                opportunity_analysis = analytics.get_market_opportunity_score(property_analysis)
                
                # Get basic metrics for unanalyzed properties
                basic_metrics = {}
                if property_analysis.status != 'completed':
                    basic_metrics = analytics.get_basic_property_metrics(property_analysis)
                
                # Get negotiation insights (only for completed analyses)
                negotiation_insights = {}
                if property_analysis.status == 'completed':
                    negotiation_insights = analytics.get_negotiation_insights(property_analysis)
                
                market_analytics = {
                    'market_stats': market_stats,
                    'comparable_analysis': comparable_analysis,
                    'opportunity_analysis': opportunity_analysis,
                    'basic_metrics': basic_metrics,
                    'negotiation_insights': negotiation_insights,
                    'analysis_status': property_analysis.status
                }
            
            # Build enhanced prompt with analytics data
            prompt = f"""
            ROLE: You are an elite Albanian real estate investment analyst specializing in ROI optimization with access to comprehensive market analytics.

            PROPERTY DATA:
            Title: {property_data.get('title', '')}
            Location: {property_data.get('location', '')}
            Neighborhood: {property_data.get('neighborhood', 'N/A')}
            Price: €{price:,}
            Price/m²: €{price_per_sqm:.0f}/m² 
            Type: {property_data.get('property_type', '')}
            Area: {area}m²
            Condition: {property_data.get('condition', '')}
            Floor: {property_data.get('floor_level', '')}

            COMPARABLE PROPERTIES: {json.dumps(comparable_properties or [], indent=2)}

            MARKET ANALYTICS: {json.dumps(market_analytics, indent=2)}

            2025 ALBANIAN MARKET CONTEXT:
            - Tirana center (Blloku): €3,500-5,000/m² (premium areas)
            - Tirana suburbs: €1,200-1,500/m² (Kombinat, Astir, Fresku)
            - Tirana outskirts: €500-700/m² (Paskuqan)
            - Durrës: €800-1,200/m²
            - Commercial ground floor: +30-50% premium
            - Rental yields: 5-8% annually

            ENHANCED ANALYSIS FRAMEWORK:
            1. Price vs actual market averages (use market_analytics data)
            2. Market opportunity score analysis
            3. Negotiation leverage assessment
            4. Rental income potential with market context
            5. Risk assessment based on market sentiment
            6. Actionable investment recommendations

            FORMAT AS JSON:
            {{
                "investment_score": 85,
                "recommendation": "strong_buy",
                "summary": "High-yield investment opportunity in prime location",
                "market_opportunity_score": 78.5,
                "price_analysis": {{
                    "price_per_sqm": {price_per_sqm:.0f},
                    "value_assessment": "below_market",
                    "market_position_percentage": -15.2,
                    "price_percentile": 35.5,
                    "negotiation_potential": "5-10%",
                    "recommended_offer_range": {{
                        "min": {price * 0.9:.0f},
                        "max": {price * 0.95:.0f}
                    }}
                }},
                "rental_analysis": {{
                    "estimated_monthly_rent": 950,
                    "annual_gross_yield": "6.8%",
                    "rental_demand": "high",
                    "market_rental_trend": "increasing"
                }},
                "market_insights": [
                    "Property priced 15% below market average",
                    "Strong neighborhood fundamentals",
                    "Property type in high demand",
                    "Market sentiment: bullish"
                ],
                "risk_factors": [
                    "Market volatility considerations",
                    "Location-specific risks"
                ],
                "negotiation_leverage": "high",
                "action_items": [
                    "Schedule property viewing immediately",
                    "Negotiate 5-8% additional reduction",
                    "Secure financing pre-approval",
                    "Monitor market trends"
                ],
                "market_timing": "optimal"
            }}
            """
            
            response = self._generate_with_thread_timeout(prompt)
            
            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                try:
                    content = response.choices[0].message.content
                    data = self._safe_json_loads(content)
                    return {"status": "success", **data}
                except Exception as e:
                    logger.error(f"Error parsing response: {e}")
                    
            return {"status": "error", "message": "Failed to generate analysis"}
        
        except Exception as e:
            logger.error(f"Property analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _generate_with_thread_timeout(self, prompt, timeout=120):
        """Generate with timeout protection"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert Albanian real estate investment analyst. Always respond with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000,
                    response_format={"type": "json_object"}
                )
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            logger.warning(f"API call timed out after {timeout} seconds")
            return None
            
        if exception[0]:
            raise exception[0]
            
        return result[0]

    def generate_report(self, property_analysis):
        """Generate detailed report content"""
        result = property_analysis.analysis_result or {}
        
        summary = result.get("summary", "Property analysis completed")
        score = property_analysis.investment_score or 0
        recommendation = property_analysis.recommendation or "hold"
        
        return f"""
        Property Investment Analysis Report
        
        Property: {property_analysis.property_title}
        Location: {property_analysis.property_location}
        Investment Score: {score}/100
        Recommendation: {recommendation.replace('_', ' ').title()}
        
        Summary:
        {summary}
        
        Generated on: {property_analysis.created_at.strftime('%Y-%m-%d %H:%M')}
        """
    
    def _safe_json_loads(self, text):
        """Safe JSON parsing with fallbacks"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Clean up common issues
            text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            text = text.replace(',}', '}').replace(',]', ']')
            try:
                return json.loads(text)
            except:
                # Extract JSON with regex
                json_match = re.search(r'({[\s\S]*})', text)
                if json_match:
                    return json.loads(json_match.group(1))
                raise
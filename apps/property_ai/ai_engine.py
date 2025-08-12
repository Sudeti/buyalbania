import json
import logging
import re
import time
import threading
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

class PropertyAI:
    """AI-powered property investment analysis"""

    def __init__(self, model_name='gemini-2.5-pro'):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.7,
                "max_output_tokens": 8000,
            }
        )
   
    # Updated ai_engine.py - simplified to match your scraper
    # ai_engine.py - Update the analyze_property method
    def analyze_property(self, property_data, comparable_properties=None):
        """Investment-focused property analysis using current 2025 market data + real market averages"""
        try:
            from .market_analytics import MarketAnalytics
            
            # Calculate key metrics from simplified data
            price = property_data.get('price', 0)
            area = property_data.get('square_meters', 0)
            price_per_sqm = (price / area) if area > 0 else 0
            
            # NEW: Get real market averages
            market_avg = MarketAnalytics.get_market_averages(
                property_type=property_data.get('property_type'),
                location=property_data.get('location')
            )
            
            neighborhood_avg = None
            if property_data.get('neighborhood'):
                neighborhood_avg = MarketAnalytics.get_market_averages(
                    property_type=property_data.get('property_type'),
                    location=property_data.get('location'),
                    neighborhood=property_data.get('neighborhood')
                )
            
            # Calculate market position
            market_context = ""
            if market_avg:
                market_price_per_sqm = market_avg['avg_price_per_sqm']
                if market_price_per_sqm > 0 and price_per_sqm > 0:
                    diff_percentage = ((price_per_sqm - market_price_per_sqm) / market_price_per_sqm) * 100
                    market_context = f"""
                    REAL MARKET DATA:
                    - City average (€{market_price_per_sqm:.0f}/m²) vs This property (€{price_per_sqm:.0f}/m²)
                    - Market position: {diff_percentage:+.1f}% vs city average
                    - Sample size: {market_avg['total_properties']} comparable properties
                    """
                    
                    if neighborhood_avg:
                        neighborhood_price_per_sqm = neighborhood_avg['avg_price_per_sqm']
                        neighborhood_diff = ((price_per_sqm - neighborhood_price_per_sqm) / neighborhood_price_per_sqm) * 100
                        market_context += f"""
                    - Neighborhood average (€{neighborhood_price_per_sqm:.0f}/m²)
                    - Neighborhood position: {neighborhood_diff:+.1f}% vs neighborhood average
                    """
            
            prompt = f"""
            ROLE: You are an elite Albanian real estate investment analyst specializing in ROI optimization.

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

            {market_context}

            COMPARABLE PROPERTIES: {json.dumps(comparable_properties or [], indent=2)}

            2025 ALBANIAN MARKET CONTEXT:
            - Tirana center (Blloku): €3,500-5,000/m² (premium areas)
            - Tirana suburbs: €1,200-1,500/m² (Kombinat, Astir, Fresku)
            - Tirana outskirts: €500-700/m² (Paskuqan)
            - Durrës: €800-1,200/m²
            - Commercial ground floor: +30-50% premium
            - Rental yields: 5-8% annually

            ANALYSIS FRAMEWORK - Use the REAL market data above for accurate assessment:
            1. Price vs actual market averages (not just estimates)
            2. Rental income potential
            3. Investment opportunity scoring
            4. Negotiation recommendations

            FORMAT AS JSON:
            {{
                "investment_score": 85,
                "recommendation": "strong_buy",
                "summary": "High-yield investment opportunity in prime location",
                "price_analysis": {{
                    "price_per_sqm": {price_per_sqm:.0f},
                    "market_average_per_sqm": {market_avg['avg_price_per_sqm'] if market_avg else 1350},
                    "value_assessment": "below_market",
                    "market_position_percentage": -15.2,
                    "negotiation_potential": "5-10%"
                }},
                "rental_analysis": {{
                    "estimated_monthly_rent": 950,
                    "annual_gross_yield": "6.8%",
                    "rental_demand": "high"
                }},
                "market_insights": [
                    "Property priced 15% below city average",
                    "Strong neighborhood fundamentals",
                    "Property type in high demand"
                ],
                "risk_factors": [
                    "Market volatility considerations"
                ],
                "action_items": [
                    "Schedule property viewing immediately",
                    "Negotiate 5-8% additional reduction",
                    "Secure financing pre-approval"
                ]
            }}
            """
            
            response = self._generate_with_thread_timeout(prompt)
            
            if response and hasattr(response, 'text'):
                try:
                    if hasattr(response, 'parts') and len(response.parts) > 0:
                        content = response.parts[0].text
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
                result[0] = self.model.generate_content(prompt)
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
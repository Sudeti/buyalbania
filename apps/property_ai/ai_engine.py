import json
import logging
import re
import time
import threading
from decimal import Decimal
from django.conf import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

class PropertyAI:
    """AI-powered property investment analysis"""

    def __init__(self, model_name='gemini-2.5-pro'):
        try:
            logger.debug(f"Initializing PropertyAI with model: {model_name}")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.7,
                    "max_output_tokens": 8000,
                }
            )
            logger.debug("PropertyAI initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing PropertyAI: {e}")
            raise
   
    def analyze_property(self, property_data, comparable_properties=None, property_analysis=None):
        """Data-driven property analysis using real market intelligence instead of AI-generated scores"""
        try:
            # If we have a property_analysis object, use data-driven analysis
            if property_analysis:
                logger.info(f"Using data-driven analysis for property {property_analysis.id}")
                from .data_driven_analyzer import DataDrivenAnalyzer
                
                analyzer = DataDrivenAnalyzer()
                result = analyzer.analyze_property(property_analysis)
                
                if result.get('status') == 'success':
                    # Generate AI summary based on real data
                    summary = self._generate_ai_summary_from_data(result, property_analysis)
                    result['summary'] = summary
                    
                    return result
                else:
                    logger.error(f"Data-driven analysis failed: {result.get('message')}")
                    return {"status": "error", "message": "Data-driven analysis failed"}
            
            # Fallback to AI analysis for properties without database records
            logger.info("No property_analysis object provided, using AI fallback")
            return self._fallback_ai_analysis(property_data, comparable_properties)
        
        except Exception as e:
            logger.error(f"Property analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _generate_ai_summary_from_data(self, data_result: dict, property_analysis) -> str:
        """Generate AI summary based on real market data"""
        try:
            # Extract key data points
            investment_score = data_result.get('investment_score', 50)
            recommendation = data_result.get('recommendation', 'hold')
            market_position = data_result.get('market_position_analysis', {})
            investment_potential = data_result.get('investment_potential', {})
            market_momentum = data_result.get('market_momentum', {})
            
            # Build context for AI summary
            context = {
                'property_title': property_analysis.property_title,
                'location': property_analysis.property_location,
                'price': float(property_analysis.asking_price),
                'investment_score': investment_score,
                'recommendation': recommendation,
                'market_percentile': market_position.get('market_percentile', 50),
                'sample_size': market_position.get('sample_size', 0),
                'gross_yield': investment_potential.get('gross_annual_yield', 0),
                'market_temperature': market_momentum.get('market_temperature', 'moderate'),
                'data_sources': data_result.get('data_sources', {})
            }
            
            prompt = f"""
            Write a professional 2-3 sentence investment summary based on these REAL market data points:
            
            Property: {context['property_title']} in {context['location']}
            Price: €{context['price']:,.0f}
            Investment Score: {context['investment_score']}/100 (data-driven)
            Recommendation: {context['recommendation'].replace('_', ' ').title()}
            Market Position: {context['market_percentile']}th percentile among {context['sample_size']} comparable properties
            Rental Yield: {context['gross_yield']:.1f}% annual gross yield
            Market Temperature: {context['market_temperature']}
            Data Sources: {context['data_sources']['comparable_properties']} comparable properties, {context['data_sources']['market_data_points']} market data points
            
            Focus on the most compelling data points and provide actionable insights.
            """
            
            response = self._generate_with_thread_timeout(prompt)
            if response and hasattr(response, 'text'):
                return response.text.strip()
            else:
                return f"Data-driven analysis shows {context['investment_score']}/100 investment score with {context['recommendation'].replace('_', ' ')} recommendation."
        
        except Exception as e:
            logger.error(f"Error generating AI summary from data: {e}")
            return "Comprehensive data-driven analysis completed with market intelligence insights."
    
    def _fallback_ai_analysis(self, property_data, comparable_properties=None):
        """Fallback AI analysis when no database record exists"""
        try:
            # Calculate key metrics from simplified data
            price = property_data.get('price', 0)
            area = property_data.get('square_meters', 0)
            price_per_sqm = (price / area) if area > 0 else 0
            
            prompt = f"""
            ROLE: You are an Albanian real estate investment analyst. Provide a basic analysis based on available data.
            
            PROPERTY DATA:
            Title: {property_data.get('title', '')}
            Location: {property_data.get('location', '')}
            Price: €{price:,}
            Price/m²: €{price_per_sqm:.0f}/m² 
            Type: {property_data.get('property_type', '')}
            Area: {area}m²
            
            COMPARABLE PROPERTIES: {json.dumps(comparable_properties or [], indent=2)}
            
            NOTE: This is a basic analysis without comprehensive market data. For detailed data-driven insights, 
            please use the full property analysis feature.
            
            FORMAT AS JSON:
            {{
                "investment_score": 50,
                "recommendation": "hold",
                "summary": "Basic analysis completed. Use full analysis for detailed insights.",
                "market_insights": ["Limited data available for comprehensive analysis"],
                "risk_factors": ["Insufficient market data for detailed risk assessment"],
                "action_items": ["Schedule full property analysis for detailed insights"]
            }}
            """
            
            response = self._generate_with_thread_timeout(prompt)
            
            if response and hasattr(response, 'text'):
                try:
                    content = response.text
                    data = self._safe_json_loads(content)
                    
                    if not isinstance(data, dict):
                        raise ValueError("Response is not a dictionary")
                    
                    # Ensure minimum required fields
                    if 'investment_score' not in data:
                        data['investment_score'] = 50
                    if 'recommendation' not in data:
                        data['recommendation'] = 'hold'
                    if 'summary' not in data:
                        data['summary'] = 'Basic analysis completed'
                    
                    return {"status": "success", **data}
                except Exception as e:
                    logger.error(f"Error parsing fallback AI response: {e}")
                    
            return {"status": "error", "message": "Fallback analysis failed"}
        
        except Exception as e:
            logger.error(f"Fallback AI analysis failed: {str(e)}")
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
    
    def _convert_decimals_to_float(self, obj):
        """Convert Decimal objects to float for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._convert_decimals_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_float(item) for item in obj]
        elif hasattr(obj, '__class__') and obj.__class__.__name__ == 'Decimal':
            return float(obj)
        else:
            return obj
    
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
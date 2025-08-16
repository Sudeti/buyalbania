import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from .models import PropertyAnalysis
from .market_engines import (
    MarketPositionEngine, 
    AgentPerformanceAnalyzer, 
    NeighborhoodVelocityTracker,
    PropertyScarcityAnalyzer,
    ROICalculator
)

logger = logging.getLogger(__name__)

class DataDrivenAnalyzer:
    """Data-driven property analysis that replaces AI-generated scores with real market intelligence"""
    
    def __init__(self):
        self.market_position = MarketPositionEngine()
        self.agent_analyzer = AgentPerformanceAnalyzer()
        self.velocity_tracker = NeighborhoodVelocityTracker()
        self.scarcity_analyzer = PropertyScarcityAnalyzer()
        self.roi_calculator = ROICalculator()
    
    def analyze_property(self, property_analysis: PropertyAnalysis) -> Dict[str, Any]:
        """Perform comprehensive data-driven analysis"""
        try:
            logger.info(f"Starting data-driven analysis for property {property_analysis.id}")
            
            # 1. Market Position Analysis (Real-time positioning)
            market_position = self.market_position.calculate_property_advantage(property_analysis)
            
            # 2. Agent Performance Intelligence
            agent_insights = self.agent_analyzer.get_agent_insights(property_analysis)
            
            # 3. Neighborhood Velocity Analytics
            market_momentum = self.velocity_tracker.analyze_market_momentum(property_analysis)
            
            # 4. Property Scarcity Scoring
            scarcity_analysis = self.scarcity_analyzer.calculate_scarcity_score(property_analysis)
            
            # 5. ROI Calculator
            investment_potential = self.roi_calculator.calculate_investment_potential(property_analysis)
            
            # 6. Calculate Data-Driven Investment Score
            investment_score = self._calculate_data_driven_score(
                market_position, agent_insights, market_momentum, 
                scarcity_analysis, investment_potential
            )
            
            # 7. Generate Investment Recommendation
            recommendation = self._generate_investment_recommendation(
                investment_score, market_position, market_momentum, investment_potential
            )
            
            # 8. Create Market Insights
            market_insights = self._generate_market_insights(
                market_position, agent_insights, market_momentum, scarcity_analysis, investment_potential, property_analysis
            )
            
            # 9. Generate Risk Assessment
            risk_factors = self._assess_risk_factors(
                market_position, market_momentum, investment_potential, agent_insights, property_analysis
            )
            
            # 10. Create Action Items
            action_items = self._generate_action_items(
                market_position, agent_insights, market_momentum, investment_potential, property_analysis
            )
            
            # Compile comprehensive analysis result
            analysis_result = {
                'status': 'success',
                'investment_score': investment_score,
                'recommendation': recommendation,
                'market_position_analysis': market_position,
                'agent_intelligence': agent_insights,
                'market_momentum': market_momentum,
                'scarcity_analysis': scarcity_analysis,
                'investment_potential': investment_potential,
                'market_insights': market_insights,
                'risk_factors': risk_factors,
                'action_items': action_items,
                'analysis_timestamp': timezone.now().isoformat(),
                'data_sources': {
                    'comparable_properties': market_position.get('sample_size', 0) if market_position else 0,
                    'agent_properties': agent_insights.get('agent_portfolio_size', 0) if agent_insights else 0,
                    'market_data_points': self._count_market_data_points(market_momentum),
                    'analysis_method': 'data_driven'
                }
            }
            
            logger.info(f"Data-driven analysis completed for property {property_analysis.id}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in data-driven analysis: {e}")
            return {
                'status': 'error',
                'message': f'Data-driven analysis failed: {str(e)}'
            }
    
    def _calculate_data_driven_score(self, market_position: Optional[Dict], 
                                   agent_insights: Optional[Dict], 
                                   market_momentum: Dict, 
                                   scarcity_analysis: Dict, 
                                   investment_potential: Dict) -> int:
        """Calculate investment score based on real market data"""
        try:
            score = 50  # Base score
            
            # Market Position Factor (30% weight)
            if market_position:
                percentile = market_position.get('market_percentile', 50)
                if percentile <= 25:
                    score += 25  # Bottom quartile = excellent value
                elif percentile <= 40:
                    score += 15  # Below median = good value
                elif percentile <= 60:
                    score += 5   # Around median = neutral
                elif percentile <= 75:
                    score -= 5   # Above median = overpriced
                else:
                    score -= 15  # Top quartile = significantly overpriced
            
            # Investment Potential Factor (25% weight)
            if investment_potential:
                gross_yield = investment_potential.get('gross_annual_yield', 0)
                if gross_yield >= 7.0:
                    score += 20
                elif gross_yield >= 6.0:
                    score += 15
                elif gross_yield >= 5.0:
                    score += 10
                elif gross_yield >= 4.0:
                    score += 5
                else:
                    score -= 10
            
            # Market Momentum Factor (20% weight)
            if market_momentum:
                temperature = market_momentum.get('market_temperature', 'moderate')
                momentum = market_momentum.get('price_momentum_30d', 0)
                
                if temperature == 'hot' and momentum > 5:
                    score += 15  # Hot market with upward momentum
                elif temperature == 'warm' and momentum > 0:
                    score += 10  # Warm market with positive momentum
                elif temperature == 'moderate':
                    score += 5   # Stable market
                elif temperature == 'cool' and momentum < 0:
                    score -= 10  # Cooling market
            
            # Scarcity Factor (15% weight)
            if scarcity_analysis:
                scarcity_score = scarcity_analysis.get('scarcity_score', 50)
                if scarcity_score >= 80:
                    score += 12
                elif scarcity_score >= 60:
                    score += 8
                elif scarcity_score >= 40:
                    score += 4
                else:
                    score -= 5
            
            # Agent Factor (10% weight)
            if agent_insights:
                negotiation_potential = agent_insights.get('negotiation_potential', 'medium')
                if negotiation_potential == 'high':
                    score += 8
                elif negotiation_potential == 'medium':
                    score += 4
                else:
                    score -= 2
            
            # Normalize score to 0-100 range
            score = max(0, min(100, score))
            
            return int(score)
            
        except Exception as e:
            logger.error(f"Error calculating data-driven score: {e}")
            return 50
    
    def _generate_investment_recommendation(self, investment_score: int, 
                                          market_position: Optional[Dict], 
                                          market_momentum: Dict, 
                                          investment_potential: Dict) -> str:
        """Generate investment recommendation based on data"""
        try:
            # Base recommendation on investment score
            if investment_score >= 80:
                base_recommendation = 'strong_buy'
            elif investment_score >= 65:
                base_recommendation = 'buy'
            elif investment_score >= 45:
                base_recommendation = 'hold'
            else:
                base_recommendation = 'avoid'
            
            # Adjust based on market momentum
            if market_momentum:
                timing = market_momentum.get('timing_recommendation', 'neutral')
                if timing == 'act_fast' and base_recommendation in ['buy', 'strong_buy']:
                    return 'strong_buy'
                elif timing == 'wait_better' and base_recommendation in ['buy', 'strong_buy']:
                    return 'hold'
            
            # Adjust based on market position
            if market_position:
                position_category = market_position.get('position_category', '')
                if position_category == 'bottom_quartile' and base_recommendation == 'buy':
                    return 'strong_buy'
                elif position_category == 'top_quartile' and base_recommendation == 'buy':
                    return 'hold'
            
            return base_recommendation
            
        except Exception as e:
            logger.error(f"Error generating investment recommendation: {e}")
            return 'hold'
    
    def _generate_market_insights(self, market_position: Optional[Dict], 
                                agent_insights: Optional[Dict], 
                                market_momentum: Dict, 
                                scarcity_analysis: Dict, 
                                investment_potential: Dict,
                                property_analysis: PropertyAnalysis) -> List[str]:
        """Generate market insights based on available data"""
        insights = []
        
        # Check data availability
        total_properties = PropertyAnalysis.objects.count()
        completed_analyses = PropertyAnalysis.objects.filter(status='completed').count()
        
        if total_properties < 10:
            insights.append(f"Limited market data available ({total_properties} properties in database). Analysis based on property fundamentals and market estimates.")
        
        # Market Position Insights
        if market_position and market_position.get('sample_size', 0) > 0:
            percentile = market_position.get('market_percentile', 50)
            if percentile <= 25:
                insights.append(f"Property priced in bottom 25% of market - strong value proposition")
            elif percentile <= 40:
                insights.append(f"Property priced below market median - good value opportunity")
            elif percentile >= 75:
                insights.append(f"Property priced in top 25% of market - premium positioning")
        elif market_position and market_position.get('sample_size', 0) == 0:
            insights.append("No comparable properties found in database. Analysis based on property fundamentals.")
        
        # Investment Potential Insights
        if investment_potential:
            gross_yield = investment_potential.get('gross_annual_yield', 0)
            net_yield = investment_potential.get('net_annual_yield', 0)
            
            if gross_yield >= 7.0:
                insights.append(f"Strong rental yield potential at {gross_yield:.1f}% gross yield")
            elif gross_yield >= 6.0:
                insights.append(f"Competitive rental yield at {gross_yield:.1f}% gross yield")
            elif gross_yield < 4.0:
                insights.append(f"Below-average rental yield at {gross_yield:.1f}% - consider appreciation potential")
            
            if net_yield > 5.0:
                insights.append(f"Positive cash flow potential with {net_yield:.1f}% net yield after costs")
        
        # Market Momentum Insights
        if market_momentum:
            temperature = market_momentum.get('market_temperature', 'moderate')
            momentum = market_momentum.get('price_momentum_30d', 0)
            
            if temperature == 'hot':
                insights.append("Market showing high activity - act quickly to secure property")
            elif temperature == 'warm':
                insights.append("Market showing positive momentum - good timing for investment")
            elif temperature == 'cool':
                insights.append("Market showing reduced activity - potential for negotiation")
            
            if momentum > 5:
                insights.append(f"Strong price momentum ({momentum:.1f}% in 30 days) - market heating up")
            elif momentum < -5:
                insights.append(f"Declining prices ({abs(momentum):.1f}% in 30 days) - buyer's market")
        
        # Scarcity Insights
        if scarcity_analysis:
            scarcity_score = scarcity_analysis.get('scarcity_score', 50)
            similar_active = scarcity_analysis.get('similar_active_count', 0)
            
            if scarcity_score >= 80:
                insights.append("Extremely rare property type - limited supply creates premium opportunity")
            elif scarcity_score >= 60:
                insights.append("Property shows unique characteristics - competitive advantage")
            
            if similar_active <= 2:
                insights.append(f"Only {similar_active} similar properties available - low supply")
            elif similar_active >= 10:
                insights.append(f"{similar_active} similar properties available - competitive market")
        
        # Agent Insights
        if agent_insights and agent_insights.get('agent_portfolio_size', 0) > 0:
            portfolio_size = agent_insights.get('agent_portfolio_size', 0)
            agent_vs_market = agent_insights.get('agent_avg_price_vs_market', 0)
            
            if portfolio_size >= 10:
                insights.append(f"Experienced agent with {portfolio_size} properties - professional representation")
            
            if agent_vs_market > 5:
                insights.append(f"Agent typically prices {agent_vs_market:.1f}% above market - negotiation potential")
            elif agent_vs_market < -5:
                insights.append(f"Agent typically prices {abs(agent_vs_market):.1f}% below market - aggressive pricing")
        
        # Property-Specific Insights
        if property_analysis.property_type:
            insights.append(f"{property_analysis.property_type.title()} properties typically offer {self._get_property_type_insight(property_analysis.property_type)}")
        
        if property_analysis.bedrooms and property_analysis.bedrooms >= 3:
            insights.append("3+ bedroom properties have strong rental demand and resale potential")
        
        # Location Insights
        location = property_analysis.property_location.lower()
        if 'tirana' in location:
            insights.append("Tirana market offers strong rental demand and capital appreciation potential")
        elif 'vlorë' in location or 'vlore' in location:
            insights.append("Vlorë coastal location provides seasonal rental opportunities")
        elif 'durrës' in location or 'durres' in location:
            insights.append("Durrës offers good value with proximity to Tirana and coastal access")
        
        # Ensure we have at least 3 insights
        if len(insights) < 3:
            insights.extend([
                "Property fundamentals suggest solid investment potential",
                "Consider professional property inspection before purchase",
                "Verify all legal documentation and property status"
            ])
        
        return insights[:5]  # Limit to 5 insights
    
    def _get_property_type_insight(self, property_type: str) -> str:
        """Get property type specific insights"""
        insights = {
            'apartment': 'stable rental income and moderate appreciation',
            'villa': 'premium rental rates and strong appreciation potential',
            'commercial': 'long-term lease stability and business growth potential',
            'office': 'corporate tenant stability and location-dependent value',
            'studio': 'high rental demand from young professionals and students'
        }
        return insights.get(property_type, 'good investment fundamentals')
    
    def _assess_risk_factors(self, market_position: Optional[Dict], 
                           market_momentum: Dict, 
                           investment_potential: Dict, 
                           agent_insights: Optional[Dict],
                           property_analysis: PropertyAnalysis) -> List[str]:
        """Assess risk factors based on market data"""
        risks = []
        
        # Check data availability
        total_properties = PropertyAnalysis.objects.count()
        if total_properties < 10:
            risks.append("Limited market data available - analysis based on estimates and fundamentals")
        
        # Market position risks
        if market_position and market_position.get('sample_size', 0) > 0:
            percentile = market_position.get('market_percentile', 50)
            if percentile >= 80:
                risks.append("Property priced in top 20% of market - potential overvaluation")
            elif percentile <= 20:
                risks.append("Property priced in bottom 20% - investigate for structural or legal issues")
        elif market_position and market_position.get('sample_size', 0) == 0:
            risks.append("No comparable properties found - difficult to assess fair market value")
        
        # Investment potential risks
        if investment_potential:
            gross_yield = investment_potential.get('gross_annual_yield', 0)
            net_yield = investment_potential.get('net_annual_yield', 0)
            
            if gross_yield < 4.0:
                risks.append(f"Low rental yield ({gross_yield:.1f}%) may not cover mortgage payments")
            
            if net_yield < 3.0:
                risks.append(f"Low net yield ({net_yield:.1f}%) after costs - limited cash flow")
            
            break_even_years = investment_potential.get('break_even_years', 0)
            if break_even_years and break_even_years > 15:
                risks.append(f"Long break-even period ({break_even_years:.1f} years) indicates high investment risk")
        
        # Market momentum risks
        if market_momentum:
            temperature = market_momentum.get('market_temperature', 'moderate')
            momentum = market_momentum.get('price_momentum_30d', 0)
            
            if temperature == 'hot' and momentum > 10:
                risks.append("Rapidly heating market - risk of buying at peak prices")
            elif temperature == 'cool' and momentum < -5:
                risks.append("Declining market conditions - potential for further value decreases")
        
        # Property-specific risks
        if property_analysis.property_type == 'commercial':
            risks.append("Commercial properties have longer vacancy periods and higher tenant turnover")
        
        if property_analysis.property_type == 'villa':
            risks.append("Villas have higher maintenance costs and seasonal rental patterns")
        
        # Location-specific risks
        location = property_analysis.property_location.lower()
        if 'tirana' in location:
            risks.append("Tirana market may be affected by economic policy changes and urban development")
        elif 'vlorë' in location or 'vlore' in location:
            risks.append("Coastal properties have seasonal demand and weather-related risks")
        
        # Agent risks
        if agent_insights and agent_insights.get('agent_portfolio_size', 0) == 0:
            risks.append("Limited agent history - difficult to assess pricing patterns")
        
        # Ensure we have at least 2 risks
        if len(risks) < 2:
            risks.extend([
                "Standard property investment risks apply",
                "Market conditions may change affecting property value"
            ])
        
        return risks[:4]  # Limit to 4 risks
    
    def _generate_action_items(self, market_position: Optional[Dict], 
                             agent_insights: Optional[Dict], 
                             market_momentum: Dict, 
                             investment_potential: Dict,
                             property_analysis: PropertyAnalysis) -> List[str]:
        """Generate actionable recommendations"""
        actions = []
        
        try:
            # Market position actions
            if market_position:
                percentile = market_position.get('market_percentile', 50)
                if percentile <= 25:
                    actions.append("Act quickly - property priced significantly below market")
                elif percentile >= 75:
                    actions.append("Negotiate aggressively - property priced above market average")
            
            # Agent-based actions
            if agent_insights:
                negotiation = agent_insights.get('negotiation_potential', 'medium')
                if negotiation == 'high':
                    actions.append("High negotiation potential - consider offering below asking price")
                elif negotiation == 'low':
                    actions.append("Limited negotiation room - be prepared to pay close to asking price")
            
            # Market timing actions
            if market_momentum:
                timing = market_momentum.get('timing_recommendation', 'neutral')
                if timing == 'act_fast':
                    actions.append("Market timing optimal - act quickly to secure property")
                elif timing == 'wait_better':
                    actions.append("Consider waiting for better market conditions")
            
            # Investment actions
            if investment_potential:
                gross_yield = investment_potential.get('gross_annual_yield', 0)
                if gross_yield >= 6.0:
                    actions.append("Strong rental yield potential - secure financing pre-approval")
                elif gross_yield < 4.0:
                    actions.append("Low yield potential - consider alternative investment strategies")
            
            # Standard actions
            actions.extend([
                "Schedule property viewing to assess condition",
                "Verify all property documentation and legal status",
                "Research local market trends and future development plans"
            ])
            
            return actions[:5]  # Limit to top 5 actions
            
        except Exception as e:
            logger.error(f"Error generating action items: {e}")
            return ["Schedule property viewing", "Conduct due diligence"]
    
    def _count_market_data_points(self, market_momentum: Dict) -> int:
        """Count total market data points used in analysis"""
        try:
            count = 0
            count += market_momentum.get('velocity_30d', 0)
            count += market_momentum.get('velocity_90d', 0) * 3
            count += market_momentum.get('supply_pressure', 0)
            return count
        except Exception:
            return 0

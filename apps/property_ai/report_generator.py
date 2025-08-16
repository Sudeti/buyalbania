import os
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from .models import PropertyAnalysis

logger = logging.getLogger(__name__)

class PropertyReportPDF:
    """
    Generate beautiful PDF property reports from AI analysis data
    """
    
    def __init__(self):
        self.output_dir = os.path.join(settings.MEDIA_ROOT, 'property_reports')
        self._ensure_output_dir()
        
    def _ensure_output_dir(self):
        """Ensure output directory exists"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_pdf_report(self, property_analysis: PropertyAnalysis, 
                      report_content: str = "") -> str:
        """
        Generate comprehensive PDF report from property analysis
        """
        try:
            logger.info(f"Generating PDF for property analysis {property_analysis.id}")
            logger.info(f"Analysis result keys: {list(property_analysis.analysis_result.keys()) if property_analysis.analysis_result else 'None'}")
            
            # Prepare template context - use analysis_result from property_analysis
            context = self._prepare_template_context(property_analysis, report_content)
            
            # Render HTML template
            logger.info(f"Rendering template with context keys: {list(context.keys())}")
            html_content = render_to_string('property_ai/reports/property_report.html', context)
            logger.info(f"Template rendered successfully, HTML length: {len(html_content)}")
            
            # Generate PDF
            pdf_filename = f"property_report_{property_analysis.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            pdf_path = os.path.join(self.output_dir, pdf_filename)
            
            # Create PDF with WeasyPrint
            html_doc = HTML(string=html_content, base_url=settings.STATIC_URL)
            css = CSS(string=self._get_pdf_css())
            
            logger.info(f"Writing PDF to: {pdf_path}")
            html_doc.write_pdf(pdf_path, stylesheets=[css])
            logger.info(f"PDF generated successfully: {pdf_path}")
            
            logger.info(f"Generated PDF report: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            import traceback
            logger.error(f"PDF generation traceback: {traceback.format_exc()}")
            raise
    
    def _prepare_template_context(self, property_analysis: PropertyAnalysis, report_content: str = "") -> Dict[str, Any]:
        # Use analysis_result from property_analysis object (data-driven content)
        analysis_result = property_analysis.analysis_result or {}
        
        logger.info(f"Preparing template context for analysis {property_analysis.id}")
        logger.info(f"Analysis result status: {analysis_result.get('status', 'unknown')}")
        logger.info(f"Investment score: {analysis_result.get('investment_score', 'not set')}")
        logger.info(f"Recommendation: {analysis_result.get('recommendation', 'not set')}")
        
        # Use data-driven analysis results
        summary = analysis_result.get("summary", "")
        if not summary:
            summary = f"This {property_analysis.bedrooms or 'N/A'}-bedroom property in {property_analysis.property_location or 'Albania'} presents a compelling investment opportunity with strong fundamentals and favorable market positioning."
        
        # Get data-driven insights
        market_insights = analysis_result.get('market_insights', [])[:4]  # Limit to 4 items
        risk_factors = analysis_result.get('risk_factors', [])[:3]  # Limit to 3 items
        action_items = analysis_result.get('action_items', [])[:5]  # Limit to 5 items
        
        # Data-driven analysis components - handle None values
        market_position = analysis_result.get('market_position_analysis', {}) or {}
        agent_intelligence = analysis_result.get('agent_intelligence', {}) or {}
        market_momentum = analysis_result.get('market_momentum', {}) or {}
        scarcity_analysis = analysis_result.get('scarcity_analysis', {}) or {}
        investment_potential = analysis_result.get('investment_potential', {}) or {}
        
        # Calculate key metrics for PDF
        price_per_sqm = property_analysis.price_per_sqm or 0
        market_percentile = market_position.get('market_percentile', 50)
        potential_savings = market_position.get('potential_savings', 0)
        sample_size = market_position.get('sample_size', 0)
        
        # Investment metrics
        gross_yield = investment_potential.get('gross_annual_yield', 0)
        net_yield = investment_potential.get('net_annual_yield', 0)
        estimated_rent = investment_potential.get('estimated_monthly_rent', 0)
        total_return_5y = investment_potential.get('projected_5y_total_return', 0)
        
        # Market timing
        market_temperature = market_momentum.get('market_temperature', 'moderate')
        price_momentum = market_momentum.get('price_momentum_30d', 0)
        timing_recommendation = market_momentum.get('timing_recommendation', 'neutral')
        
        # Agent insights
        agent_portfolio_size = agent_intelligence.get('agent_portfolio_size', 0)
        agent_vs_market = agent_intelligence.get('agent_avg_price_vs_market', 0)
        negotiation_potential = agent_intelligence.get('negotiation_potential', 'medium')
        
        # Scarcity metrics
        scarcity_score = scarcity_analysis.get('scarcity_score', 50)
        similar_active = scarcity_analysis.get('similar_active_count', 0)
        historical_demand = scarcity_analysis.get('historical_demand', 0)
        
        return {
            'property_analysis': property_analysis,
            'user': property_analysis.user,
            'analysis_result': analysis_result,
            'summary': summary,
            'investment_score': property_analysis.investment_score or 50,
            'recommendation': property_analysis.recommendation or 'HOLD',
            
            # Data-driven market position
            'market_position': market_position,
            'price_per_sqm': price_per_sqm,
            'market_percentile': market_percentile,
            'potential_savings': potential_savings,
            'sample_size': sample_size,
            
            # Investment potential
            'investment_potential': investment_potential,
            'gross_yield': gross_yield,
            'net_yield': net_yield,
            'estimated_rent': estimated_rent,
            'total_return_5y': total_return_5y,
            
            # Market momentum
            'market_momentum': market_momentum,
            'market_temperature': market_temperature,
            'price_momentum': price_momentum,
            'timing_recommendation': timing_recommendation,
            
            # Agent intelligence
            'agent_intelligence': agent_intelligence,
            'agent_portfolio_size': agent_portfolio_size,
            'agent_vs_market': agent_vs_market,
            'negotiation_potential': negotiation_potential,
            
            # Scarcity analysis
            'scarcity_analysis': scarcity_analysis,
            'scarcity_score': scarcity_score,
            'similar_active': similar_active,
            'historical_demand': historical_demand,
            
            # Legacy support (for backward compatibility)
            'price_analysis': analysis_result.get('price_analysis', {}),
            'rental_analysis': analysis_result.get('rental_analysis', {}),
            
            # Insights and actions
            'market_insights': market_insights,
            'risk_factors': risk_factors,
            'action_items': action_items,
            
            # Report metadata
            'generation_date': datetime.now(),
            'report_id': str(property_analysis.id)[:8].upper(),
            'data_sources': analysis_result.get('data_sources', {}),
        }
    
    def _get_pdf_css(self) -> str:
        """Get CSS styling for PDF report"""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        @page {
            margin: 1.5cm 1.5cm;
            size: A4;
            font-family: 'Inter', 'Helvetica', 'Arial', sans-serif;
        }
        
        body {
            font-family: 'Inter', 'Helvetica', 'Arial', sans-serif;
            line-height: 1.5;
            color: #1e293b;
            font-size: 10px;
            margin: 0;
            padding: 0;
            background: white;
        }
        
        /* Page Layout */
        .page-1, .page-2 {
            page-break-after: always;
            min-height: 100vh;
            position: relative;
        }
        
        .page-2 {
            page-break-before: always;
        }
        
        /* Header */
        .report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }
        
        .logo-section {
            flex: 1;
        }
        
        .logo {
            font-size: 18px;
            font-weight: 800;
            color: #1e40af;
            margin-bottom: 0.25rem;
        }
        
        .tagline {
            font-size: 9px;
            color: #64748b;
            font-weight: 400;
        }
        
        .report-meta {
            text-align: right;
        }
        
        .report-id {
            font-size: 11px;
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 0.25rem;
        }
        
        .date {
            font-size: 9px;
            color: #64748b;
        }
        
        /* Property Header */
        .property-header {
            margin-bottom: 2rem;
        }
        
        .property-title {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 0.5rem 0;
            line-height: 1.3;
        }
        
        .property-location {
            font-size: 11px;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .location-icon {
            font-style: normal;
        }
        
        /* Investment Summary */
        .investment-summary {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .score-card {
            flex: 1;
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .score-label {
            font-size: 9px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
            opacity: 0.9;
        }
        
        .score-value {
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        
        .score-max {
            font-size: 11px;
            opacity: 0.8;
        }
        
        .score-note {
            font-size: 8px;
            color: #64748b;
            margin-top: 0.25rem;
        }
        
        .recommendation-card {
            flex: 1;
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
        }
        
        .recommendation-note {
            font-size: 8px;
            color: #64748b;
            margin-top: 0.25rem;
        }
        
        .recommendation-label {
            font-size: 9px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            margin-bottom: 0.5rem;
        }
        
        .recommendation-value {
            font-size: 18px;
            font-weight: 700;
            color: #059669;
        }
        
        .recommendation-value.sell {
            color: #dc2626;
        }
        
        .recommendation-value.hold {
            color: #d97706;
        }
        
        /* Key Metrics */
        .key-metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        
        .metric-card .metric-value {
            font-size: 14px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }
        
        .metric-card .metric-label {
            font-size: 8px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Section Headers */
        h2 {
            font-size: 14px;
            font-weight: 700;
            color: #0f172a;
            margin: 1.5rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }
        
        /* Executive Summary */
        .executive-summary p {
            font-size: 10px;
            line-height: 1.6;
            color: #374151;
            margin: 0;
        }
        
        /* Market Analysis */
        .market-metrics, .investment-metrics, .momentum-metrics, .agent-metrics, .scarcity-metrics {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .market-metric, .investment-metric, .momentum-metric, .agent-metric, .scarcity-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .market-metric:last-child, .investment-metric:last-child, .momentum-metric:last-child, .agent-metric:last-child, .scarcity-metric:last-child {
            border-bottom: none;
        }
        
        .market-metric .metric-name, .investment-metric .metric-name, .momentum-metric .metric-name, .agent-metric .metric-name, .scarcity-metric .metric-name {
            font-size: 9px;
            color: #64748b;
            font-weight: 500;
        }
        
        .market-metric .metric-value, .investment-metric .metric-value, .momentum-metric .metric-value, .agent-metric .metric-value, .scarcity-metric .metric-value {
            font-size: 10px;
            font-weight: 600;
            color: #1e293b;
        }
        
        /* Investment Metrics Grid */
        .investment-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .investment-metric {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            flex-direction: column;
        }
        
        .investment-metric .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #0369a1;
            margin-bottom: 0.25rem;
        }
        
        .investment-metric .metric-label {
            font-size: 8px;
            color: #0c4a6e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Momentum Metrics Grid */
        .momentum-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .momentum-metric {
            background: #fef3c7;
            border: 1px solid #fbbf24;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            flex-direction: column;
        }
        
        .momentum-metric .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #d97706;
            margin-bottom: 0.25rem;
        }
        
        .momentum-metric .metric-label {
            font-size: 8px;
            color: #92400e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Agent Metrics Grid */
        .agent-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .agent-metric {
            background: #f3e8ff;
            border: 1px solid #c084fc;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            flex-direction: column;
        }
        
        .agent-metric .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #7c3aed;
            margin-bottom: 0.25rem;
        }
        
        .agent-metric .metric-label {
            font-size: 8px;
            color: #5b21b6;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Scarcity Metrics Grid */
        .scarcity-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }
        
        .scarcity-metric {
            background: #ecfdf5;
            border: 1px solid #6ee7b7;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            flex-direction: column;
        }
        
        .scarcity-metric .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #059669;
            margin-bottom: 0.25rem;
        }
        
        .scarcity-metric .metric-label {
            font-size: 8px;
            color: #047857;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Data Sources */
        .data-metrics {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .data-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .data-metric:last-child {
            border-bottom: none;
        }
        
        .data-metric .metric-name {
            font-size: 9px;
            color: #64748b;
            font-weight: 500;
        }
        
        .data-metric .metric-value {
            font-size: 10px;
            font-weight: 600;
            color: #1e293b;
        }
        
        /* Action Items */
        .action-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .action-list li {
            font-size: 9px;
            line-height: 1.5;
            color: #374151;
            padding: 0.25rem 0;
            position: relative;
            padding-left: 1rem;
        }
        
        .action-list li::before {
            content: '→';
            color: #1e40af;
            font-weight: bold;
            position: absolute;
            left: 0;
        }
        
        /* Rental Analysis */
        .rental-metrics {
            display: flex;
            gap: 1rem;
        }
        
        .rental-metric {
            flex: 1;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        
        .rental-metric .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #0369a1;
            margin-bottom: 0.25rem;
        }
        
        .rental-metric .metric-label {
            font-size: 8px;
            color: #0c4a6e;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Lists */
        .insights-list, .risk-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        
        .insights-list li, .risk-list li {
            font-size: 9px;
            line-height: 1.5;
            color: #374151;
            padding: 0.25rem 0;
            position: relative;
            padding-left: 1rem;
        }
        
        .insights-list li::before {
            content: '✓';
            color: #059669;
            font-weight: bold;
            position: absolute;
            left: 0;
        }
        
        .risk-list li::before {
            content: '⚠';
            color: #d97706;
            font-weight: bold;
            position: absolute;
            left: 0;
        }
        
        /* Investment Highlights */
        .highlights-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }
        
        .highlight-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem;
        }
        
        .highlight-icon {
            font-size: 16px;
        }
        
        .highlight-text {
            font-size: 9px;
            font-weight: 500;
            color: #374151;
        }
        
        /* Footer */
        .report-footer {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
            padding: 1rem 0;
        }
        
        .footer-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .footer-left {
            text-align: left;
        }
        
        .footer-right {
            text-align: right;
        }
        
        .company-name {
            font-size: 10px;
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 0.25rem;
        }
        
        .contact-info {
            font-size: 8px;
            color: #64748b;
        }
        
        .report-info {
            font-size: 8px;
            color: #64748b;
            margin-bottom: 0.25rem;
        }
        
        .report-id-footer {
            font-size: 8px;
            color: #1e40af;
            font-weight: 500;
        }
        """
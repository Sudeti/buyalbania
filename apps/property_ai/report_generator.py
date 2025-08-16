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
                      report_content: str) -> str:
        """
        Generate comprehensive PDF report from property analysis
        """
        try:
            # Prepare template context
            context = self._prepare_template_context(property_analysis, report_content)
            
            # Render HTML template
            html_content = render_to_string('property_ai/reports/property_report.html', context)
            
            # Generate PDF
            pdf_filename = f"property_report_{property_analysis.id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            pdf_path = os.path.join(self.output_dir, pdf_filename)
            
            # Create PDF with WeasyPrint
            html_doc = HTML(string=html_content, base_url=settings.STATIC_URL)
            css = CSS(string=self._get_pdf_css())
            
            html_doc.write_pdf(pdf_path, stylesheets=[css])
            
            logger.info(f"Generated PDF report: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            raise
    
    def _prepare_template_context(self, property_analysis: PropertyAnalysis, report_content: str) -> Dict[str, Any]:
        analysis_result = property_analysis.analysis_result or {}
        
        # Ensure we have default values for all fields
        summary = analysis_result.get("summary", "")
        if not summary:
            summary = f"This {property_analysis.bedrooms or 'N/A'}-bedroom property in {property_analysis.property_location or 'Albania'} presents a compelling investment opportunity with strong fundamentals and favorable market positioning."
        
        # Limit market insights and risk factors for compact layout
        market_insights = analysis_result.get('market_insights', [])[:4]  # Limit to 4 items
        risk_factors = analysis_result.get('risk_factors', [])[:3]  # Limit to 3 items
        
        return {
            'property_analysis': property_analysis,
            'user': property_analysis.user,
            'analysis_result': analysis_result,
            'summary': summary,
            'investment_score': property_analysis.investment_score or 85,
            'recommendation': property_analysis.recommendation or 'BUY',
            'price_analysis': analysis_result.get('price_analysis', {}),
            'rental_analysis': analysis_result.get('rental_analysis', {}),
            'market_insights': market_insights,
            'risk_factors': risk_factors,
            'action_items': analysis_result.get('action_items', []),
            'five_year_projection': analysis_result.get('five_year_projection', {}),
            'generation_date': datetime.now(),
            'report_id': str(property_analysis.id)[:8].upper(),
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
        
        .recommendation-card {
            flex: 1;
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
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
        
        /* Price Analysis */
        .price-metrics {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .price-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f1f5f9;
        }
        
        .price-metric:last-child {
            border-bottom: none;
        }
        
        .price-metric .metric-name {
            font-size: 9px;
            color: #64748b;
            font-weight: 500;
        }
        
        .price-metric .metric-value {
            font-size: 10px;
            font-weight: 600;
            color: #1e293b;
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
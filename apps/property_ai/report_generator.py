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
    
    def _get_pdf_css(self) -> str:
        """Get CSS styling for PDF report"""
        return """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        @page {
            margin: 2.5cm 2cm;
            size: A4;
            font-family: 'Inter', 'Helvetica', 'Arial', sans-serif;
            
            @top-center {
                content: "AI Property Analysis Report";
                font-size: 10px;
                color: #64748b;
                font-weight: 500;
            }
            
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9px;
                color: #64748b;
                font-weight: 500;
            }
        }
        
        body {
            font-family: 'Inter', 'Helvetica', 'Arial', sans-serif;
            line-height: 1.6;
            color: #1e293b;
            font-size: 11px;
            margin: 0;
            padding: 0;
        }
        
        /* Cover Page */
        .cover-page {
            text-align: center;
            padding: 4cm 0;
            page-break-after: always;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: -2.5cm -2cm;
            padding: 6cm 4cm 4cm;
        }
        
        .cover-title {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 1rem;
        }
        
        .property-title {
            font-size: 24px;
            font-weight: 400;
            margin-bottom: 2rem;
            opacity: 0.9;
        }
        
        .cover-details {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 2rem;
            margin: 2rem auto;
            max-width: 400px;
        }
        
        /* Headers */
        h1 {
            color: #0f172a;
            font-size: 24px;
            font-weight: 700;
            margin: 2rem 0 1rem 0;
            page-break-after: avoid;
        }
        
        h2 {
            color: #334155;
            font-size: 18px;
            font-weight: 600;
            margin: 1.5rem 0 0.75rem 0;
            page-break-after: avoid;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.5rem;
        }
        
        h3 {
            color: #475569;
            font-size: 14px;
            font-weight: 600;
            margin: 1rem 0 0.5rem 0;
            page-break-after: avoid;
        }
        
        /* Score badges */
        .score-section {
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin: 2rem 0;
            text-align: center;
        }
        
        .investment-score {
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .recommendation {
            font-size: 18px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Analysis sections */
        .analysis-section {
            background: #f8fafc;
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
            page-break-inside: avoid;
        }
        
        .insight-list {
            list-style: none;
            padding: 0;
        }
        
        .insight-item {
            padding: 0.5rem 0;
            border-bottom: 1px solid #e2e8f0;
            position: relative;
            padding-left: 1.5rem;
        }
        
        .insight-item::before {
            content: '•';
            color: #3b82f6;
            font-weight: bold;
            position: absolute;
            left: 0;
        }
        
        /* Tables */
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 10px;
        }
        
        .info-table th,
        .info-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .info-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
        }
        
        /* Footer */
        .report-footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 2px solid #e2e8f0;
            text-align: center;
            color: #6b7280;
            font-size: 9px;
        }
        """
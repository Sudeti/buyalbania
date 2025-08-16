from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.report_generator import PropertyReportPDF
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test PDF generation for data-driven analyses'

    def add_arguments(self, parser):
        parser.add_argument('--analysis-id', type=str, help='Specific analysis ID to test')
        parser.add_argument('--limit', type=int, default=5, help='Number of analyses to test')

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get analyses to test
        if options['analysis_id']:
            analyses = PropertyAnalysis.objects.filter(id=options['analysis_id'])
        else:
            analyses = PropertyAnalysis.objects.filter(
                status='completed',
                analysis_result__isnull=False
            ).exclude(analysis_result={})[:options['limit']]
        
        if not analyses.exists():
            self.stdout.write(self.style.ERROR('No completed analyses found'))
            return
        
        self.stdout.write(f"Testing PDF generation for {analyses.count()} analyses")
        
        pdf_generator = PropertyReportPDF()
        
        for analysis in analyses:
            try:
                self.stdout.write(f"Testing analysis {analysis.id}: {analysis.property_title}")
                
                # Check analysis result
                if not analysis.analysis_result:
                    self.stdout.write(self.style.WARNING(f"  No analysis result for {analysis.id}"))
                    continue
                
                result_keys = list(analysis.analysis_result.keys())
                self.stdout.write(f"  Analysis result keys: {result_keys}")
                
                # Check if it's data-driven
                analysis_method = analysis.analysis_result.get('data_sources', {}).get('analysis_method', 'unknown')
                self.stdout.write(f"  Analysis method: {analysis_method}")
                
                # Try to generate PDF
                try:
                    pdf_path = pdf_generator.generate_pdf_report(analysis)
                    self.stdout.write(self.style.SUCCESS(f"  PDF generated: {pdf_path}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  PDF generation failed: {e}"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing analysis {analysis.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS('PDF generation test completed'))

from django.core.management.base import BaseCommand
from apps.property_ai.models import ScrapingProgress, PropertyAnalysis

class Command(BaseCommand):
    help = 'Show current scraping status'
    
    def handle(self, *args, **options):
        progress = ScrapingProgress.get_current()
        total = PropertyAnalysis.objects.count()
        pending = PropertyAnalysis.objects.filter(status='analyzing').count()
        analyzed = PropertyAnalysis.objects.filter(status='completed').count()
        
        # Fix: Handle division by zero
        completion_percentage = (analyzed / total * 100) if total > 0 else 0.0
        
        self.stdout.write(f"""
📊 Scraping Status:
- Last scraped page: {progress.last_scraped_page}
- Bootstrap complete: {'✅ Yes' if progress.bootstrap_complete else '⏳ In Progress'}
- Total properties: {total:,}
- Pending analysis: {pending:,}
- Analyzed: {analyzed:,}
- Completion: {completion_percentage:.1f}% analyzed
- Last update: {progress.last_update.strftime('%Y-%m-%d %H:%M')}
        """)
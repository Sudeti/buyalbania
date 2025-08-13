from django.core.management.base import BaseCommand
from apps.property_ai.models import ScrapingProgress
from apps.property_ai.tasks import bootstrap_scrape_batch

class Command(BaseCommand):
    help = 'Start or restart the bootstrap scraping process'
    
    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Reset progress and start from page 1')
    
    def handle(self, *args, **options):
        progress = ScrapingProgress.get_current()
        
        if options['reset']:
            progress.last_scraped_page = 0
            progress.bootstrap_complete = False
            progress.save()
            self.stdout.write("🔄 Reset scraping progress")
        
        if progress.bootstrap_complete:
            self.stdout.write("✅ Bootstrap already complete!")
            return
        
        # Kick off the bootstrap
        bootstrap_scrape_batch.delay()
        self.stdout.write("🚀 Bootstrap scraping started!")
        self.stdout.write(f"📍 Will resume from page {progress.last_scraped_page + 1}")
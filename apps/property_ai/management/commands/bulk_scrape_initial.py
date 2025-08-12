# apps/property_ai/management/commands/bulk_scrape_initial.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Initial bulk scraping of all available Century21 properties'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--max-pages', type=int, default=20, help='Max pages for initial scrape')
        parser.add_argument('--analyze', action='store_true', help='Run AI analysis immediately')
        parser.add_argument('--batch-delay', type=int, default=300, help='Delay between batches (seconds)')
        
    def handle(self, *args, **options):
        user = User.objects.get(id=options['user_id'])
        
        self.stdout.write(f"🚀 Starting INITIAL BULK SCRAPE for user: {user.username}")
        self.stdout.write(f"📊 Max pages: {options['max_pages']}")
        self.stdout.write(f"🤖 AI Analysis: {'Enabled' if options['analyze'] else 'Disabled'}")
        
        # Run the scraping in smaller batches to avoid overwhelming the server
        pages_per_batch = 5
        total_batches = (options['max_pages'] + pages_per_batch - 1) // pages_per_batch
        
        for batch_num in range(total_batches):
            start_page = batch_num * pages_per_batch + 1
            end_page = min((batch_num + 1) * pages_per_batch, options['max_pages'])
            
            self.stdout.write(f"\n📦 BATCH {batch_num + 1}/{total_batches}: Pages {start_page}-{end_page}")
            
            try:
                call_command(
                    'scrape_century21_sales',
                    f'--user-id={options["user_id"]}',
                    f'--max-pages={end_page - start_page + 1}',
                    '--analyze' if options['analyze'] else '',  # Pass through analyze flag
                )
                
                # Rest between batches to be respectful to the server
                if batch_num < total_batches - 1:  # Don't wait after the last batch
                    self.stdout.write(f"⏳ Waiting {options['batch_delay']} seconds before next batch...")
                    time.sleep(options['batch_delay'])
                    
            except Exception as e:
                self.stdout.write(f"❌ Batch {batch_num + 1} failed: {e}")
                continue
        
        self.stdout.write(f"\n🎉 INITIAL BULK SCRAPE COMPLETED!")
        
        # Show summary with neighborhood data
        from apps.property_ai.models import PropertyAnalysis
        total_properties = PropertyAnalysis.objects.filter(scraped_by=user).count()
        completed_analyses = PropertyAnalysis.objects.filter(scraped_by=user, status='completed').count()
        with_neighborhoods = PropertyAnalysis.objects.filter(scraped_by=user, neighborhood__isnull=False).exclude(neighborhood='').count()

        self.stdout.write(f"📊 Total properties scraped: {total_properties}")
        self.stdout.write(f"🏘️ Properties with neighborhoods: {with_neighborhoods}")
        self.stdout.write(f"🤖 Completed analyses: {completed_analyses}")
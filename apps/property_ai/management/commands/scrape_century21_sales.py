# Updated management command - simplified with neighborhood fix
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.scrapers import Century21AlbaniaScraper
import time
import random

User = get_user_model()

# apps/property_ai/management/commands/scrape_century21_sales.py
class Command(BaseCommand):
    help = 'Scrape Century21 Albania sale properties - SIMPLIFIED'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--max-pages', type=int, default=5)
        parser.add_argument('--analyze', action='store_true', help='Run AI analysis immediately')
    
    def handle(self, *args, **options):
        user = User.objects.get(id=options['user_id'])
        scraper = Century21AlbaniaScraper()
        
        self.stdout.write(f"🏠 Scraping for user: {user.username}")
        
        # Get property URLs
        urls = scraper.get_sale_property_listings(max_pages=options['max_pages'])
        self.stdout.write(f"📋 Found {len(urls)} URLs")
        
        successful = 0
        failed = 0
        
        for i, url in enumerate(urls, 1):
            self.stdout.write(f"⚡ {i}/{len(urls)}: {url}")
            
            # Skip if exists globally
            if PropertyAnalysis.objects.filter(property_url=url).exists():
                self.stdout.write("  ⏭️ Already exists")
                continue
            
            # Scrape
            data = scraper.scrape_property(url)
            
            if data and data['price'] > 0:
                try:
                    analysis = PropertyAnalysis.objects.create(
                        user=None,  # Admin scrapes have no specific user
                        scraped_by=user,  # Track who scraped it
                        property_url=data['url'],
                        property_title=data['title'],
                        property_location=data['location'],
                        neighborhood=data.get('neighborhood', ''),
                        asking_price=data['price'],
                        property_type=data['property_type'],
                        total_area=data['square_meters'],
                        property_condition=data['condition'],
                        floor_level=data['floor_level'],
                        status='analyzing'
                    )
                    
                    area_info = f"{data['square_meters']}m²" if data['square_meters'] else "No area"
                    price_per_sqm = f"€{int(data['price']/data['square_meters'])}/m²" if data['square_meters'] else ""
                    neighborhood_info = f" | {data['neighborhood']}" if data.get('neighborhood') else ""
                    
                    self.stdout.write(f"  ✅ {data['title'][:40]}... - €{data['price']:,} | {area_info} {price_per_sqm}{neighborhood_info}")
                    
                    # Run analysis if requested
                    if options['analyze']:
                        from apps.property_ai.tasks import analyze_property_task
                        analyze_property_task.delay(analysis.id)
                        self.stdout.write("    🤖 Queued for AI analysis")
                    
                    successful += 1
                    
                except Exception as e:
                    self.stdout.write(f"  ❌ DB error: {e}")
                    failed += 1
            else:
                self.stdout.write("  ❌ No valid data")
                failed += 1
            
            time.sleep(random.uniform(2, 4))
        
        self.stdout.write(f"\n🎉 Done! ✅ {successful} ❌ {failed}")
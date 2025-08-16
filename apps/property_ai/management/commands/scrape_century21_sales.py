# apps/property_ai/management/commands/scrape_century21_sales.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.scrapers import Century21AlbaniaScraper
import time
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Scrape Century21 Albania sale properties with agent data'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--max-pages', type=int, default=5)
        parser.add_argument('--analyze', action='store_true', help='Run AI analysis immediately')
        parser.add_argument('--delay', type=float, default=2.5, help='Delay between requests')
    
    def handle(self, *args, **options):
        user = User.objects.get(id=options['user_id'])
        scraper = Century21AlbaniaScraper()
        
        self.stdout.write(f"🏠 Scraping for user: {user.username}")
        self.stdout.write(f"📄 Max pages: {options['max_pages']}")
        self.stdout.write(f"⏱️ Delay: {options['delay']}s")
        
        # Get property URLs
        urls = scraper.get_sale_property_listings(max_pages=options['max_pages'])
        self.stdout.write(f"📋 Found {len(urls)} URLs")
        
        successful = 0
        failed = 0
        with_agents = 0
        
        for i, url in enumerate(urls, 1):
            self.stdout.write(f"⚡ {i}/{len(urls)}: {url}")
            
            # Skip if exists globally
            if PropertyAnalysis.objects.filter(property_url=url).exists():
                self.stdout.write("  ⭐ Already exists")
                continue
            
            # Scrape with agent data
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
                        total_area=data['total_area'],
                        internal_area=data.get('internal_area'),
                        bedrooms=data.get('bedrooms'),
                        property_condition=data['condition'],
                        floor_level=data['floor_level'],
                        # Agent fields
                        agent_name=data.get('agent_name', ''),
                        agent_email=data.get('agent_email', ''),
                        agent_phone=data.get('agent_phone', ''),
                        status='analyzing'
                    )
                    
                    # Enhanced logging with new data
                    area_info = f"{data['total_area']}m²" if data['total_area'] else "No area"
                    if data.get('internal_area'):
                        area_info += f" ({data['internal_area']}m² internal)"
                    if data.get('bedrooms'):
                        area_info += f" | {data['bedrooms']}BR"
                    
                    price_per_sqm = f"€{int(data['price']/data['total_area'])}/m²" if data['total_area'] else ""
                    neighborhood_info = f" | {data['neighborhood']}" if data.get('neighborhood') else ""
                    
                    # Agent info
                    agent_info = ""
                    if data.get('agent_name'):
                        agent_info = f" | 🧑‍💼 {data['agent_name']}"
                        if data.get('agent_email'):
                            agent_info += f" ({data['agent_email']})"
                        with_agents += 1
                    
                    self.stdout.write(f"  ✅ {data['title'][:40]}... - €{data['price']:,} | {area_info} {price_per_sqm}{neighborhood_info}{agent_info}")
                    
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
            
            time.sleep(random.uniform(options['delay']-0.5, options['delay']+0.5))
        
        self.stdout.write(f"\n🎉 SCRAPING COMPLETE!")
        self.stdout.write(f"✅ Successful: {successful}")
        self.stdout.write(f"❌ Failed: {failed}")
        self.stdout.write(f"🧑‍💼 With Agent Info: {with_agents}")
        
        # Show agent statistics
        if with_agents > 0:
            self.show_agent_stats()
    
    def show_agent_stats(self):
        """Show quick agent statistics"""
        from django.db.models import Count
        
        agent_stats = PropertyAnalysis.objects.filter(
            agent_name__isnull=False
        ).exclude(
            agent_name=''
        ).values('agent_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        if agent_stats:
            self.stdout.write("\n🏆 TOP AGENTS BY LISTINGS:")
            for i, stat in enumerate(agent_stats, 1):
                self.stdout.write(f"  {i}. {stat['agent_name']}: {stat['count']} properties")
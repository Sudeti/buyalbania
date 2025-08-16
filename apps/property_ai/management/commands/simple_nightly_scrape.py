# apps/property_ai/management/commands/simple_nightly_scrape.py
"""
Ultra-simple nightly scraping with hardcoded page ranges by day of week.

This is the simplest possible approach - no cache, no tracking, just hardcoded ranges:

- Sunday: Pages 1-100
- Monday: Pages 101-200  
- Tuesday: Pages 201-300
- Wednesday: Pages 301-400
- Thursday: Pages 401-500
- Friday: Pages 501-600
- Saturday: Pages 601-700

Then it repeats the cycle. Super simple!
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.scrapers import Century21AlbaniaScraper
import time
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Ultra-simple nightly scraping with hardcoded day-based page ranges'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=False, help='User ID for tracking')
        parser.add_argument('--delay', type=float, default=6.0, help='Delay between requests')
        parser.add_argument('--ultra-safe', action='store_true', help='Ultra-safe mode with longer delays')
        parser.add_argument('--force-day', type=str, choices=['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'], help='Force a specific day')
        parser.add_argument('--test', action='store_true', help='Test mode - scrape only 1 page')
        
    def handle(self, *args, **options):
        # Handle optional user
        user = None
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                self.stdout.write(f"❌ User with ID {options['user_id']} not found")
                return
        else:
            self.stdout.write("ℹ️ No user specified - running as system scrape")
        
        # Enhanced safety for ultra-safe mode
        if options['ultra_safe']:
            options['delay'] = max(options['delay'], 8.0)
            self.stdout.write("🛡️ ULTRA-SAFE MODE: Maximum protection enabled")
        
        # Get page range based on day of week
        if options['force_day']:
            day_name = options['force_day']
            self.stdout.write(f"🔄 FORCED DAY: {day_name.title()}")
        else:
            day_name = datetime.now().strftime('%A').lower()
        
        start_page, end_page = self.get_page_range_for_day(day_name)
        
        # Test mode - only scrape 1 page
        if options['test']:
            end_page = start_page
            self.stdout.write("🧪 TEST MODE: Scraping only 1 page")
        
        pages_to_scrape = end_page - start_page + 1
        
        self.stdout.write(f"🌙 ULTRA-SIMPLE NIGHTLY SCRAPE")
        self.stdout.write(f"👤 User: {user.username if user else 'System'}")
        self.stdout.write(f"📅 Day: {day_name.title()}")
        self.stdout.write(f"📄 Pages: {start_page} to {end_page} ({pages_to_scrape} pages)")
        self.stdout.write(f"⏰ Delay: {options['delay']}s")
        self.stdout.write(f"🎯 Expected properties: ~{pages_to_scrape * 12}")
        
        # Calculate estimated time
        estimated_requests = pages_to_scrape * 12
        estimated_time_minutes = (estimated_requests * options['delay']) / 60
        self.stdout.write(f"⏱️ Estimated time: ~{estimated_time_minutes:.1f} minutes")
        
        start_time = time.time()
        
        # Initialize scraper
        scraper = Century21AlbaniaScraper()
        
        # Collect URLs for the specified page range
        self.stdout.write(f"\n📋 Collecting URLs from pages {start_page}-{end_page}...")
        
        try:
            all_urls = self.get_urls_for_page_range(scraper, start_page, end_page, options['delay'])
            
            if not all_urls:
                self.stdout.write("❌ No URLs collected - possible blocking detected")
                return
                
            self.stdout.write(f"✅ Collected {len(all_urls)} URLs successfully")
            
        except Exception as e:
            self.stdout.write(f"❌ URL collection failed: {e}")
            return
        
        # Filter existing URLs
        existing_urls = set(PropertyAnalysis.objects.values_list('property_url', flat=True))
        new_urls = [url for url in all_urls if url not in existing_urls]
        
        self.stdout.write(f"🆕 New URLs to scrape: {len(new_urls)}")
        self.stdout.write(f"⚠️ Already exist: {len(all_urls) - len(new_urls)}")
        
        if len(new_urls) == 0:
            self.stdout.write("✅ No new properties to scrape - all already exist")
            return
        
        # Scrape properties
        self.stdout.write(f"\n🕷️ Scraping properties...")
        
        successful = 0
        failed = 0
        
        for i, url in enumerate(new_urls, 1):
            try:
                # Progress indicator
                if i % 25 == 0:
                    progress = (i / len(new_urls)) * 100
                    elapsed = time.time() - start_time
                    eta = (elapsed / i) * (len(new_urls) - i)
                    self.stdout.write(f"📈 Progress: {progress:.1f}% | ETA: {int(eta/60)}m | Success: {successful}")
                
                # Human-like breaks
                if i > 1 and i % 50 == 0:
                    break_time = random.uniform(120, 300)  # 2-5 minute break
                    self.stdout.write(f"😴 Human-like break: {break_time:.0f}s")
                    time.sleep(break_time)
                
                # Scrape property
                data = scraper.scrape_property(url)
                
                if data and data['price'] > 0:
                    # Create property
                    PropertyAnalysis.objects.create(
                        user=None,
                        scraped_by=user,
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
                        agent_name=data.get('agent_name', ''),
                        agent_email=data.get('agent_email', ''),
                        agent_phone=data.get('agent_phone', ''),
                        status='analyzing'
                    )
                    
                    successful += 1
                    
                    # Enhanced logging
                    area_info = f"{data['total_area']}m²"
                    if data.get('internal_area'):
                        area_info += f" ({data['internal_area']}m² internal)"
                    if data.get('bedrooms'):
                        area_info += f" | {data['bedrooms']}BR"
                    
                    neighborhood_info = f" | {data.get('neighborhood', '')}" if data.get('neighborhood') else ""
                    agent_info = f" | Agent: {data.get('agent_name', 'N/A')}"
                    
                    self.stdout.write(f"  ✅ {i}/{len(new_urls)}: €{data['price']:,} - {data['title'][:30]}... | {area_info}{neighborhood_info}{agent_info}")
                    
                else:
                    failed += 1
                    self.stdout.write(f"  ❌ {i}/{len(new_urls)}: No valid data")
                
                # Dynamic delay
                base_delay = options['delay']
                jitter = random.uniform(1.0, 4.0)
                fatigue_factor = 1 + (i / len(new_urls)) * 0.8
                
                if random.random() < 0.1:  # 10% chance of longer delay
                    jitter += random.uniform(5.0, 15.0)
                
                actual_delay = (base_delay + jitter) * fatigue_factor
                time.sleep(actual_delay)
                
            except Exception as e:
                failed += 1
                self.stdout.write(f"  ❌ {i}/{len(new_urls)}: Error - {str(e)[:50]}")
                
                # Longer delay after errors
                error_delay = options['delay'] * random.uniform(2.0, 4.0)
                time.sleep(error_delay)
        
        total_time = time.time() - start_time
        
        self.stdout.write(f"\n🎉 NIGHTLY SCRAPE COMPLETED!")
        self.stdout.write(f"⏱️ Total time: {int(total_time/60)}m {int(total_time%60)}s")
        self.stdout.write(f"✅ Successful: {successful}")
        self.stdout.write(f"❌ Failed: {failed}")
        self.stdout.write(f"📊 Success rate: {successful/(successful+failed)*100:.1f}%")
        
        # Show what's next
        next_day, next_start, next_end = self.get_next_day_info(day_name)
        self.stdout.write(f"🔄 Next run ({next_day}): pages {next_start} to {next_end}")
        
        # Show final stats
        self.show_final_stats()
    
    def get_page_range_for_day(self, day_name):
        """Get page range for a specific day of the week"""
        # Hardcoded page ranges - super simple!
        day_ranges = {
            'sunday': (1, 100),
            'monday': (101, 200),
            'tuesday': (201, 300),
            'wednesday': (301, 400),
            'thursday': (401, 500),
            'friday': (501, 600),
            'saturday': (601, 700),
        }
        
        return day_ranges.get(day_name, (1, 100))
    
    def get_next_day_info(self, current_day):
        """Get info about the next day's scraping"""
        days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        current_index = days.index(current_day)
        next_index = (current_index + 1) % 7
        next_day = days[next_index]
        next_start, next_end = self.get_page_range_for_day(next_day)
        return next_day, next_start, next_end
    
    def get_urls_for_page_range(self, scraper, start_page, end_page, delay):
        """Get URLs for a specific page range"""
        all_urls = []
        
        for page in range(start_page, end_page + 1):
            try:
                if page == 1:
                    url = f"{scraper.base_url}/properties"
                else:
                    url = f"{scraper.base_url}/properties?page={page}"
                
                response = scraper.session.get(url, timeout=30)
                
                # Safety checks
                if response.status_code == 429:
                    self.stdout.write(f"⚠️ Rate limited on page {page} - backing off")
                    time.sleep(300)  # 5 min cooldown
                    continue
                
                if response.status_code != 200:
                    self.stdout.write(f"⚠️ Page {page}: HTTP {response.status_code}")
                    continue
                
                if "captcha" in response.text.lower():
                    self.stdout.write(f"🛑 CAPTCHA detected on page {page} - stopping")
                    break
                
                page_urls = scraper._extract_urls_from_page(response.content, url)
                
                if not page_urls:
                    self.stdout.write(f"⚠️ Page {page}: No URLs found - possible end of listings")
                    break
                
                all_urls.extend(page_urls)
                self.stdout.write(f"📄 Page {page}: {len(page_urls)} URLs")
                
                # Respectful delay between page requests
                time.sleep(random.uniform(delay, delay + 1.0))
                
            except Exception as e:
                self.stdout.write(f"❌ Page {page} failed: {e}")
                time.sleep(delay * 2)
                continue
        
        return all_urls
    
    def show_final_stats(self):
        """Show comprehensive statistics"""
        total = PropertyAnalysis.objects.count()
        with_agents = PropertyAnalysis.objects.exclude(agent_name='').count()
        with_phones = PropertyAnalysis.objects.exclude(agent_phone='').count()
        with_internal_area = PropertyAnalysis.objects.exclude(internal_area__isnull=True).count()
        with_bedrooms = PropertyAnalysis.objects.exclude(bedrooms__isnull=True).count()
        with_neighborhood = PropertyAnalysis.objects.exclude(neighborhood='').count()
        
        self.stdout.write(f"\n📊 DATABASE SUMMARY:")
        self.stdout.write(f"🏠 Total properties: {total:,}")
        self.stdout.write(f"👨‍💼 With agent names: {with_agents:,} ({with_agents/total*100:.1f}%)")
        self.stdout.write(f"📞 With agent phones: {with_phones:,} ({with_phones/total*100:.1f}%)")
        self.stdout.write(f"📐 With internal area: {with_internal_area:,} ({with_internal_area/total*100:.1f}%)")
        self.stdout.write(f"🛏️ With bedrooms: {with_bedrooms:,} ({with_bedrooms/total*100:.1f}%)")
        self.stdout.write(f"📍 With neighborhood: {with_neighborhood:,} ({with_neighborhood/total*100:.1f}%)")

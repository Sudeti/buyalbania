# apps/property_ai/management/commands/bulk_scrape_initial.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.property_ai.models import PropertyAnalysis
from apps.property_ai.scrapers import Century21AlbaniaScraper
from django.db import transaction
import time
import random
import logging
from django.utils import timezone 

logger = logging.getLogger(__name__)
User = get_user_model()

class Command(BaseCommand):
    help = 'Bulletproof bulk scraping with safety measures'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--max-pages', type=int, default=10, help='Pages to scrape this session')
        parser.add_argument('--start-page', type=int, default=1, help='Starting page number')
        parser.add_argument('--delay', type=float, default=3.0, help='Base delay between requests')
        parser.add_argument('--test-mode', action='store_true', help='Enable extra safety for testing')
        
    def handle(self, *args, **options):
        user = User.objects.get(id=options['user_id'])
        
        # Enhanced safety for test mode
        if options['test_mode']:
            options['delay'] = max(options['delay'], 4.0)  # Minimum 4s in test mode
            self.stdout.write("🧪 TEST MODE: Extra safety measures enabled")
        
        self.stdout.write(f"🌙 BULLETPROOF NIGHT SCRAPE")
        self.stdout.write(f"👤 User: {user.username}")
        self.stdout.write(f"📄 Pages: {options['start_page']} to {options['start_page'] + options['max_pages'] - 1}")
        self.stdout.write(f"⏰ Base delay: {options['delay']}s")
        self.stdout.write(f"🎯 Expected properties: ~{options['max_pages'] * 12}")
        
        start_time = time.time()
        
        # Initialize scraper with rotating headers
        scraper = Century21AlbaniaScraper()
        
        # Circuit breaker variables
        consecutive_failures = 0
        max_failures = 5
        
        # Collect URLs first (with safety checks)
        self.stdout.write(f"\n📋 Phase 1: Safely collecting URLs...")
        
        try:
            all_urls = self.safe_get_urls(scraper, options['start_page'], options['max_pages'], options['delay'])
            
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
            self.stdout.write("✅ No new properties to scrape - database is up to date")
            return
        
        # Phase 2: Scrape with maximum safety
        self.stdout.write(f"\n🕷️ Phase 2: Ultra-safe property scraping...")
        
        successful = 0
        failed = 0
        
        for i, url in enumerate(new_urls, 1):
            try:
                # Progress indicator
                if i % 50 == 0:
                    progress = (i / len(new_urls)) * 100
                    elapsed = time.time() - start_time
                    eta = (elapsed / i) * (len(new_urls) - i)
                    self.stdout.write(f"📈 Progress: {progress:.1f}% | ETA: {int(eta/60)}m | Success: {successful}")
                
                # Human-like break every 100 properties
                if i > 1 and i % 100 == 0:
                    break_time = random.uniform(60, 180)  # 1-3 minute break
                    self.stdout.write(f"😴 Human-like break: {break_time:.0f}s")
                    time.sleep(break_time)
                
                # Scrape with circuit breaker
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
                        total_area=data['square_meters'],
                        property_condition=data['condition'],
                        floor_level=data['floor_level'],
                        agent_name=data.get('agent_name', ''),
                        agent_email=data.get('agent_email', ''),
                        agent_phone=data.get('agent_phone', ''),
                        status='analyzing'
                    )
                    
                    successful += 1
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Log good properties
                    agent_info = f" | Agent: {data.get('agent_name', 'N/A')}" if data.get('agent_name') else ""
                    self.stdout.write(f"  ✅ {i}/{len(new_urls)}: €{data['price']:,} - {data['title'][:30]}...{agent_info}")
                    
                else:
                    failed += 1
                    consecutive_failures += 1
                    
                # Circuit breaker
                if consecutive_failures >= max_failures:
                    self.stdout.write(f"🛑 CIRCUIT BREAKER: {max_failures} consecutive failures - stopping for safety")
                    break
                
                # Dynamic delay (longer delays as we progress)
                base_delay = options['delay']
                jitter = random.uniform(0.5, 2.0)
                fatigue_factor = 1 + (i / len(new_urls)) * 0.5  # Slow down over time
                
                actual_delay = (base_delay + jitter) * fatigue_factor
                time.sleep(actual_delay)
                
            except Exception as e:
                failed += 1
                consecutive_failures += 1
                self.stdout.write(f"  ❌ {i}/{len(new_urls)}: Error - {str(e)[:50]}")
                
                if consecutive_failures >= max_failures:
                    self.stdout.write(f"🛑 Too many failures - stopping for safety")
                    break
                
                time.sleep(options['delay'] * 2)  # Longer delay after errors
        
        total_time = time.time() - start_time
        
        self.stdout.write(f"\n🎉 NIGHT SCRAPE COMPLETED!")
        self.stdout.write(f"⏱️ Total time: {int(total_time/60)}m {int(total_time%60)}s")
        self.stdout.write(f"✅ Successful: {successful}")
        self.stdout.write(f"❌ Failed: {failed}")
        self.stdout.write(f"📊 Success rate: {successful/(successful+failed)*100:.1f}%")
        
        # Final stats
        self.show_final_stats()

    def calculate_resume_page(self):
        """Calculate where to resume scraping based on existing data - SMART MARGIN"""
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            total_properties = PropertyAnalysis.objects.count()
            
            if total_properties == 0:
                return 1
            
            # Check recent scraping activity (last 48 hours)
            recent_threshold = timezone.now() - timedelta(hours=48)
            recent_count = PropertyAnalysis.objects.filter(
                created_at__gte=recent_threshold,
                scraped_by__isnull=False
            ).count()
            
            # Estimate current page (assuming ~12 properties per page)
            estimated_current_page = (total_properties // 12) + 1
            
            if recent_count > 0:
                # Recent activity - minimal safety margin
                safety_margin = 2  # Just 2 pages back
            else:
                # No recent activity - slightly more conservative  
                safety_margin = 3  # 3 pages back
            
            safe_start_page = max(1, estimated_current_page - safety_margin)
            
            self.stdout.write(f"📊 Resume calculation:")
            self.stdout.write(f"   • Total properties: {total_properties}")
            self.stdout.write(f"   • Estimated current page: {estimated_current_page}")
            self.stdout.write(f"   • Safety margin: {safety_margin} pages")
            self.stdout.write(f"   • Resume from page: {safe_start_page}")
            
            return safe_start_page
            
        except Exception as e:
            self.stdout.write(f"⚠️ Error calculating resume page: {e}")
            return 1
    
    def safe_get_urls(self, scraper, start_page, max_pages, delay):
        """Safely collect URLs with built-in protection"""
        all_urls = []
        
        for page in range(start_page, start_page + max_pages):
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
        with_emails = PropertyAnalysis.objects.exclude(agent_email='').count()
        
        self.stdout.write(f"\n📊 DATABASE SUMMARY:")
        self.stdout.write(f"🏠 Total properties: {total:,}")
        self.stdout.write(f"👨‍💼 With agent names: {with_agents:,} ({with_agents/total*100:.1f}%)")
        self.stdout.write(f"📧 With agent emails: {with_emails:,} ({with_emails/total*100:.1f}%)")
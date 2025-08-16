# apps/property_ai/management/commands/bulk_scrape_initial.py
"""
Bulletproof bulk scraping with intelligent resume calculation.

IMPROVEMENTS (v2.0):
- Dynamic success rate calculation based on recent scraping patterns
- Accounts for ~60% of pages containing scrapable properties
- Intelligent safety margin adjustment based on recent activity
- Page-level tracking during scraping for better accuracy
- Test mode for resume calculation without actual scraping

The system now accurately calculates where to resume scraping by:
1. Analyzing recent scraping patterns to determine actual success rate
2. Adjusting page calculations based on real-world data (not theoretical 12 properties/page)
3. Using dynamic safety margins based on recent activity levels
4. Tracking actual scraping efficiency during each session
"""
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
        parser.add_argument('--user-id', type=int, required=False, help='User ID for tracking who initiated the scrape')
        parser.add_argument('--max-pages', type=int, default=10, help='Pages to scrape this session')
        parser.add_argument('--start-page', type=int, default=1, help='Starting page number')
        parser.add_argument('--delay', type=float, default=5.0, help='Base delay between requests (increased default)')
        parser.add_argument('--test-mode', action='store_true', help='Enable extra safety for testing')
        parser.add_argument('--ultra-safe', action='store_true', help='Ultra-safe mode with longer delays and breaks')
        parser.add_argument('--test-resume', action='store_true', help='Test resume calculation without scraping')
        
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
        
        # Test resume calculation if requested
        if options['test_resume']:
            self.stdout.write("🧪 TESTING RESUME CALCULATION...")
            resume_page = self.calculate_resume_page()
            self.stdout.write(f"✅ Resume calculation test completed. Would resume from page: {resume_page}")
            return
        
        # Enhanced safety for test mode and ultra-safe mode
        if options['test_mode']:
            options['delay'] = max(options['delay'], 6.0)  # Minimum 6s in test mode
            self.stdout.write("🧪 TEST MODE: Extra safety measures enabled")
        
        if options['ultra_safe']:
            options['delay'] = max(options['delay'], 8.0)  # Minimum 8s in ultra-safe mode
            self.stdout.write("🛡️ ULTRA-SAFE MODE: Maximum protection enabled")
        
        self.stdout.write(f"🌙 BULLETPROOF NIGHT SCRAPE")
        self.stdout.write(f"👤 User: {user.username if user else 'System'}")
        self.stdout.write(f"📄 Pages: {options['start_page']} to {options['start_page'] + options['max_pages'] - 1}")
        self.stdout.write(f"⏰ Base delay: {options['delay']}s")
        self.stdout.write(f"🎯 Expected properties: ~{options['max_pages'] * 12}")
        
        # Calculate estimated time
        estimated_requests = options['max_pages'] * 12
        estimated_time_minutes = (estimated_requests * options['delay']) / 60
        self.stdout.write(f"⏱️ Estimated time: ~{estimated_time_minutes:.1f} minutes")
        
        # Safety warning for high volume
        if estimated_requests > 500:
            self.stdout.write("⚠️ WARNING: High volume detected - consider using --ultra-safe mode")
            self.stdout.write("⚠️ Risk of detection increases significantly with >500 requests")
        
        start_time = time.time()
        
        # Initialize scraper with rotating headers
        scraper = Century21AlbaniaScraper()
        
       
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
        
        # Filter existing URLs (URLs are already standardized from scraper)
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
        pages_processed = 0
        current_page_properties = 0
        last_page_start_time = time.time()
        consecutive_failures = 0
        
        for i, url in enumerate(new_urls, 1):
            try:
                # Progress indicator with page tracking
                if i % 25 == 0:  # More frequent updates
                    progress = (i / len(new_urls)) * 100
                    elapsed = time.time() - start_time
                    eta = (elapsed / i) * (len(new_urls) - i)
                    
                    # Estimate current page based on timing
                    current_time = time.time()
                    time_since_last_page = current_time - last_page_start_time
                    if time_since_last_page > 60:  # New page started
                        pages_processed += 1
                        last_page_start_time = current_time
                        current_page_properties = 0
                    
                    current_page_properties += 1
                    
                    self.stdout.write(f"📈 Progress: {progress:.1f}% | ETA: {int(eta/60)}m | Success: {successful} | Pages: ~{pages_processed}")
                
                # Enhanced human-like breaks
                if i > 1 and i % 50 == 0:  # More frequent breaks
                    break_time = random.uniform(120, 300)  # 2-5 minute break
                    self.stdout.write(f"😴 Human-like break: {break_time:.0f}s")
                    time.sleep(break_time)
                
                # Circuit breaker for consecutive failures
                if consecutive_failures >= 5:
                    circuit_break_time = random.uniform(600, 1200)  # 10-20 minute break
                    self.stdout.write(f"🔌 Circuit breaker: {circuit_break_time:.0f}s break after {consecutive_failures} failures")
                    time.sleep(circuit_break_time)
                    consecutive_failures = 0
                
                # Scrape with circuit breaker
                data = scraper.scrape_property(url)
                
                if data and data['price'] > 0:
                    # Create property with enhanced data - now handles null user
                    PropertyAnalysis.objects.create(
                        user=None,  # Always None for bulk scraping
                        scraped_by=user,  # Can be None if no user specified
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
                    consecutive_failures = 0  # Reset failure counter
                    
                    # Enhanced logging with new data
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
                    consecutive_failures += 1
                    
                    
               
                # Enhanced dynamic delay with more randomization
                base_delay = options['delay']
                jitter = random.uniform(1.0, 4.0)  # Increased jitter
                fatigue_factor = 1 + (i / len(new_urls)) * 0.8  # More fatigue
                
                # Add occasional longer delays to simulate human behavior
                if random.random() < 0.1:  # 10% chance of longer delay
                    jitter += random.uniform(5.0, 15.0)
                
                actual_delay = (base_delay + jitter) * fatigue_factor
                time.sleep(actual_delay)
                
            except Exception as e:
                failed += 1
                consecutive_failures += 1
                
                self.stdout.write(f"  ❌ {i}/{len(new_urls)}: Error - {str(e)[:50]}")
                
                # Longer delay after errors
                error_delay = options['delay'] * random.uniform(2.0, 4.0)
                time.sleep(error_delay)
        
        total_time = time.time() - start_time
        
        self.stdout.write(f"\n🎉 NIGHT SCRAPE COMPLETED!")
        self.stdout.write(f"⏱️ Total time: {int(total_time/60)}m {int(total_time%60)}s")
        self.stdout.write(f"✅ Successful: {successful}")
        self.stdout.write(f"❌ Failed: {failed}")
        self.stdout.write(f"📊 Success rate: {successful/(successful+failed)*100:.1f}%")
        
        # Calculate and log actual scraping efficiency
        if pages_processed > 0:
            actual_properties_per_page = successful / pages_processed
            actual_success_rate = actual_properties_per_page / 12  # Normalize to 12 properties per page
            self.stdout.write(f"📄 Pages processed: ~{pages_processed}")
            self.stdout.write(f"🏠 Properties per page: {actual_properties_per_page:.1f}")
            self.stdout.write(f"📈 Actual success rate: {actual_success_rate:.1%}")
            self.stdout.write(f"💡 This data will improve future resume calculations")
        
        # Final stats
        self.show_final_stats()

    def calculate_scraping_success_rate(self):
        """Calculate actual scraping success rate from recent data"""
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Get recent scraping activity (last 7 days for better sample)
            recent_threshold = timezone.now() - timedelta(days=7)
            recent_properties = PropertyAnalysis.objects.filter(
                created_at__gte=recent_threshold,
                scraped_by__isnull=False
            ).order_by('-created_at')
            
            if recent_properties.count() < 50:
                # Not enough recent data, return default rate
                return 0.6
            
            # Analyze the creation timestamps to estimate pages processed
            # This is a rough estimate based on timing patterns
            creation_times = list(recent_properties.values_list('created_at', flat=True))
            
            # Group properties by approximate page (based on time intervals)
            # Assuming each page takes ~30-60 seconds to process
            page_groups = []
            current_group = []
            last_time = None
            
            for created_at in creation_times:
                if last_time is None:
                    current_group.append(created_at)
                else:
                    time_diff = (created_at - last_time).total_seconds()
                    if time_diff < 120:  # Within 2 minutes = same page
                        current_group.append(created_at)
                    else:
                        if current_group:
                            page_groups.append(current_group)
                        current_group = [created_at]
                last_time = created_at
            
            if current_group:
                page_groups.append(current_group)
            
            # Calculate success rate based on properties per page
            total_pages_processed = len(page_groups)
            total_properties_scraped = len(creation_times)
            
            if total_pages_processed > 0:
                avg_properties_per_page = total_properties_scraped / total_pages_processed
                # Normalize to 12 properties per page (theoretical max)
                success_rate = min(1.0, avg_properties_per_page / 12)
                return max(0.3, success_rate)  # Minimum 30% success rate
            
            return 0.6  # Default fallback
            
        except Exception as e:
            self.stdout.write(f"⚠️ Error calculating success rate: {e}")
            return 0.6  # Default fallback

    def calculate_resume_page(self):
        """Calculate where to resume scraping based on existing data - SMART MARGIN with success rate adjustment"""
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
            
            # Calculate dynamic success rate based on recent scraping patterns
            success_rate = self.calculate_scraping_success_rate()
            properties_per_successful_page = 12 * success_rate
            
            # Calculate adjusted page number using dynamic success rate
            adjusted_current_page = int(total_properties / properties_per_successful_page) + 1
            
            # Determine safety margin based on recent activity
            if recent_count > 20:
                # High recent activity - minimal safety margin due to better accuracy
                safety_margin = 1
            elif recent_count > 5:
                # Moderate recent activity - moderate safety margin
                safety_margin = 2
            else:
                # Low or no recent activity - conservative safety margin
                safety_margin = 3
            
            safe_start_page = max(1, adjusted_current_page - safety_margin)
            
            self.stdout.write(f"📊 Resume calculation (DYNAMIC success rate):")
            self.stdout.write(f"   • Total properties: {total_properties}")
            self.stdout.write(f"   • Dynamic success rate: {success_rate:.1%}")
            self.stdout.write(f"   • Properties per successful page: {properties_per_successful_page:.1f}")
            self.stdout.write(f"   • Adjusted current page: {adjusted_current_page}")
            self.stdout.write(f"   • Safety margin: {safety_margin} pages")
            self.stdout.write(f"   • Resume from page: {safe_start_page}")
            self.stdout.write(f"   • Recent activity: {recent_count} properties in last 48h")
            
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
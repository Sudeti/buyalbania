# apps/property_ai/management/commands/bulk_scrape_initial.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from apps.property_ai.models import PropertyAnalysis
from django.db.models import Count, Q
import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Initial bulk scraping of all available Century21 properties with agent intelligence'
    
    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, required=True)
        parser.add_argument('--max-pages', type=int, default=50, help='Max pages for initial scrape')
        parser.add_argument('--analyze', action='store_true', help='Run AI analysis immediately')
        parser.add_argument('--batch-delay', type=int, default=300, help='Delay between batches (seconds)')
        parser.add_argument('--delay', type=float, default=2.5, help='Delay between individual requests')
        
    def handle(self, *args, **options):
        user = User.objects.get(id=options['user_id'])
        
        self.stdout.write(f"🚀 STARTING INITIAL BULK SCRAPE")
        self.stdout.write(f"👤 User: {user.username}")
        self.stdout.write(f"📊 Max pages: {options['max_pages']}")
        self.stdout.write(f"🤖 AI Analysis: {'Enabled' if options['analyze'] else 'Disabled'}")
        self.stdout.write(f"⏱️ Request delay: {options['delay']}s")
        self.stdout.write(f"⏸️ Batch delay: {options['batch_delay']}s")
        
        # Run the scraping in smaller batches to avoid overwhelming the server
        pages_per_batch = 8  # Increased from 5 since we have delays
        total_batches = (options['max_pages'] + pages_per_batch - 1) // pages_per_batch
        
        total_scraped = 0
        total_with_agents = 0
        batch_start_time = time.time()
        
        for batch_num in range(total_batches):
            start_page = batch_num * pages_per_batch + 1
            end_page = min((batch_num + 1) * pages_per_batch, options['max_pages'])
            pages_in_batch = end_page - start_page + 1
            
            self.stdout.write(f"\n📦 BATCH {batch_num + 1}/{total_batches}: Pages {start_page}-{end_page}")
            
            # Track before batch
            properties_before = PropertyAnalysis.objects.filter(scraped_by=user).count()
            
            try:
                call_command(
                    'scrape_century21_sales',
                    f'--user-id={options["user_id"]}',
                    f'--max-pages={pages_in_batch}',
                    f'--delay={options["delay"]}',
                    '--analyze' if options['analyze'] else '',
                )
                
                # Track after batch
                properties_after = PropertyAnalysis.objects.filter(scraped_by=user).count()
                batch_scraped = properties_after - properties_before
                total_scraped += batch_scraped
                
                self.stdout.write(f"📈 Batch {batch_num + 1} scraped: {batch_scraped} properties")
                
                # Rest between batches to be respectful to the server
                if batch_num < total_batches - 1:  # Don't wait after the last batch
                    self.stdout.write(f"⏳ Waiting {options['batch_delay']} seconds before next batch...")
                    time.sleep(options['batch_delay'])
                    
            except Exception as e:
                self.stdout.write(f"❌ Batch {batch_num + 1} failed: {e}")
                continue
        
        total_time = time.time() - batch_start_time
        
        self.stdout.write(f"\n🎉 INITIAL BULK SCRAPE COMPLETED!")
        self.stdout.write(f"⏱️ Total time: {int(total_time/60)}m {int(total_time%60)}s")
        
        # Comprehensive statistics
        self.show_comprehensive_stats(user)
    
    def show_comprehensive_stats(self, user):
        """Show comprehensive statistics after bulk scrape"""
        
        # Basic stats
        total_properties = PropertyAnalysis.objects.filter(scraped_by=user).count()
        completed_analyses = PropertyAnalysis.objects.filter(scraped_by=user, status='completed').count()
        with_neighborhoods = PropertyAnalysis.objects.filter(
            scraped_by=user, 
            neighborhood__isnull=False
        ).exclude(neighborhood='').count()
        
        # NEW: Agent statistics
        with_agent_names = PropertyAnalysis.objects.filter(
            scraped_by=user,
            agent_name__isnull=False
        ).exclude(agent_name='').count()
        
        with_agent_emails = PropertyAnalysis.objects.filter(
            scraped_by=user,
            agent_email__isnull=False
        ).exclude(agent_email='').count()
        
        with_agent_phones = PropertyAnalysis.objects.filter(
            scraped_by=user,
            agent_phone__isnull=False
        ).exclude(agent_phone='').count()
        
        self.stdout.write(f"\n📊 SCRAPING STATISTICS:")
        self.stdout.write(f"🏠 Total properties scraped: {total_properties}")
        self.stdout.write(f"🏘️ Properties with neighborhoods: {with_neighborhoods} ({with_neighborhoods/total_properties*100:.1f}%)")
        self.stdout.write(f"🤖 Completed analyses: {completed_analyses}")
        
        self.stdout.write(f"\n👥 AGENT INTELLIGENCE DATA:")
        self.stdout.write(f"🧑‍💼 Properties with agent names: {with_agent_names} ({with_agent_names/total_properties*100:.1f}%)")
        self.stdout.write(f"📧 Properties with agent emails: {with_agent_emails} ({with_agent_emails/total_properties*100:.1f}%)")
        self.stdout.write(f"📞 Properties with agent phones: {with_agent_phones} ({with_agent_phones/total_properties*100:.1f}%)")
        
        # Top agents by listings
        top_agents = PropertyAnalysis.objects.filter(
            scraped_by=user,
            agent_name__isnull=False
        ).exclude(
            agent_name=''
        ).values('agent_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        if top_agents:
            self.stdout.write(f"\n🏆 TOP 10 AGENTS BY LISTINGS:")
            for i, agent in enumerate(top_agents, 1):
                self.stdout.write(f"  {i:2d}. {agent['agent_name']}: {agent['count']} properties")
        
        # Location distribution
        top_locations = PropertyAnalysis.objects.filter(
            scraped_by=user
        ).values('property_location').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        if top_locations:
            self.stdout.write(f"\n🌍 TOP 5 LOCATIONS:")
            for i, location in enumerate(top_locations, 1):
                self.stdout.write(f"  {i}. {location['property_location']}: {location['count']} properties")
        
        # Revenue potential calculation
        if with_agent_emails > 0:
            self.stdout.write(f"\n💰 AGENT INTELLIGENCE REVENUE POTENTIAL:")
            self.stdout.write(f"📧 {with_agent_emails} agent contacts available")
            
            # Conservative estimates (10% conversion)
            conservative_agents = int(with_agent_emails * 0.1)
            conservative_revenue = conservative_agents * 299  # €299/month per agent
            
            # Optimistic estimates (25% conversion)
            optimistic_agents = int(with_agent_emails * 0.25)
            optimistic_revenue = optimistic_agents * 299
            
            self.stdout.write(f"💼 Conservative (10% conversion): {conservative_agents} agents × €299 = €{conservative_revenue:,}/month")
            self.stdout.write(f"🚀 Optimistic (25% conversion): {optimistic_agents} agents × €299 = €{optimistic_revenue:,}/month")
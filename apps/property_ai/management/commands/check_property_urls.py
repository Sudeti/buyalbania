# apps/property_ai/management/commands/check_property_urls.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Q
from apps.property_ai.models import PropertyAnalysis
import requests
import time
import random

class Command(BaseCommand):
    help = 'Check if property URLs are still accessible and track agent performance'
    
    def add_arguments(self, parser):
        parser.add_argument('--days-old', type=int, default=7, 
                          help='Check properties not checked in X days')
        parser.add_argument('--limit', type=int, default=50,
                          help='Max properties to check per run')
        parser.add_argument('--show-agent-stats', action='store_true',
                          help='Show agent performance statistics')
    
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timezone.timedelta(days=options['days_old'])
        
        # Get active properties that need checking
        properties_to_check = PropertyAnalysis.objects.filter(
            is_active=True,
            property_url__isnull=False
        ).filter(
            Q(last_checked__isnull=True) | 
            Q(last_checked__lt=cutoff_date)
        ).order_by('last_checked')[:options['limit']]
        
        self.stdout.write(f"🔍 Checking {properties_to_check.count()} property URLs...")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        checked = 0
        removed = 0
        agent_performance = {}
        
        for prop in properties_to_check:
            self.stdout.write(f"Checking: {prop.property_title[:40]}...")
            
            # Track agent performance
            if prop.agent_name:
                if prop.agent_name not in agent_performance:
                    agent_performance[prop.agent_name] = {'checked': 0, 'removed': 0, 'total_days': []}
                agent_performance[prop.agent_name]['checked'] += 1
            
            try:
                response = session.get(prop.property_url, timeout=15)
                
                if response.status_code == 200:
                    # URL still accessible
                    prop.last_checked = timezone.now()
                    prop.save(update_fields=['last_checked'])
                    self.stdout.write("  ✅ Still accessible")
                else:
                    # URL no longer accessible (404, 500, etc.)
                    prop.is_active = False
                    prop.removed_date = timezone.now()
                    prop.last_checked = timezone.now()
                    prop.save(update_fields=['is_active', 'removed_date', 'last_checked'])
                    
                    days_listed = prop.days_on_market
                    agent_info = f" (Agent: {prop.agent_name})" if prop.agent_name else ""
                    self.stdout.write(f"  ❌ Removed after {days_listed} days{agent_info}")
                    
                    # Track agent performance
                    if prop.agent_name:
                        agent_performance[prop.agent_name]['removed'] += 1
                        agent_performance[prop.agent_name]['total_days'].append(days_listed)
                    
                    removed += 1
                
                checked += 1
                time.sleep(random.uniform(1, 3))  # Be nice to the server
                
            except Exception as e:
                # Network error - just update last_checked, don't mark as removed
                prop.last_checked = timezone.now()
                prop.save(update_fields=['last_checked'])
                self.stdout.write(f"  ⚠️ Error: {e}")
            
        self.stdout.write(f"\n✅ Checked: {checked} | ❌ Removed: {removed}")
        
        # Show agent performance if requested
        if options['show_agent_stats'] and agent_performance:
            self.show_agent_removal_stats(agent_performance)
    
    def show_agent_removal_stats(self, agent_performance):
        """Show agent performance based on removal statistics"""
        self.stdout.write(f"\n📊 AGENT PERFORMANCE (Properties Sold/Removed):")
        self.stdout.write(f"{'Agent Name':<25} {'Checked':<8} {'Removed':<8} {'Avg Days':<10} {'Success %':<10}")
        self.stdout.write("-" * 70)
        
        for agent_name, stats in agent_performance.items():
            if stats['checked'] > 0:
                success_rate = (stats['removed'] / stats['checked']) * 100
                avg_days = sum(stats['total_days']) / len(stats['total_days']) if stats['total_days'] else 0
                
                self.stdout.write(
                    f"{agent_name[:24]:<25} {stats['checked']:<8} "
                    f"{stats['removed']:<8} {avg_days:<10.1f} {success_rate:<10.1f}"
                )
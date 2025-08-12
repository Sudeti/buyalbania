from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.property_ai.models import PropertyAnalysis
import requests
import time
import random
from django.db import models

class Command(BaseCommand):
    help = 'Check if property URLs are still accessible'
    
    def add_arguments(self, parser):
        parser.add_argument('--days-old', type=int, default=7, 
                          help='Check properties not checked in X days')
        parser.add_argument('--limit', type=int, default=50,
                          help='Max properties to check per run')
    
    def handle(self, *args, **options):
        cutoff_date = timezone.now() - timezone.timedelta(days=options['days_old'])
        
        # Get active properties that need checking
        properties_to_check = PropertyAnalysis.objects.filter(
            is_active=True,
            property_url__isnull=False
        ).filter(
            models.Q(last_checked__isnull=True) | 
            models.Q(last_checked__lt=cutoff_date)
        ).order_by('last_checked')[:options['limit']]
        
        self.stdout.write(f"🔍 Checking {properties_to_check.count()} property URLs...")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        checked = 0
        removed = 0
        
        for prop in properties_to_check:
            self.stdout.write(f"Checking: {prop.property_title[:40]}...")
            
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
                    self.stdout.write(f"  ❌ Removed after {days_listed} days")
                    removed += 1
                
                checked += 1
                time.sleep(random.uniform(1, 3))  # Be nice to the server
                
            except Exception as e:
                # Network error - just update last_checked, don't mark as removed
                prop.last_checked = timezone.now()
                prop.save(update_fields=['last_checked'])
                self.stdout.write(f"  ⚠️ Error: {e}")
            
        self.stdout.write(f"\n✅ Checked: {checked} | ❌ Removed: {removed}")
#!/usr/bin/env python
"""
Test script to calculate actual scraping success rate from database
"""
import os
import sys
import django
from datetime import timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.utils import timezone
from apps.property_ai.models import PropertyAnalysis

def calculate_actual_success_rate():
    """Calculate the actual success rate from database data"""
    
    # Get recent scraping activity (last 7 days)
    recent_threshold = timezone.now() - timedelta(days=7)
    recent_properties = PropertyAnalysis.objects.filter(
        created_at__gte=recent_threshold,
        scraped_by__isnull=False
    ).order_by('-created_at')
    
    print(f"📊 Analyzing scraping data from last 7 days...")
    print(f"   • Total properties in database: {PropertyAnalysis.objects.count()}")
    print(f"   • Recent properties (last 7 days): {recent_properties.count()}")
    
    if recent_properties.count() < 10:
        print(f"   ⚠️ Not enough recent data (< 10 properties)")
        print(f"   📈 Using all scraped properties for analysis...")
        
        # Use all scraped properties
        all_scraped = PropertyAnalysis.objects.filter(
            scraped_by__isnull=False
        ).order_by('-created_at')
        
        if all_scraped.count() < 10:
            print(f"   ❌ Not enough data for analysis (< 10 total scraped properties)")
            return None
            
        recent_properties = all_scraped
    
    # Get creation timestamps
    creation_times = list(recent_properties.values_list('created_at', flat=True))
    
    # Group by time intervals (same page = within 2 minutes)
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
    
    # Calculate success rate
    total_pages_processed = len(page_groups)
    total_properties_scraped = len(creation_times)
    
    print(f"   • Pages processed (estimated): {total_pages_processed}")
    print(f"   • Properties scraped: {total_properties_scraped}")
    
    if total_pages_processed > 0:
        avg_properties_per_page = total_properties_scraped / total_pages_processed
        success_rate = min(1.0, avg_properties_per_page / 12)
        success_rate = max(0.3, success_rate)  # Minimum 30%
        
        print(f"   • Average properties per page: {avg_properties_per_page:.1f}")
        print(f"   • Success rate: {success_rate:.1%}")
        print(f"   • Properties per successful page: {12 * success_rate:.1f}")
        
        # Show page group details
        print(f"\n📄 Page group details:")
        for i, group in enumerate(page_groups[:10]):  # Show first 10 groups
            print(f"   • Page {i+1}: {len(group)} properties")
        
        if len(page_groups) > 10:
            print(f"   • ... and {len(page_groups) - 10} more pages")
        
        return success_rate
    
    return None

if __name__ == "__main__":
    success_rate = calculate_actual_success_rate()
    if success_rate:
        print(f"\n✅ Actual success rate: {success_rate:.1%}")
        print(f"💡 This is what the system will use for resume calculations!")
    else:
        print(f"\n❌ Could not calculate success rate - insufficient data")

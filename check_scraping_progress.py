#!/usr/bin/env python
"""
Simple script to check scraping progress and see what's next.

Usage:
    python check_scraping_progress.py

This shows:
- Current database stats
- Today's page range to be scraped
- Next day's page range
- How many weeks of scraping have been completed
"""

import os
import sys
import django
from datetime import datetime

# Add the project directory to Python path
sys.path.append('/Users/idlirsulstarova/django/property_ai')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.property_ai.models import PropertyAnalysis

def get_page_range_for_day(day_name):
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

def get_next_day_info(current_day):
    """Get info about the next day's scraping"""
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    current_index = days.index(current_day)
    next_index = (current_index + 1) % 7
    next_day = days[next_index]
    next_start, next_end = get_page_range_for_day(next_day)
    return next_day, next_start, next_end

def check_progress():
    """Check current scraping progress"""
    
    # Get current database stats
    total_properties = PropertyAnalysis.objects.count()
    with_agents = PropertyAnalysis.objects.exclude(agent_name='').count()
    with_phones = PropertyAnalysis.objects.exclude(agent_phone='').count()
    
    # Get current day and page range
    current_day = datetime.now().strftime('%A').lower()
    current_start, current_end = get_page_range_for_day(current_day)
    pages_today = current_end - current_start + 1
    
    # Get next day info
    next_day, next_start, next_end = get_next_day_info(current_day)
    
    # Calculate weeks completed (each week = 700 pages)
    weeks_completed = current_start // 700
    current_week = weeks_completed + 1
    
    # Calculate estimated properties based on pages
    estimated_properties = (current_start - 1) * 12  # 12 properties per page average
    
    print("🌙 ULTRA-SIMPLE SCRAPING PROGRESS REPORT")
    print("=" * 55)
    print(f"📊 Database Stats:")
    print(f"   • Total properties: {total_properties:,}")
    print(f"   • With agent names: {with_agents:,} ({with_agents/total_properties*100:.1f}%)")
    print(f"   • With agent phones: {with_phones:,} ({with_phones/total_properties*100:.1f}%)")
    print()
    
    print(f"📅 Today's Scraping ({current_day.title()}):")
    print(f"   • Pages: {current_start} to {current_end} ({pages_today} pages)")
    print(f"   • Expected properties: ~{pages_today * 12}")
    print(f"   • Estimated time: ~{(pages_today * 12 * 6) / 60:.1f} minutes")
    print()
    
    print(f"🔄 Next Day ({next_day.title()}):")
    print(f"   • Pages: {next_start} to {next_end} (100 pages)")
    print(f"   • Expected properties: ~1200")
    print()
    
    print(f"📈 Overall Progress:")
    print(f"   • Current week: {current_week}")
    print(f"   • Weeks completed: {weeks_completed}")
    print(f"   • Current page: {current_start}")
    print(f"   • Total pages in cycle: 700")
    print()
    
    print(f"📊 Efficiency:")
    print(f"   • Actual properties: {total_properties:,}")
    print(f"   • Estimated properties: {estimated_properties:,}")
    if estimated_properties > 0:
        efficiency = (total_properties / estimated_properties) * 100
        print(f"   • Efficiency: {efficiency:.1f}%")
    print()
    
    print(f"💡 Commands:")
    print(f"   • Run today's scrape: python manage.py simple_nightly_scrape")
    print(f"   • Force specific day: python manage.py simple_nightly_scrape --force-day monday")
    print(f"   • Check progress: python check_scraping_progress.py")
    print()
    
    print(f"📋 Weekly Schedule:")
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    for day in days:
        start, end = get_page_range_for_day(day)
        marker = " → " if day == current_day else "   "
        print(f"   {marker}{day.title()}: pages {start:3d}-{end:3d}")

if __name__ == "__main__":
    check_progress()

# Resume Calculation Improvements

## Problem Identified

The original `calculate_resume_page` method had a critical flaw in its safety margin calculation:

- **Assumption**: All properties in the database were from "on sale" listings
- **Calculation**: Simple division by 12 (properties per page)
- **Reality**: Only ~60% of pages actually contain properties that get scraped
- **Result**: Page number calculation was significantly skewed, leading to incorrect resume points

## Root Cause Analysis

The issue occurred because:
1. Not all pages contain properties that meet scraping criteria
2. Some properties are filtered out (rentals, invalid data, etc.)
3. The system was counting all database properties as if they were evenly distributed
4. This caused the estimated page number to be much higher than reality

## Solution Implemented

### 1. Dynamic Success Rate Calculation

Added `calculate_scraping_success_rate()` method that:
- Analyzes recent scraping activity (last 7 days)
- Groups properties by time intervals to estimate pages processed
- Calculates actual success rate based on real-world data
- Returns a dynamic success rate (defaults to 60% if insufficient data)

### 2. Improved Resume Calculation

Enhanced `calculate_resume_page()` method with:
- **Dynamic success rate**: Uses actual scraping patterns instead of fixed assumptions
- **Properties per successful page**: Calculated as `12 * success_rate` (~7.2 properties per page)
- **Adjusted page calculation**: `total_properties / properties_per_successful_page`
- **Intelligent safety margins**: Based on recent activity levels
  - High activity (>20 properties): 1 page margin
  - Moderate activity (5-20 properties): 2 page margin  
  - Low activity (<5 properties): 3 page margin

### 3. Real-time Tracking

Added page-level tracking during scraping:
- Monitors actual properties scraped per page
- Calculates real success rate achieved
- Provides feedback for future improvements
- Logs efficiency metrics for analysis

### 4. Test Mode

Added `--test-resume` flag to:
- Test resume calculation without actual scraping
- Validate the logic works correctly
- Debug calculation issues safely

## Key Improvements

### Before (Problematic)
```python
# Simple, flawed calculation
estimated_current_page = (total_properties // 12) + 1
safety_margin = 2  # Fixed margin
safe_start_page = max(1, estimated_current_page + safety_margin)
```

### After (Improved)
```python
# Dynamic, accurate calculation
success_rate = self.calculate_scraping_success_rate()  # ~60%
properties_per_successful_page = 12 * success_rate     # ~7.2
adjusted_current_page = int(total_properties / properties_per_successful_page) + 1

# Dynamic safety margin based on activity
if recent_count > 20:
    safety_margin = 1
elif recent_count > 5:
    safety_margin = 2
else:
    safety_margin = 3

safe_start_page = max(1, adjusted_current_page - safety_margin)
```

## Benefits

1. **Accurate Resume Points**: Page calculations now reflect real-world scraping patterns
2. **Reduced Duplicate Work**: Less likely to re-scrape already processed pages
3. **Better Efficiency**: Optimized safety margins based on activity levels
4. **Self-Improving**: System learns from actual scraping patterns
5. **Testable**: Can validate calculations without running full scrapes

## Usage

### Test Resume Calculation
```bash
python manage.py bulk_scrape_initial --test-resume
```

### Normal Scraping with Improved Logic
```bash
python manage.py bulk_scrape_initial --max-pages 10
```

## Monitoring

The system now provides detailed logging:
- Dynamic success rate calculation
- Properties per successful page
- Adjusted current page estimation
- Safety margin reasoning
- Recent activity levels
- Actual scraping efficiency achieved

This data helps monitor and further optimize the scraping process over time.

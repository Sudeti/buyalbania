# Ultra-Simple Nightly Scraping System

## Overview

This is the **simplest possible** approach to nightly scraping - hardcoded page ranges based on the day of the week. No cache, no tracking, no complex calculations.

## How It Works

### Hardcoded Day-Based Page Ranges

The system uses simple hardcoded ranges that never change:

- **Sunday**: Pages 1-100
- **Monday**: Pages 101-200  
- **Tuesday**: Pages 201-300
- **Wednesday**: Pages 301-400
- **Thursday**: Pages 401-500
- **Friday**: Pages 501-600
- **Saturday**: Pages 601-700

Then it repeats the cycle. That's it!

### No Complex Logic

- **No cache** - just uses the current day
- **No tracking** - page ranges are fixed
- **No calculations** - everything is hardcoded
- **No resume logic** - each day has its own range

## Usage

### Automatic Nightly Runs

The system is already configured to run automatically at 1:30 AM every night via Celery Beat:

```python
# In config/settings/base.py
'midnight-bulk-scrape': {
    'task': 'apps.property_ai.tasks.midnight_bulk_scrape_task',
    'schedule': crontab(hour=1, minute=30),  # 1:30 AM daily
},
```

### Manual Runs

You can also run it manually:

```bash
# Run today's page range automatically
python manage.py simple_nightly_scrape

# Force a specific day
python manage.py simple_nightly_scrape --force-day monday

# Ultra-safe mode (longer delays)
python manage.py simple_nightly_scrape --ultra-safe
```

### Check Progress

See what's happening and what's next:

```bash
python check_scraping_progress.py
```

This shows:
- Current database stats
- Today's page range to be scraped
- Next day's page range
- Weekly schedule
- Efficiency metrics

## Weekly Schedule

Here's exactly what gets scraped each day:

| Day | Pages | Properties | Time |
|-----|-------|------------|------|
| Sunday | 1-100 | ~1,200 | ~2 hours |
| Monday | 101-200 | ~1,200 | ~2 hours |
| Tuesday | 201-300 | ~1,200 | ~2 hours |
| Wednesday | 301-400 | ~1,200 | ~2 hours |
| Thursday | 401-500 | ~1,200 | ~2 hours |
| Friday | 501-600 | ~1,200 | ~2 hours |
| Saturday | 601-700 | ~1,200 | ~2 hours |

**Total per week**: 700 pages, ~8,400 properties

## Configuration

### Safety Settings

- **Default delay**: 6 seconds between requests
- **Ultra-safe mode**: 8+ seconds between requests
- **Human-like breaks**: Random 2-5 minute breaks every 50 properties
- **Circuit breaker**: 10-20 minute breaks after consecutive failures

## Benefits of This Approach

### ✅ Ultra-Simple
- No complex calculations
- No cache management
- No tracking logic
- Just hardcoded ranges

### ✅ Predictable
- Same pages every Sunday
- Same pages every Monday
- Easy to understand and debug
- No surprises

### ✅ Reliable
- No risk of calculation errors
- No risk of skipping pages
- No risk of duplicating pages
- Always scrapes the right range

### ✅ Easy to Monitor
- Clear weekly schedule
- Simple status checking
- Easy to see what's next

## Comparison with Old System

| Feature | Old System (Complex) | New System (Ultra-Simple) |
|---------|---------------------|---------------------------|
| Resume Logic | Complex calculations based on database content | Hardcoded day-based ranges |
| Page Tracking | Estimated based on properties per page | Fixed ranges by day |
| Risk of Duplicates | High (calculation errors) | None (fixed ranges) |
| Risk of Skipping | High (wrong calculations) | None (fixed ranges) |
| Debugging | Complex | Trivial |
| Maintenance | High | Zero |

## Troubleshooting

### Force a Specific Day
If you need to scrape a different day's range:
```bash
python manage.py simple_nightly_scrape --force-day monday
```

### Check Current Status
```bash
python check_scraping_progress.py
```

### Manual Page Range
If you need to scrape a specific range:
```bash
python manage.py bulk_scrape_initial --start-page=1 --end-page=100
```

## Monitoring

The system logs everything clearly:
- Which day is being scraped
- Which pages are being scraped
- How many properties found
- Success/failure rates
- Next day's schedule

## That's It!

This system is **ultra-simple** - just hardcoded page ranges based on the day of the week. No complex logic, no calculations, no tracking. Just:

- Sunday = pages 1-100
- Monday = pages 101-200
- Tuesday = pages 201-300
- etc.

Super simple and reliable!

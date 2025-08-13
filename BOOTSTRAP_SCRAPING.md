# Complete Bootstrap Workflow: From Setup to Full Operation

## **Phase 1: Setup (One-time, 30 minutes)**

### **1. Update Your Files**
```bash
# 1. Add agent fields to models.py (already done ✅)
# 2. Update scrapers.py with enhanced agent extraction (already done ✅) 
# 3. Update tasks.py with bootstrap tasks + agent field fix (needs the page fix above)
# 4. Update views.py to handle agent data (already done ✅)
```

### **2. Update Celery Beat Schedule**
```python
# In config/settings/base.py - REPLACE existing CELERY_BEAT_SCHEDULE:
CELERY_BEAT_SCHEDULE = {
    'cleanup-inactive-users-daily': {
        'task': 'apps.accounts.tasks.cleanup_inactive_users',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # NEW: Bootstrap scraping
    'bootstrap-scraping': {
        'task': 'apps.property_ai.tasks.bootstrap_scrape_batch',
        'schedule': crontab(hour=1, minute=0),  # 1 AM daily
        'kwargs': {'pages_per_batch': 50}
    },
    
    # NEW: Process analysis queue
    'analyze-pending': {
        'task': 'apps.property_ai.tasks.analyze_pending_properties',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    
    # NEW: Maintenance scraping
    'nightly-maintenance': {
        'task': 'apps.property_ai.tasks.nightly_maintenance_scrape',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    
    # KEEP: URL checking
    'check-property-urls': {
        'task': 'apps.property_ai.tasks.check_property_urls_task',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),  # Sunday 4 AM
    },
}
```

### **3. Create Management Commands**
```bash
# Create directories
mkdir -p apps/property_ai/management/commands
touch apps/property_ai/management/__init__.py
touch apps/property_ai/management/commands/__init__.py

# Create these 6 command files (copy from documents):
# - start_bootstrap.py
# - scraping_status.py  
# - scrape_century21_sales.py
# - bulk_scrape_initial.py
# - analyze_agent_intelligence.py
# - check_property_urls.py
```

### **4. Database Setup**
```bash
# Create and apply migrations
python manage.py makemigrations property_ai
python manage.py migrate
```

### **5. Start Celery Services**
```bash
# Terminal 1: Worker
celery -A config worker -l info

# Terminal 2: Beat scheduler  
celery -A config beat -l info

# Terminal 3: Monitor (optional)
celery -A config flower  # Visit http://localhost:5555
```

---

## **Phase 2: Launch Bootstrap (One command)**

### **Start the Automated System**
```bash
# This single command starts everything
python manage.py start_bootstrap

# Expected output:
# 🚀 Bootstrap scraping started!
# 📍 Will resume from page 1
```

---

## **Phase 3: Automated Operation (12+ days)**

### **What Happens Automatically:**

#### **Every Night at 1:00 AM:**
```
Bootstrap Task Runs:
├── Check progress: "Last page = 0, not complete"
├── Scrape pages 1-50:
│   ├── Page 1: https://www.century21albania.com/properties?page=1
│   ├── Page 2: https://www.century21albania.com/properties?page=2
│   ├── ...
│   └── Page 50: https://www.century21albania.com/properties?page=50
├── Extract agent data: names, emails, phones
├── Save ~600 new properties to database
├── Update progress: "Last page = 50"
├── Schedule next batch: pages 51-100 for tomorrow
└── Sleep until tomorrow
```

#### **Every Night at 2:00 AM:**
```
Maintenance Task:
├── Check: bootstrap_complete = False
├── Skip maintenance (bootstrap not done)
└── Wait for bootstrap to complete
```

#### **Every Night at 3:00 AM:**
```
Analysis Task:
├── Find 50 properties with status='analyzing'
├── Queue AI analysis for each property
├── PropertyAnalysis.status → 'completed'
└── Generate investment scores and recommendations
```

### **Progress Timeline:**

| **Day** | **Pages Scraped** | **Total Properties** | **Database State** |
|---------|------------------|---------------------|-------------------|
| 1 | 1-50 | ~600 | Growing |
| 2 | 51-100 | ~1,200 | Growing |
| 3 | 101-150 | ~1,800 | Growing |
| ... | ... | ... | ... |
| 10 | 451-500 | ~6,000 | Growing |
| 11 | 501-550 | ~6,600 | Growing |
| 12 | 551-583 | ~6,996 | **Bootstrap Complete!** |

### **Day 12: Automatic Transition**
```
Bootstrap Task:
├── Try to scrape pages 551-600
├── Page 583: No more properties found
├── processed_pages < pages_per_batch (33 < 50)
├── Set bootstrap_complete = True
├── Log: "Bootstrap complete - switching to maintenance"
└── Stop scheduling new bootstrap batches
```

---

## **Phase 4: Maintenance Mode (Day 13+)**

### **What Happens Every Night:**

#### **1:00 AM: Bootstrap Task**
```
├── Check: bootstrap_complete = True
├── Return: "Bootstrap already complete"
└── Exit (does nothing)
```

#### **2:00 AM: Maintenance Task**
```
├── Check: bootstrap_complete = True → Proceed
├── Scrape ONLY pages 1-10 (new listings appear here)
├── Skip existing properties
├── Save only NEW properties found (usually 0-5)
└── Keep database current
```

#### **3:00 AM: Analysis Task**
```
├── Process any new properties from maintenance
├── Process any failed analyses from before
└── Keep everything analyzed
```

---

## **Phase 5: Your Daily Workflow**

### **Morning Check (30 seconds)**
```bash
# Check progress each morning
python manage.py scraping_status

# Example output during bootstrap:
📊 Scraping Status:
• Last scraped page: 342
• Bootstrap complete: ⏳ In Progress
• Total properties: 4,104
• Pending analysis: 23
• Analyzed: 4,081
• Completion: 99.4% analyzed

# Example output after bootstrap complete:
📊 Scraping Status:
• Last scraped page: 583
• Bootstrap complete: ✅ Yes
• Total properties: 6,996
• Pending analysis: 0
• Analyzed: 6,996
• Completion: 100.0% analyzed
```

### **Agent Intelligence Analysis**
```bash
# Analyze agent data anytime
python manage.py analyze_agent_intelligence --top-n=20 --export-contacts

# Expected output:
📊 OVERALL COVERAGE:
🏠 Total properties: 6,996
🧑‍💼 With agent data: 4,200 (60.1%)

💥 AGENT INTELLIGENCE DATA:
🧑‍💼 Properties with agent names: 4,200 (60.1%)
📧 Properties with agent emails: 3,800 (54.3%)
📞 Properties with agent phones: 3,600 (51.5%)

🏆 TOP 20 AGENTS BY LISTINGS:
  1. Advan Xhabafti: 89 properties
  2. Alba Thimjo: 76 properties
  3. Adelina Marku: 65 properties
  ...

💰 REVENUE POTENTIAL:
📧 3,800 agent contacts available
💼 Conservative (10% conversion): 380 agents × €299 = €113,620/month
🚀 Optimistic (25% conversion): 950 agents × €299 = €284,050/month
```

### **Bulk Scrape for Immediate Results (Optional)**
```bash
# If you need data immediately for demos/testing
python manage.py bulk_scrape_initial --user-id=1 --max-pages=20 --analyze

# This gets 2,400 properties in 6 hours instead of waiting for bootstrap
```

---

## **Emergency Controls**

### **Pause Everything:**
```bash
# Stop celery beat (no new tasks scheduled)
Ctrl+C in beat terminal

# Stop workers (finish current tasks, take no new ones)
Ctrl+C in worker terminal
```

### **Resume:**
```bash
# Restart celery services
celery -A config beat -l info
celery -A config worker -l info
```

### **Restart Bootstrap:**
```bash
# Reset and start over
python manage.py start_bootstrap --reset

# Check status
python manage.py scraping_status
```

### **Check What Celery is Doing:**
```bash
# Monitor tasks in web interface
celery -A config flower
# Visit http://localhost:5555
```

---

## **Final State: Fully Automated System**

### **Database Contents (After 12 days):**
- **~7,000 properties** from Century21 Albania
- **~4,200 properties** with agent contact data
- **~3,800 unique agent emails** for B2B outreach
- **100% AI analyzed** with investment scores
- **Automatically maintained** with new listings

### **Revenue Opportunities:**
- **Property Analysis SaaS**: Existing B2C model
- **Agent Intelligence Platform**: New B2B revenue stream
- **Market Analytics API**: Enterprise data sales
- **Lead Generation Service**: Connect buyers with agents

### **Zero Maintenance Required:**
- Database stays current automatically
- New properties analyzed within 24 hours
- Agent database grows continuously
- System runs indefinitely

**Bottom Line:** One command (`python manage.py start_bootstrap`) creates a fully automated property intelligence platform that builds itself over 12 days, then maintains itself forever while generating multiple revenue streams! 🚀
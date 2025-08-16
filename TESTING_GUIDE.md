# Testing Guide for Resume Calculation System

## 🧪 **Testing Options Overview**

The improved resume calculation system can be tested in several ways, from safe read-only tests to full scraping tests.

## **1. Safe Testing (No Scraping)**

### **Test Resume Calculation Only**
```bash
python manage.py bulk_scrape_initial --test-resume
```
**What it does:**
- Calculates where the system would resume scraping
- Shows success rate calculation
- No actual scraping occurs
- Perfect for testing the logic

**Example output:**
```
🧪 TESTING RESUME CALCULATION...
📊 Resume calculation (DYNAMIC success rate):
   • Total properties: 14
   • Dynamic success rate: 60.0%
   • Properties per successful page: 7.2
   • Adjusted current page: 2
   • Safety margin: 2 pages
   • Resume from page: 1
✅ Resume calculation test completed. Would resume from page: 1
```

### **Test Success Rate Analysis**
```bash
python test_success_rate.py
```
**What it does:**
- Analyzes your database for scraping patterns
- Shows detailed breakdown of scraped vs manual properties
- Calculates actual success rate from your data
- Shows examples with different success rates

## **2. Small-Scale Testing (Safe Scraping)**

### **Test Mode with Minimal Pages**
```bash
python manage.py bulk_scrape_initial --test-mode --max-pages 2 --delay 8
```
**What it does:**
- Uses extra safety measures (longer delays)
- Scrapes only 2 pages maximum
- Shows real-time progress tracking
- Calculates actual success rate achieved
- Perfect for testing the full workflow

**Safety features in test mode:**
- Minimum 6-second delays between requests
- More frequent human-like breaks
- Extra logging and monitoring
- Circuit breaker for failures

### **Ultra-Safe Mode**
```bash
python manage.py bulk_scrape_initial --ultra-safe --max-pages 1 --delay 10
```
**What it does:**
- Maximum safety with 8+ second delays
- Only 1 page maximum
- Long breaks between requests
- Best for testing on sensitive sites

## **3. Production-Style Testing**

### **Normal Scraping with Monitoring**
```bash
python manage.py bulk_scrape_initial --max-pages 5 --delay 5
```
**What it does:**
- Normal scraping with 5 pages
- Shows real-time page tracking
- Calculates success rate at the end
- Good for testing production scenarios

### **With User Tracking**
```bash
python manage.py bulk_scrape_initial --user-id 1 --max-pages 3
```
**What it does:**
- Tracks which user initiated the scrape
- Shows user information in logs
- Useful for testing user-specific features

## **4. Testing Different Scenarios**

### **Test with Different Starting Pages**
```bash
python manage.py bulk_scrape_initial --start-page 10 --max-pages 2 --test-mode
```
**What it does:**
- Starts from page 10 instead of calculated resume page
- Tests the system's ability to handle manual starting points
- Shows how the system adapts

### **Test with Different Delays**
```bash
python manage.py bulk_scrape_initial --delay 3 --max-pages 2 --test-mode
```
**What it does:**
- Tests with faster delays (3 seconds)
- Shows how timing affects page grouping
- Tests system's adaptability to different speeds

## **5. Monitoring and Analysis**

### **Real-Time Progress Tracking**
During scraping, you'll see:
```
📈 Progress: 25.0% | ETA: 45m | Success: 180 | Pages: ~25
📈 Progress: 50.0% | ETA: 30m | Success: 360 | Pages: ~50
```

### **Final Statistics**
After scraping completes:
```
🎉 NIGHT SCRAPE COMPLETED!
✅ Successful: 13
❌ Failed: 10
📊 Success rate: 56.5%
📄 Pages processed: ~2
🏠 Properties per page: 6.5
📈 Actual success rate: 54.2%
💡 This data will improve future resume calculations
```

## **6. Testing Success Rate Learning**

### **Before and After Comparison**
1. **Run initial test:**
   ```bash
   python manage.py bulk_scrape_initial --test-resume
   ```

2. **Run small scrape:**
   ```bash
   python manage.py bulk_scrape_initial --test-mode --max-pages 2
   ```

3. **Test resume calculation again:**
   ```bash
   python manage.py bulk_scrape_initial --test-resume
   ```

**Expected result:** The success rate should change based on actual scraping data!

## **7. Troubleshooting Tests**

### **Test with Insufficient Data**
If you have < 5 scraped properties:
```bash
python test_success_rate.py
```
**Expected:** Shows default values and explains why

### **Test with No Scraped Properties**
If all properties are manual:
```bash
python test_success_rate.py
```
**Expected:** Shows 0 scraped properties and explains the issue

### **Test Error Handling**
```bash
python manage.py bulk_scrape_initial --test-resume --max-pages 999
```
**Expected:** System should handle large numbers gracefully

## **8. Performance Testing**

### **Test Large Scale (Be Careful!)**
```bash
python manage.py bulk_scrape_initial --max-pages 20 --delay 3
```
**Warning:** Only use on test environments or when you're sure it's safe!

### **Test Memory Usage**
Monitor memory usage during large scrapes:
```bash
# In another terminal
watch -n 1 'ps aux | grep python'
```

## **9. Validation Tests**

### **Verify Resume Accuracy**
1. Run a scrape from page 1-5
2. Note how many properties were scraped
3. Run resume calculation
4. Verify it suggests the correct next page

### **Verify Success Rate Accuracy**
1. Run a scrape and note the final success rate
2. Manually calculate: `properties_scraped / pages_processed / 12`
3. Compare with system's calculation

## **10. Recommended Testing Sequence**

### **For New Users:**
1. ```bash
   python manage.py bulk_scrape_initial --test-resume
   ```
2. ```bash
   python test_success_rate.py
   ```
3. ```bash
   python manage.py bulk_scrape_initial --test-mode --max-pages 1 --delay 8
   ```
4. ```bash
   python manage.py bulk_scrape_initial --test-resume
   ```

### **For Experienced Users:**
1. ```bash
   python manage.py bulk_scrape_initial --test-resume
   ```
2. ```bash
   python manage.py bulk_scrape_initial --test-mode --max-pages 3 --delay 6
   ```
3. ```bash
   python test_success_rate.py
   ```

## **🎯 Key Testing Points**

- **Safety:** Always start with `--test-resume` or `--test-mode`
- **Scale:** Start small and increase gradually
- **Monitoring:** Watch the real-time progress and final statistics
- **Learning:** Verify that success rates change based on actual data
- **Validation:** Compare system calculations with manual calculations

## **⚠️ Safety Reminders**

- Always use `--test-mode` for initial testing
- Start with small `--max-pages` values
- Use longer `--delay` values when testing
- Monitor the output for any errors or warnings
- Test on non-production environments first

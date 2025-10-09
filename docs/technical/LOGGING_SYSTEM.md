# Logging System - Detailed Process Monitoring

**Feature:** Dual logging (console + file) with detailed process tracking
**Purpose:** Monitor processing in real-time and review detailed logs later
**Status:** ✅ Implemented

---

## 📋 Overview

The pipeline now features comprehensive logging that outputs to both:
- **Console:** Clean, INFO-level logs for real-time monitoring
- **Log Files:** Detailed DEBUG-level logs for analysis and troubleshooting

---

## 🗂️ Log File Structure

### Location

```
logs/
├── bus_20251009_083000.log
├── ccp_20251009_090000.log
├── fam_20251009_120000.log
└── pen_20251009_150000.log
```

**Format:** `<code>_<timestamp>.log`

**Each Processing Run Creates a New Log File**

---

## 📊 Logging Levels

### Console Output (INFO Level)

**What You See:**
- Major stage transitions
- Progress updates (every 500 sections)
- Completion summaries
- Warnings and errors

**Example:**
```
2025-10-09 08:30:00 - INFO - Processing BUS with Auto-Reconciliation
2025-10-09 08:30:01 - INFO - Connected to MongoDB
2025-10-09 08:30:01 - INFO - Deleted 0 sections from section_contents
2025-10-09 08:30:05 - INFO - Stage 1 Complete: 5.2 min (312.5s)
2025-10-09 08:30:05 - INFO - Sections discovered: 6,234
2025-10-09 08:35:00 - INFO - Progress: 500/6234 (8%)
2025-10-09 08:40:00 - INFO - Progress: 1000/6234 (16%)
...
2025-10-09 09:00:00 - INFO - ✅ BUS PROCESSING COMPLETE
2025-10-09 09:00:00 - INFO - Log file saved to: logs/bus_20251009_083000.log
```

### Log File (DEBUG Level)

**What's Logged:**
- All INFO messages from console
- DEBUG messages with detailed context
- File names and line numbers
- Module names
- Detailed error traces
- All retry attempts
- Individual section successes/failures

**Example:**
```
2025-10-09 08:30:00 - __main__ - INFO - process_code_with_reconciliation.py:85 - Processing BUS
2025-10-09 08:30:01 - pipeline.core.database - DEBUG - database.py:42 - Connected to MongoDB: ca_codes_db
2025-10-09 08:30:01 - pipeline.services.architecture_crawler - DEBUG - architecture_crawler.py:115 - Starting architecture crawl for BUS
2025-10-09 08:30:15 - pipeline.services.architecture_crawler - DEBUG - architecture_crawler.py:206 - Found 12 sections in text page
2025-10-09 08:30:46 - pipeline.services.firecrawl_concurrent - WARNING - firecrawl_concurrent.py:81 - Retriable error on attempt 1: Timeout
2025-10-09 08:30:48 - pipeline.services.firecrawl_concurrent - INFO - firecrawl_concurrent.py:63 - Successfully scraped after retry
...
```

---

## 🔍 Log Contents

### Complete Process Log Includes:

**1. Initialization**
```
Logging initialized for BUS
Log file: /Users/.../logs/bus_20251009_083000.log
Connected to MongoDB
```

**2. Data Cleanup**
```
Deleted 5,234 sections from section_contents
Deleted 1 documents from code_architectures
Data cleared
```

**3. Stage 1 Details**
```
Starting architecture crawl for BUS
Scraping architecture page: https://...
Found 450 text pages
Processing text page 1/450
Found 15 sections in text page
...
Stage 1 Complete: 8.5 min (510s)
Sections discovered: 6,234
Tree nodes: 842
Tree depth: 4
Session ID: abc12345
```

**4. Stage 2 Progress**
```
Starting concurrent content extraction for BUS
Batch size: 50, Workers: 15
Processing batch 1: sections 1-50
Progress: 50/6234 (0.8%)
Concurrent batch complete: 48/50 successful
Processing batch 2: sections 51-100
...
Progress: 500/6234 (8%)
Progress: 1000/6234 (16%)
...
Stage 2 Complete: 45.2 min (2712s)
Total processed: 6,234
Single-version extracted: 6,198
Multi-version detected: 36
Failed sections: 0
Processing rate: 2.30 sections/second
```

**5. Stage 3 Details** (if multi-version found)
```
Starting multi-version extraction for 36 sections
Fetching version 1/36: BUS §1234.5
Extracted 2 versions for BUS §1234.5
...
Stage 3 Complete: 5.2 min (312s)
Multi-version extracted: 36/36
Avg time per multi-version: 8.67s
Synced 36 multi-version sections to code_architectures
```

**6. Reconciliation**
```
Starting reconciliation check
Initial assessment: 6,234/6,234 (100%)
100% Complete, no reconciliation needed
```

**Or if missing:**
```
Initial assessment: 6,184/6,234 (99.2%)
Retry attempt 1 with 10 workers
Retrying 50 missing sections
...
Retry complete: 50 success, 0 failed
Final assessment: 6,234/6,234 (100%)
```

**7. Final Summary**
```
BUS PROCESSING COMPLETE
Total Duration: 58.9 minutes (3534s)
   Stage 1 (Architecture): 8.5 min
   Stage 2 (Content): 45.2 min
   Stage 3 (Multi-Version): 5.2 min
Final Status:
   Total sections: 6,234
   Complete: 6,234
   Success Rate: 100.00%
   Single-version: 6,198
   Multi-version: 36
STATUS: 100% COMPLETE!
```

---

## 📁 Accessing Log Files

### View Latest Log

```bash
# List all logs
ls -lt logs/

# View specific code's latest log
ls -lt logs/bus_*.log | head -1

# Tail the log file
tail -f logs/bus_20251009_083000.log

# View entire log
cat logs/bus_20251009_083000.log

# Search for errors
grep ERROR logs/bus_20251009_083000.log

# Search for warnings
grep WARNING logs/bus_20251009_083000.log
```

### Log Analysis

```bash
# Count total sections processed
grep "Total processed" logs/bus_*.log

# Find retry attempts
grep "Retry attempt" logs/bus_*.log

# Check final status
grep "STATUS:" logs/bus_*.log

# Get processing rate
grep "Processing rate" logs/bus_*.log
```

---

## 🎯 Logging Best Practices

### During Processing

**Monitor in Real-Time:**
```bash
# Run in one terminal
python scripts/process_code_with_reconciliation.py BUS

# In another terminal, tail the log
tail -f logs/bus_*.log | grep -E "INFO|WARNING|ERROR"
```

### After Processing

**Review for Issues:**
```bash
# Check for any errors
grep -i error logs/bus_20251009_083000.log

# Check for warnings
grep -i warning logs/bus_20251009_083000.log

# Check retry attempts
grep -i retry logs/bus_20251009_083000.log

# View summary
tail -50 logs/bus_20251009_083000.log
```

### Debugging

**Full Debug Info:**
```bash
# View all DEBUG messages
grep DEBUG logs/bus_20251009_083000.log

# Find specific section
grep "§1234" logs/bus_20251009_083000.log

# Track batch processing
grep "batch" logs/bus_20251009_083000.log
```

---

## 📊 Log Rotation

### Current Setup

**No automatic rotation** - Each run creates a new file

**Advantages:**
- Complete history preserved
- Easy to compare runs
- No data loss

**Cleanup:**
```bash
# Keep last 30 days
find logs/ -name "*.log" -mtime +30 -delete

# Keep only latest 10 per code
ls -t logs/bus_*.log | tail -n +11 | xargs rm
```

---

## 🎨 Log Format

### Console Format

```
%(asctime)s - %(levelname)s - %(message)s
```

**Example:**
```
2025-10-09 08:30:00 - INFO - Stage 1 Complete: 5.2 min
```

### File Format

```
%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s
```

**Example:**
```
2025-10-09 08:30:00 - pipeline.services.architecture_crawler - INFO - architecture_crawler.py:115 - Starting architecture crawl for BUS
```

**Benefits:**
- Timestamp for correlation
- Module name for debugging
- File and line number for code tracing
- Full context for troubleshooting

---

## ✅ What Gets Logged

### Always Logged (INFO)

- ✅ Start/end of each stage
- ✅ Section counts and progress
- ✅ Success rates
- ✅ Processing times
- ✅ Errors and warnings
- ✅ Final summary

### Debug Only (DEBUG)

- Session IDs
- Individual section processing
- Detailed retry information
- MongoDB query details
- Tree structure details
- URL lists

---

## 🎯 Usage Examples

### Example 1: Process with Log Monitoring

```bash
# Terminal 1: Run processing
python scripts/process_code_with_reconciliation.py BUS 2>&1 | tee console_output.log

# Terminal 2: Monitor detailed log
tail -f logs/bus_*.log
```

### Example 2: Check After Completion

```bash
# Process code
python scripts/process_code_with_reconciliation.py BUS

# Review log
cat logs/bus_20251009_083000.log | less

# Check for issues
grep -E "ERROR|WARNING" logs/bus_20251009_083000.log
```

### Example 3: Compare Runs

```bash
# Process same code twice
python scripts/process_code_with_reconciliation.py BUS  # Run 1
python scripts/process_code_with_reconciliation.py BUS  # Run 2

# Compare times
grep "Total Duration" logs/bus_*.log

# Compare success rates
grep "Success Rate" logs/bus_*.log
```

---

## 📈 Production Monitoring

### Key Metrics to Track

**From Logs:**
```bash
# Processing time per code
grep "Total Duration" logs/*.log

# Success rates
grep "Success Rate" logs/*.log

# Failed sections
grep "Failed sections:" logs/*.log

# Rate limit hits
grep "Rate limit" logs/*.log

# Retry attempts
grep "Retry attempt" logs/*.log
```

### Alert Conditions

**Should trigger alerts:**
- Success rate < 95%
- Processing time > 2x expected
- Failed sections > 5%
- Multiple rate limit errors
- Reconciliation failures

---

## 🎉 Benefits

### Real-Time Monitoring

- ✅ See progress as it happens
- ✅ Detect issues immediately
- ✅ ETA calculations
- ✅ Rate tracking

### Post-Processing Analysis

- ✅ Review complete history
- ✅ Debug specific issues
- ✅ Performance analysis
- ✅ Compare runs

### Production Operations

- ✅ Audit trail
- ✅ Troubleshooting data
- ✅ Performance metrics
- ✅ Compliance logging

---

## 📝 Example Log File

**Location:** `logs/bus_20251009_083000.log`

**Size:** ~500KB - 2MB depending on code size

**Content:**
```
2025-10-09 08:30:00 - __main__ - INFO - Logging initialized for BUS
2025-10-09 08:30:00 - __main__ - INFO - Log file: logs/bus_20251009_083000.log
2025-10-09 08:30:01 - pipeline.core.database - INFO - Connected to MongoDB: ca_codes_db
2025-10-09 08:30:01 - __main__ - INFO - Deleted 5234 sections
...
[58 minutes of detailed logs]
...
2025-10-09 09:28:54 - __main__ - INFO - ✅ BUS PROCESSING COMPLETE
2025-10-09 09:28:54 - __main__ - INFO - Success Rate: 100.00%
```

---

## 🎯 Summary

**Logging System:** ✅ Production Ready

**Features:**
- ✅ Dual output (console + file)
- ✅ Different levels (INFO console, DEBUG file)
- ✅ Timestamp on every message
- ✅ File/line number tracking
- ✅ Automatic log file creation
- ✅ Organized in logs/ directory

**Benefits:**
- Monitor in real-time
- Debug issues later
- Performance analysis
- Audit trail
- Production operations

**Usage:**
```bash
python scripts/process_code_with_reconciliation.py <CODE>
# Logs automatically to console and logs/<code>_<timestamp>.log
```

---

**Created:** October 9, 2025
**Status:** Implemented and ready for production

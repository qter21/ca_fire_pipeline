# Manual Code Processing Guide

**Purpose:** Guide for manually processing any California legal code
**Audience:** Developers, operators
**Date:** October 9, 2025

---

## 📋 Quick Start

### Simplest Method (Recommended)

```bash
# Process any code with auto-reconciliation
source venv/bin/activate
python scripts/process_code_with_reconciliation.py <CODE>

# Examples:
python scripts/process_code_with_reconciliation.py BUS
python scripts/process_code_with_reconciliation.py GOV
python scripts/process_code_with_reconciliation.py VEH
```

**Features:**
- ✅ All 3 stages automatically
- ✅ Tree structure built
- ✅ Concurrent scraping (15 workers)
- ✅ Auto-retry missing sections
- ✅ 100% completion or logged failures

**Time:** 5-40 minutes depending on code size

---

## 🎯 Step-by-Step Manual Process

### Prerequisites

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Ensure MongoDB is running
# Check: docker ps | grep mongodb

# 3. Verify Firecrawl API key in .env
# Should have FIRECRAWL_API_KEY set
```

---

### Method 1: Complete Automated Processing

**File:** `scripts/process_code_with_reconciliation.py`

**Usage:**
```bash
python scripts/process_code_with_reconciliation.py <CODE>
```

**What It Does:**
1. Cleans existing data for that code
2. Stage 1: Discovers all sections, builds tree
3. Stage 2: Extracts content (concurrent)
4. Stage 3: Extracts multi-version sections
5. Reconciliation: Auto-retries missing sections
6. Reports: Initial and final status

**Example:**
```bash
$ python scripts/process_code_with_reconciliation.py LAB

================================================================================
Processing LAB with Auto-Reconciliation
Initial concurrent workers: 15
================================================================================

🧹 Step 1: Cleaning existing data
   ✅ Data cleared

🗺️  Step 2: Stage 1 (Architecture + Tree)
   ✅ Complete: 5.2 min
   Sections discovered: 2,450
   Tree nodes: 380

📄 Step 3: Stage 2 (Concurrent - 15 workers)
   Progress: 500/2450 (20%)
   Progress: 1000/2450 (41%)
   Progress: 1500/2450 (61%)
   Progress: 2000/2450 (82%)
   Progress: 2450/2450 (100%)
   ✅ Complete: 11.8 min
   Extracted: 2,438
   Multi-version detected: 12

✨ Step 4: Stage 3 (Multi-Version: 12 sections)
   ✅ Complete: 1.8 min
   Extracted: 12/12

🔍 Step 5: Reconciliation
   Initial: 2,450/2,450 (100%)
   ✅ 100% Complete, no reconciliation needed

✅ LAB PROCESSING COMPLETE
Total Duration: 18.8 minutes
Success Rate: 100%
```

---

### Method 2: Stage-by-Stage Processing

**Use when:** You want more control over each stage

#### Step 1: Stage 1 (Architecture Discovery)

```python
from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.firecrawl_service import FirecrawlService

# Setup
code = "BUS"
db = DatabaseManager()
db.connect()

# Clean old data (optional)
db.section_contents.delete_many({'code': code})
db.code_architectures.delete_many({'code': code})

# Run Stage 1
firecrawl = FirecrawlService()
crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
result = crawler.crawl(code, save_to_db=True)

print(f"Discovered: {result['total_sections']} sections")
print(f"Tree nodes: {result['items_count']}")
print(f"Tree depth: {result['statistics']['max_depth']}")

db.disconnect()
```

**Output:**
```
Discovered: 1,850 sections
Tree nodes: 245
Tree depth: 4
```

#### Step 2: Stage 2 (Content Extraction - Concurrent)

```python
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor

db = DatabaseManager()
db.connect()

# Process with concurrent scraping
extractor = ConcurrentContentExtractor(
    db_manager=db,
    batch_size=50,
    max_workers=15  # Adjust based on code size
)

# Progress callback
def show_progress(processed, total):
    pct = (processed/total*100) if total > 0 else 0
    if processed % 100 == 0 or processed == total:
        print(f"Progress: {processed}/{total} ({pct:.1f}%)")

# Run Stage 2
result = extractor.extract(
    code,
    skip_multi_version=False,
    progress_callback=show_progress
)

print(f"Extracted: {result['single_version_count']}")
print(f"Multi-version: {result['multi_version_count']}")
print(f"Failed: {len(result['failed_sections'])}")

db.disconnect()
```

#### Step 3: Stage 3 (Multi-Version Extraction)

```python
from pipeline.services.content_extractor import ContentExtractor

db = DatabaseManager()
db.connect()

# Only needed if Stage 2 found multi-version sections
multi_count = db.section_contents.count_documents({
    'code': code,
    'is_multi_version': True
})

if multi_count > 0:
    print(f"Processing {multi_count} multi-version sections...")

    firecrawl = FirecrawlService()
    stage3 = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)
    result = stage3.extract_multi_version_sections(code)

    print(f"Extracted: {result['extracted_count']}/{result['total_sections']}")

    # Sync to code_architectures
    mv_secs = list(db.section_contents.find(
        {'code': code, 'is_multi_version': True},
        {'section': 1}
    ))
    mv_list = sorted([s['section'] for s in mv_secs])
    db.code_architectures.update_one(
        {'code': code},
        {'$set': {'multi_version_sections': mv_list}}
    )
    print(f"Synced {len(mv_list)} multi-version sections")

db.disconnect()
```

#### Step 4: Reconciliation (Fill Gaps)

```python
from pipeline.services.reconciliation_service import ReconciliationService

db = DatabaseManager()
db.connect()

# Check and retry missing sections
reconciliation = ReconciliationService(db_manager=db)
report = reconciliation.reconcile_code(
    code,
    max_retry_attempts=2,
    initial_workers=10,
    min_workers=5
)

# Print report
print(reconciliation.generate_reconciliation_report(code))

if report['success']:
    print("✅ 100% Complete!")
else:
    print(f"⚠️ {report['final_status']['missing']} sections still missing")
    print("Logged to processing_status collection")

db.disconnect()
```

---

### Method 3: Via FastAPI (Background Job)

**Start server:**
```bash
python pipeline/main.py
# Server runs on http://localhost:8001
```

**Process code:**
```bash
# Start processing
curl -X POST http://localhost:8001/api/v2/crawler/start/BUS

# Returns:
{
  "job_id": "bus_20251009_120000",
  "code": "BUS",
  "status": "started",
  "message": "Pipeline started for code BUS"
}

# Check status
curl http://localhost:8001/api/v2/crawler/status/bus_20251009_120000

# View all codes
curl http://localhost:8001/api/v2/crawler/codes
```

---

## ⚙️ Configuration Options

### Concurrent Workers

**Adjust based on code size and rate limits:**

```python
# Small code (<500 sections)
max_workers = 20  # Fast

# Medium code (500-2,000 sections)
max_workers = 15  # Balanced (recommended)

# Large code (>2,000 sections)
max_workers = 10  # Safe, avoids rate limits
```

### Batch Size

```python
# Default: 50 sections per batch
batch_size = 50

# For faster processing (if no rate limits):
batch_size = 100

# For conservative processing:
batch_size = 25
```

### Retry Configuration

```python
# In reconciliation
max_retry_attempts = 2  # Default
initial_workers = 10    # First retry
min_workers = 5         # Final retry
```

---

## 📊 Monitoring Progress

### Check Database Status

```bash
source venv/bin/activate
python -c "
from pipeline.core.database import DatabaseManager

db = DatabaseManager()
db.connect()

# Replace 'BUS' with your code
code = 'BUS'

total = db.section_contents.count_documents({'code': code})
with_content = db.section_contents.count_documents({'code': code, 'has_content': True})
multi = db.section_contents.count_documents({'code': code, 'versions': {'\$ne': None}})

complete = with_content + multi
pct = (complete/total*100) if total > 0 else 0

print(f'{code}: {complete}/{total} ({pct:.1f}%)')

db.disconnect()
"
```

### Check code_architectures

```python
from pipeline.core.database import DatabaseManager

db = DatabaseManager()
db.connect()

arch = db.code_architectures.find_one({'code': 'BUS'})

if arch:
    print(f"Code: {arch['code']}")
    print(f"Total sections: {arch.get('total_sections', 0)}")
    print(f"Stage 1: {'✅' if arch.get('stage1_completed') else '❌'}")
    print(f"Stage 2: {'✅' if arch.get('stage2_completed') else '❌'}")
    print(f"Stage 3: {'✅' if arch.get('stage3_completed') else '❌'}")
    print(f"Has tree: {'✅' if 'tree' in arch else '❌'}")
    print(f"Multi-version: {len(arch.get('multi_version_sections', []))}")

db.disconnect()
```

---

## 🐛 Troubleshooting

### Rate Limit Errors (429)

**Symptoms:**
```
Rate limit exceeded. Consumed (req/min): 501
```

**Solution:**
```bash
# Reduce concurrent workers
# Edit script or use lower value:
python scripts/process_code_with_reconciliation.py BUS
# (uses 15 workers by default - safe)

# Or wait 60 seconds and retry
```

### Missing Sections

**Check:**
```python
db = DatabaseManager()
db.connect()

missing = list(db.section_contents.find({
    'code': 'BUS',
    'has_content': False,
    '$or': [{'versions': None}, {'versions': {'$exists': False}}]
}, {'section': 1}))

print(f"Missing: {len(missing)} sections")
for sec in missing[:10]:
    print(f"  §{sec['section']}")

db.disconnect()
```

**Fix:**
```bash
# Use reconciliation
python -c "
from pipeline.core.database import DatabaseManager
from pipeline.services.reconciliation_service import ReconciliationService

db = DatabaseManager()
db.connect()

service = ReconciliationService(db)
report = service.reconcile_code('BUS')

print(service.generate_reconciliation_report('BUS'))

db.disconnect()
"
```

### Check for Errors

**Query processing_status:**
```python
db = DatabaseManager()
db.connect()

# Check for logged failures
failures = db.processing_status.find({'code': 'BUS'})

for failure in failures:
    print(f"Type: {failure.get('type')}")
    print(f"Missing: {failure.get('missing_count', 0)}")
    print(f"Sections: {failure.get('missing_sections', [])}")

db.disconnect()
```

---

## 📈 Expected Processing Times

### By Code Size

| Code | Est. Sections | Stage 1 | Stage 2 (15 workers) | Stage 3 | Total |
|------|---------------|---------|----------------------|---------|-------|
| Small (<500) | ~300 | ~1 min | ~2 min | ~0.5 min | **~3-4 min** |
| Medium (500-1,500) | ~1,000 | ~3 min | ~6 min | ~1 min | **~10-12 min** |
| Large (1,500-3,000) | ~2,000 | ~5 min | ~12 min | ~2 min | **~19-22 min** |
| Very Large (>3,000) | ~5,000 | ~8 min | ~30 min | ~5 min | **~43-50 min** |

**Note:** With 15 concurrent workers (recommended)

---

## ✅ Verification Checklist

After processing, verify:

```bash
source venv/bin/activate
python -c "
from pipeline.core.database import DatabaseManager

db = DatabaseManager()
db.connect()

code = 'BUS'  # Change this

# 1. Check section_contents
total = db.section_contents.count_documents({'code': code})
single = db.section_contents.count_documents({'code': code, 'has_content': True, 'is_multi_version': False})
multi = db.section_contents.count_documents({'code': code, 'versions': {'\$ne': None}})

print('✅ Verification Checklist:')
print()
print(f'1. Total sections in DB: {total}')
print(f'   Status: {\"✅\" if total > 0 else \"❌\"} ')
print()
print(f'2. Single-version with content: {single}')
print(f'   Status: {\"✅\" if single > 0 else \"⚠️\"} ')
print()
print(f'3. Multi-version with versions: {multi}')
print(f'   Status: {\"✅\" if multi >= 0 else \"❌\"} ')
print()

# 2. Check code_architectures
arch = db.code_architectures.find_one({'code': code})

print(f'4. code_architectures exists: {arch is not None}')
print(f'   Status: {\"✅\" if arch else \"❌\"} ')
print()

if arch:
    print(f'5. Has tree structure: {\"tree\" in arch}')
    print(f'   Status: {\"✅\" if \"tree\" in arch else \"❌\"} ')
    print()

    print(f'6. Has url_manifest: {\"url_manifest\" in arch}')
    print(f'   Status: {\"✅\" if \"url_manifest\" in arch else \"❌\"} ')
    print()

    print(f'7. All stages complete:')
    print(f'   Stage 1: {\"✅\" if arch.get(\"stage1_completed\") else \"❌\"}')
    print(f'   Stage 2: {\"✅\" if arch.get(\"stage2_completed\") else \"❌\"}')
    print(f'   Stage 3: {\"✅\" if arch.get(\"stage3_completed\") else \"❌\"}')
    print()

# 3. Overall success
complete = single + multi
success_rate = (complete/total*100) if total > 0 else 0

print('='*70)
print(f'OVERALL: {complete}/{total} ({success_rate:.2f}%)')
if success_rate >= 100:
    print('✅ PROCESSING COMPLETE AND VERIFIED')
elif success_rate >= 99:
    print('✅ PROCESSING MOSTLY COMPLETE (>99%)')
else:
    print(f'⚠️  INCOMPLETE - {total-complete} sections missing')
print('='*70)

db.disconnect()
"
```

---

## 📚 California Legal Code List

### All 30 California Codes

| Code | Name | Est. Sections | Est. Time |
|------|------|---------------|-----------|
| **BUS** | Business and Professions | ~6,000 | ~45 min |
| **CCP** | Code of Civil Procedure | ~3,353 | ~25 min | ✅ Done |
| **CIV** | Civil Code | ~5,000 | ~40 min |
| **COM** | Commercial Code | ~800 | ~8 min |
| **CORP** | Corporations Code | ~2,500 | ~20 min |
| **EDC** | Education Code | ~4,000 | ~30 min |
| **ELEC** | Elections Code | ~1,000 | ~10 min |
| **EVID** | Evidence Code | ~506 | ~5 min | ✅ Done |
| **FAM** | Family Code | ~1,626 | ~12 min | ✅ Done |
| **FGC** | Fish and Game Code | ~3,000 | ~25 min |
| **FIN** | Financial Code | ~2,000 | ~15 min |
| **GOV** | Government Code | ~7,000 | ~55 min |
| **HNC** | Harbors and Navigation | ~1,000 | ~10 min |
| **HSC** | Health and Safety Code | ~5,000 | ~40 min |
| **INS** | Insurance Code | ~3,500 | ~28 min |
| **LAB** | Labor Code | ~2,500 | ~20 min |
| **MVC** | Military and Veterans | ~500 | ~5 min |
| **PCC** | Probate Code | ~1,500 | ~12 min |
| **PEN** | Penal Code | ~5,660 | ~38 min | ✅ Done |
| **PROB** | Probate Code | ~1,500 | ~12 min |
| **PRC** | Public Resources Code | ~3,000 | ~25 min |
| **PUC** | Public Utilities Code | ~4,000 | ~32 min |
| **RTC** | Revenue and Taxation | ~4,500 | ~36 min |
| **SHC** | Streets and Highways | ~1,200 | ~10 min |
| **UIC** | Unemployment Insurance | ~1,000 | ~10 min |
| **VEH** | Vehicle Code | ~4,000 | ~32 min |
| **WAT** | Water Code | ~2,500 | ~20 min |
| **WIC** | Welfare and Institutions | ~2,000 | ~15 min |

**Total:** ~20,000 sections (estimated)
**Total Time:** ~4-6 hours with concurrent scraping

---

## 🎯 Best Practices

### 1. Start with Small Codes

**Good for testing:**
- EVID (506 sections) - 5 min
- COM (800 sections) - 8 min
- MVC (500 sections) - 5 min

### 2. Use Recommended Workers

**For most codes:**
```python
max_workers = 15  # Sweet spot: fast but safe
```

### 3. Monitor First Batch

Watch the first 50-100 sections:
- If rate limits (429): Reduce workers
- If successful: Continue
- If errors: Check logs

### 4. Always Run Reconciliation

Even if initial shows 100%, run reconciliation to verify:
```bash
python -c "
from pipeline.services.reconciliation_service import ReconciliationService
from pipeline.core.database import DatabaseManager

db = DatabaseManager()
db.connect()
service = ReconciliationService(db)
report = service.reconcile_code('BUS')
print(service.generate_reconciliation_report('BUS'))
db.disconnect()
"
```

---

## 📝 Processing Queue Strategy

### Recommended Order

**Week 1: Small Codes** (validate system)
1. COM (800) - ~8 min
2. MVC (500) - ~5 min
3. UIC (1,000) - ~10 min
4. SHC (1,200) - ~10 min

**Week 2: Medium Codes**
5. ELEC (1,000) - ~10 min
6. HNC (1,000) - ~10 min
7. PROB (1,500) - ~12 min
8. LAB (2,500) - ~20 min
9. WAT (2,500) - ~20 min

**Week 3: Large Codes**
10. CORP (2,500) - ~20 min
11. FGC (3,000) - ~25 min
12. PRC (3,000) - ~25 min
13. INS (3,500) - ~28 min
14. EDC (4,000) - ~30 min
15. VEH (4,000) - ~32 min

**Week 4: Very Large Codes**
16. PUC (4,000) - ~32 min
17. RTC (4,500) - ~36 min
18. HSC (5,000) - ~40 min
19. CIV (5,000) - ~40 min
20. BUS (6,000) - ~45 min
21. GOV (7,000) - ~55 min

**Total for 26 remaining:** ~4-6 hours

---

## 🎉 Quick Reference

### One Command Processing

```bash
# Most common usage
python scripts/process_code_with_reconciliation.py <CODE>
```

### Check Status

```bash
# See all processed codes
python -c "
from pipeline.core.database import DatabaseManager
db = DatabaseManager()
db.connect()
codes = db.code_architectures.find({}, {'code': 1, 'total_sections': 1})
for c in codes:
    print(f\"{c['code']}: {c.get('total_sections', 0)} sections\")
db.disconnect()
"
```

### Verify Completion

```bash
# Check specific code
python scripts/sync_multi_version_data.py  # Updates all codes
```

---

**That's it!** The simplest way is just:

```bash
python scripts/process_code_with_reconciliation.py <CODE>
```

It handles everything automatically! 🚀

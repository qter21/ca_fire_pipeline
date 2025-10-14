# GCloud Production Architecture Reprocessing

**Date:** October 14, 2025  
**Version:** v0.3.0  
**Purpose:** Update production database with fixed architecture parser

---

## Overview

The local database has been updated with the fixed architecture parser (v0.3.0), which corrected 55 node type misclassifications. Now we need to update the production GCloud database.

**What needs updating:**
- Production `code_architectures` collection with correct tree structures
- All 4 codes: CCP, FAM, EVID, PEN

**What won't change:**
- Section URLs (unchanged by fix)
- Section content (Stage 2/3 don't need reprocessing)
- Total section counts (11,146 preserved)

---

## Step-by-Step Instructions

### 1. SSH into GCloud Instance

```bash
# SSH into the codecond instance
gcloud compute ssh codecond --zone=us-west2-a

# Or if using SSH directly:
# ssh user@INSTANCE_IP
```

### 2. Navigate to Pipeline Directory

```bash
cd /path/to/ca_fire_pipeline

# Check current version
git status
git log --oneline -5
```

### 3. Pull Latest Code (v0.3.0)

```bash
# Pull the latest code with the fix
git fetch origin
git pull origin main

# Verify v0.3.0 tag
git tag -l
git log --oneline -1

# Should show: "fix architecture with different code structure"
```

### 4. Activate Virtual Environment

```bash
# Activate venv if not already active
source venv/bin/activate

# Verify Python version
python --version  # Should be 3.12+
```

### 5. Verify MongoDB Connection

```bash
# Check if MongoDB is accessible
python -c "
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings

settings = get_settings()
print(f'MongoDB URI: {settings.mongodb_uri}')

db = DatabaseManager(settings.mongodb_uri)
db.connect()
print('✅ MongoDB connected successfully')
"
```

### 6. Check Current Architecture Status

```bash
# Check which codes need reprocessing
python << 'PYEOF'
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings

db = DatabaseManager(get_settings().mongodb_uri)
db.connect()

codes = ['CCP', 'FAM', 'EVID', 'PEN']
print("="*60)
print("CURRENT ARCHITECTURE STATUS")
print("="*60)

for code in codes:
    arch = db.code_architectures.find_one({'code': code})
    if arch:
        crawled = arch.get('crawled_at', 'N/A')
        sections = arch.get('total_sections', 0)
        print(f"\n{code}:")
        print(f"  Last crawled: {crawled}")
        print(f"  Sections: {sections:,}")
    else:
        print(f"\n{code}: Not found")
PYEOF
```

### 7. Reprocess Architecture (Stage 1 Only)

**Option A: Using API (Recommended)**

```bash
# Start the API server in background
nohup python pipeline/main.py > api.log 2>&1 &

# Get the PID
API_PID=$!
echo "API running on PID: $API_PID"

# Wait for startup
sleep 5

# Reprocess each code via API
for code in CCP FAM EVID PEN; do
    echo "Reprocessing $code architecture..."
    curl -X POST "http://localhost:8001/api/v2/crawler/start/$code" \
         -H "Content-Type: application/json" \
         -d '{"stages": [1]}'
    
    echo "Waiting for $code to complete..."
    sleep 30  # Adjust based on code size
done

# Stop API
kill $API_PID
```

**Option B: Using Python Script (Alternative)**

```bash
python << 'PYEOF'
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings

print("="*60)
print("REPROCESSING ARCHITECTURE WITH FIXED PARSER")
print("="*60)

settings = get_settings()
db = DatabaseManager(settings.mongodb_uri)
db.connect()

firecrawl = FirecrawlService()
crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)

codes = ['EVID', 'FAM', 'CCP', 'PEN']  # Smallest to largest

for code in codes:
    print(f"\n{'='*60}")
    print(f"Processing {code}...")
    print(f"{'='*60}")
    
    try:
        result = crawler.crawl(code, save_to_db=True)
        print(f"✅ {code} complete!")
        print(f"   Sections: {result.get('total_sections', 0):,}")
        print(f"   Nodes: {result.get('statistics', {}).get('total_nodes', 0)}")
    except Exception as e:
        print(f"❌ {code} failed: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*60)
print("REPROCESSING COMPLETE")
print("="*60)
PYEOF
```

### 8. Verify Results

```bash
# Check updated architecture
python << 'PYEOF'
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings
from datetime import datetime

db = DatabaseManager(get_settings().mongodb_uri)
db.connect()

def count_node_types(node, counts=None):
    if counts is None:
        counts = {}
    node_type = node.get('type', 'UNKNOWN')
    counts[node_type] = counts.get(node_type, 0) + 1
    for child in node.get('children', []):
        count_node_types(child, counts)
    return counts

codes = ['CCP', 'FAM', 'EVID', 'PEN']
print("="*60)
print("VERIFICATION RESULTS")
print("="*60)

for code in codes:
    arch = db.code_architectures.find_one({'code': code})
    if not arch:
        print(f"\n{code}: Not found")
        continue
    
    tree = arch.get('tree', {})
    counts = count_node_types(tree)
    crawled = arch.get('crawled_at', 'N/A')
    
    print(f"\n{code}:")
    print(f"  Crawled: {crawled}")
    print(f"  Sections: {arch.get('total_sections', 0):,}")
    print(f"  Node types:")
    for ntype, count in sorted(counts.items()):
        print(f"    {ntype}: {count}")

print("\n" + "="*60)
print("Expected node counts (after fix):")
print("  CCP:  PART=4, TITLE=56, CHAPTER=233, ARTICLE=333")
print("  FAM:  PART=73, DIVISION=18, CHAPTER=140, ARTICLE=80")
print("  EVID: DIVISION=12, CHAPTER=28, ARTICLE=57")
print("  PEN:  PART=6, TITLE=85, CHAPTER=368, ARTICLE=232")
print("="*60)
PYEOF
```

### 9. Verify Section Counts Unchanged

```bash
# Ensure no data loss
python << 'PYEOF'
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings

db = DatabaseManager(get_settings().mongodb_uri)
db.connect()

codes = {
    'CCP': 3354,
    'FAM': 1626,
    'EVID': 506,
    'PEN': 5660
}

print("="*60)
print("SECTION COUNT VERIFICATION")
print("="*60)

all_good = True
for code, expected in codes.items():
    arch = db.code_architectures.find_one({'code': code})
    if arch:
        actual = arch.get('total_sections', 0)
        status = "✅" if actual == expected else "❌"
        print(f"{status} {code}: {actual:,} (expected: {expected:,})")
        if actual != expected:
            all_good = False
    else:
        print(f"❌ {code}: Not found")
        all_good = False

if all_good:
    print("\n✅ All section counts verified - no data loss!")
else:
    print("\n⚠️  Some counts don't match - investigate!")
PYEOF
```

### 10. Restart API (if needed)

```bash
# If API is running, restart it to pick up changes
pkill -f "python pipeline/main.py"
nohup python pipeline/main.py > api.log 2>&1 &
```

---

## Verification Checklist

After reprocessing, verify:

- [ ] All 4 codes show today's date in `crawled_at`
- [ ] Node type distributions match expected values
- [ ] Section counts unchanged (11,146 total)
- [ ] PART counts reduced (CCP: 4, FAM: 73, PEN: 6)
- [ ] API responds with updated tree structures
- [ ] No errors in logs

---

## Expected Results

### Before Fix (Old Production)
- CCP: 36 PART nodes (many misclassified)
- FAM: 81 PART nodes (8 misclassified)
- PEN: 21 PART nodes (15 misclassified)

### After Fix (New Production)
- CCP: 4 PART nodes ✅
- FAM: 73 PART nodes ✅
- PEN: 6 PART nodes ✅
- EVID: Unchanged (was already correct) ✅

---

## Rollback (If Needed)

If something goes wrong:

```bash
# Restore from backup (if you created one)
mongorestore --uri="$MONGODB_URI" --drop backup/

# Or revert code
git checkout v0.2.0  # Previous version
```

---

## Estimated Time

- EVID: ~30 seconds (506 sections)
- FAM: ~1-2 minutes (1,626 sections)
- CCP: ~2-3 minutes (3,354 sections)
- PEN: ~3-5 minutes (5,660 sections)

**Total: ~10-15 minutes** for all codes

---

## Notes

- **Only Stage 1 needs reprocessing** (architecture crawling)
- Stage 2 & 3 (content extraction) do NOT need reprocessing
- Section URLs are unchanged by this fix
- Zero data loss expected
- The fix only improves tree structure organization

---

## Support

If issues occur:
1. Check logs: `tail -f api.log`
2. Check MongoDB connection
3. Verify code version: `git log --oneline -1`
4. Compare node counts with expected values above

---

**Ready to proceed?** Follow steps 1-9 in order.

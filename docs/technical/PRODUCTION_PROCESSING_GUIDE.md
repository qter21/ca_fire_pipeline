# Production Code Processing Guide

**Version:** v0.3.0
**Last Updated:** October 15, 2025
**Environment:** GCloud Production (codecond, us-west2-a)
**Validated:** 6 codes processed successfully (35,274 sections)

---

## 🎯 Quick Start (Most Common Use Case)

### Process Any California Code

```bash
# 1. SSH to GCloud
gcloud compute ssh codecond --zone=us-west2-a

# 2. Process code (one command!)
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE>

# Examples:
# sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py BUS
# sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py CIV
# sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py VEH
```

**That's it!** The script handles everything automatically.

---

## 📋 Complete Step-by-Step Process

### Step 1: Access Production Environment

```bash
# SSH into GCloud instance
gcloud compute ssh codecond --zone=us-west2-a

# Verify you're connected
hostname  # Should show: codecond
```

### Step 2: Verify Pipeline Status

```bash
# Check Docker containers are running
sudo docker ps

# Should see:
# - ca-fire-pipeline (healthy)
# - ca-codes-mongodb (healthy)
# - ca-codes-redis (healthy)
# - legal-codes-api (healthy)
```

### Step 3: Choose Code to Process

**Remaining Codes (24 of 30):**

**Small (quick wins):**
- MVC, COM, ELEC, UIC, HNC (~500-1,000 sections, 5-10 min each)

**Medium:**
- SHC, PCC, WIC, FIN, WAT, LAB, CORP (~1,200-2,500 sections, 10-20 min each)

**Large:**
- FGC, PRC, INS, EDC, VEH, PUC, RTC, CIV, HSC, BUS (~3,000-6,000 sections, 20-45 min each)

### Step 4: Run Processing

```bash
# Process the code
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE>

# Example for Business and Professions Code:
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py BUS
```

### Step 5: Monitor Progress

The script will show real-time progress:

```
================================================================================
🚀 COMPLETE PIPELINE - Processing BUS
================================================================================
Workers: 15
Resume mode: OFF
Auto-retry: ON
================================================================================

✅ Connected to MongoDB

================================================================================
🧹 STEP 1: Cleaning Existing Data
================================================================================
✅ Data cleared

================================================================================
🗺️  STEP 2: Stage 1 - Architecture & Tree Discovery
================================================================================
✅ Stage 1 Complete: 5.2 min
   Sections discovered: 6,000

================================================================================
📄 STEP 3: Stage 2 - Concurrent Content Extraction
   Workers: 15 | Batch size: 50
================================================================================
Progress: 500/6000 (8%)
Progress: 1000/6000 (17%)
...
Progress: 6000/6000 (100%)
✅ Stage 2 Complete: 35.0 min

================================================================================
✨ STEP 4: Stage 3 - Multi-Version Extraction
   Sections: 5
================================================================================
✅ Stage 3 Complete: 0.5 min

================================================================================
🔍 STEP 5: Reconciliation - Auto-Retry Missing Sections
================================================================================
✅ 100% Complete after reconciliation

================================================================================
🎉 BUS PROCESSING COMPLETE
================================================================================
Total Duration: 40.7 minutes
Completion rate: 100.00%
✅ STATUS: 100% COMPLETE!
```

### Step 6: Verify Completion

```bash
# Quick verification
sudo docker exec ca-fire-pipeline python -c '
from pipeline.core.database import DatabaseManager
db = DatabaseManager()
db.connect()
codes = list(db.code_architectures.find({}, {"code": 1, "total_sections": 1}))
print("All codes:", [(c["code"], c.get("total_sections", 0)) for c in sorted(codes, key=lambda x: x["code"])])
db.disconnect()
'
```

---

## ⏱️ Expected Processing Times

### Based on Production Data (6 codes, 35,274 sections)

| Code Size | Sections | Stage 1 | Stage 2 | Stage 3 | Total |
|-----------|----------|---------|---------|---------|-------|
| **Small** | 500 | 1 min | 3-4 min | <1 min | **5-6 min** |
| **Medium** | 1,500 | 2-3 min | 8-12 min | <1 min | **12-16 min** |
| **Large** | 2,500-3,000 | 4-5 min | 15-20 min | 1-2 min | **20-27 min** |
| **Very Large** | 5,000-6,000 | 6-8 min | 30-40 min | 2-3 min | **40-50 min** |
| **Huge** | 20,000+ (GOV) | 15 min | 90 min | 5 min | **110 min** |

**Rate:** ~2.5-3.5 sections/second with 15 concurrent workers

---

## 🔧 Troubleshooting

### Issue: Rate Limit (429 Error)

**Symptom:**
```
Rate limit exceeded. Consumed (req/min): 501
```

**Solution:**
Wait 60 seconds. The script has automatic retry with exponential backoff. It will recover automatically.

**Manual Override (if needed):**
```bash
# Reduce workers if rate limits persist
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE> --workers 10
```

### Issue: Process Interrupted (SIGINT/SIGTERM)

**Symptom:**
```
Received SIGINT signal - initiating graceful shutdown...
Checkpoint saved
```

**Solution:**
Resume from checkpoint:
```bash
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE> --resume
```

### Issue: Some Sections Failed

**Symptom:**
```
Completion rate: 98.5%
Failed sections: 45
```

**Solution:**
Automatic retry will handle it. If failures persist:
```bash
# View failure report
sudo docker exec ca-fire-pipeline python scripts/retry_failed_sections.py <CODE> --report

# Retry all failed sections
sudo docker exec ca-fire-pipeline python scripts/retry_failed_sections.py <CODE> --all
```

### Issue: MongoDB Connection Failed

**Symptom:**
```
Failed to connect to MongoDB
```

**Solution:**
```bash
# Check MongoDB container
sudo docker ps | grep mongodb

# Restart if needed
sudo docker restart ca-codes-mongodb

# Wait 10 seconds
sleep 10

# Retry processing
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE>
```

### Issue: Container Not Running

**Symptom:**
```
Error: No such container: ca-fire-pipeline
```

**Solution:**
```bash
# Check containers
sudo docker ps -a

# Start if stopped
sudo docker start ca-fire-pipeline

# Or restart
sudo docker restart ca-fire-pipeline

# Verify
sudo docker ps | grep ca-fire-pipeline
```

---

## 📊 Verification Checklist

After processing completes, verify:

```bash
# 1. Check code architecture exists
sudo docker exec ca-fire-pipeline python << 'EOF'
from pipeline.core.database import DatabaseManager
db = DatabaseManager()
db.connect()

code = 'BUS'  # Change to your code

arch = db.code_architectures.find_one({'code': code})
if arch:
    print(f"✅ {code} Architecture:")
    print(f"   Total sections: {arch.get('total_sections', 0):,}")
    print(f"   Stage 1: {'✅' if arch.get('stage1_completed') else '❌'}")
    print(f"   Stage 2: {'✅' if arch.get('stage2_completed') else '❌'}")
    print(f"   Stage 3: {'✅' if arch.get('stage3_completed') else '❌'}")
    print(f"   Tree: {'✅' if 'tree' in arch else '❌'}")
    print(f"   Manifest: {'✅' if 'url_manifest' in arch else '❌'}")
else:
    print(f"❌ {code} not found")

db.disconnect()
EOF
```

```bash
# 2. Check section contents
sudo docker exec ca-fire-pipeline python -c "
from pipeline.core.database import DatabaseManager
db = DatabaseManager()
db.connect()

code = 'BUS'  # Change to your code

total = db.section_contents.count_documents({'code': code})
single = db.section_contents.count_documents({'code': code, 'has_content': True, 'is_multi_version': False})
multi = db.section_contents.count_documents({'code': code, 'versions': {'\$ne': None}})

print(f'{code} Sections:')
print(f'  Total: {total:,}')
print(f'  Single-version: {single:,}')
print(f'  Multi-version: {multi}')
print(f'  Complete: {single + multi:,}')

arch = db.code_architectures.find_one({'code': code})
if arch:
    expected = arch.get('total_sections', 0)
    pct = (single + multi) / expected * 100 if expected > 0 else 0
    print(f'  Completion: {pct:.2f}%')
    if pct >= 100:
        print('  ✅ STATUS: 100% COMPLETE')
    elif pct >= 99:
        print('  ✅ STATUS: EXCELLENT (≥99%)')
    else:
        print(f'  ⚠️ STATUS: {expected - single - multi} sections missing')

db.disconnect()
"
```

```bash
# 3. Test API endpoint (if legal-codes-api is running)
curl -s http://localhost:8000/api/v2/codes/BUS | python -m json.tool | head -20
```

**All checks should show ✅**

---

## 🎯 Best Practices

### 1. Process During Low-Traffic Hours
- Best time: Late evening or early morning PST
- Reduces load on production website
- Faster Firecrawl API responses

### 2. Start with Small Codes
- Test with 500-1,000 section codes first
- Verify process works before tackling large codes
- Quick feedback loop

### 3. Monitor First Few Batches
- Watch first 100-200 sections
- Verify no rate limits or errors
- Confirm expected progress rate

### 4. Use Screen for Long Processes
```bash
# Start screen session
screen -S code-processing

# Run processing
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py GOV

# Detach: Ctrl+A, then D
# Reattach: screen -r code-processing
```

### 5. Check Logs if Issues Occur
```bash
# View processing logs
sudo docker exec ca-fire-pipeline ls -la logs/

# View specific log
sudo docker exec ca-fire-pipeline tail -100 logs/bus_complete_20251015_*.log
```

---

## 📝 Processing Log Template

Keep a log of processed codes:

```markdown
| Code | Date | Duration | Sections | Status | Notes |
|------|------|----------|----------|--------|-------|
| CCP | 2025-10-09 | 23.6 min | 3,354 | ✅ 100% | - |
| EVID | 2025-10-09 | 3.4 min | 506 | ✅ 100% | - |
| FAM | 2025-10-09 | 74.2 min | 1,626 | ✅ 100% | Sequential (pre-concurrent) |
| GOV | 2025-10-14 | ~110 min | 21,418 | ✅ 100% | Largest code |
| PEN | 2025-10-09 | 38.0 min | 5,660 | ✅ 100% | - |
| PROB | 2025-10-15 | 20.5 min | 2,710 | ✅ 100% | 181% larger than estimate |
| BUS | 2025-10-XX | TBD | ~6,000 | Pending | Next to process |
```

---

## 🔄 Batch Processing Multiple Codes

To process multiple codes in sequence:

```bash
# Create batch script
cat > process_batch.sh << 'EOF'
#!/bin/bash

CODES=("MVC" "COM" "ELEC" "UIC" "HNC")

for CODE in "${CODES[@]}"; do
    echo "=================================================="
    echo "Processing $CODE"
    echo "=================================================="

    sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py $CODE

    STATUS=$?
    if [ $STATUS -eq 0 ]; then
        echo "✅ $CODE completed successfully"
    else
        echo "❌ $CODE failed with status $STATUS"
        exit $STATUS
    fi

    echo ""
    echo "Waiting 30 seconds before next code..."
    sleep 30
done

echo "=================================================="
echo "Batch processing complete!"
echo "=================================================="
EOF

# Make executable
chmod +x process_batch.sh

# Run
./process_batch.sh
```

---

## 📚 All Available Commands

### Main Processing
```bash
# Standard processing
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE>

# Resume from checkpoint
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE> --resume

# Custom worker count
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE> --workers 20

# Skip automatic retry
sudo docker exec ca-fire-pipeline python scripts/process_code_complete.py <CODE> --skip-retry
```

### Retry Operations
```bash
# View failure report
sudo docker exec ca-fire-pipeline python scripts/retry_failed_sections.py <CODE> --report

# Retry all failed sections
sudo docker exec ca-fire-pipeline python scripts/retry_failed_sections.py <CODE> --all

# Retry specific section
sudo docker exec ca-fire-pipeline python scripts/retry_failed_sections.py <CODE> --section 1234
```

### Database Operations
```bash
# Check database status
sudo docker exec ca-fire-pipeline python -c "from pipeline.core.database import DatabaseManager; db = DatabaseManager(); db.connect(); print('Codes:', db.code_architectures.count_documents({})); db.disconnect()"

# List all codes
sudo docker exec ca-fire-pipeline python -c "from pipeline.core.database import DatabaseManager; db = DatabaseManager(); db.connect(); codes = list(db.code_architectures.find({}, {'code': 1, 'total_sections': 1})); print('\\n'.join([f\"{c['code']}: {c.get('total_sections', 0):,}\" for c in sorted(codes, key=lambda x: x['code'])])); db.disconnect()"
```

---

## ✅ Success Criteria

A code is considered successfully processed when:

- [x] Total sections discovered in Stage 1
- [x] 99%+ sections extracted with content
- [x] Multi-version sections detected and extracted
- [x] Tree structure created in code_architectures
- [x] URL manifest generated
- [x] All three stages marked as completed
- [x] Reconciliation shows 100% or near-100%
- [x] No critical errors in logs

---

## 🎉 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│            CALIFORNIA CODE PROCESSING                        │
│               Quick Reference v0.3.0                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SSH:     gcloud compute ssh codecond --zone=us-west2-a │
│                                                             │
│  2. PROCESS: sudo docker exec ca-fire-pipeline \            │
│              python scripts/process_code_complete.py <CODE> │
│                                                             │
│  3. VERIFY:  Check for "✅ STATUS: 100% COMPLETE!"          │
│                                                             │
│  4. DONE:    Code is live on codecond.com                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Expected Time: 5-50 min (size-dependent)                   │
│  Success Rate: 99.95%+                                      │
│  Worker Count: 15 (auto-configured)                         │
├─────────────────────────────────────────────────────────────┤
│  Troubleshooting:                                           │
│    - Rate limit: Auto-retry handles it                      │
│    - Interrupted: Add --resume flag                         │
│    - Failures: Run retry_failed_sections.py                 │
└─────────────────────────────────────────────────────────────┘
```

---

**Status:** ✅ Production-Tested and Validated
**Codes Processed:** 6 (CCP, EVID, FAM, GOV, PEN, PROB)
**Total Sections:** 35,274
**Success Rate:** 100%

**Last Updated:** October 15, 2025
**Version:** v0.3.0

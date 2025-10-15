# PROB Processing - Quick Start

**Target:** PROB (Probate Code) on GCloud Production
**Version:** v0.3.0
**Expected Time:** 10-14 minutes
**Expected Sections:** ~1,500

---

## 🚀 Quick Commands

### 1. SSH to GCloud
```bash
gcloud compute ssh codecond --zone=us-west2-a
cd ~/ca_fire_pipeline
source venv/bin/activate
```

### 2. Process PROB
```bash
python scripts/process_code_complete.py PROB
```

### 3. Verify
```bash
python << 'EOF'
from pipeline.core.database import DatabaseManager
db = DatabaseManager()
db.connect()

arch = db.code_architectures.find_one({'code': 'PROB'})
total = db.section_contents.count_documents({'code': 'PROB', 'has_content': True})
multi = db.section_contents.count_documents({'code': 'PROB', 'versions': {'$ne': None}})

print(f"PROB: {total + multi}/{arch.get('total_sections', 0)} sections")
print(f"Status: {'✅ Complete' if (total + multi) >= arch.get('total_sections', 0) * 0.99 else '⚠️ Incomplete'}")
db.disconnect()
EOF
```

---

## 📋 Expected Output

```
🚀 COMPLETE PIPELINE - Processing PROB
Workers: 15

Stage 1: ✅ 1.0 min → 1,500 sections discovered
Stage 2: ✅ 8-10 min → 1,495 extracted
Stage 3: ✅ 0-2 min → 0-5 multi-version
Reconciliation: ✅ 100% Complete

Total Duration: 10-12 minutes
Completion: 100%
```

---

## 🔧 If Issues Occur

### Retry Failed Sections
```bash
python scripts/retry_failed_sections.py PROB --all
```

### Resume from Interrupt
```bash
python scripts/process_code_complete.py PROB --resume
```

### View Failure Report
```bash
python scripts/retry_failed_sections.py PROB --report
```

---

## ✅ Success Checklist

- [ ] ~1,500 sections in database
- [ ] code_architectures has PROB entry
- [ ] Completion rate ≥99%
- [ ] No errors in logs
- [ ] Tree structure present
- [ ] URL manifest generated

---

**Full Guide:** See `docs/technical/GCLOUD_PROCESS_PROB.md`

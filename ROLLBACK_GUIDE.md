# Rollback Guide - Pipeline Upgrades

## WIC Processing Results (Before Upgrade)

**Baseline Performance:**
- Total sections: 6,989
- Successfully extracted: 6,985 (99.94%)
- Failed sections: 4
  - §4639.81 - Firecrawl API failure (network errors after 3 retries)
  - §10492.2 - Content parsing failure (empty/malformed page)
  - §14005.20 - Playwright timeout (>30s multi-version page load)
  - §14196.5 - Content parsing failure (empty/malformed page)
- Duration: 62 minutes (Stage 1: 10.65min, Stage 2: 36.12min, Stage 3: 17.54min)
- Workers: 15 concurrent

**Issues Observed:**
1. ⚠️ No timeout protection - hung requests block entire batch
2. ⚠️ No pause/resume - must restart from scratch if interrupted
3. ⚠️ Limited progress visibility - unclear ETA and success rate
4. ⚠️ Multi-version timeouts not configurable (hardcoded 30s)
5. ⚠️ One hung request at batch 7 required manual kill (09:27)

## Quick Rollback (If Upgrades Fail)

### Method 1: Automated Script (Recommended)
```bash
./scripts/rollback_upgrades.sh
```
This script will:
- Create a backup branch with your changes
- Restore all files to pre-upgrade state
- Remove new files (checkpoint.py)
- Show you the backup branch name for future reference

### Method 2: Manual Git Restore
```bash
# Restore all modified files
git restore pipeline/core/config.py \
           pipeline/services/content_extractor_concurrent.py \
           pipeline/services/firecrawl_concurrent.py \
           scripts/process_code_with_reconciliation.py

# Remove new checkpoint model
rm pipeline/models/checkpoint.py

# Verify
git status
```

### Method 3: Selective Rollback

Keep timeout fixes, rollback pause/resume:
```bash
# Only rollback checkpoint-related changes
git restore pipeline/services/content_extractor_concurrent.py \
           scripts/process_code_with_reconciliation.py
rm pipeline/models/checkpoint.py

# Keep: timeout fixes in firecrawl_concurrent.py and config.py
```

Keep everything, only remove new features:
```bash
# Remove only the checkpoint file
rm pipeline/models/checkpoint.py

# Manually edit other files to disable checkpointing:
# - In content_extractor_concurrent.py: set enable_checkpointing=False
# - In process_code_with_reconciliation.py: set resume=False
```

## Testing Before Committing

Before you commit the upgrades, test them:

```bash
# Test with a small code first
python scripts/process_code_with_reconciliation.py TEST

# Test pause/resume
python scripts/process_code_with_reconciliation.py WIC
# Press Ctrl+C after a few batches
python scripts/process_code_with_reconciliation.py WIC --resume
```

## If Upgrades Work - Commit Them

```bash
git add -A
git commit -m "Add pipeline robustness features: timeouts, pause/resume, enhanced logging"
git push
```

## Restore Upgrades After Rollback

If you used the rollback script, your changes are saved:

```bash
# List backup branches
git branch | grep upgrade-backup

# Restore from backup (replace with your branch name)
git checkout upgrade-backup-20251013_092718
git checkout main
git merge upgrade-backup-20251013_092718
```

## Modified Files Summary

**Modified:**
- `pipeline/core/config.py` - Added timeout settings
- `pipeline/services/firecrawl_concurrent.py` - Added timeout handling
- `pipeline/services/content_extractor_concurrent.py` - Added checkpointing
- `scripts/process_code_with_reconciliation.py` - Added signal handlers & resume

**New:**
- `pipeline/models/checkpoint.py` - Checkpoint model
- `scripts/rollback_upgrades.sh` - This rollback script

**Lines Changed:**
- +257 lines added
- -41 lines removed
- Net: +216 lines

**Key Improvements:**
1. ✅ Request-level timeout (60-120s configurable)
2. ✅ Hung request cancellation after 2x timeout
3. ✅ Checkpoint save after each batch (50 sections)
4. ✅ Graceful shutdown on Ctrl+C with checkpoint save
5. ✅ Resume from last checkpoint with --resume flag
6. ✅ Enhanced progress logging (success rate, ETA, rate)
7. ✅ Batch and overall progress visibility

**Expected Impact:**
- Prevents indefinite hangs (timeout protection)
- Zero lost work on interruption (pause/resume)
- Better observability (real-time metrics)
- Faster failure detection (60s vs infinite)
- Recoverable from any point (batch-level checkpoints)

**Testing Recommendations:**
1. Test timeout handling with a problematic URL
2. Test Ctrl+C during Stage 2 and verify checkpoint saved
3. Test --resume flag and verify it skips completed batches
4. Compare processing time with baseline (should be similar)
5. Verify final completion rate matches or exceeds 99.94%

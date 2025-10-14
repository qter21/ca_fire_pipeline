# Pipeline Upgrades - Quick Reference

## What Changed?

Added **robustness, recoverability, and observability** features to the WIC processing pipeline.

## TL;DR

- ✅ **No more hangs**: Requests timeout after 60-120s
- ✅ **Pause anytime**: Press Ctrl+C, resume with `--resume`
- ✅ **Better visibility**: Real-time progress, success rate, ETA
- ✅ **Easy rollback**: `./scripts/rollback_upgrades.sh`

## Quick Start

### Normal Processing (as before)
```bash
python scripts/process_code_with_reconciliation.py WIC
```

### Resume After Interruption (NEW)
```bash
# Press Ctrl+C during processing
# Then resume:
python scripts/process_code_with_reconciliation.py WIC --resume
```

### Rollback If Issues
```bash
./scripts/rollback_upgrades.sh
```

## New Features

### 1. Timeout Protection
- Requests timeout after 60s (configurable in `.env`)
- Hung requests cancelled after 120s
- Batch continues even with failures

### 2. Pause/Resume
- Press Ctrl+C anytime during Stage 2
- Checkpoint saved automatically
- Resume with `--resume` flag
- Skips already-processed batches

### 3. Enhanced Logging
```
================================================================================
Batch 25/140 (17.9%) | Overall: 1200/6989 (17.2%)
Sections 1201-1250 | Workers: 15
================================================================================

Progress: 25/50 (50.0%) | Rate: 5.4/s | Success: 98.5% | ETA: 2.3min
```

## Configuration

Edit `.env` to adjust timeouts:
```bash
FIRECRAWL_TIMEOUT=60          # Batch-level timeout
FIRECRAWL_REQUEST_TIMEOUT=90  # Individual request timeout
```

## Files Changed

- `pipeline/core/config.py` - Timeout settings
- `pipeline/services/firecrawl_concurrent.py` - Timeout logic
- `pipeline/services/content_extractor_concurrent.py` - Checkpointing
- `scripts/process_code_with_reconciliation.py` - Signal handling
- `pipeline/models/checkpoint.py` - **NEW** checkpoint model

## Documentation

- **[UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)** - Complete technical details
- **[ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md)** - Rollback instructions & baseline data

## Testing Checklist

- [ ] Process completes without indefinite hangs
- [ ] Ctrl+C saves checkpoint
- [ ] `--resume` skips completed batches
- [ ] Progress logging shows ETA and success rate
- [ ] Final completion rate ≥ 99.94% (baseline)
- [ ] Duration ~60 minutes (baseline)

## Rollback

If anything goes wrong:

### Quick Rollback
```bash
./scripts/rollback_upgrades.sh
```

### Manual Rollback
```bash
git restore pipeline/core/config.py \
           pipeline/services/content_extractor_concurrent.py \
           pipeline/services/firecrawl_concurrent.py \
           scripts/process_code_with_reconciliation.py
rm pipeline/models/checkpoint.py
```

## Before/After Comparison

### Before (Baseline)
- ❌ Hung request requires manual kill
- ❌ Ctrl+C loses all progress (~60 min work)
- ❌ Progress updates every 10 items only
- ❌ No ETA or success rate
- ❌ Multi-version timeout hardcoded (30s)

### After (Upgraded)
- ✅ Hung requests auto-cancelled after 120s
- ✅ Ctrl+C saves checkpoint, resume anytime
- ✅ Progress updates every 5 items
- ✅ Real-time ETA and success rate
- ✅ Configurable timeouts via .env

## WIC Baseline Results

**Pre-upgrade performance (for comparison):**
- Total: 6,989 sections
- Success: 6,985 (99.94%)
- Failed: 4 sections
- Duration: 62 minutes
- One manual kill required at batch 7

**Expected post-upgrade:**
- Same success rate (99.94%)
- Similar duration (~60 min)
- Zero manual intervention
- Full recoverability

## Support

If you encounter issues:

1. Check [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md) for details
2. Run rollback script: `./scripts/rollback_upgrades.sh`
3. Review logs in `logs/` directory
4. Check git status: `git status`

## Commit Message Template

```bash
git add -A
git commit -m "feat: Add pipeline robustness features

- Request-level timeout protection (60-120s)
- Checkpoint system for pause/resume
- Enhanced progress logging with ETA
- Graceful shutdown (Ctrl+C support)
- --resume flag for recovery

Baseline: WIC 6,989 sections, 99.94% success"
```

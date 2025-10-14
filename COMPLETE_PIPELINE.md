# Complete Processing Pipeline Documentation

## Overview

The complete processing pipeline (`scripts/process_code_complete.py`) is the **main entry point** for processing California legal codes. It integrates all pipeline components into one seamless, robust workflow.

## Features

### ✨ Fully Integrated Pipeline

1. **Stage 1**: Architecture & Tree Discovery
2. **Stage 2**: Concurrent Content Extraction (with checkpoints)
3. **Stage 3**: Multi-Version Section Handling
4. **Automatic Reconciliation**: Retry missing sections
5. **Failure Logging**: Track all failures to MongoDB
6. **Automatic Retry**: Retry failed sections automatically
7. **Final Report**: Comprehensive completion report

### 🛡️ Robustness Features

- **Request-level timeouts** (60-120s configurable)
- **Pause/Resume** capability with checkpoints
- **Graceful shutdown** (Ctrl+C handled properly)
- **Failure tracking** to MongoDB
- **Automatic retry** of failed sections
- **Progress logging** with ETA and success rates

### 📊 Complete Observability

- Real-time progress updates
- Success rate monitoring
- Stage timing and performance metrics
- Comprehensive failure reports
- MongoDB persistence for review

## Quick Start

### Basic Usage

```bash
# Process a code (most common)
python scripts/process_code_complete.py WIC

# Resume from checkpoint
python scripts/process_code_complete.py WIC --resume

# Custom worker count
python scripts/process_code_complete.py WIC --workers 20

# Skip automatic retry
python scripts/process_code_complete.py WIC --skip-retry
```

### Command-Line Options

```
usage: process_code_complete.py [-h] [--resume] [--workers WORKERS]
                                [--skip-retry] [--max-retry MAX_RETRY]
                                code

positional arguments:
  code                  Code abbreviation (e.g., WIC, FAM)

optional arguments:
  --resume              Resume from checkpoint
  --workers WORKERS     Concurrent workers (default: 15)
  --skip-retry          Skip automatic retry of failures
  --max-retry MAX_RETRY Max reconciliation retry attempts (default: 2)
```

## Pipeline Stages

### STEP 1: Data Cleanup (if not resuming)

```
🧹 STEP 1: Cleaning Existing Data
================================================================================
Deleted 6989 sections
Deleted 1 architecture documents
Deleted 140 checkpoints
Deleted 4 failure records
✅ Data cleared
```

**What it does:**
- Clears existing data for the code
- Removes old checkpoints and failures
- Prepares for fresh processing

**Skip this:** Use `--resume` flag

### STEP 2: Stage 1 - Architecture & Tree Discovery

```
🗺️  STEP 2: Stage 1 - Architecture & Tree Discovery
================================================================================
✅ Stage 1 Complete: 10.65 min
   Sections discovered: 6,991
   Tree depth: 5
```

**What it does:**
- Scrapes the code's table of contents
- Builds hierarchical tree structure
- Discovers all section URLs
- Saves architecture to MongoDB

**Duration:** ~10-15 minutes for large codes

### STEP 3: Stage 2 - Concurrent Content Extraction

```
📄 STEP 3: Stage 2 - Concurrent Content Extraction
   Workers: 15 | Batch size: 50
================================================================================
Progress: 500/6989 (7%)
Progress: 1000/6989 (14%)
...
✅ Stage 2 Complete: 36.12 min
   Total processed: 6,989
   Single-version: 6,903
   Multi-version: 83
   Failed: 3
   Rate: 5.2 sections/second
```

**What it does:**
- Scrapes all sections concurrently
- Batch size: 50 sections
- Workers: 15 (configurable)
- Saves checkpoint after each batch
- Logs failures to MongoDB

**Duration:** ~30-40 minutes for large codes
**Checkpoint:** Saved every 50 sections

### STEP 4: Stage 3 - Multi-Version Extraction

```
✨ STEP 4: Stage 3 - Multi-Version Extraction
   Sections: 83
================================================================================
✅ Stage 3 Complete: 17.54 min
   Extracted: 82/83
   Avg time: 12.68s per section
```

**What it does:**
- Handles sections with multiple versions
- Uses Playwright for complex pages
- Extracts all historical versions
- Logs failures to MongoDB

**Duration:** ~10-20 minutes (depends on multi-version count)

### STEP 5: Reconciliation

```
🔍 STEP 5: Reconciliation - Auto-Retry Missing Sections
================================================================================
Initial: 6985/6989 (99.94%)
Retry attempt 1/2 with 10 workers
No missing sections found
✅ 100% Complete after reconciliation
```

**What it does:**
- Identifies missing/incomplete sections
- Retries with reduced concurrency
- Adaptive worker reduction
- Logs persistent failures

**Max Attempts:** 2 (configurable with `--max-retry`)

### STEP 6: Automatic Retry of Failed Sections

```
🔄 STEP 6: Automatic Retry of Failed Sections
================================================================================
Found 4 logged failures
Attempting automatic retry...
✅ Retry Complete:
   Total: 4
   Succeeded: 2
   Failed: 2

Updated completion: 99.97%
```

**What it does:**
- Loads all logged failures from MongoDB
- Retries each failed section
- Updates failure status
- Re-calculates completion rate

**Skip this:** Use `--skip-retry` flag

### STEP 7: Final Report Generation

```
📊 STEP 7: Generating Final Report
================================================================================
✅ Final report generated and saved to MongoDB
   Collection: failure_reports
   View with: python scripts/retry_failed_sections.py WIC --report
```

**What it does:**
- Generates comprehensive failure report
- Saves to MongoDB `failure_reports` collection
- Includes failure breakdown by type/stage
- Tracks retry status

## Output Example

### Complete Run (WIC)

```
================================================================================
🚀 COMPLETE PIPELINE - Processing WIC
================================================================================
Workers: 15
Resume mode: OFF
Auto-retry: ON
================================================================================

[... processing stages ...]

================================================================================
🎉 WIC PROCESSING COMPLETE
================================================================================
Total Duration: 65.42 minutes
  Stage 1 (Architecture): 10.65 min
  Stage 2 (Content): 36.12 min
  Stage 3 (Multi-Version): 17.54 min

📊 Final Statistics:
  Total sections: 6,989
  Successful: 6,987
  Completion rate: 99.97%
  Failed sections: 2

🔧 Retry Options:
  Retry all: python scripts/retry_failed_sections.py WIC --all
  View report: python scripts/retry_failed_sections.py WIC --report

✅ STATUS: EXCELLENT (≥99%)
================================================================================
📁 Log file: logs/wic_complete_20251013_120000.log
================================================================================
```

## Pause and Resume

### Pausing During Processing

Press **Ctrl+C** at any time:

```
================================================================================
Received SIGINT signal - initiating graceful shutdown...
Checkpoint will be saved. Resume with --resume flag.
================================================================================

================================================================================
GRACEFUL SHUTDOWN
================================================================================
Process interrupted by user
Checkpoint saved for WIC

Resume with:
  python scripts/process_code_complete.py WIC --resume
================================================================================
```

### Resuming

```bash
python scripts/process_code_complete.py WIC --resume
```

**Behavior:**
- Skips data cleanup
- Loads last checkpoint
- Continues from last completed batch
- Preserves all progress

## Failure Handling

### Automatic Failure Logging

All failures are automatically logged to MongoDB:

- **Stage 2 failures** → `failed_sections` collection
- **Stage 3 failures** → `failed_sections` collection
- **Categorized** by failure type (API error, timeout, parse error, etc.)
- **Tracked** with retry status (pending, succeeded, failed, abandoned)

### Automatic Retry

By default, the pipeline automatically retries all logged failures:

```python
retry_service = RetryService(db)
retry_result = retry_service.retry_all_failed_sections(code)
```

**Disable:** Use `--skip-retry` flag

### Manual Retry

After processing, use the retry script:

```bash
# View failures
python scripts/retry_failed_sections.py WIC --report

# Retry specific section
python scripts/retry_failed_sections.py WIC --section 14005.20

# Retry all
python scripts/retry_failed_sections.py WIC --all

# Mark as abandoned
python scripts/retry_failed_sections.py WIC --section 10492.2 --abandon "Repealed"
```

## Monitoring Progress

### Real-Time Console Output

- Progress every 500 sections
- Batch completion messages
- Stage timing and statistics
- Success rate indicators

### Log Files

Located in `logs/` directory:
- Format: `{code}_complete_{timestamp}.log`
- Contains: DEBUG level details
- Includes: All errors, warnings, stack traces

### MongoDB Collections

1. **`section_contents`** - Extracted content
2. **`code_architectures`** - Tree structures
3. **`processing_checkpoints`** - Resume points
4. **`failed_sections`** - Failure tracking
5. **`failure_reports`** - Final reports

## Performance Tuning

### Worker Count

```bash
# More workers = faster (but more API load)
python scripts/process_code_complete.py WIC --workers 20

# Fewer workers = slower (but more reliable)
python scripts/process_code_complete.py WIC --workers 10
```

**Recommended:**
- Small codes (<1000 sections): 10 workers
- Medium codes (1000-5000): 15 workers
- Large codes (>5000): 15-20 workers

**Warning:** Too many workers may hit API rate limits

### Batch Size

Currently hardcoded at 50. To change:

```python
extractor = ConcurrentContentExtractor(
    db_manager=db,
    batch_size=100,  # Increase for fewer checkpoints
    max_workers=initial_workers
)
```

## Comparison with Other Scripts

| Script | Purpose | Best For |
|--------|---------|----------|
| `process_code_complete.py` | **Full pipeline** | Production use, complete processing |
| `process_code_with_reconciliation.py` | Pipeline without retry | Testing, legacy |
| `retry_failed_sections.py` | Manual retry tool | Post-processing, investigation |

## Exit Codes

- `0` - Success (completion rate ≥99%)
- `1` - Failure (completion rate <99%)
- `130` - Interrupted (Ctrl+C pressed)

## Best Practices

### 1. Always Start Fresh

```bash
# Don't use --resume unless you interrupted a run
python scripts/process_code_complete.py WIC
```

### 2. Monitor First 10 Minutes

- Check Stage 1 completes successfully
- Verify sections are being discovered
- Watch for immediate failures

### 3. Let It Run

- Don't interrupt during Stage 2
- If you must interrupt, press Ctrl+C (not kill)
- Resume with `--resume` flag

### 4. Review Results

```bash
# After completion, check report
python scripts/retry_failed_sections.py WIC --report

# Retry failures if needed
python scripts/retry_failed_sections.py WIC --all
```

### 5. Investigate Failures

- Review log file for patterns
- Check MongoDB `failed_sections` collection
- Use `--report --save-file` for permanent record

## Troubleshooting

### Process Hangs

**Symptom:** No progress for >5 minutes

**Solution:**
1. Press Ctrl+C to interrupt
2. Check log file for last activity
3. Resume with `--resume`
4. If still stuck, reduce workers

### High Failure Rate

**Symptom:** >5% failures

**Possible Causes:**
1. API rate limiting → Reduce workers
2. Network issues → Retry later
3. Invalid code → Check code name
4. Too many workers → Reduce to 10

### Resume Not Working

**Symptom:** `--resume` restarts from beginning

**Solution:**
1. Check `processing_checkpoints` collection exists
2. Verify checkpoint for your code
3. Try without `--resume` (will cleanup and restart)

### MongoDB Connection Error

**Symptom:** "Connection refused" or timeout

**Solution:**
```bash
# Check MongoDB is running
docker ps | grep mongo

# Start if needed
docker-compose up -d mongodb
```

## Integration Examples

### Cron Job (Daily Processing)

```bash
#!/bin/bash
# Process all codes daily

CODES=("WIC" "FAM" "CCP" "EVID")

for code in "${CODES[@]}"; do
    echo "Processing $code..."
    python scripts/process_code_complete.py "$code"

    # Check exit code
    if [ $? -eq 0 ]; then
        echo "$code completed successfully"
    else
        echo "$code failed - check logs"
    fi
done
```

### Python Integration

```python
import subprocess
import sys

def process_code(code: str) -> bool:
    """Process a code and return success status"""
    result = subprocess.run(
        [sys.executable, 'scripts/process_code_complete.py', code],
        capture_output=True,
        text=True
    )

    return result.returncode == 0

# Usage
if process_code('WIC'):
    print("WIC processed successfully")
else:
    print("WIC processing failed")
```

## Future Enhancements

1. **Parallel Code Processing**
   - Process multiple codes simultaneously
   - Shared worker pool

2. **Smart Worker Adjustment**
   - Auto-reduce on high failure rate
   - Auto-increase on success

3. **Notification System**
   - Email/Slack on completion
   - Alert on high failure rate

4. **Web Dashboard**
   - Real-time progress monitoring
   - Historical statistics
   - Failure analytics

## See Also

- [RETRY_SYSTEM.md](RETRY_SYSTEM.md) - Detailed retry system documentation
- [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md) - Pipeline robustness features
- [ROLLBACK_GUIDE.md](ROLLBACK_GUIDE.md) - Rollback instructions

## Support

For issues:
1. Check log file in `logs/` directory
2. Query MongoDB collections
3. Use retry script for investigation
4. Review failure report

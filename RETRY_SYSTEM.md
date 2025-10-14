

# Retry System Documentation

## Overview

The retry system provides comprehensive tracking and recovery for sections that fail during processing. It allows you to:

1. **Automatically log failures** during processing
2. **Manually retry failed sections** later
3. **Generate failure reports** for review
4. **Track retry attempts** and outcomes
5. **Mark unretrievable sections** as abandoned

## Architecture

### Components

1. **FailedSection Model** (`pipeline/models/failed_section.py`)
   - Tracks failure details, retry status, and attempt history
   - Stored in MongoDB `failed_sections` collection

2. **FailureLogger** (`pipeline/services/failure_logger.py`)
   - Helper class to log failures during processing
   - Categorizes failures by type (API error, timeout, parse error, etc.)

3. **RetryService** (`pipeline/services/retry_service.py`)
   - Handles manual retry of failed sections
   - Generates failure reports
   - Manages retry status updates

4. **Retry Script** (`scripts/retry_failed_sections.py`)
   - CLI tool for manual intervention
   - Retry individual or bulk sections
   - Generate reports

## Failure Types

| Type | Description | Retriable |
|------|-------------|-----------|
| `api_error` | Firecrawl API errors | ✅ Yes |
| `timeout` | Request timeout | ✅ Yes |
| `parse_error` | Content parsing failed | ✅ Yes |
| `empty_content` | No content found | ⚠️ Maybe (could be repealed) |
| `network_error` | Network connectivity issues | ✅ Yes |
| `multi_version_timeout` | Playwright timeout (>30s) | ✅ Yes |
| `repealed` | Section repealed/doesn't exist | ❌ No |

## Retry Status

| Status | Description |
|--------|-------------|
| `pending` | Not yet retried (default) |
| `retrying` | Currently being retried |
| `succeeded` | Manual retry succeeded |
| `failed` | Manual retry failed |
| `abandoned` | Confirmed unretrievable |

## Usage

### 1. Retry a Single Section

```bash
# Basic retry
python scripts/retry_failed_sections.py WIC --section 14005.20

# Force retry even if already succeeded
python scripts/retry_failed_sections.py WIC --section 14005.20 --force
```

**Example Output:**
```
================================================================================
Retrying WIC §14005.20
================================================================================

✅ SUCCESS
   version_count: 2
   total_content_length: 1828
```

### 2. Retry All Failed Sections

```bash
# Retry all
python scripts/retry_failed_sections.py WIC --all

# Retry with limit
python scripts/retry_failed_sections.py WIC --all --max 10

# Retry only specific failure types
python scripts/retry_failed_sections.py WIC --all --type timeout
python scripts/retry_failed_sections.py WIC --all --type api_error --type network_error
```

**Example Output:**
```
================================================================================
Retrying All Failed Sections for WIC
================================================================================

================================================================================
RETRY SUMMARY
================================================================================
Total attempted: 4
Succeeded: 2
Failed: 2

Errors:
  §10492.2: No content extracted
  §14196.5: No content extracted
```

### 3. Mark Section as Abandoned

For sections that are confirmed to be repealed or non-existent:

```bash
python scripts/retry_failed_sections.py WIC --section 10492.2 --abandon "Section repealed"
python scripts/retry_failed_sections.py WIC --section 14196.5 --abandon "Does not exist on official site"
```

### 4. Generate Failure Report

```bash
# Display report
python scripts/retry_failed_sections.py WIC --report

# Save to file
python scripts/retry_failed_sections.py WIC --report --save-file
```

**Example Output:**
```
================================================================================
Failure Report - WIC
================================================================================

Generated: 2025-10-13T11:30:00

Overall Statistics:
  Total sections: 6,989
  Successful: 6,987
  Failed: 4
  Completion rate: 99.97%

Failures by Type:
  api_error: 1
  empty_content: 2
  multi_version_timeout: 1

Failures by Stage:
  stage2_content: 3
  stage3_multi_version: 1

Retry Status:
  Pending retry: 0
  Retry succeeded: 2
  Retry failed: 0
  Abandoned: 2

Failed Sections (showing first 20):
  1. ✅ §4639.81 - api_error
      Firecrawl API error: Failed after 3 attempts...
  2. 🚫 §10492.2 - empty_content
      No content extracted from page (may be repealed)...
  3. ✅ §14005.20 - multi_version_timeout
      Request timed out after 30s...
  4. 🚫 §14196.5 - empty_content
      No content extracted from page (may be repealed)...

✅ Report saved to MongoDB collection: failure_reports
✅ Report also saved to file: failure_report_wic_20251013_113000.txt
```

## Integration with Processing Pipeline

### During Processing

The failure logger automatically records failures:

```python
from pipeline.services.failure_logger import log_section_failure

# In your extraction code
try:
    result = extract_section(url)
except Exception as e:
    log_section_failure(
        db=db_manager,
        code='WIC',
        section='14005.20',
        url=url,
        error=e,
        stage='stage2_content',
        is_multi_version=True,
        batch_number=25
    )
```

### After Processing

1. **Check for failures:**
   ```bash
   python scripts/retry_failed_sections.py WIC --report
   ```

2. **Retry failed sections:**
   ```bash
   python scripts/retry_failed_sections.py WIC --all
   ```

3. **Review remaining failures:**
   ```bash
   python scripts/retry_failed_sections.py WIC --report
   ```

4. **Mark unretrievable sections:**
   ```bash
   python scripts/retry_failed_sections.py WIC --section 10492.2 --abandon "Repealed"
   ```

## MongoDB Collections

### `failed_sections`

Stores individual failure records:

```json
{
  "code": "WIC",
  "section": "14005.20",
  "url": "https://...",
  "failure_type": "multi_version_timeout",
  "error_message": "Request timed out after 30s",
  "stage": "stage3_multi_version",
  "batch_number": 55,
  "is_multi_version": true,
  "retry_status": "succeeded",
  "retry_count": 1,
  "retry_attempts": [
    {
      "timestamp": "2025-10-13T11:15:00",
      "success": true,
      "details": {
        "version_count": 2,
        "total_content_length": 1828
      }
    }
  ],
  "failed_at": "2025-10-13T10:52:33",
  "resolved_at": "2025-10-13T11:15:00"
}
```

### `failure_reports`

Stores generated failure reports:

```json
{
  "code": "WIC",
  "generated_at": "2025-10-13T11:30:00",
  "total_sections": 6989,
  "successful_sections": 6987,
  "failed_sections": 4,
  "completion_rate": 99.97,
  "failures_by_type": {
    "api_error": 1,
    "empty_content": 2,
    "multi_version_timeout": 1
  },
  "failures_by_stage": {
    "stage2_content": 3,
    "stage3_multi_version": 1
  },
  "pending_retry": 0,
  "retry_succeeded": 2,
  "retry_failed": 0,
  "abandoned": 2
}
```

## Workflow Example: WIC Processing

### 1. Initial Processing
```bash
python scripts/process_code_with_reconciliation.py WIC
```
**Result:** 6,985/6,989 sections (99.94%) - 4 failures

### 2. Generate Report
```bash
python scripts/retry_failed_sections.py WIC --report
```
**Shows:** 4 failed sections - 1 api_error, 2 empty_content, 1 multi_version_timeout

### 3. Retry All Failures
```bash
python scripts/retry_failed_sections.py WIC --all
```
**Result:** 2 succeeded (§4639.81, §14005.20), 2 failed (§10492.2, §14196.5)

### 4. Investigate Failures
Manual check reveals §10492.2 and §14196.5 are empty pages (repealed)

### 5. Mark as Abandoned
```bash
python scripts/retry_failed_sections.py WIC --section 10492.2 --abandon "Empty page - likely repealed"
python scripts/retry_failed_sections.py WIC --section 14196.5 --abandon "Empty page - likely repealed"
```

### 6. Final Report
```bash
python scripts/retry_failed_sections.py WIC --report --save-file
```
**Result:** 6,987/6,989 (99.97%) - 2 abandoned (repealed sections)

## Best Practices

### 1. During Development
- Use `--report` frequently to monitor failure rates
- Investigate high failure rates immediately
- Test retry logic with known-good sections

### 2. In Production
- Run retry script daily for new failures
- Generate weekly failure reports
- Maintain abandoned section documentation

### 3. Performance
- Retry in batches (`--max`) to avoid overwhelming APIs
- Use `--type` filter to prioritize retriable failures
- Retry during off-peak hours

### 4. Data Quality
- Always verify retry results
- Document abandoned sections with clear reasons
- Periodically review abandoned sections (may be reinstated)

## Advanced Usage

### Programmatic Access

```python
from pipeline.core.database import DatabaseManager
from pipeline.services.retry_service import RetryService

db = DatabaseManager()
db.connect()

retry_service = RetryService(db)

# Retry a specific section
result = retry_service.retry_failed_section('WIC', '14005.20')

# Generate report
report = retry_service.generate_failure_report('WIC')

# Retry all timeouts
results = retry_service.retry_all_failed_sections(
    'WIC',
    failure_types=[FailureType.TIMEOUT, FailureType.MULTI_VERSION_TIMEOUT]
)

db.disconnect()
```

### Custom Queries

```python
from pymongo import MongoClient

client = MongoClient('mongodb://...')
db = client['ca_codes_db']

# Find all pending retries
pending = list(db.failed_sections.find({
    'code': 'WIC',
    'retry_status': 'pending'
}))

# Find sections that failed multiple times
frequent_failures = list(db.failed_sections.find({
    'code': 'WIC',
    'attempt_number': {'$gt': 3}
}))

# Get failure rate by batch
pipeline = [
    {'$match': {'code': 'WIC'}},
    {'$group': {
        '_id': '$batch_number',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}}
]
failure_by_batch = list(db.failed_sections.aggregate(pipeline))
```

## Troubleshooting

### No Failures Logged
**Problem:** Failures occurring but not being logged

**Solution:**
- Check that failure_logger is imported
- Verify MongoDB connection
- Check log files for exceptions

### Retry Always Fails
**Problem:** Section fails every retry attempt

**Possible Causes:**
1. Section truly doesn't exist (mark as abandoned)
2. API issues (wait and retry later)
3. Parsing logic needs update

### Report Not Generating
**Problem:** `--report` command fails

**Solution:**
- Ensure MongoDB is accessible
- Check failed_sections collection exists
- Verify code name is correct (case-sensitive)

## Future Enhancements

1. **Auto-Retry During Processing**
   - Retry failures immediately with reduced concurrency
   - Smart retry based on failure type

2. **Scheduled Retries**
   - Cron job for daily retry attempts
   - Email notifications on retry results

3. **Failure Prediction**
   - ML model to predict likely failures
   - Preemptive timeout adjustment

4. **Web Dashboard**
   - Real-time failure monitoring
   - Interactive retry management
   - Failure analytics and trends

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review failure report for patterns
3. Query MongoDB `failed_sections` collection directly
4. Check `UPGRADE_SUMMARY.md` for related features


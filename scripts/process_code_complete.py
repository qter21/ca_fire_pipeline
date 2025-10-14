"""
Complete Code Processing Pipeline
Full end-to-end pipeline with automatic retry and failure tracking

This is the main entry point for processing California legal codes.
Includes:
1. Architecture crawling (Stage 1)
2. Concurrent content extraction (Stage 2)
3. Multi-version extraction (Stage 3)
4. Automatic reconciliation
5. Failure logging and tracking
6. Automatic retry of failed sections
7. Final report generation

Usage:
    python scripts/process_code_complete.py WIC
    python scripts/process_code_complete.py WIC --resume
    python scripts/process_code_complete.py WIC --workers 20
    python scripts/process_code_complete.py WIC --skip-retry
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import signal
from typing import Dict
from datetime import datetime
import logging

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.reconciliation_service import ReconciliationService
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.retry_service import RetryService
from pipeline.services.failure_logger import FailureLogger
from pipeline.models.checkpoint import CheckpointUpdate, CheckpointStatus

# Create logs directory
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global shutdown_requested
    signal_name = signal.Signals(signum).name
    logging.warning(f"\n{'='*80}")
    logging.warning(f"Received {signal_name} signal - initiating graceful shutdown...")
    logging.warning(f"Checkpoint will be saved. Resume with --resume flag.")
    logging.warning(f"{'='*80}")
    shutdown_requested = True


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logging.info("Signal handlers registered (SIGINT, SIGTERM)")


def setup_logging(code: str):
    """Setup logging to console and file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{code.lower()}_complete_{timestamp}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []

    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized for {code}")
    logging.info(f"Log file: {log_file}")

    return log_file


def process_code_complete(
    code: str,
    initial_workers: int = 15,
    resume: bool = False,
    skip_retry: bool = False,
    max_retry_attempts: int = 2
) -> Dict:
    """
    Complete end-to-end code processing pipeline

    Args:
        code: Code abbreviation (e.g., 'WIC', 'FAM')
        initial_workers: Initial concurrent workers (default: 15)
        resume: Resume from checkpoint if available
        skip_retry: Skip automatic retry of failed sections
        max_retry_attempts: Maximum retry attempts during reconciliation

    Returns:
        Complete processing report
    """
    # Setup
    log_file = setup_logging(code)
    setup_signal_handlers()

    logging.info('='*80)
    logging.info(f'🚀 COMPLETE PIPELINE - Processing {code}')
    logging.info('='*80)
    logging.info(f'Workers: {initial_workers}')
    logging.info(f'Resume mode: {"ON" if resume else "OFF"}')
    logging.info(f'Auto-retry: {"OFF" if skip_retry else "ON"}')
    logging.info('='*80)

    # Connect to database
    db = DatabaseManager()
    db.connect()
    logging.info("✅ Connected to MongoDB")

    # Initialize services
    firecrawl = FirecrawlService()
    failure_logger = FailureLogger(db)

    # Timing
    pipeline_start = datetime.now()
    stage_times = {}

    # Clean data (if not resuming)
    if not resume:
        logging.info('='*80)
        logging.info('🧹 STEP 1: Cleaning Existing Data')
        logging.info('='*80)

        sections_deleted = db.section_contents.delete_many({'code': code}).deleted_count
        arch_deleted = db.code_architectures.delete_many({'code': code}).deleted_count
        checkpoints_deleted = db.db['processing_checkpoints'].delete_many({'code': code}).deleted_count
        failures_deleted = db.db['failed_sections'].delete_many({'code': code}).deleted_count

        logging.info(f"Deleted {sections_deleted} sections")
        logging.info(f"Deleted {arch_deleted} architecture documents")
        logging.info(f"Deleted {checkpoints_deleted} checkpoints")
        logging.info(f"Deleted {failures_deleted} failure records")
        logging.info('✅ Data cleared')
    else:
        logging.info('='*80)
        logging.info('🔄 STEP 1: Resuming from Checkpoint')
        logging.info('='*80)
        logging.info('Skipping data cleanup')

    # STAGE 1: Architecture
    logging.info('='*80)
    logging.info('🗺️  STEP 2: Stage 1 - Architecture & Tree Discovery')
    logging.info('='*80)

    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
    start = datetime.now()
    result1 = crawler.crawl(code, save_to_db=True)
    stage_times['stage1'] = (datetime.now() - start).total_seconds()

    logging.info(f'✅ Stage 1 Complete: {stage_times["stage1"]/60:.2f} min')
    logging.info(f'   Sections discovered: {result1["total_sections"]:,}')
    logging.info(f'   Tree depth: {result1.get("statistics", {}).get("max_depth", 0)}')

    if shutdown_requested:
        logging.warning("Shutdown requested during Stage 1")
        return _handle_shutdown(db, code, log_file)

    # STAGE 2: Concurrent Content Extraction
    logging.info('='*80)
    logging.info(f'📄 STEP 3: Stage 2 - Concurrent Content Extraction')
    logging.info(f'   Workers: {initial_workers} | Batch size: 50')
    logging.info('='*80)

    extractor = ConcurrentContentExtractor(
        db_manager=db,
        batch_size=50,
        max_workers=initial_workers,
        enable_checkpointing=True
    )

    start = datetime.now()
    result2 = extractor.extract(
        code,
        skip_multi_version=False,
        progress_callback=lambda p, t: logging.info(f'Progress: {p}/{t} ({p/t*100:.0f}%)')
        if p % 500 == 0 or p == t else None
    )
    stage_times['stage2'] = (datetime.now() - start).total_seconds()

    rate = result2["total_sections"] / stage_times['stage2'] if stage_times['stage2'] > 0 else 0

    logging.info(f'✅ Stage 2 Complete: {stage_times["stage2"]/60:.2f} min')
    logging.info(f'   Total processed: {result2["total_sections"]:,}')
    logging.info(f'   Single-version: {result2["single_version_count"]:,}')
    logging.info(f'   Multi-version: {result2["multi_version_count"]}')
    logging.info(f'   Failed: {len(result2["failed_sections"])}')
    logging.info(f'   Rate: {rate:.2f} sections/second')

    # Log Stage 2 failures
    for failed in result2.get("failed_sections", []):
        parts = failed.split(':')
        if len(parts) == 2:
            section_doc = db.section_contents.find_one({'code': code, 'section': parts[1]})
            if section_doc:
                failure_logger.log_empty_content(
                    code=code,
                    section=parts[1],
                    url=section_doc.get('url', ''),
                    stage='stage2_content',
                    is_multi_version=section_doc.get('is_multi_version', False)
                )

    if shutdown_requested:
        logging.warning("Shutdown requested during Stage 2")
        return _handle_shutdown(db, code, log_file)

    # STAGE 3: Multi-Version Extraction
    stage_times['stage3'] = 0
    if result2['multi_version_count'] > 0:
        logging.info('='*80)
        logging.info(f'✨ STEP 4: Stage 3 - Multi-Version Extraction')
        logging.info(f'   Sections: {result2["multi_version_count"]}')
        logging.info('='*80)

        stage3_extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        start = datetime.now()
        result3 = stage3_extractor.extract_multi_version_sections(code)
        stage_times['stage3'] = (datetime.now() - start).total_seconds()

        avg_per_section = stage_times['stage3'] / result3["total_sections"] if result3["total_sections"] > 0 else 0

        logging.info(f'✅ Stage 3 Complete: {stage_times["stage3"]/60:.2f} min')
        logging.info(f'   Extracted: {result3["extracted_count"]}/{result3["total_sections"]}')
        logging.info(f'   Avg time: {avg_per_section:.2f}s per section')

        # Log Stage 3 failures
        for failed in result3.get("failed_sections", []):
            parts = failed.split(':')
            if len(parts) == 2:
                section_doc = db.section_contents.find_one({'code': code, 'section': parts[1]})
                if section_doc:
                    failure_logger.log_timeout(
                        code=code,
                        section=parts[1],
                        url=section_doc.get('url', ''),
                        timeout_duration=30.0,
                        stage='stage3_multi_version',
                        is_multi_version=True
                    )
    else:
        logging.info('⏭️  Skipping Stage 3 - No multi-version sections')

    if shutdown_requested:
        logging.warning("Shutdown requested during Stage 3")
        return _handle_shutdown(db, code, log_file)

    # RECONCILIATION
    logging.info('='*80)
    logging.info('🔍 STEP 5: Reconciliation - Auto-Retry Missing Sections')
    logging.info('='*80)

    reconciliation = ReconciliationService(db_manager=db)
    recon_report = reconciliation.reconcile_code(
        code,
        max_retry_attempts=max_retry_attempts,
        initial_workers=10,
        min_workers=5
    )

    # Log reconciliation report
    report_text = reconciliation.generate_reconciliation_report(code)
    for line in report_text.split('\n'):
        logging.info(line)

    if recon_report['success']:
        logging.info('✅ 100% Complete after reconciliation')
    else:
        logging.warning(f"⚠️  {recon_report['final_status']['missing']} sections still missing")

    # AUTOMATIC RETRY (if enabled)
    retry_result = None
    if not skip_retry and not recon_report['success']:
        logging.info('='*80)
        logging.info('🔄 STEP 6: Automatic Retry of Failed Sections')
        logging.info('='*80)

        retry_service = RetryService(db)
        failure_count = failure_logger.get_failure_count(code)

        if failure_count > 0:
            logging.info(f"Found {failure_count} logged failures")
            logging.info("Attempting automatic retry...")

            retry_result = retry_service.retry_all_failed_sections(
                code,
                max_retries=None  # Retry all
            )

            logging.info(f"✅ Retry Complete:")
            logging.info(f"   Total: {retry_result['total']}")
            logging.info(f"   Succeeded: {retry_result['succeeded']}")
            logging.info(f"   Failed: {retry_result['failed']}")

            if retry_result['succeeded'] > 0:
                # Re-check completion after successful retries
                final_status = reconciliation._assess_code_completeness(code)
                logging.info(f"\nUpdated completion: {final_status['completion_rate']:.2f}%")
        else:
            logging.info("No failures logged for retry")
    elif skip_retry:
        logging.info('⏭️  Skipping automatic retry (--skip-retry flag)')

    # FINAL REPORT GENERATION
    logging.info('='*80)
    logging.info('📊 STEP 7: Generating Final Report')
    logging.info('='*80)

    retry_service = RetryService(db)
    failure_report = retry_service.generate_failure_report(code)

    logging.info(f"✅ Final report generated and saved to MongoDB")
    logging.info(f"   Collection: failure_reports")
    logging.info(f"   View with: python scripts/retry_failed_sections.py {code} --report")

    # FINAL SUMMARY
    total_time = sum(stage_times.values())
    pipeline_end = datetime.now()
    actual_duration = (pipeline_end - pipeline_start).total_seconds()

    logging.info('='*80)
    logging.info(f'🎉 {code} PROCESSING COMPLETE')
    logging.info('='*80)
    logging.info(f'Total Duration: {actual_duration/60:.2f} minutes')
    logging.info(f'  Stage 1 (Architecture): {stage_times.get("stage1", 0)/60:.2f} min')
    logging.info(f'  Stage 2 (Content): {stage_times.get("stage2", 0)/60:.2f} min')
    logging.info(f'  Stage 3 (Multi-Version): {stage_times.get("stage3", 0)/60:.2f} min')
    logging.info('')
    logging.info('📊 Final Statistics:')
    logging.info(f'  Total sections: {failure_report.total_sections:,}')
    logging.info(f'  Successful: {failure_report.successful_sections:,}')
    logging.info(f'  Completion rate: {failure_report.completion_rate:.2f}%')
    logging.info(f'  Failed sections: {failure_report.failed_sections}')
    logging.info('')

    if failure_report.failed_sections > 0:
        logging.info('🔧 Retry Options:')
        logging.info(f'  Retry all: python scripts/retry_failed_sections.py {code} --all')
        logging.info(f'  View report: python scripts/retry_failed_sections.py {code} --report')
        logging.info('')

    if failure_report.completion_rate >= 100.0:
        logging.info('✅ STATUS: 100% COMPLETE!')
    elif failure_report.completion_rate >= 99.0:
        logging.info('✅ STATUS: EXCELLENT (≥99%)')
    elif failure_report.completion_rate >= 95.0:
        logging.info('⚠️  STATUS: GOOD (≥95%)')
    else:
        logging.info('❌ STATUS: NEEDS ATTENTION (<95%)')

    logging.info('='*80)
    logging.info(f'📁 Log file: {log_file}')
    logging.info('='*80)

    db.disconnect()
    logging.info("Disconnected from MongoDB")

    return {
        'code': code,
        'success': failure_report.completion_rate >= 99.0,
        'completion_rate': failure_report.completion_rate,
        'total_time': actual_duration,
        'log_file': str(log_file),
        'stages': stage_times,
        'reconciliation': recon_report,
        'retry_result': retry_result,
        'failure_report': failure_report.dict()
    }


def _handle_shutdown(db: DatabaseManager, code: str, log_file: Path) -> Dict:
    """Handle graceful shutdown"""
    logging.warning("="*80)
    logging.warning("GRACEFUL SHUTDOWN")
    logging.warning("="*80)
    logging.warning("Process interrupted by user")
    logging.warning(f"Checkpoint saved for {code}")
    logging.warning("")
    logging.warning("Resume with:")
    logging.warning(f"  python scripts/process_code_complete.py {code} --resume")
    logging.warning("="*80)

    db.disconnect()

    return {
        'code': code,
        'success': False,
        'interrupted': True,
        'log_file': str(log_file),
        'message': 'Process interrupted - checkpoint saved'
    }


def main():
    parser = argparse.ArgumentParser(
        description='Complete code processing pipeline with automatic retry',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process a code
  python scripts/process_code_complete.py WIC

  # Resume from checkpoint
  python scripts/process_code_complete.py WIC --resume

  # Custom worker count
  python scripts/process_code_complete.py WIC --workers 20

  # Skip automatic retry
  python scripts/process_code_complete.py WIC --skip-retry

  # Custom retry attempts
  python scripts/process_code_complete.py WIC --max-retry 3
        '''
    )

    parser.add_argument('code', help='Code abbreviation (e.g., WIC, FAM)')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--workers', type=int, default=15, help='Concurrent workers (default: 15)')
    parser.add_argument('--skip-retry', action='store_true', help='Skip automatic retry of failures')
    parser.add_argument('--max-retry', type=int, default=2, help='Max reconciliation retry attempts (default: 2)')

    args = parser.parse_args()

    code = args.code.upper()

    result = process_code_complete(
        code=code,
        initial_workers=args.workers,
        resume=args.resume,
        skip_retry=args.skip_retry,
        max_retry_attempts=args.max_retry
    )

    # Exit codes
    if result.get('interrupted'):
        sys.exit(130)  # SIGINT
    elif result.get('success'):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == '__main__':
    main()

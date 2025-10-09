"""
Complete code processing with automatic reconciliation

Workflow:
1. Run all 3 stages
2. Generate initial report
3. Find missing sections
4. Retry with adaptive concurrency
5. Log failures to MongoDB if any
6. Generate final report
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict
import os
from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.reconciliation_service import ReconciliationService
from pipeline.services.firecrawl_service import FirecrawlService
from datetime import datetime
import logging

# Create logs directory if it doesn't exist
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)


def setup_logging(code: str):
    """Setup detailed logging to both console and file"""
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{code.lower()}_{timestamp}.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    root_logger.handlers = []

    # Console handler (INFO level, clean format)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)

    # File handler (DEBUG level, detailed format)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized for {code}")
    logging.info(f"Log file: {log_file}")

    return log_file


def process_code_complete(code: str, initial_workers: int = 15) -> Dict:
    """
    Process a complete code with automatic reconciliation

    Args:
        code: Code abbreviation
        initial_workers: Initial concurrent workers (default: 15, safe for rate limits)

    Returns:
        Complete processing report
    """
    # Setup logging first
    log_file = setup_logging(code)

    logging.info('='*80)
    logging.info(f'Processing {code} with Auto-Reconciliation')
    logging.info(f'Initial concurrent workers: {initial_workers}')
    logging.info('='*80)

    db = DatabaseManager()
    db.connect()
    logging.info(f"Connected to MongoDB")

    # Clean data
    logging.info('='*80)
    logging.info('🧹 Step 1: Cleaning existing data')
    logging.info('='*80)

    sections_deleted = db.section_contents.delete_many({'code': code}).deleted_count
    arch_deleted = db.code_architectures.delete_many({'code': code}).deleted_count

    logging.info(f"Deleted {sections_deleted} sections from section_contents")
    logging.info(f"Deleted {arch_deleted} documents from code_architectures")
    logging.info('✅ Data cleared')

    firecrawl = FirecrawlService()

    # STAGE 1: Architecture with tree
    logging.info('='*80)
    logging.info('🗺️  Step 2: Stage 1 (Architecture + Tree)')
    logging.info('='*80)

    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)

    logging.info(f"Starting architecture crawl for {code}")
    start = datetime.now()
    result1 = crawler.crawl(code, save_to_db=True)
    s1_time = (datetime.now() - start).total_seconds()

    logging.info(f'✅ Stage 1 Complete: {s1_time/60:.2f} min ({s1_time:.2f}s)')
    logging.info(f'Sections discovered: {result1["total_sections"]}')
    logging.info(f'Text pages processed: {len(result1.get("text_page_urls", []))}')
    logging.info(f'Tree nodes: {result1.get("items_count", 0)}')
    logging.info(f'Tree depth: {result1.get("statistics", {}).get("max_depth", 0)}')
    logging.debug(f'Session ID: {result1.get("session_id", "N/A")}')

    # STAGE 2: Content extraction (concurrent)
    logging.info('='*80)
    logging.info(f'📄 Step 3: Stage 2 (Concurrent - {initial_workers} workers)')
    logging.info('='*80)

    extractor = ConcurrentContentExtractor(
        db_manager=db,
        batch_size=50,
        max_workers=initial_workers
    )

    logging.info(f"Starting concurrent content extraction for {code}")
    logging.info(f"Batch size: 50, Workers: {initial_workers}")

    start = datetime.now()
    result2 = extractor.extract(
        code,
        skip_multi_version=False,
        progress_callback=lambda p, t: logging.info(f'Progress: {p}/{t} ({p/t*100:.0f}%)')
        if p % 500 == 0 or p == t else None
    )
    s2_time = (datetime.now() - start).total_seconds()

    rate = result2["total_sections"] / s2_time if s2_time > 0 else 0

    logging.info(f'✅ Stage 2 Complete: {s2_time/60:.2f} min ({s2_time:.2f}s)')
    logging.info(f'Total processed: {result2["total_sections"]}')
    logging.info(f'Single-version extracted: {result2["single_version_count"]}')
    logging.info(f'Multi-version detected: {result2["multi_version_count"]}')
    logging.info(f'Failed sections: {len(result2["failed_sections"])}')
    logging.info(f'Processing rate: {rate:.2f} sections/second')

    if result2["failed_sections"]:
        logging.warning(f'Failed sections list: {result2["failed_sections"][:10]}...')
        logging.debug(f'All failed sections: {result2["failed_sections"]}')

    # STAGE 3: Multi-version extraction
    s3_time = 0
    if result2['multi_version_count'] > 0:
        logging.info('='*80)
        logging.info(f'✨ Step 4: Stage 3 (Multi-Version: {result2["multi_version_count"]} sections)')
        logging.info('='*80)

        stage3_extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        logging.info(f"Starting multi-version extraction for {result2['multi_version_count']} sections")
        start = datetime.now()
        result3 = stage3_extractor.extract_multi_version_sections(code)
        s3_time = (datetime.now() - start).total_seconds()

        avg_per_section = s3_time / result3["total_sections"] if result3["total_sections"] > 0 else 0

        logging.info(f'✅ Stage 3 Complete: {s3_time/60:.2f} min ({s3_time:.2f}s)')
        logging.info(f'Multi-version extracted: {result3["extracted_count"]}/{result3["total_sections"]}')
        logging.info(f'Avg time per multi-version: {avg_per_section:.2f}s')

        if result3["failed_sections"]:
            logging.warning(f'Failed multi-version sections: {result3["failed_sections"]}')

        # Sync multi_version_sections to code_architectures
        mv_secs = list(db.section_contents.find(
            {'code': code, 'is_multi_version': True},
            {'section': 1}
        ))
        mv_list = sorted([s['section'] for s in mv_secs])
        db.code_architectures.update_one(
            {'code': code},
            {'$set': {'multi_version_sections': mv_list}}
        )
        logging.info(f'Synced {len(mv_list)} multi-version sections to code_architectures')
        logging.debug(f'Multi-version sections: {mv_list}')
    else:
        logging.info('No multi-version sections detected, skipping Stage 3')

    # RECONCILIATION: Check and retry missing
    logging.info('='*80)
    logging.info('🔍 Step 5: Reconciliation (Auto-retry missing sections)')
    logging.info('='*80)

    reconciliation = ReconciliationService(db_manager=db)

    logging.info("Starting reconciliation check")
    recon_report = reconciliation.reconcile_code(
        code,
        max_retry_attempts=2,
        initial_workers=10,  # Lower for retries
        min_workers=5
    )

    # Log reconciliation report
    report_text = reconciliation.generate_reconciliation_report(code)
    for line in report_text.split('\n'):
        logging.info(line)

    if recon_report['success']:
        logging.info('✅ 100% Complete after reconciliation')
    else:
        logging.warning(f"⚠️  {recon_report['final_status']['missing']} sections still missing after reconciliation")
        logging.warning('Failures logged to processing_status collection for manual review')

    # Log reconciliation attempts
    if recon_report.get('attempts'):
        logging.debug(f"Reconciliation attempts: {len(recon_report['attempts'])}")
        for attempt in recon_report['attempts']:
            logging.debug(
                f"Attempt {attempt['attempt']}: {attempt['workers']} workers, "
                f"{attempt['success']} success, {attempt['failed']} failed"
            )

    # FINAL SUMMARY
    total_time = s1_time + s2_time + s3_time

    logging.info('='*80)
    logging.info(f'✅ {code} PROCESSING COMPLETE')
    logging.info('='*80)
    logging.info(f'Total Duration: {total_time/60:.2f} minutes ({total_time:.2f}s)')
    logging.info(f'   Stage 1 (Architecture): {s1_time/60:.2f} min')
    logging.info(f'   Stage 2 (Content): {s2_time/60:.2f} min')
    logging.info(f'   Stage 3 (Multi-Version): {s3_time/60:.2f} min' if s3_time > 0 else '   Stage 3: N/A (no multi-version)')
    logging.info('')
    logging.info('Final Status:')
    logging.info(f'   Total sections: {recon_report["final_status"]["total"]}')
    logging.info(f'   Complete: {recon_report["final_status"]["complete"]}')
    logging.info(f'   Success Rate: {recon_report["final_status"]["completion_rate"]:.2f}%')
    logging.info(f'   Single-version: {recon_report["final_status"]["single_version"]}')
    logging.info(f'   Multi-version: {recon_report["final_status"]["multi_version"]}')

    if recon_report["final_status"]["completion_rate"] >= 100.0:
        logging.info('🎉 STATUS: 100% COMPLETE!')
    else:
        logging.warning(f'⚠️  STATUS: {recon_report["final_status"]["missing"]} sections incomplete')

    logging.info('='*80)
    logging.info(f'Log file saved to: {log_file}')
    logging.info('='*80)

    db.disconnect()
    logging.info("Disconnected from MongoDB")

    return {
        'code': code,
        'total_time': total_time,
        'log_file': str(log_file),
        'stages': {
            'stage1': s1_time,
            'stage2': s2_time,
            'stage3': s3_time
        },
        'reconciliation': recon_report
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python process_code_with_reconciliation.py <CODE>")
        print("Example: python process_code_with_reconciliation.py FAM")
        sys.exit(1)

    code = sys.argv[1].upper()
    result = process_code_complete(code, initial_workers=15)

    # Exit with appropriate code
    sys.exit(0 if result['reconciliation']['success'] else 1)

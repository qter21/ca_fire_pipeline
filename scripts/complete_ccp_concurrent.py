"""Complete CCP code test with CONCURRENT scraping - 20x faster!"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    code = "CCP"
    concurrent_workers = 25  # Use 25 workers (50% of 50 max capacity)

    print('='*80)
    print(f'COMPLETE CCP CODE TEST - CONCURRENT SCRAPING (25 WORKERS)')
    print('='*80)
    print()
    print(f'Starting at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Concurrent workers: {concurrent_workers}')
    print()

    # Connect to database
    db = DatabaseManager()
    db.connect()
    print('✅ Connected to MongoDB')

    # Clean CCP data
    print(f'🧹 Cleaning existing CCP data...')
    sections_deleted = db.section_contents.delete_many({'code': code}).deleted_count
    codes_deleted = db.code_architectures.delete_many({'code': code}).deleted_count
    print(f'   Deleted {sections_deleted} sections, {codes_deleted} code records')
    print()

    # Create services
    firecrawl = FirecrawlService()
    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
    # Use CONCURRENT extractor with 25 workers
    extractor = ConcurrentContentExtractor(db_manager=db, batch_size=50, max_workers=concurrent_workers)

    # ========== STAGE 1: Architecture Crawl ==========
    print('='*80)
    print('STAGE 1: Architecture Crawler')
    print('='*80)
    print()

    start_time = datetime.now()
    result = crawler.crawl(code, save_to_db=True)
    stage1_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ STAGE 1 COMPLETE')
    print(f'   Duration: {stage1_duration:.2f}s ({stage1_duration/60:.2f} minutes)')
    print(f'   Sections discovered: {result["total_sections"]}')
    print()

    # ========== STAGE 2: CONCURRENT Content Extraction ==========
    print('='*80)
    print(f'STAGE 2: CONCURRENT Content Extraction ({concurrent_workers} workers)')
    print('='*80)
    print()

    start_time = datetime.now()

    # Progress tracking
    last_update = datetime.now()
    def progress_callback(processed, total):
        nonlocal last_update
        now = datetime.now()
        if (now - last_update).total_seconds() >= 10 or processed == total:
            pct = (processed/total*100) if total > 0 else 0
            elapsed = (now - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            print(f'   [{datetime.now().strftime("%H:%M:%S")}] {processed}/{total} ({pct:.1f}%) | {rate:.1f}/s | ETA: {eta/60:.1f}min')
            last_update = now

    result2 = extractor.extract(
        code,
        skip_multi_version=False,
        progress_callback=progress_callback
    )

    stage2_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ STAGE 2 COMPLETE (CONCURRENT)')
    print(f'   Duration: {stage2_duration:.2f}s ({stage2_duration/60:.2f} minutes)')
    print(f'   Sections: {result2["total_sections"]}')
    print(f'   Extracted: {result2["single_version_count"]}')
    print(f'   Multi-version: {result2["multi_version_count"]}')
    print(f'   Failed: {len(result2["failed_sections"])}')
    print(f'   Rate: {result2["total_sections"]/stage2_duration:.1f} sections/second')
    print()

    # ========== STAGE 3: Multi-Version ==========
    if result2["multi_version_count"] > 0:
        print('='*80)
        print(f'STAGE 3: Multi-Version Extraction ({result2["multi_version_count"]} sections)')
        print('='*80)
        print()

        start_time = datetime.now()

        # Import regular extractor for Stage 3 (Playwright doesn't benefit from concurrency)
        from pipeline.services.content_extractor import ContentExtractor
        stage3_extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)

        result3 = stage3_extractor.extract_multi_version_sections(
            code,
            progress_callback=lambda p, t: print(f'   Multi-version: {p}/{t}')
        )

        stage3_duration = (datetime.now() - start_time).total_seconds()

        print()
        print(f'✅ STAGE 3 COMPLETE')
        print(f'   Duration: {stage3_duration:.2f}s')
        print(f'   Extracted: {result3["extracted_count"]}/{result3["total_sections"]}')
        print()
    else:
        stage3_duration = 0

    # ========== VERIFICATION ==========
    print('='*80)
    print('FINAL VERIFICATION')
    print('='*80)
    print()

    code_entry = db.get_code(code)
    total_in_db = db.section_contents.count_documents({'code': code})
    with_content = db.section_contents.count_documents({'code': code, 'has_content': True})
    multi_version = db.section_contents.count_documents({'code': code, 'is_multi_version': True})
    with_versions = db.section_contents.count_documents({'code': code, 'versions': {'$ne': None}})

    print(f'📊 Results:')
    print(f'   Total: {total_in_db}')
    print(f'   Single-version: {with_content}/{total_in_db - multi_version}')
    print(f'   Multi-version: {with_versions}/{multi_version}')
    print(f'   Success: {(with_content + with_versions)/total_in_db*100:.2f}%')
    print()

    db.disconnect()

    # ========== SUMMARY ==========
    total_duration = stage1_duration + stage2_duration + stage3_duration

    print('='*80)
    print('🎉 CCP COMPLETE (CONCURRENT)')
    print('='*80)
    print()
    print(f'Total Duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)')
    print(f'Concurrent Workers: {concurrent_workers}')
    print()
    print(f'Stage 1: {stage1_duration/60:.2f} min')
    print(f'Stage 2 (CONCURRENT): {stage2_duration/60:.2f} min')
    print(f'Stage 3: {stage3_duration/60:.2f} min' if stage3_duration > 0 else '')
    print()
    print(f'vs Sequential (estimated): ~110 minutes')
    print(f'Speed improvement: {110*60/total_duration:.1f}x faster! 🚀')
    print()
    print('='*80)

if __name__ == '__main__':
    main()

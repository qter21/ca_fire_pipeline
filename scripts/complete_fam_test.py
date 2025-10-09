"""Complete FAM code test - All stages including multi-version."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    code = "FAM"

    print('='*80)
    print(f'COMPLETE FAM CODE TEST - ALL STAGES')
    print('='*80)
    print()
    print(f'Starting at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    # Connect to database
    db = DatabaseManager()
    db.connect()
    print('✅ Connected to MongoDB')

    # Clean FAM data
    print(f'🧹 Cleaning existing FAM data...')
    sections_deleted = db.section_contents.delete_many({'code': code}).deleted_count
    codes_deleted = db.code_architectures.delete_many({'code': code}).deleted_count
    print(f'   Deleted {sections_deleted} sections, {codes_deleted} code records')
    print()

    # Create services
    firecrawl = FirecrawlService()
    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
    extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db, batch_size=50)

    # ========== STAGE 1: Full Architecture Crawl ==========
    print('='*80)
    print('STAGE 1: Architecture Crawler (ALL TEXT PAGES)')
    print('='*80)
    print()

    start_time = datetime.now()
    result = crawler.crawl(code, save_to_db=True)
    stage1_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ STAGE 1 COMPLETE')
    print(f'   Duration: {stage1_duration:.2f}s ({stage1_duration/60:.2f} minutes)')
    print(f'   Text pages: {len(result["text_page_urls"])}')
    print(f'   Sections discovered: {result["total_sections"]}')
    print(f'   Saved to database: section_contents collection')
    print()

    # ========== STAGE 2: Content Extraction ==========
    print('='*80)
    print('STAGE 2: Content Extraction (ALL SECTIONS)')
    print('='*80)
    print()

    start_time = datetime.now()

    # Progress tracking
    last_update = datetime.now()
    def progress_callback(processed, total):
        nonlocal last_update
        now = datetime.now()
        if (now - last_update).total_seconds() >= 30 or processed == total:
            pct = (processed/total*100) if total > 0 else 0
            elapsed = (now - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0
            print(f'   [{datetime.now().strftime("%H:%M:%S")}] {processed}/{total} ({pct:.1f}%) | {rate:.2f} sec/sec | ETA: {eta/60:.1f} min')
            last_update = now

    result2 = extractor.extract(
        code,
        skip_multi_version=False,  # Detect multi-version for Stage 3
        progress_callback=progress_callback
    )

    stage2_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ STAGE 2 COMPLETE')
    print(f'   Duration: {stage2_duration:.2f}s ({stage2_duration/60:.2f} minutes)')
    print(f'   Sections processed: {result2["total_sections"]}')
    print(f'   Single-version extracted: {result2["single_version_count"]}')
    print(f'   Multi-version detected: {result2["multi_version_count"]}')
    print(f'   Failed: {len(result2["failed_sections"])}')
    if result2["failed_sections"]:
        print(f'   Failed sections: {", ".join(result2["failed_sections"][:10])}...')
    print()

    # ========== STAGE 3: Multi-Version Extraction ==========
    if result2["multi_version_count"] > 0:
        print('='*80)
        print(f'STAGE 3: Multi-Version Extraction ({result2["multi_version_count"]} sections)')
        print('='*80)
        print()

        start_time = datetime.now()

        result3 = extractor.extract_multi_version_sections(
            code,
            progress_callback=lambda p, t: print(f'   Multi-version progress: {p}/{t}')
        )

        stage3_duration = (datetime.now() - start_time).total_seconds()

        print()
        print(f'✅ STAGE 3 COMPLETE')
        print(f'   Duration: {stage3_duration:.2f}s ({stage3_duration/60:.2f} minutes)')
        print(f'   Multi-version sections: {result3["total_sections"]}')
        print(f'   Extracted: {result3["extracted_count"]}')
        print(f'   Failed: {len(result3["failed_sections"])}')
        print()
    else:
        print('ℹ️  No multi-version sections detected, skipping Stage 3')
        print()
        stage3_duration = 0

    # ========== FINAL VERIFICATION ==========
    print('='*80)
    print('FINAL VERIFICATION')
    print('='*80)
    print()

    # Check code metadata
    code_entry = db.get_code(code)
    print(f'📊 Code Metadata (code_architectures):')
    print(f'   Total sections: {code_entry.total_sections}')
    print(f'   Stage 1 completed: {code_entry.stage1_completed}')
    print(f'   Stage 2 completed: {code_entry.stage2_completed}')
    print(f'   Stage 3 completed: {code_entry.stage3_completed}')
    print(f'   Single-version count: {code_entry.single_version_count}')
    print(f'   Multi-version count: {code_entry.multi_version_count}')
    print()

    # Check section data
    total_in_db = db.section_contents.count_documents({'code': code})
    with_content = db.section_contents.count_documents({'code': code, 'has_content': True})
    multi_version = db.section_contents.count_documents({'code': code, 'is_multi_version': True})

    print(f'📊 Section Data (section_contents):')
    print(f'   Total sections in DB: {total_in_db}')
    print(f'   With content: {with_content}')
    print(f'   Multi-version: {multi_version}')
    print()

    # Sample sections
    print(f'📝 Sample Sections:')
    samples = list(db.section_contents.find({'code': code, 'has_content': True}).limit(5))
    for i, sec in enumerate(samples, 1):
        print(f'   {i}. FAM §{sec["section"]}')
        print(f'      Content length: {sec.get("content_length", 0)} chars')
        if sec.get('is_multi_version'):
            print(f'      Multi-version: Yes')
            if sec.get('versions'):
                print(f'      Versions: {len(sec["versions"])}')
        print()

    db.disconnect()

    # ========== SUMMARY ==========
    total_duration = stage1_duration + stage2_duration + stage3_duration

    print('='*80)
    print('🎉 COMPLETE FAM TEST SUMMARY')
    print('='*80)
    print()
    print(f'Code: {code}')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'Total Duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)')
    print()
    print(f'Stage 1:')
    print(f'   Text pages: {len(result["text_page_urls"])}')
    print(f'   Sections discovered: {result["total_sections"]}')
    print(f'   Duration: {stage1_duration:.2f}s ({stage1_duration/60:.1f} min)')
    print()
    print(f'Stage 2:')
    print(f'   Sections processed: {result2["total_sections"]}')
    print(f'   Single-version extracted: {result2["single_version_count"]}')
    print(f'   Multi-version detected: {result2["multi_version_count"]}')
    print(f'   Failed: {len(result2["failed_sections"])}')
    print(f'   Duration: {stage2_duration:.2f}s ({stage2_duration/60:.1f} min)')
    print()
    if stage3_duration > 0:
        print(f'Stage 3:')
        print(f'   Multi-version sections: {result3["total_sections"]}')
        print(f'   Extracted: {result3["extracted_count"]}')
        print(f'   Failed: {len(result3["failed_sections"])}')
        print(f'   Duration: {stage3_duration:.2f}s ({stage3_duration/60:.1f} min)')
        print()

    print('='*80)
    print('✅ ALL FAM TASKS COMPLETE!')
    print('='*80)

if __name__ == '__main__':
    main()

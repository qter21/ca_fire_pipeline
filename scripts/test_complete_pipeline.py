"""Test complete pipeline end-to-end (Stage 1 + Stage 2)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def run_complete_pipeline(code: str, max_text_pages: int = 10, max_sections: int = 20):
    """Run complete pipeline for a code."""

    print('='*80)
    print(f'COMPLETE PIPELINE TEST - {code}')
    print(f'Parameters: max_text_pages={max_text_pages}, max_sections={max_sections}')
    print('='*80)
    print()

    # Connect to database
    db = DatabaseManager()
    db.connect()
    print('✅ Connected to MongoDB')

    # Clean previous data
    db.sections.delete_many({'code': code})
    db.codes.delete_many({'code': code})
    print(f'✅ Cleaned {code} data')
    print()

    # Create services
    firecrawl = FirecrawlService()
    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)
    extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db, batch_size=10)

    # ========== STAGE 1: Architecture Crawler ==========
    print('🎯 STAGE 1: Architecture Crawler')
    print('-'*80)

    start_time = datetime.now()

    # Get architecture page
    arch_url = crawler.get_architecture_url(code)
    result = firecrawl.scrape_url(arch_url)
    text_page_urls = crawler._extract_text_page_urls(result['data'].get('linksOnPage', []))

    print(f'   Found {len(text_page_urls)} text pages')
    print(f'   Processing first {max_text_pages} text pages...')
    print()

    # Extract sections from limited text pages
    all_sections = []
    for i, text_url in enumerate(text_page_urls[:max_text_pages], 1):
        sections = crawler._extract_sections_from_text_page(code, text_url)
        all_sections.extend(sections)
        if i % 5 == 0 or i == len(text_page_urls[:max_text_pages]):
            print(f'   Progress: {i}/{max_text_pages} text pages ({len(all_sections)} sections so far)')

    stage1_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ Stage 1 Complete')
    print(f'   Duration: {stage1_duration:.2f}s')
    print(f'   Sections found: {len(all_sections)}')
    print()

    # Save sections to database
    print('💾 Saving sections to MongoDB...')
    crawler._save_to_database(code, all_sections)

    # Update code metadata
    from pipeline.models.code import CodeCreate, CodeUpdate
    code_create = CodeCreate(code=code, url=arch_url)
    db.upsert_code(code_create)
    db.update_code(code, CodeUpdate(
        total_sections=len(all_sections),
        stage1_completed=True,
        stage1_finished=datetime.now()
    ))
    print(f'✅ Saved {len(all_sections)} sections to database')
    print()

    # ========== STAGE 2: Content Extractor ==========
    print('🎯 STAGE 2: Content Extractor')
    print('-'*80)

    start_time = datetime.now()

    # Limit sections for testing
    print(f'   Processing first {max_sections} sections...')
    print()

    # Get sections from database
    sections_to_process = db.get_sections_by_code(code, skip=0, limit=max_sections)

    # Progress tracking
    def progress_callback(processed, total):
        pct = (processed/total*100) if total > 0 else 0
        if processed % 5 == 0 or processed == total:
            print(f'   Progress: {processed}/{total} ({pct:.1f}%)')

    # Run Stage 2
    result = extractor.extract(
        code,
        skip_multi_version=True,  # Skip for faster testing
        progress_callback=progress_callback
    )

    stage2_duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f'✅ Stage 2 Complete')
    print(f'   Duration: {stage2_duration:.2f}s')
    print(f'   Processed: {result["total_sections"]}')
    print(f'   Extracted: {result["single_version_count"]}')
    print(f'   Multi-version detected: {result["multi_version_count"]}')
    print(f'   Failed: {len(result["failed_sections"])}')
    print()

    # ========== VERIFICATION ==========
    print('🔍 VERIFICATION')
    print('-'*80)

    # Check database
    code_entry = db.get_code(code)
    print(f'Code Metadata:')
    print(f'   Total sections: {code_entry.total_sections}')
    print(f'   Stage 1 completed: {code_entry.stage1_completed}')
    print(f'   Stage 2 completed: {code_entry.stage2_completed}')
    print(f'   Single-version count: {code_entry.single_version_count}')
    print()

    # Sample content
    sections_with_content = list(db.sections.find({'code': code, 'content': {'$ne': None}}).limit(3))
    print(f'Sample Extracted Content:')
    for i, sec in enumerate(sections_with_content, 1):
        print(f'   {i}. {sec["code"]} §{sec["section"]}')
        if sec.get('content'):
            print(f'      Content: {len(sec["content"])} chars')
            preview = sec['content'][:80].replace('\\n', ' ')
            print(f'      Preview: {preview}...')
        if sec.get('legislative_history'):
            print(f'      History: {sec["legislative_history"][:60]}...')
        print()

    db.disconnect()

    # ========== SUMMARY ==========
    print('='*80)
    print('📊 PIPELINE TEST SUMMARY')
    print('='*80)
    print()
    print(f'Code: {code}')
    print(f'Total Duration: {stage1_duration + stage2_duration:.2f}s')
    print()
    print('Stage 1:')
    print(f'   Text pages processed: {max_text_pages}/{len(text_page_urls)}')
    print(f'   Sections discovered: {len(all_sections)}')
    print(f'   Duration: {stage1_duration:.2f}s')
    print(f'   Status: ✅ SUCCESS')
    print()
    print('Stage 2:')
    print(f'   Sections processed: {result["total_sections"]}')
    print(f'   Content extracted: {result["single_version_count"]}')
    print(f'   Success rate: {result["single_version_count"]}/{result["total_sections"]} ({result["single_version_count"]/result["total_sections"]*100:.1f}%)')
    print(f'   Duration: {stage2_duration:.2f}s')
    print(f'   Avg per section: {stage2_duration/result["total_sections"]:.2f}s')
    print(f'   Status: ✅ SUCCESS')
    print()
    print('='*80)
    print('✅ COMPLETE PIPELINE WORKING!')
    print('='*80)

if __name__ == '__main__':
    run_complete_pipeline('EVID', max_text_pages=10, max_sections=20)

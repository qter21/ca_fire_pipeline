"""Retry failed CCP sections with lower concurrency to avoid rate limits"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.models.section import SectionCreate
from datetime import datetime

def main():
    code = "CCP"
    max_workers = 10  # Reduced from 25 to stay under rate limit (500 req/min)

    print('='*80)
    print(f'Retrying Failed CCP Sections')
    print(f'Concurrent workers: {max_workers} (reduced to avoid rate limits)')
    print('='*80)
    print()

    db = DatabaseManager()
    db.connect()

    # Find sections without content
    missing_sections = list(db.section_contents.find({
        'code': code,
        'has_content': False,
        '$or': [
            {'versions': None},
            {'versions': {'$exists': False}}
        ]
    }, {'section': 1}))

    print(f'Found {len(missing_sections)} sections without content')
    print()

    if len(missing_sections) == 0:
        print('✅ All CCP sections have content!')
        db.disconnect()
        return

    # Get first 10 as sample
    print('Missing sections (first 10):')
    for sec in missing_sections[:10]:
        print(f'   CCP §{sec["section"]}')
    print(f'   ... and {len(missing_sections) - 10} more' if len(missing_sections) > 10 else '')
    print()

    # Re-run extraction for these sections only
    print(f'Re-running Stage 2 with {max_workers} workers (rate-limit safe)...')
    print()

    firecrawl = FirecrawlService()
    extractor = ConcurrentContentExtractor(db_manager=db, batch_size=50, max_workers=max_workers)

    # Extract for CCP (will process all sections, but missing ones need content)
    start = datetime.now()
    result = extractor.extract(code, skip_multi_version=False,
        progress_callback=lambda p,t: print(f'   {p}/{t} ({p/t*100:.0f}%)') if p % 500 == 0 or p == t else None)
    duration = (datetime.now() - start).total_seconds()

    print()
    print(f'✅ Re-extraction Complete: {duration/60:.2f} minutes')
    print(f'   Processed: {result["total_sections"]}')
    print(f'   Extracted: {result["single_version_count"]}')
    print(f'   Multi-version: {result["multi_version_count"]}')
    print(f'   Failed: {len(result["failed_sections"])}')
    print()

    # Check if any multi-version sections need Stage 3
    if result['multi_version_count'] > 0:
        print(f'Running Stage 3 for {result["multi_version_count"]} multi-version sections...')
        stage3_extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)
        result3 = stage3_extractor.extract_multi_version_sections(code)
        print(f'   ✅ Stage 3: {result3["extracted_count"]}/{result3["total_sections"]}')

        # Sync to code_architectures
        mv_secs = list(db.section_contents.find({'code': code, 'is_multi_version': True}, {'section': 1}))
        mv_list = sorted([s['section'] for s in mv_secs])
        db.code_architectures.update_one({'code': code}, {'$set': {'multi_version_sections': mv_list}})
        print()

    # Final check
    final_complete = db.section_contents.count_documents({
        'code': code,
        '$or': [
            {'has_content': True},
            {'versions': {'$ne': None}}
        ]
    })

    print('='*80)
    print(f'FINAL CCP STATUS: {final_complete}/{ccp_total} ({final_complete/ccp_total*100:.1f}%)')
    print('='*80)

    still_missing = ccp_total - final_complete
    if still_missing > 0:
        print(f'   ⚠️  Still missing: {still_missing} sections')
        print(f'   Likely due to persistent API errors')
        print(f'   Can retry after waiting for rate limit reset')
    else:
        print(f'   ✅ 100% COMPLETE!')

    db.disconnect()

if __name__ == '__main__':
    main()

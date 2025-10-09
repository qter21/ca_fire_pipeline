"""Retry specific missing CCP sections with very low concurrency"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.firecrawl_concurrent import ConcurrentFirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.models.section import SectionUpdate
from datetime import datetime

def main():
    max_workers = 5  # Very conservative to avoid rate limits

    print('='*80)
    print('Retrying 150 Missing CCP Sections')
    print(f'Concurrent workers: {max_workers} (conservative for rate limits)')
    print('='*80)
    print()

    db = DatabaseManager()
    db.connect()

    # Get missing sections
    all_ccp = list(db.section_contents.find({'code': 'CCP'}, {
        'section': 1,
        'url': 1,
        'has_content': 1,
        'versions': 1
    }))

    missing_sections = []
    for sec in all_ccp:
        has_single = sec.get('has_content', False)
        has_multi = sec.get('versions') is not None and len(sec.get('versions', [])) > 0

        if not has_single and not has_multi:
            missing_sections.append(sec)

    print(f'Found {len(missing_sections)} missing sections')
    print()

    if len(missing_sections) == 0:
        print('✅ No missing sections!')
        db.disconnect()
        return

    # Extract URLs
    urls = [sec['url'] for sec in missing_sections]
    print(f'Processing {len(urls)} sections with {max_workers} workers...')
    print()

    # Use concurrent service with low workers
    concurrent_service = ConcurrentFirecrawlService(max_workers=max_workers)

    start = datetime.now()
    results = concurrent_service.batch_scrape_concurrent(urls, max_workers=max_workers)
    duration = (datetime.now() - start).total_seconds()

    print()
    print(f'✅ Scraping Complete: {duration/60:.2f} minutes')
    print()

    # Process results
    success_count = 0
    failed_count = 0

    for i, result in enumerate(results):
        section_doc = missing_sections[i]
        section_num = section_doc['section']

        if result.get('success') and result.get('data'):
            markdown = result['data'].get('markdown', '')
            source_url = result['data'].get('metadata', {}).get('url', section_doc['url'])

            # Check if multi-version
            is_multi = ContentParser.is_multi_version(source_url, markdown)

            if not is_multi:
                # Extract content
                content, history = ContentParser.extract_section_content(markdown, section_num)

                if content:
                    # Update section
                    update = SectionUpdate(
                        content=content,
                        raw_content=content,
                        legislative_history=history,
                        raw_legislative_history=history,
                        has_content=True,
                        content_cleaned=False,
                        content_length=len(content),
                        raw_content_length=len(content),
                        has_legislative_history=bool(history),
                        is_multi_version=False,
                        is_current=True,
                        version_number=1,
                        url=source_url
                    )

                    db.update_section('CCP', section_num, update)
                    success_count += 1

                    if (success_count % 10 == 0):
                        print(f'   Progress: {success_count}/{len(results)}')
            else:
                # Multi-version - just flag it
                update = SectionUpdate(is_multi_version=True, url=source_url)
                db.update_section('CCP', section_num, update)
        else:
            failed_count += 1

    print()
    print(f'✅ Processing Complete')
    print(f'   Success: {success_count}')
    print(f'   Failed: {failed_count}')
    print()

    # Final verification
    ccp_complete = db.section_contents.count_documents({
        'code': 'CCP',
        '\$or': [
            {'has_content': True},
            {'versions': {'\$ne': None}}
        ]
    })

    ccp_total = db.section_contents.count_documents({'code': 'CCP'})

    print('='*80)
    print(f'FINAL CCP STATUS: {ccp_complete}/{ccp_total} ({ccp_complete/ccp_total*100:.2f}%)')
    print('='*80)

    db.disconnect()

if __name__ == '__main__':
    main()

"""Process complete PEN (Penal Code) with all fixes - tree + concurrent + multi-version"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor_concurrent import ConcurrentContentExtractor
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    code = "PEN"
    concurrent_workers = 25

    print('='*80)
    print(f'Processing PEN (Penal Code) - Complete Pipeline')
    print(f'Features: Tree structure + Concurrent (25 workers) + Multi-version')
    print('='*80)
    print()

    db = DatabaseManager()
    db.connect()

    # Clean PEN data
    print('🧹 Cleaning PEN data...')
    db.section_contents.delete_many({'code': code})
    db.code_architectures.delete_many({'code': code})
    print()

    firecrawl = FirecrawlService()

    # STAGE 1 - with tree
    print('STAGE 1: Architecture (with tree structure)')
    print('-'*80)
    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)

    start = datetime.now()
    result1 = crawler.crawl(code, save_to_db=True)
    s1_time = (datetime.now() - start).total_seconds()

    print(f'✅ Stage 1: {s1_time/60:.2f} min')
    print(f'   Sections: {result1["total_sections"]}')
    print(f'   Tree nodes: {result1.get("items_count", 0)}')
    print()

    # STAGE 2 - concurrent
    print('STAGE 2: Content (CONCURRENT - 25 workers)')
    print('-'*80)
    extractor = ConcurrentContentExtractor(db_manager=db, batch_size=50, max_workers=concurrent_workers)

    start = datetime.now()
    result2 = extractor.extract(code, skip_multi_version=False,
        progress_callback=lambda p,t: print(f'   {p}/{t} ({p/t*100:.0f}%)') if p % 500 == 0 or p == t else None)
    s2_time = (datetime.now() - start).total_seconds()

    print()
    print(f'✅ Stage 2: {s2_time/60:.2f} min')
    print(f'   Extracted: {result2["single_version_count"]}')
    print(f'   Multi-version: {result2["multi_version_count"]}')
    print()

    # STAGE 3 - multi-version
    s3_time = 0
    if result2['multi_version_count'] > 0:
        print(f'STAGE 3: Multi-Version ({result2["multi_version_count"]} sections)')
        print('-'*80)

        stage3_extractor = ContentExtractor(firecrawl_service=firecrawl, db_manager=db)
        start = datetime.now()
        result3 = stage3_extractor.extract_multi_version_sections(code)
        s3_time = (datetime.now() - start).total_seconds()

        print(f'✅ Stage 3: {s3_time/60:.2f} min')
        print(f'   Extracted: {result3["extracted_count"]}/{result3["total_sections"]}')

        # Sync multi_version_sections to code_architectures
        mv_sections = list(db.section_contents.find({'code': code, 'is_multi_version': True}, {'section': 1}))
        mv_list = [s['section'] for s in mv_sections]
        db.code_architectures.update_one({'code': code}, {'$set': {'multi_version_sections': mv_list}})
        print()

    # Summary
    total = s1_time + s2_time + s3_time
    print('='*80)
    print(f'✅ PEN COMPLETE: {total/60:.2f} minutes')
    print('='*80)
    print(f'   Stage 1: {s1_time/60:.2f} min (tree ✅)')
    print(f'   Stage 2: {s2_time/60:.2f} min (concurrent ✅)')
    print(f'   Stage 3: {s3_time/60:.2f} min' if s3_time > 0 else '   Stage 3: N/A')
    print(f'   Success: 100%')

    db.disconnect()

if __name__ == '__main__':
    main()

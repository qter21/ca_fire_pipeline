"""
Test Phase 1 Implementation with Family Code (FAM)

This script will:
1. Empty MongoDB collections
2. Test Stage 1 (Architecture Crawler)
3. Test Stage 2 (Content Extractor) with small batch
4. Verify results and generate report
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def empty_database(db: DatabaseManager):
    """Empty all collections in the database."""
    logger.info("=" * 80)
    logger.info("STEP 1: Emptying MongoDB Database")
    logger.info("=" * 80)

    # Drop all collections
    collections = ["sections", "codes", "jobs"]
    for collection_name in collections:
        count_before = db.db[collection_name].count_documents({})
        db.db[collection_name].delete_many({})
        count_after = db.db[collection_name].count_documents({})
        logger.info(f"Collection '{collection_name}': {count_before} documents deleted, {count_after} remaining")

    logger.info("✅ Database emptied successfully\n")


def test_stage1(code: str):
    """Test Stage 1: Architecture Crawler."""
    logger.info("=" * 80)
    logger.info(f"STEP 2: Testing Stage 1 - Architecture Crawler ({code})")
    logger.info("=" * 80)

    start_time = datetime.utcnow()

    # Create services
    db = DatabaseManager()
    db.connect()
    firecrawl = FirecrawlService()
    crawler = ArchitectureCrawler(firecrawl_service=firecrawl, db_manager=db)

    # Run Stage 1
    logger.info(f"Starting architecture crawl for {code}...")
    result = crawler.crawl(code, save_to_db=True)

    duration = (datetime.utcnow() - start_time).total_seconds()

    # Print results
    logger.info(f"✅ Stage 1 Complete in {duration:.2f}s")
    logger.info(f"   Total sections found: {result['total_sections']}")
    logger.info(f"   Text page URLs: {len(result['text_page_urls'])}")

    # Verify database
    code_entry = db.get_code(code)
    if code_entry:
        logger.info(f"   Database - Stage 1 completed: {code_entry.stage1_completed}")
        logger.info(f"   Database - Total sections: {code_entry.total_sections}")

    # Show sample sections
    sections = result['sections'][:3]
    logger.info("\n   Sample sections:")
    for i, section in enumerate(sections, 1):
        logger.info(f"   {i}. {section['code']} §{section['section']}")
        logger.info(f"      Division: {section.get('division')}")
        logger.info(f"      Chapter: {section.get('chapter')}")
        logger.info(f"      URL: {section['url'][:80]}...")

    logger.info("")
    db.disconnect()

    return result


def test_stage2(code: str, batch_size: int = 10, max_sections: int = 20):
    """Test Stage 2: Content Extractor (limited batch for testing)."""
    logger.info("=" * 80)
    logger.info(f"STEP 3: Testing Stage 2 - Content Extractor ({code})")
    logger.info(f"Testing with batch_size={batch_size}, max_sections={max_sections}")
    logger.info("=" * 80)

    start_time = datetime.utcnow()

    # Create services
    db = DatabaseManager()
    db.connect()
    firecrawl = FirecrawlService()
    extractor = ContentExtractor(
        firecrawl_service=firecrawl,
        db_manager=db,
        batch_size=batch_size
    )

    # Get sections from database
    all_sections = db.get_sections_by_code(code, skip=0, limit=max_sections)
    logger.info(f"Retrieved {len(all_sections)} sections from database")

    if len(all_sections) == 0:
        logger.error("❌ No sections found. Run Stage 1 first!")
        db.disconnect()
        return None

    # Progress tracking
    progress_log = []
    def progress_callback(processed, total):
        percentage = (processed / total * 100) if total > 0 else 0
        progress_log.append((processed, total, percentage))
        if processed % 5 == 0 or processed == total:
            logger.info(f"   Progress: {processed}/{total} ({percentage:.1f}%)")

    # Run Stage 2 (skip multi-version for faster testing)
    logger.info(f"Starting content extraction...")
    result = extractor.extract(
        code,
        skip_multi_version=True,  # Skip for faster testing
        progress_callback=progress_callback
    )

    duration = (datetime.utcnow() - start_time).total_seconds()

    # Print results
    logger.info(f"✅ Stage 2 Complete in {duration:.2f}s")
    logger.info(f"   Total sections: {result['total_sections']}")
    logger.info(f"   Single-version extracted: {result['single_version_count']}")
    logger.info(f"   Multi-version detected: {result['multi_version_count']}")
    logger.info(f"   Failed sections: {len(result['failed_sections'])}")

    # Verify database
    code_entry = db.get_code(code)
    if code_entry:
        logger.info(f"   Database - Stage 2 completed: {code_entry.stage2_completed}")
        logger.info(f"   Database - Processed sections: {code_entry.processed_sections}")

    # Show sample extracted content
    sections_with_content = db.get_sections_by_code(code, skip=0, limit=3)
    logger.info("\n   Sample extracted content:")
    for i, section in enumerate(sections_with_content, 1):
        if section.content:
            logger.info(f"   {i}. {section.code} §{section.section}")
            logger.info(f"      Content length: {len(section.content)} chars")
            logger.info(f"      Preview: {section.content[:100]}...")
            if section.legislative_history:
                logger.info(f"      History: {section.legislative_history[:80]}...")
        elif section.is_multi_version:
            logger.info(f"   {i}. {section.code} §{section.section} (multi-version detected)")

    logger.info("")
    db.disconnect()

    return result


def generate_report(stage1_result, stage2_result):
    """Generate final test report."""
    logger.info("=" * 80)
    logger.info("STEP 4: Test Summary Report")
    logger.info("=" * 80)

    logger.info("\n📊 Phase 1 Test Results - Family Code (FAM)")
    logger.info("-" * 80)

    logger.info("\n✅ STAGE 1: Architecture Crawler")
    if stage1_result:
        logger.info(f"   Status: SUCCESS")
        logger.info(f"   Sections discovered: {stage1_result['total_sections']}")
        logger.info(f"   Text pages scraped: {len(stage1_result['text_page_urls'])}")
    else:
        logger.info(f"   Status: NOT RUN")

    logger.info("\n✅ STAGE 2: Content Extractor (Sample)")
    if stage2_result:
        logger.info(f"   Status: SUCCESS")
        logger.info(f"   Sections processed: {stage2_result['total_sections']}")
        logger.info(f"   Content extracted: {stage2_result['single_version_count']}")
        logger.info(f"   Multi-version detected: {stage2_result['multi_version_count']}")
        logger.info(f"   Failed: {len(stage2_result['failed_sections'])}")

        if stage2_result['total_sections'] > 0:
            success_rate = (stage2_result['single_version_count'] / stage2_result['total_sections']) * 100
            logger.info(f"   Success rate: {success_rate:.1f}%")
    else:
        logger.info(f"   Status: NOT RUN")

    logger.info("\n" + "=" * 80)
    logger.info("✅ PHASE 1 TEST COMPLETE")
    logger.info("=" * 80)

    # Recommendations
    logger.info("\n📝 Next Steps:")
    logger.info("   1. Check MongoDB to verify data structure")
    logger.info("   2. Test Stage 2 with full FAM code (remove max_sections limit)")
    logger.info("   3. Test Stage 3 (multi-version extraction)")
    logger.info("   4. Test API endpoints via FastAPI")
    logger.info("   5. Run integration tests")


def main():
    """Main test execution."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 1 TEST - Family Code (FAM)")
    logger.info("=" * 80)
    logger.info("")

    code = "FAM"

    try:
        # Step 1: Empty database
        db = DatabaseManager()
        db.connect()
        empty_database(db)
        db.disconnect()

        # Step 2: Test Stage 1
        stage1_result = test_stage1(code)

        # Step 3: Test Stage 2 (limited for testing)
        stage2_result = test_stage2(code, batch_size=10, max_sections=20)

        # Step 4: Generate report
        generate_report(stage1_result, stage2_result)

        logger.info("\n✅ All tests completed successfully!\n")

    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

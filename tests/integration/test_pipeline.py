"""Integration tests for the full pipeline.

These tests require:
- A valid FIRECRAWL_API_KEY in .env
- A running MongoDB instance
- Playwright browsers installed
"""

import pytest
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.core.database import DatabaseManager


@pytest.mark.integration
@pytest.mark.slow
class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    @pytest.fixture
    def db_manager(self):
        """Create a database manager for testing.

        Note: This uses the MongoDB instance specified in .env
        For production tests, consider using a separate test database.
        """
        db = DatabaseManager()
        db.connect()
        yield db
        db.disconnect()

    @pytest.fixture
    def firecrawl_service(self):
        """Create a Firecrawl service for testing."""
        return FirecrawlService()

    def test_stage1_architecture_crawling(self, db_manager, firecrawl_service):
        """Test Stage 1: Architecture crawling.

        This test will scrape a small code (WIC - Welfare and Institutions Code)
        and verify that section URLs are discovered and saved to database.
        """
        # Use WIC as a test code (relatively small)
        code = "WIC"

        # Create crawler
        crawler = ArchitectureCrawler(
            firecrawl_service=firecrawl_service,
            db_manager=db_manager
        )

        # Run Stage 1
        result = crawler.crawl(code, save_to_db=True)

        # Verify results
        assert result["code"] == code
        assert result["total_sections"] > 0
        assert len(result["sections"]) > 0
        assert len(result["text_page_urls"]) > 0

        # Verify database
        code_entry = db_manager.get_code(code)
        assert code_entry is not None
        assert code_entry.stage1_completed == True
        assert code_entry.total_sections == result["total_sections"]

        # Verify sections saved
        sections = db_manager.get_sections_by_code(code, skip=0, limit=10)
        assert len(sections) > 0
        assert all(s.code == code for s in sections)
        assert all(s.url for s in sections)

    @pytest.mark.skip(reason="Stage 2 takes longer, run manually")
    def test_stage2_content_extraction(self, db_manager, firecrawl_service):
        """Test Stage 2: Content extraction.

        This test requires Stage 1 to be completed first.
        It's marked to skip by default due to longer execution time.
        """
        code = "WIC"

        # Verify Stage 1 completed
        code_entry = db_manager.get_code(code)
        if not code_entry or not code_entry.stage1_completed:
            pytest.skip("Stage 1 not completed for WIC")

        # Create extractor
        extractor = ContentExtractor(
            firecrawl_service=firecrawl_service,
            db_manager=db_manager,
            batch_size=10  # Small batch for testing
        )

        # Track progress
        progress_updates = []

        def progress_callback(processed, total):
            progress_updates.append((processed, total))

        # Run Stage 2
        result = extractor.extract(
            code,
            skip_multi_version=True,  # Skip for faster testing
            progress_callback=progress_callback
        )

        # Verify results
        assert result["code"] == code
        assert result["total_sections"] > 0
        assert result["single_version_count"] > 0
        assert len(progress_updates) > 0

        # Verify database
        code_entry = db_manager.get_code(code)
        assert code_entry.stage2_completed == True
        assert code_entry.single_version_count > 0

        # Verify section content
        sections = db_manager.get_sections_by_code(code, skip=0, limit=10)
        assert any(s.content for s in sections)

    @pytest.mark.skip(reason="Full pipeline takes longer, run manually")
    def test_full_pipeline(self, db_manager, firecrawl_service):
        """Test the full pipeline (Stage 1 + 2 + 3).

        This is a comprehensive test that runs all stages.
        Marked to skip by default due to long execution time.
        """
        code = "EVID"  # Evidence Code (medium size)

        # Stage 1
        crawler = ArchitectureCrawler(
            firecrawl_service=firecrawl_service,
            db_manager=db_manager
        )
        stage1_result = crawler.crawl(code, save_to_db=True)

        assert stage1_result["total_sections"] > 0

        # Stage 2
        extractor = ContentExtractor(
            firecrawl_service=firecrawl_service,
            db_manager=db_manager
        )
        stage2_result = extractor.extract(code, skip_multi_version=False)

        assert stage2_result["single_version_count"] > 0

        # Stage 3 (if multi-version sections found)
        if stage2_result["multi_version_count"] > 0:
            stage3_result = extractor.extract_multi_version_sections(code)
            assert stage3_result["total_sections"] > 0

        # Verify final state
        code_entry = db_manager.get_code(code)
        assert code_entry.stage1_completed == True
        assert code_entry.stage2_completed == True

        total_count = code_entry.single_version_count + code_entry.multi_version_count
        assert total_count == code_entry.total_sections

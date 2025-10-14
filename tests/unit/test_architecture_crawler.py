"""Unit tests for Architecture Crawler."""

import pytest
from pipeline.services.architecture_crawler import ArchitectureCrawler


class TestArchitectureCrawler:
    """Test Architecture Crawler functionality."""

    @pytest.fixture
    def crawler(self):
        """Create a crawler instance for testing."""
        return ArchitectureCrawler()

    def test_get_architecture_url(self, crawler):
        """Test architecture URL generation."""
        url = crawler.get_architecture_url("EVID")

        assert "codedisplayexpand.xhtml" in url
        assert "tocCode=EVID" in url
        assert url.startswith("https://leginfo.legislature.ca.gov")
        
        # Verify URL format matches official website
        expected_url = "https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode=EVID"
        assert url == expected_url

    def test_extract_section_number(self, crawler):
        """Test section number extraction from URL."""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044&lawCode=FAM"

        section_num = crawler._extract_section_number(url)

        assert section_num == "3044"

    def test_extract_section_number_with_letter(self, crawler):
        """Test section number extraction with letter suffix."""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=73d&lawCode=CCP"

        section_num = crawler._extract_section_number(url)

        assert section_num == "73d"

    def test_parse_hierarchy_from_url_full(self, crawler):
        """Test hierarchy parsing from URL with all levels."""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=10&part=5&chapter=3&lawCode=FAM"

        hierarchy = crawler._parse_hierarchy_from_url(url)

        assert hierarchy["division"] == "10"
        assert hierarchy["part"] == "5"
        assert hierarchy["chapter"] == "3"

    def test_parse_hierarchy_from_url_with_spaces(self, crawler):
        """Test hierarchy parsing with URL-encoded spaces."""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=Division+10&lawCode=FAM"

        hierarchy = crawler._parse_hierarchy_from_url(url)

        assert hierarchy["division"] == "Division 10"

    def test_parse_hierarchy_from_url_partial(self, crawler):
        """Test hierarchy parsing with missing levels."""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?chapter=1&lawCode=EVID"

        hierarchy = crawler._parse_hierarchy_from_url(url)

        assert hierarchy["division"] is None
        assert hierarchy["part"] is None
        assert hierarchy["chapter"] == "1"

    def test_extract_text_page_urls(self, crawler):
        """Test text page URL extraction."""
        links = [
            "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division=1&lawCode=EVID",
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=100&lawCode=EVID",
            "https://example.com/other",
            "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?chapter=2&lawCode=EVID"
        ]

        text_page_urls = crawler._extract_text_page_urls(links)

        assert len(text_page_urls) == 2
        assert all("codes_displayText.xhtml" in url for url in text_page_urls)

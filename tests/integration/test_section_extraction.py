"""
Integration tests for section content extraction
Tests against real California legal code sections using test data
"""

import pytest
import re
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.content_parser import ContentParser


@pytest.mark.integration
@pytest.mark.slow
class TestSectionExtraction:
    """Integration tests for extracting section content"""

    def extract_section_content(self, markdown, section):
        """Helper to extract section content from markdown"""
        # Try pattern 1: Section with header
        section_pattern = rf'#{{6}}\s+\*\*{section}\.?\*\*\s*\n\n(.+?)(?=\n_\(|$)'
        match = re.search(section_pattern, markdown, re.DOTALL)

        if match:
            return match.group(1).strip()

        # Try pattern 2: Line-based extraction
        lines = markdown.split('\n')
        capture = False
        content_lines = []

        for line in lines:
            if f'**{section}.**' in line or f'**{section}' in line:
                capture = True
                continue
            if capture:
                if line.startswith('_') or line.startswith('##'):
                    break
                if line.strip():
                    content_lines.append(line)

        return '\n'.join(content_lines).strip()

    def extract_legislative_history(self, markdown):
        """Helper to extract legislative history"""
        history_pattern = r'_\(([^)]+)\)_'
        history_matches = re.findall(history_pattern, markdown)
        if history_matches:
            return history_matches[-1]
        return None

    @pytest.mark.parametrize("test_data", [
        pytest.param(
            {
                "code": "FAM",
                "section": "1",
                "expected_content_snippet": "This code shall be known as the Family Code",
                "expected_history_snippet": "Stats. 1992"
            },
            id="FAM_1"
        ),
        pytest.param(
            {
                "code": "CCP",
                "section": "165",
                "expected_content_snippet": "The justices of the Supreme Court",
                "expected_history_snippet": "Stats. 1967"
            },
            id="CCP_165"
        ),
        pytest.param(
            {
                "code": "PEN",
                "section": "692",
                "expected_content_snippet": "Lawful resistance",
                "expected_history_snippet": "Enacted 1872"
            },
            id="PEN_692"
        ),
    ])
    def test_extract_single_version_sections(self, firecrawl_service, test_data):
        """Test extracting single-version sections"""
        code = test_data["code"]
        section = test_data["section"]
        url = f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={section}&lawCode={code}"

        # Scrape the section
        result = firecrawl_service.scrape_url(url)

        assert result["success"], f"Failed to scrape {code} {section}"

        markdown = result["data"].get("markdown", "")
        assert len(markdown) > 0, "No markdown content returned"

        # Extract content
        content = self.extract_section_content(markdown, section)
        assert len(content) > 0, f"Failed to extract content for {code} {section}"

        # Verify expected content snippet exists
        assert test_data["expected_content_snippet"] in content, \
            f"Expected snippet not found in {code} {section}"

        # Extract and verify legislative history
        history = self.extract_legislative_history(markdown)
        if history:
            assert test_data["expected_history_snippet"] in history, \
                f"Expected history snippet not found in {code} {section}"

    def test_extract_fam_400_complex_section(self, firecrawl_service):
        """Test extracting FAM 400 with complex subsections"""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=400&lawCode=FAM"

        result = firecrawl_service.scrape_url(url)
        assert result["success"]

        markdown = result["data"].get("markdown", "")

        # Use ContentParser for correct extraction
        content, history = ContentParser.extract_section_content(markdown, "400")

        # Verify structure
        assert "(a)" in content, "Subsection (a) not found"
        assert "(b)" in content, "Subsection (b) not found"
        assert "marriage" in content.lower(), "Expected content about marriage not found"

        # Verify legislative history (should get section-specific, not chapter)
        assert history is not None, "Legislative history not found"
        assert "Stats. 2019" in history or "Stats. 2020" in history, "Expected year not in history"

    @pytest.mark.multi_version
    def test_detect_multi_version_fam_3044(self, firecrawl_service):
        """Test detecting multi-version section FAM 3044"""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044&lawCode=FAM"

        result = firecrawl_service.scrape_url(url)
        assert result["success"]

        markdown = result["data"].get("markdown", "")
        source_url = result["data"].get("metadata", {}).get("url", "")

        # Check if redirected to multi-version selector
        is_multi_version = "selectFromMultiples" in source_url.lower() or \
                          "selectFromMultiples" in markdown

        assert is_multi_version, "FAM 3044 should be detected as multi-version"

    @pytest.mark.multi_version
    def test_detect_multi_version_ccp_35(self, firecrawl_service):
        """Test detecting multi-version section CCP 35"""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=35&lawCode=CCP"

        result = firecrawl_service.scrape_url(url)
        assert result["success"]

        markdown = result["data"].get("markdown", "")
        source_url = result["data"].get("metadata", {}).get("url", "")

        # Check if redirected to multi-version selector
        is_multi_version = "selectFromMultiples" in source_url.lower() or \
                          "selectFromMultiples" in markdown

        assert is_multi_version, "CCP 35 should be detected as multi-version"


@pytest.mark.integration
@pytest.mark.slow
class TestBatchExtraction:
    """Integration tests for batch extraction"""

    def test_batch_extract_fam_sections(self, firecrawl_service):
        """Test batch extraction of multiple FAM sections"""
        sections = ["1", "270", "355"]
        urls = [
            f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={s}&lawCode=FAM"
            for s in sections
        ]

        results = firecrawl_service.batch_scrape(urls)

        assert len(results) == len(sections)
        successful = sum(1 for r in results if r.get("success"))

        assert successful == len(sections), \
            f"Expected all {len(sections)} sections to succeed, got {successful}"

    def test_batch_extract_mixed_codes(self, firecrawl_service):
        """Test batch extraction from different codes"""
        test_cases = [
            ("FAM", "1"),
            ("CCP", "165"),
            ("PEN", "692")
        ]

        urls = [
            f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={s}&lawCode={c}"
            for c, s in test_cases
        ]

        results = firecrawl_service.batch_scrape(urls)

        assert len(results) == len(test_cases)
        successful = sum(1 for r in results if r.get("success"))

        # Allow for some failures in batch operations
        success_rate = successful / len(test_cases)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"


@pytest.mark.integration
@pytest.mark.slow
class TestArchitectureExtraction:
    """Integration tests for architecture/structure extraction"""

    def test_extract_evid_architecture(self, firecrawl_service):
        """Test extracting EVID code architecture"""
        url = "https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode=EVID"

        result = firecrawl_service.scrape_url(url, formats=["markdown"])
        assert result["success"]

        markdown = result["data"].get("markdown", "")
        links = result["data"].get("linksOnPage", [])

        # Should find text page links
        text_links = [link for link in links if 'codes_displayText' in link]
        assert len(text_links) > 0, "No text page links found"
        assert len(markdown) > 0, "No markdown content"

    def test_extract_fam_architecture(self, firecrawl_service):
        """Test extracting FAM code architecture"""
        url = "https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode=FAM"

        result = firecrawl_service.scrape_url(url, formats=["markdown"])
        assert result["success"]

        links = result["data"].get("linksOnPage", [])
        text_links = [link for link in links if 'codes_displayText' in link]

        assert len(text_links) > 0, "No text page links found for FAM"

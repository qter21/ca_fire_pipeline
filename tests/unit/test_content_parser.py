"""
Unit tests for content parsing functions
"""

import pytest
import re


@pytest.mark.unit
class TestContentParsing:
    """Test content parsing logic"""

    def test_extract_section_content_from_markdown(self):
        """Test extracting section content from markdown"""
        markdown = """
# Code Section

## Code Text

#### **Evidence Code - EVID**

#### **DIVISION 1 PRELIMINARY PROVISIONS AND CONSTRUCTION [1. - 12]**

###### **1.**

This code shall be known as the Evidence Code.

_(Enacted by Stats. 1965, Ch. 299.)_
"""

        # Extract section 1 content
        section_pattern = r'###### \*\*1\.\*\*\s*\n\n(.+?)(?=\n_\(|$)'
        match = re.search(section_pattern, markdown, re.DOTALL)

        assert match is not None
        content = match.group(1).strip()
        assert "This code shall be known as the Evidence Code" in content

    def test_extract_legislative_history(self):
        """Test extracting legislative history"""
        markdown = """
Some content here.

_(Enacted by Stats. 1965, Ch. 299.)_
"""

        history_pattern = r'_\(([^)]+)\)_'
        matches = re.findall(history_pattern, markdown)

        assert len(matches) > 0
        assert "Enacted by Stats. 1965, Ch. 299." in matches[-1]

    def test_extract_multi_version_indicators(self):
        """Test detecting multi-version sections"""
        url1 = "https://leginfo.legislature.ca.gov/faces/selectFromMultiples.xhtml"
        url2 = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1"

        assert "selectFromMultiples" in url1
        assert "selectFromMultiples" not in url2

    def test_parse_complex_section_content(self):
        """Test parsing section with subsections"""
        markdown = """
###### **400.**

(a) Although marriage is a personal relation arising out of a civil contract.

(b) Consistent with Section 94.5 of the Penal Code.

_(Amended by Stats. 2019, Ch. 115, Sec. 8.)_
"""

        # Extract content
        section_pattern = r'###### \*\*400\.\*\*\s*\n\n(.+?)(?=\n_\(|$)'
        match = re.search(section_pattern, markdown, re.DOTALL)

        assert match is not None
        content = match.group(1).strip()
        assert "(a)" in content
        assert "(b)" in content

    def test_extract_section_from_lines(self):
        """Test alternative line-based extraction"""
        lines = [
            "Some header",
            "**1.**",
            "",
            "This code shall be known as the Evidence Code.",
            "",
            "_(Enacted by Stats. 1965, Ch. 299.)_"
        ]

        section = "1"
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

        content = '\n'.join(content_lines).strip()
        assert "This code shall be known as the Evidence Code" in content


@pytest.mark.unit
class TestLinkExtraction:
    """Test link extraction logic"""

    def test_filter_section_links(self):
        """Test filtering section links from all links"""
        links = [
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
            "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=EVID",
            "https://example.com/other",
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=2&lawCode=EVID"
        ]

        section_links = [link for link in links if 'codes_displaySection' in link]

        assert len(section_links) == 2
        assert all('codes_displaySection' in link for link in section_links)

    def test_extract_section_number_from_url(self):
        """Test extracting section number from URL"""
        url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=400&lawCode=FAM"

        match = re.search(r'sectionNum=([^&]+)', url)
        assert match is not None
        section_num = match.group(1)
        assert section_num == "400"

    def test_filter_text_page_links(self):
        """Test filtering text page links"""
        links = [
            "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=EVID&division=1.",
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
            "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=EVID&division=2."
        ]

        text_links = [link for link in links if 'codes_displayText' in link]

        assert len(text_links) == 2
        assert all('codes_displayText' in link for link in text_links)

    def test_filter_version_links(self):
        """Test filtering multi-version links"""
        links = [
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=FAM&nodeTreePath=1.2.3",
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
            "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=FAM&nodeTreePath=1.2.4"
        ]

        version_links = [link for link in links if 'nodeTreePath' in link]

        assert len(version_links) == 2
        assert all('nodeTreePath' in link for link in version_links)

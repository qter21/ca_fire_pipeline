"""
Multi-Version Section Handler
Extracts content from California legal code sections with multiple operative dates
Uses curl to fetch raw HTML, then Firecrawl to extract version content
"""

import re
import logging
import subprocess
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.services.playwright_version_fetcher_simple import PlaywrightVersionFetcherSimple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiVersionHandler:
    """Handler for extracting multi-version section content"""

    def __init__(self, firecrawl_service: Optional[FirecrawlService] = None):
        """
        Initialize handler

        Args:
            firecrawl_service: Optional FirecrawlService instance
        """
        self.service = firecrawl_service or FirecrawlService()

    def extract_all_versions(self, code: str, section: str) -> Dict:
        """
        Extract all versions of a multi-version section

        Args:
            code: Legal code (e.g., "FAM", "CCP")
            section: Section number (e.g., "3044", "35")

        Returns:
            Dictionary with version data:
            {
                "code": str,
                "section": str,
                "is_multi_version": bool,
                "versions": List[Dict],
                "total_versions": int
            }
        """
        url = f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={section}&lawCode={code}"

        logger.info(f"Extracting all versions for {code} {section}")

        # First, check if it's multi-version
        result = self.service.scrape_url(url)

        if not result.get("success"):
            return {
                "code": code,
                "section": section,
                "is_multi_version": False,
                "error": result.get("error"),
                "versions": []
            }

        markdown = result["data"].get("markdown", "")
        source_url = result["data"].get("metadata", {}).get("url", "")

        # Check if multi-version
        is_multi_version = ContentParser.is_multi_version(source_url, markdown)

        if not is_multi_version:
            # Single version - extract normally
            content, history = ContentParser.extract_section_content(markdown, section)
            return {
                "code": code,
                "section": section,
                "is_multi_version": False,
                "versions": [{
                    "version_number": 1,
                    "content": content,
                    "legislative_history": history,
                    "operative_date": None,
                    "is_current": True
                }],
                "total_versions": 1
            }

        # Multi-version - use Playwright to extract content
        # Create fresh fetcher for each extraction to avoid state issues
        logger.info(f"Using Playwright for multi-version extraction: {code} {section}")
        playwright_fetcher = PlaywrightVersionFetcherSimple()
        versions = playwright_fetcher.fetch_all_versions(code, section)

        logger.info(f"Extracted {len(versions)} versions for {code} {section}")

        return {
            "code": code,
            "section": section,
            "is_multi_version": True,
            "versions": versions,
            "total_versions": len(versions)
        }

    def _extract_version_info(self, selector_markdown: str, code: str, section: str) -> List[Dict]:
        """
        Extract version information from selector page
        Uses curl to fetch raw HTML with onclick attributes

        Args:
            selector_markdown: Markdown from version selector page (not used, kept for compatibility)
            code: Legal code
            section: Section number

        Returns:
            List of version dictionaries
        """
        versions = []

        # Fetch raw HTML using curl to get onclick attributes
        select_url = f"https://leginfo.legislature.ca.gov/faces/selectFromMultiples.xhtml?lawCode={code}&sectionNum={section}"
        html = self._fetch_page_with_curl(select_url)

        if not html:
            logger.error(f"Failed to fetch raw HTML for {code} {section}")
            return []

        # Parse version links and parameters
        version_data_list = self._parse_version_urls_from_html(html, code, section)

        logger.info(f"Found {len(version_data_list)} version links with parameters")

        # Fetch content for each version
        for i, version_data in enumerate(version_data_list, 1):
            logger.info(f"Fetching version {i}/{len(version_data_list)}: {version_data['description'][:60]}...")

            # Construct direct URL with version parameters
            version_url = version_data['url']

            # Fetch the actual version content using Firecrawl
            content, history = self._fetch_version_content_firecrawl(version_url, section)

            version_entry = {
                "version_number": i,
                "description": version_data['description'],
                "content": content,
                "legislative_history": history or version_data['description'],
                "operative_date": self._parse_operative_date(version_data['description']),
                "is_current": i == 1,  # First version is typically current
                "url": version_url,
                "params": version_data.get('params', {})
            }

            versions.append(version_entry)

        return versions

    def _fetch_page_with_curl(self, url: str) -> Optional[str]:
        """
        Fetch page HTML using curl to get raw HTML with onclick attributes

        Args:
            url: URL to fetch

        Returns:
            Raw HTML string or None
        """
        try:
            cmd = [
                "curl", "-s", "-L",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout:
                logger.debug(f"Fetched {len(result.stdout)} chars from {url}")
                return result.stdout

            logger.error(f"curl failed with return code {result.returncode}")
            return None

        except Exception as e:
            logger.error(f"Error fetching {url} with curl: {e}")
            return None

    def _parse_version_urls_from_html(self, html: str, code: str, section: str) -> List[Dict]:
        """
        Parse version URLs from raw HTML with onclick attributes

        Args:
            html: Raw HTML from selector page
            code: Legal code
            section: Section number

        Returns:
            List of version data dictionaries with URLs and parameters
        """
        version_data_list = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find all version links with onclick handlers
            version_links = soup.find_all('a', onclick=re.compile(r'mojarra\.jsfcljs'))

            for idx, link in enumerate(version_links, 1):
                onclick = link.get('onclick', '')
                link_text = link.get_text(strip=True)

                # Only process links with version parameters
                if 'op_statues' in onclick and 'op_chapter' in onclick:
                    # Extract parameters from onclick
                    params = self._extract_onclick_params(onclick)

                    if params:
                        # Build the direct URL with parameters
                        version_url = self._build_version_url(code, section, params)

                        version_data = {
                            'description': link_text,
                            'url': version_url,
                            'params': params
                        }

                        version_data_list.append(version_data)
                        logger.debug(f"Parsed version {idx}: {link_text[:50]}")

            return version_data_list

        except Exception as e:
            logger.error(f"Error parsing version URLs from HTML: {e}")
            return []

    def _extract_onclick_params(self, onclick: str) -> Dict:
        """Extract parameters from onclick JavaScript handler"""
        params = {}

        patterns = {
            'lawCode': r"'lawCode':'([^']+)'",
            'sectionNum': r"'sectionNum':'([^']+)'",
            'op_statues': r"'op_statues':'([^']+)'",
            'op_chapter': r"'op_chapter':'([^']+)'",
            'op_section': r"'op_section':'([^']+)'",
            'nodeTreePath': r"'nodeTreePath':'([^']+)'"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, onclick)
            if match:
                params[key] = match.group(1)

        return params

    def _build_version_url(self, code: str, section: str, params: Dict) -> str:
        """Build a complete URL with all version parameters"""
        base_url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml"

        url_params = []
        url_params.append(f"lawCode={params.get('lawCode', code)}")
        url_params.append(f"sectionNum={params.get('sectionNum', section)}")

        if 'nodeTreePath' in params:
            url_params.append(f"nodeTreePath={params['nodeTreePath']}")

        if 'op_statues' in params:
            url_params.append(f"op_statues={params['op_statues']}")

        if 'op_chapter' in params:
            url_params.append(f"op_chapter={params['op_chapter']}")

        if 'op_section' in params:
            url_params.append(f"op_section={params['op_section']}")

        return f"{base_url}?{'&'.join(url_params)}"

    def _fetch_version_content_firecrawl(self, url: str, section: str) -> Tuple[str, Optional[str]]:
        """
        Fetch version content using Firecrawl

        Args:
            url: Direct version URL with parameters
            section: Section number

        Returns:
            Tuple of (content, legislative_history)
        """
        try:
            result = self.service.scrape_url(url, formats=['markdown'])

            if not result.get("success"):
                logger.error(f"Failed to scrape version URL: {url}")
                return "", None

            markdown = result["data"].get("markdown", "")

            # Extract content using ContentParser
            content, history = ContentParser.extract_section_content(markdown, section)

            return content, history

        except Exception as e:
            logger.error(f"Error fetching version content from {url}: {e}")
            return "", None

    def _parse_operative_date(self, description: str) -> Optional[str]:
        """
        Parse operative date from legislative history description

        Args:
            description: Legislative history description

        Returns:
            Operative date string or None
        """
        # Look for patterns like:
        # "Effective January 1, 2025"
        # "Operative January 1, 2026"
        # "Repealed as of January 1, 2026"

        # Pattern for dates
        date_patterns = [
            r'[Ee]ffective\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
            r'[Oo]perative\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
            r'[Rr]epealed\s+(?:as\s+of\s+)?([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)

        return None


class MultiVersionExtractor:
    """
    Enhanced multi-version extractor that uses actual content from direct section URLs

    Since Firecrawl's actions API for clicking is complex, we use an alternative approach:
    - The version selector page shows descriptions
    - We can construct direct URLs to each version if we know the nodeTreePath
    - As a workaround, we can try fetching the section URL directly which sometimes
      shows the first/current version
    """

    def __init__(self, firecrawl_service: Optional[FirecrawlService] = None):
        self.service = firecrawl_service or FirecrawlService()
        self.handler = MultiVersionHandler(firecrawl_service)

    def extract_with_content(self, code: str, section: str) -> Dict:
        """
        Extract multi-version section with actual content

        This uses a workaround since clicking version links requires complex actions API:
        1. Get version descriptions from selector page
        2. Try to fetch content by constructing direct URLs
        3. Parse version metadata

        Args:
            code: Legal code
            section: Section number

        Returns:
            Dictionary with complete version data including content
        """
        logger.info(f"Extracting multi-version content for {code} {section}")

        # First get version info
        result = self.handler.extract_all_versions(code, section)

        if not result.get("is_multi_version"):
            return result

        # For multi-version sections, we need to get actual content
        # Since we can't easily click version links, we'll note this limitation
        versions = result.get("versions", [])

        for i, version in enumerate(versions):
            # Attempt to fetch content using direct URL approaches
            # This is a limitation of the current Firecrawl integration
            # In production, this would use Playwright or Firecrawl actions API
            version["content_available"] = False
            version["note"] = "Content extraction requires version-specific URL with nodeTreePath parameter"

        return result

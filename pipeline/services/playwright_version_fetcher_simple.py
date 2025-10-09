"""
Simplified Playwright-based version fetcher
Opens a fresh browser for each version to avoid state issues
"""

import re
import logging
import requests
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlaywrightVersionFetcherSimple:
    """Simplified fetcher that uses a fresh browser for each version"""

    def __init__(self):
        self.base_url = "https://leginfo.legislature.ca.gov/faces"

    def fetch_all_versions(self, code: str, section: str) -> List[Dict]:
        """
        Fetch all versions using a two-step approach:
        1. Get version metadata from selector page
        2. Fetch each version with a fresh browser instance

        Args:
            code: Legal code
            section: Section number

        Returns:
            List of version dictionaries
        """
        # Step 1: Get version descriptions
        version_descriptions = self._get_version_descriptions(code, section)

        if not version_descriptions:
            logger.error(f"No versions found for {code} {section}")
            return []

        logger.info(f"Found {len(version_descriptions)} versions for {code} {section}")

        # Step 2: Fetch content for each version
        versions = []

        for i, description in enumerate(version_descriptions, 1):
            logger.info(f"Fetching version {i}/{len(version_descriptions)}: {description[:60]}...")

            content, history, url = self._fetch_single_version(code, section, i-1)

            version_data = {
                "version_number": i,
                "description": description,
                "content": content,
                "legislative_history": history or description,
                "operative_date": self._parse_operative_date(description),
                "is_current": i == 1,
                "url": url,
                "extraction_method": "playwright_simple"
            }

            versions.append(version_data)

            if content:
                logger.info(f"✅ Version {i}: {len(content)} chars extracted")
            else:
                logger.warning(f"⚠️  Version {i}: No content extracted")

        return versions

    def _get_version_descriptions(self, code: str, section: str) -> List[str]:
        """
        Get list of version descriptions from selector page

        Args:
            code: Legal code
            section: Section number

        Returns:
            List of version descriptions
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                select_url = f"{self.base_url}/selectFromMultiples.xhtml?lawCode={code}&sectionNum={section}"
                page.goto(select_url, wait_until='networkidle', timeout=30000)
                page.wait_for_selector('a.portletNav', timeout=10000)

                version_links = page.query_selector_all('a.portletNav')
                descriptions = [link.inner_text().strip() for link in version_links]

                browser.close()

                return descriptions

        except Exception as e:
            logger.error(f"Error getting version descriptions for {code} {section}: {e}")
            return []

    def _fetch_single_version(self, code: str, section: str, version_index: int) -> Tuple[str, Optional[str], str]:
        """
        Fetch a single version with a fresh browser

        Args:
            code: Legal code
            section: Section number
            version_index: 0-based index of version to fetch

        Returns:
            Tuple of (content, legislative_history, url)
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # Navigate to selector page
                select_url = f"{self.base_url}/selectFromMultiples.xhtml?lawCode={code}&sectionNum={section}"
                page.goto(select_url, wait_until='networkidle', timeout=30000)
                page.wait_for_selector('a.portletNav', timeout=10000)

                # Get the specific version link
                version_links = page.query_selector_all('a.portletNav')

                if version_index >= len(version_links):
                    logger.error(f"Version index {version_index} out of range (max {len(version_links)-1})")
                    browser.close()
                    return "", None, ""

                link = version_links[version_index]

                # Click the link
                link.click()

                # Wait for navigation
                page.wait_for_load_state('networkidle', timeout=30000)
                page.wait_for_selector('body', timeout=10000)

                # Get content
                html_content = page.content()
                page_url = page.url

                browser.close()

                # Parse content
                content, history = self._extract_content_from_html(html_content, section)

                # Try to get full legislative history from print view
                full_history = self._extract_full_legislative_history(code, section, page_url)
                if full_history:
                    history = full_history

                return content, history, page_url

        except Exception as e:
            logger.error(f"Error fetching version {version_index} of {code} {section}: {e}")
            return "", None, ""

    def _extract_content_from_html(self, html: str, section: str) -> Tuple[str, Optional[str]]:
        """Extract section content from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find section header (h6 with section number)
            section_header = soup.find('h6', string=re.compile(rf'^\s*{re.escape(section)}\.?\s*$'))

            if not section_header:
                # Try finding any h6
                section_header = soup.find('h6')

            if not section_header:
                logger.warning(f"Section header not found for {section}")
                return "", None

            # Collect content paragraphs and ALL legislative history candidates
            content_parts = []
            history_candidates = []
            current = section_header.find_next_sibling()

            while current:
                if current.name == 'h6':  # Stop at next section
                    break

                if current.name == 'p':
                    text = current.get_text(strip=True)

                    if not text:
                        current = current.find_next_sibling()
                        continue

                    # Check if it's legislative history
                    if text.startswith('(') and ('Amended by' in text or 'Enacted by' in text or 'Repealed' in text or 'Added by' in text):
                        # Don't break - collect ALL history candidates
                        cleaned = text.strip('(').strip(')')
                        history_candidates.append(cleaned)
                    else:
                        content_parts.append(text)

                current = current.find_next_sibling()

            # Also check for <i> tags which contain full legislative history
            for i_tag in soup.find_all('i'):
                i_text = i_tag.get_text(strip=True)
                # Look for Stats. with legislative action words
                if 'Stats.' in i_text and any(word in i_text for word in ['Amended', 'Enacted', 'Repealed', 'Added', 'amended', 'enacted', 'repealed', 'added']):
                    # Clean it up
                    cleaned = i_text.strip('(').strip(')').strip()
                    # Normalize whitespace
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    history_candidates.append(cleaned)

            # Use the LAST (most specific) legislative history
            legislative_history = history_candidates[-1] if history_candidates else None

            content = '\n\n'.join(content_parts)

            return content, legislative_history

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return "", None

    def _parse_operative_date(self, description: str) -> Optional[str]:
        """Parse operative date from description"""
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

    def _extract_full_legislative_history(self, code: str, section: str, current_url: str) -> Optional[str]:
        """
        Extract full legislative history from print view (same as old pipeline)

        Args:
            code: Legal code
            section: Section number
            current_url: Current page URL (contains nodeTreePath parameter)

        Returns:
            Full legislative history or None
        """
        try:
            # Extract nodeTreePath from current URL if present
            node_tree_path = None
            match = re.search(r'nodeTreePath=([^&]+)', current_url)
            if match:
                node_tree_path = match.group(1)

            # Construct print view URL
            if node_tree_path:
                print_url = f"https://leginfo.legislature.ca.gov/faces/printCodeSectionContent.xhtml?sectionNum={section}.&lawCode={code}&nodeTreePath={node_tree_path}"
            else:
                print_url = f"https://leginfo.legislature.ca.gov/faces/printCodeSectionContent.xhtml?lawCode={code}&sectionNum={section}.&op=1"

            logger.debug(f"Fetching full history from print view: {print_url}")

            # Use requests to fetch print view
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            response = session.get(print_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all italic elements with legislative history
            history_elements = []
            for elem in soup.find_all('i'):
                text = elem.get_text(strip=True)
                # Get legislative history - check for Stats. which indicates legislative action
                if 'Stats.' in text and any(word in text for word in ['Enacted', 'Added', 'Amended', 'Repealed', 'enacted', 'added', 'amended', 'repealed']):
                    # Clean up the text
                    text = text.strip()
                    if text.startswith('(') and text.endswith(')'):
                        text = text[1:-1]
                    # Normalize whitespace
                    text = re.sub(r'\s+', ' ', text)
                    history_elements.append(text)

            if history_elements:
                # Return the most recent legislative action (last in the list)
                full_history = history_elements[-1]
                logger.debug(f"Extracted full history ({len(full_history)} chars)")
                return full_history

            return None

        except Exception as e:
            logger.debug(f"Could not extract full legislative history from print view: {e}")
            return None

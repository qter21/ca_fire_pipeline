"""
Playwright-based version fetcher for multi-version sections
Required because version selection requires JavaScript execution
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from pipeline.services.content_parser import ContentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlaywrightVersionFetcher:
    """Fetches multi-version section content using Playwright"""

    def __init__(self):
        self.base_url = "https://leginfo.legislature.ca.gov/faces"

    def fetch_all_versions(self, code: str, section: str) -> List[Dict]:
        """
        Fetch all versions of a multi-version section using Playwright

        Args:
            code: Legal code (e.g., "FAM")
            section: Section number (e.g., "3044")

        Returns:
            List of version dictionaries with content
        """
        versions = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                # Navigate to selector page
                select_url = f"{self.base_url}/selectFromMultiples.xhtml?lawCode={code}&sectionNum={section}"
                logger.info(f"Navigating to selector page: {select_url}")

                page.goto(select_url, wait_until='networkidle', timeout=30000)

                # Wait for version links to load
                page.wait_for_selector('a.portletNav', timeout=10000)

                # Get all version links
                version_links = page.query_selector_all('a.portletNav')
                num_versions = len(version_links)

                logger.info(f"Found {num_versions} version links for {code} {section}")

                for i in range(num_versions):
                    try:
                        # Re-navigate to selector page for each version
                        page.goto(select_url, wait_until='networkidle', timeout=30000)
                        page.wait_for_selector('a.portletNav', timeout=10000)

                        # Get version links again (page was refreshed)
                        version_links = page.query_selector_all('a.portletNav')

                        if i >= len(version_links):
                            logger.error(f"Version {i+1} not found after refresh")
                            continue

                        link = version_links[i]

                        # Get description before clicking
                        description = link.inner_text().strip()
                        logger.info(f"Processing version {i+1}/{num_versions}: {description[:60]}...")

                        # Click the link
                        link.click()

                        # Wait for content to load
                        page.wait_for_load_state('networkidle', timeout=30000)
                        page.wait_for_selector('body', timeout=10000)

                        # Get the content
                        html_content = page.content()
                        page_url = page.url

                        # Parse content
                        content, history = self._extract_content_from_html(html_content, section)

                        version_data = {
                            "version_number": i + 1,
                            "description": description,
                            "content": content,
                            "legislative_history": history or description,
                            "operative_date": self._parse_operative_date(description),
                            "is_current": i == 0,  # First version is typically current
                            "url": page_url,
                            "extraction_method": "playwright"
                        }

                        versions.append(version_data)

                        logger.info(f"✅ Version {i+1}: {len(content)} chars extracted")

                    except Exception as e:
                        logger.error(f"Error processing version {i+1} of {code} {section}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Continue with next version
                        continue

                # Browser and context will be closed automatically when exiting the `with` block
                return versions

        except Exception as e:
            logger.error(f"Error fetching versions with Playwright for {code} {section}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _extract_content_from_html(self, html: str, section: str) -> Tuple[str, Optional[str]]:
        """
        Extract section content from HTML

        Args:
            html: HTML content
            section: Section number

        Returns:
            Tuple of (content, legislative_history)
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Find section header
            section_header = soup.find('h6', string=re.compile(rf'^{section}\.?\s*$'))

            if not section_header:
                # Try alternative selectors
                section_header = soup.find('h6')

            if not section_header:
                logger.warning(f"Section header not found for section {section}")
                return "", None

            # Collect paragraphs after the header
            content_parts = []
            current = section_header.find_next_sibling()

            while current:
                if current.name == 'h6':  # Stop at next section
                    break
                if current.name == 'p':
                    text = current.get_text(strip=True)
                    # Skip if it looks like a legislative history line
                    if text and not text.startswith('(Amended by') and not text.startswith('(Enacted by') and not text.startswith('(Repealed'):
                        content_parts.append(text)
                    elif text and (text.startswith('(Amended') or text.startswith('(Enacted') or text.startswith('(Repealed')):
                        # This might be legislative history
                        # Extract it but don't include in content
                        history = text.strip('(').strip(')')
                        break

                current = current.find_next_sibling()

            content = '\n\n'.join(content_parts)

            # Extract legislative history
            history = None
            history_elem = soup.find('p', string=re.compile(r'\((?:Amended|Enacted|Repealed)'))
            if history_elem:
                history_text = history_elem.get_text(strip=True)
                history = history_text.strip('(').strip(')')

            return content, history

        except Exception as e:
            logger.error(f"Error extracting content from HTML: {e}")
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

"""Architecture crawler for Stage 1: URL discovery and hierarchy parsing."""

import logging
import re
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.core.database import DatabaseManager
from pipeline.models.code import CodeCreate, CodeUpdate
from pipeline.models.section import SectionCreate

logger = logging.getLogger(__name__)


class ArchitectureCrawler:
    """Crawler for extracting code architecture and section URLs (Stage 1)."""

    def __init__(
        self,
        firecrawl_service: Optional[FirecrawlService] = None,
        db_manager: Optional[DatabaseManager] = None
    ):
        """Initialize the architecture crawler.

        Args:
            firecrawl_service: Firecrawl service instance (will create if not provided)
            db_manager: Database manager instance (will create if not provided)
        """
        self.firecrawl = firecrawl_service or FirecrawlService()
        self.db = db_manager
        self.base_url = "https://leginfo.legislature.ca.gov/faces"

    def get_architecture_url(self, code: str) -> str:
        """Get the architecture page URL for a code.

        Args:
            code: Code abbreviation (e.g., 'EVID', 'FAM')

        Returns:
            Full URL to the code's architecture page
        """
        return f"{self.base_url}/codedisplayexpand.xhtml?tocCode={code}"

    def crawl(self, code: str, save_to_db: bool = True) -> Dict:
        """Crawl code architecture and extract section URLs (Stage 1).

        Args:
            code: Code abbreviation (e.g., 'EVID', 'FAM')
            save_to_db: Whether to save results to database

        Returns:
            Dictionary containing:
                - code: Code abbreviation
                - url: Architecture page URL
                - total_sections: Number of sections found
                - sections: List of section metadata
                - text_page_urls: List of text page URLs
        """
        logger.info(f"Starting Stage 1 for code: {code}")
        start_time = datetime.utcnow()

        # Update database - mark stage 1 started
        if save_to_db and self.db:
            code_url = self.get_architecture_url(code)
            code_create = CodeCreate(code=code, url=code_url)
            self.db.upsert_code(code_create)
            self.db.update_code(code, CodeUpdate(stage1_started=start_time))

        # Get architecture page URL
        url = self.get_architecture_url(code)
        logger.info(f"Scraping architecture page: {url}")

        # Scrape with Firecrawl
        result = self.firecrawl.scrape_url(url)
        markdown = result["data"].get("markdown", "")
        links_on_page = result["data"].get("linksOnPage", [])

        # Extract text page URLs (divisions, parts, chapters)
        text_page_urls = self._extract_text_page_urls(links_on_page)
        logger.info(f"Found {len(text_page_urls)} text pages")

        # Extract section URLs from all text pages
        all_sections = []
        for text_url in text_page_urls:
            sections = self._extract_sections_from_text_page(code, text_url)
            all_sections.extend(sections)
            logger.debug(f"Found {len(sections)} sections in {text_url}")

        logger.info(f"Total sections found: {len(all_sections)}")

        # Save to database if requested
        if save_to_db and self.db:
            self._save_to_database(code, all_sections)

            # Update code metadata
            finish_time = datetime.utcnow()
            self.db.update_code(
                code,
                CodeUpdate(
                    total_sections=len(all_sections),
                    stage1_completed=True,
                    stage1_finished=finish_time
                )
            )

        result_data = {
            "code": code,
            "url": url,
            "total_sections": len(all_sections),
            "sections": all_sections,
            "text_page_urls": text_page_urls,
        }

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Stage 1 complete for {code}: {len(all_sections)} sections in {duration:.2f}s")

        return result_data

    def _extract_text_page_urls(self, links_on_page: List[str]) -> List[str]:
        """Extract text page URLs from links.

        Text pages are the division/part/chapter pages that contain actual section links.

        Args:
            links_on_page: List of URLs from Firecrawl

        Returns:
            List of text page URLs
        """
        text_page_urls = []

        for link in links_on_page:
            # Look for codes_displayText.xhtml URLs
            if "codes_displayText.xhtml" in link:
                text_page_urls.append(link)

        return text_page_urls

    def _extract_sections_from_text_page(self, code: str, text_url: str) -> List[Dict]:
        """Extract section URLs and metadata from a text page using requests+BeautifulSoup.

        Args:
            code: Code abbreviation
            text_url: URL of the text page

        Returns:
            List of section metadata dictionaries
        """
        try:
            # Use requests+BeautifulSoup (same as old pipeline)
            time.sleep(0.3)  # Rate limiting
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; CaliforniaLegalCodes/1.0)'
            })
            response = session.get(text_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse hierarchy from URL
            hierarchy = self._parse_hierarchy_from_url(text_url)

            # Extract sections from h6 tags (same method as old pipeline)
            sections = []
            seen_sections = set()

            # Method 1: Look for h6 tags containing section numbers
            for h6 in soup.find_all('h6'):
                text = h6.get_text(strip=True)
                # Match section numbers like "1.", "1.5.", "1798.24a.", etc.
                match = re.match(r'^(\d+(?:\.\d+)?[a-z]?)\.?$', text)
                if match:
                    section_num = match.group(1)
                    if section_num not in seen_sections:
                        seen_sections.add(section_num)
                        sections.append({
                            "code": code,
                            "section": section_num,
                            "url": f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode={code}&sectionNum={section_num}",
                            **hierarchy
                        })

            # Method 2: Look for links within h6 tags
            for h6 in soup.find_all('h6'):
                link = h6.find('a')
                if link:
                    text = link.get_text(strip=True)
                    match = re.match(r'^(\d+(?:\.\d+)?[a-z]?)\.?$', text)
                    if match:
                        section_num = match.group(1)
                        if section_num not in seen_sections:
                            seen_sections.add(section_num)
                            sections.append({
                                "code": code,
                                "section": section_num,
                                "url": f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode={code}&sectionNum={section_num}",
                                **hierarchy
                            })

            logger.debug(f"Found {len(sections)} sections in {text_url}")
            return sections

        except Exception as e:
            logger.warning(f"Failed to fetch {text_url}: {e}")
            return []

    def _parse_hierarchy_from_url(self, url: str) -> Dict[str, Optional[str]]:
        """Parse hierarchy information from text page URL.

        Args:
            url: Text page URL with hierarchy parameters

        Returns:
            Dictionary with division, part, chapter, article
        """
        hierarchy = {
            "division": None,
            "part": None,
            "chapter": None,
            "article": None,
        }

        # Extract division
        division_match = re.search(r"division=([^&]+)", url)
        if division_match:
            hierarchy["division"] = division_match.group(1).replace("+", " ")

        # Extract part
        part_match = re.search(r"part=([^&]+)", url)
        if part_match:
            hierarchy["part"] = part_match.group(1).replace("+", " ")

        # Extract chapter
        chapter_match = re.search(r"chapter=([^&]+)", url)
        if chapter_match:
            hierarchy["chapter"] = chapter_match.group(1).replace("+", " ")

        # Extract article
        article_match = re.search(r"article=([^&]+)", url)
        if article_match:
            hierarchy["article"] = article_match.group(1).replace("+", " ")

        return hierarchy

    def _extract_section_number(self, url: str) -> Optional[str]:
        """Extract section number from section URL.

        Args:
            url: Section URL

        Returns:
            Section number or None
        """
        match = re.search(r"sectionNum=([^&]+)", url)
        if match:
            return match.group(1)
        return None

    def _save_to_database(self, code: str, sections: List[Dict]) -> None:
        """Save sections to database.

        Args:
            code: Code abbreviation
            sections: List of section metadata
        """
        if not self.db:
            logger.warning("No database manager provided, skipping save")
            return

        logger.info(f"Saving {len(sections)} sections to database")

        # Create SectionCreate objects (without content, just URL and hierarchy)
        section_creates = []
        for section_data in sections:
            section_create = SectionCreate(
                code=section_data["code"],
                section=section_data["section"],
                url=section_data["url"],
                division=section_data.get("division"),
                part=section_data.get("part"),
                chapter=section_data.get("chapter"),
                article=section_data.get("article"),
            )
            section_creates.append(section_create)

        # Bulk upsert
        count = self.db.bulk_upsert_sections(section_creates)
        logger.info(f"Saved {count} sections to database")

    def get_all_section_urls(self, code: str) -> List[str]:
        """Get all section URLs for a code from the database.

        Args:
            code: Code abbreviation

        Returns:
            List of section URLs
        """
        if not self.db:
            raise ValueError("Database manager required to get section URLs")

        sections = self.db.get_sections_by_code(code, skip=0, limit=10000)
        return [section.url for section in sections]

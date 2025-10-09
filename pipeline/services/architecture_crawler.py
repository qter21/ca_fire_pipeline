"""Architecture crawler for Stage 1: URL discovery and hierarchy parsing."""

import logging
import re
import time
import hashlib
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
                - tree: Hierarchical structure
                - url_manifest: List of all sections with metadata
                - statistics: Tree statistics
                - total_sections: Number of sections found
                - session_id: Unique session identifier
        """
        logger.info(f"Starting Stage 1 for code: {code}")
        start_time = datetime.utcnow()

        # Generate session ID
        session_id = hashlib.md5(f"{code}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]

        # Update database - mark stage 1 started
        if save_to_db and self.db:
            code_url = self.get_architecture_url(code)
            code_create = CodeCreate(code=code, url=code_url)
            self.db.upsert_code(code_create)
            self.db.update_code(code, CodeUpdate(stage1_started=start_time))

        # Get architecture page URL
        url = self.get_architecture_url(code)
        logger.info(f"Scraping architecture page: {url}")

        # Build tree structure and get text page URLs
        tree, text_page_urls = self._get_tree_and_text_urls(code)
        logger.info(f"Found {len(text_page_urls)} text pages")

        # Extract section URLs from all text pages
        all_sections = []
        for text_url in text_page_urls:
            sections = self._extract_sections_from_text_page(code, text_url)
            all_sections.extend(sections)
            logger.debug(f"Found {len(sections)} sections in {text_url}")

        logger.info(f"Total sections found: {len(all_sections)}")

        # Create url_manifest (sorted section list)
        url_manifest = self._create_url_manifest(all_sections)

        # Calculate statistics
        statistics = self._calculate_statistics(tree, url_manifest)

        # Get multi-version section list
        multi_version_sections = [s["section"] for s in all_sections if s.get("is_multi_version")]

        # Save to database if requested
        if save_to_db and self.db:
            self._save_to_database(code, all_sections)
            self._save_architecture_to_db(code, tree, url_manifest, statistics, session_id, multi_version_sections)

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
            "success": True,
            "code": code,
            "url": url,
            "tree": tree,
            "url_manifest": url_manifest,
            "statistics": statistics,
            "multi_version_sections": multi_version_sections,
            "total_sections": len(all_sections),
            "total_urls": len(url_manifest),
            "items_count": statistics.get('total_nodes', 0),
            "session_id": session_id,
            "crawled_at": datetime.now().isoformat()
        }

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Stage 1 complete for {code}: {len(all_sections)} sections in {duration:.2f}s")

        return result_data

    def _get_tree_and_text_urls(self, code: str) -> Tuple[Dict, List[str]]:
        """
        Build hierarchical tree structure and collect text page URLs (same as old pipeline)

        Args:
            code: Code abbreviation

        Returns:
            Tuple of (tree dict, text_page_urls list)
        """
        url = self.get_architecture_url(code)

        # Fetch HTML with requests (same as old pipeline)
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CaliforniaLegalCodes/1.0)'
        })
        response = session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        tree = {
            'type': 'CODE',
            'code': code,
            'name': f'California {code} Code',
            'children': []
        }

        text_page_urls = []

        # Find the container
        container = soup.find('div', {'id': 'expandedbranchcodesid'})
        if not container:
            logger.warning(f"Container not found for {code}")
            return tree, text_page_urls

        current_level_nodes = {}

        for link in container.find_all('a', href=True):
            href = link.get('href', '')

            if 'codes_display' not in href:
                continue

            # Collect text page URLs
            if 'codes_displayText' in href:
                full_url = self.base_url + '/' + href.lstrip('/') if not href.startswith('http') else href
                text_page_urls.append(full_url)

            # Get text and section range
            text_div = link.find('div', style=lambda x: x and 'float:left' in x)
            range_div = link.find('div', style=lambda x: x and 'float:right' in x)

            if not text_div:
                continue

            text = text_div.get_text(strip=True)
            section_range_display = range_div.get_text(strip=True) if range_div else ''

            # Get indentation level
            style = text_div.get('style', '')
            indent_match = re.search(r'margin-left:(\d+)px', style)
            indent = int(indent_match.group(1)) if indent_match else 0
            level = max(0, (indent - 10) // 10)

            # Create node
            node_type = self._determine_node_type(text)
            node_number = self._extract_node_number(text, node_type)

            full_label = ""
            if node_type != 'SECTION' and node_number:
                full_label = f"{node_type.title()} {node_number}"
            elif node_type != 'SECTION':
                full_label = node_type.title()

            node = {
                'type': node_type,
                'number': node_number,
                'title': self._extract_title(text),
                'full_label': full_label,
                'level': level,
                'section_range_display': section_range_display,
                'children': []
            }

            # Build hierarchy
            if level == 0:
                tree['children'].append(node)
                current_level_nodes[level] = node
            else:
                parent_level = level - 1
                if parent_level in current_level_nodes:
                    current_level_nodes[parent_level]['children'].append(node)
                    current_level_nodes[level] = node

        return tree, text_page_urls

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

    def _determine_node_type(self, text: str) -> str:
        """Determine the type of hierarchy node"""
        text_upper = text.upper()
        if 'DIVISION' in text_upper:
            return 'DIVISION'
        elif 'PART' in text_upper:
            return 'PART'
        elif 'TITLE' in text_upper:
            return 'TITLE'
        elif 'CHAPTER' in text_upper:
            return 'CHAPTER'
        elif 'ARTICLE' in text_upper:
            return 'ARTICLE'
        else:
            return 'SECTION'

    def _extract_node_number(self, text: str, node_type: str) -> str:
        """Extract the node number"""
        if node_type == 'SECTION':
            return ""
        pattern = f"{node_type}\\s+(\\d+(?:\\.\\d+)?)"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else ""

    def _extract_title(self, text: str) -> str:
        """Extract the title portion of the text"""
        for node_type in ['DIVISION', 'PART', 'TITLE', 'CHAPTER', 'ARTICLE']:
            pattern = f"{node_type}\\s+\\d+(?:\\.\\d+)?\\s*\\.?\\s*"
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        return text.strip()

    def _create_url_manifest(self, sections: List[Dict]) -> List[Dict]:
        """Create sorted URL manifest"""
        def section_sort_key(item):
            section = item['section']
            match = re.match(r'(\d+)(?:\.(\d+))?([a-z]?)', section)
            if match:
                main = int(match.group(1))
                decimal = int(match.group(2)) if match.group(2) else 0
                letter = ord(match.group(3)) if match.group(3) else 0
                return (main, decimal, letter)
            return (0, 0, 0)

        return sorted(sections, key=section_sort_key)

    def _calculate_statistics(self, tree: Dict, url_manifest: List[Dict]) -> Dict:
        """Calculate statistics"""
        def count_nodes(node):
            count = 1
            for child in node.get('children', []):
                count += count_nodes(child)
            return count

        def get_max_depth(node, depth=0):
            if not node.get('children'):
                return depth
            return max(get_max_depth(child, depth + 1) for child in node['children'])

        total_nodes = count_nodes(tree) - 1
        max_depth = get_max_depth(tree)

        return {
            'total_nodes': total_nodes,
            'max_depth': max_depth,
            'total_sections': len(url_manifest)
        }

    def _save_architecture_to_db(self, code: str, tree: Dict, url_manifest: List[Dict],
                                  statistics: Dict, session_id: str, multi_version_sections: List[str]) -> None:
        """Save complete architecture to database (old pipeline format)"""
        if not self.db:
            return

        # Save to code_architectures collection (old pipeline format)
        architecture_doc = {
            'code': code,
            'tree': tree,
            'url_manifest': url_manifest,
            'statistics': statistics,
            'multi_version_sections': multi_version_sections,
            'total_urls': len(url_manifest),
            'items_count': statistics.get('total_nodes', 0),
            'session_id': session_id,
            'crawled_at': datetime.now().isoformat(),
            'success': True
        }

        # Upsert to code_architectures
        self.db.code_architectures.update_one(
            {'code': code},
            {'$set': architecture_doc},
            upsert=True
        )

        logger.info(f"Saved architecture tree and manifest for {code} to code_architectures")

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

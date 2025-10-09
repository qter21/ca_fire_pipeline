"""
Content parsing utilities for California legal code sections
Extracts section content and legislative history from Firecrawl markdown
"""

import re
from typing import Dict, Optional, Tuple


class ContentParser:
    """Parser for extracting section content from Firecrawl markdown"""

    @staticmethod
    def extract_section_content(markdown: str, section: str) -> Tuple[str, Optional[str]]:
        """
        Extract section content and legislative history from markdown

        Args:
            markdown: Full markdown content from Firecrawl
            section: Section number (e.g., "400", "3044")

        Returns:
            Tuple of (content, legislative_history)
            Returns ("", None) if section not found
        """
        # Pattern: Match from section header to next section/chapter or end
        section_pattern = rf'#{{6}}\s+\*\*{re.escape(section)}\.?\*\*\s*\n\n(.+?)(?=\n#{{5,6}}|\Z)'
        match = re.search(section_pattern, markdown, re.DOTALL)

        if not match:
            # Try alternative line-based extraction
            return ContentParser._extract_by_lines(markdown, section)

        full_section = match.group(1).strip()

        # Split content and history
        # Legislative history is the last line starting with _( and ending with )_
        lines = full_section.split('\n')

        content_lines = []
        history = None

        # Process lines in reverse to find the section-specific history
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith('_(') and stripped.endswith(')_'):
                # This is legislative history
                history = stripped[2:-2]  # Remove _( and )_
                break

        # Collect content (everything except the last history line)
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('_(') and stripped.endswith(')_') and stripped[2:-2] == history:
                # Skip the history line
                continue
            if line.strip():  # Skip empty lines
                content_lines.append(line)

        content = '\n'.join(content_lines).strip()

        return content, history

    @staticmethod
    def _extract_by_lines(markdown: str, section: str) -> Tuple[str, Optional[str]]:
        """
        Fallback line-based extraction

        Args:
            markdown: Full markdown content
            section: Section number

        Returns:
            Tuple of (content, legislative_history)
        """
        lines = markdown.split('\n')
        capture = False
        content_lines = []
        history = None

        for line in lines:
            # Start capturing after section header
            if f'**{section}.**' in line or f'**{section}' in line:
                capture = True
                continue

            if capture:
                # Stop at next section or chapter
                if line.startswith('##'):
                    break

                stripped = line.strip()

                # Check for legislative history
                if stripped.startswith('_(') and stripped.endswith(')_'):
                    history = stripped[2:-2]
                    break

                # Collect content
                if stripped:
                    content_lines.append(line)

        content = '\n'.join(content_lines).strip()
        return content, history

    @staticmethod
    def extract_all_legislative_histories(markdown: str) -> list:
        """
        Extract all legislative history entries from markdown
        Useful for debugging or finding section-specific vs chapter-level histories

        Args:
            markdown: Full markdown content

        Returns:
            List of legislative history strings
        """
        history_pattern = r'_\(([^)]+)\)_'
        return re.findall(history_pattern, markdown)

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison
        Removes extra whitespace and normalizes formatting

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove newlines
        text = text.replace('\n', ' ')
        return text.strip()

    @staticmethod
    def is_multi_version(url: str, markdown: str) -> bool:
        """
        Check if section is multi-version

        Args:
            url: Source URL from metadata
            markdown: Markdown content

        Returns:
            True if multi-version section detected
        """
        return "selectFromMultiples" in url.lower() or \
               "selectFromMultiples" in markdown

    @staticmethod
    def extract_version_links(links: list) -> list:
        """
        Extract version-specific links from linksOnPage

        Args:
            links: List of all links from Firecrawl linksOnPage

        Returns:
            List of version-specific links (containing nodeTreePath)
        """
        return [link for link in links if 'nodeTreePath' in link]

    @staticmethod
    def extract_section_number_from_url(url: str) -> Optional[str]:
        """
        Extract section number from URL

        Args:
            url: Section URL

        Returns:
            Section number or None
        """
        match = re.search(r'sectionNum=([^&]+)', url)
        return match.group(1) if match else None

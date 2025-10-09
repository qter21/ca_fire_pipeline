"""
Concurrent Content Extractor for Stage 2
Optimized for high-throughput scraping using concurrent requests
"""

import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime

from pipeline.services.firecrawl_concurrent import ConcurrentFirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.services.multi_version_handler import MultiVersionHandler
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings
from pipeline.models.section import SectionUpdate

logger = logging.getLogger(__name__)


class ConcurrentContentExtractor:
    """
    High-performance content extractor using concurrent requests

    Utilizes Firecrawl's concurrent request capacity (up to 50 parallel requests)
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        batch_size: Optional[int] = None,
        max_workers: int = 10
    ):
        """
        Initialize concurrent content extractor

        Args:
            db_manager: Database manager instance
            batch_size: Batch size for processing (default from settings)
            max_workers: Max concurrent workers (default: 10, max: 50)
        """
        self.firecrawl = ConcurrentFirecrawlService(max_workers=max_workers)
        self.multi_version_handler = MultiVersionHandler()
        self.db = db_manager
        settings = get_settings()
        self.batch_size = batch_size or settings.BATCH_SIZE
        self.max_workers = max_workers

        logger.info(f"Concurrent Content Extractor initialized with {max_workers} workers")

    def extract(
        self,
        code: str,
        skip_multi_version: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """
        Extract content for all sections of a code using concurrent requests

        Args:
            code: Code abbreviation (e.g., 'EVID', 'FAM')
            skip_multi_version: If True, skip multi-version sections
            progress_callback: Optional callback function(processed, total)

        Returns:
            Dictionary containing extraction results
        """
        logger.info(f"Starting concurrent Stage 2 for code: {code}")
        start_time = datetime.now()

        # Get all sections from database
        if not self.db:
            raise ValueError("Database manager required for content extraction")

        sections = self.db.get_sections_by_code(code, skip=0, limit=10000)
        total_sections = len(sections)
        logger.info(f"Found {total_sections} sections to process concurrently")

        if total_sections == 0:
            logger.warning(f"No sections found for code {code}. Run Stage 1 first.")
            return {
                "code": code,
                "total_sections": 0,
                "single_version_count": 0,
                "multi_version_count": 0,
                "failed_sections": []
            }

        # Update database - mark stage 2 started
        from pipeline.models.code import CodeUpdate
        self.db.update_code(code, CodeUpdate(stage2_started=start_time))

        # Process in batches with concurrent requests
        single_version_count = 0
        multi_version_count = 0
        failed_sections = []
        processed = 0

        for i in range(0, total_sections, self.batch_size):
            batch = sections[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1}: sections {i+1}-{min(i+self.batch_size, total_sections)}")

            # Extract URLs for batch
            urls = [section.url for section in batch]

            # Concurrent batch scrape
            try:
                results = self.firecrawl.batch_scrape_concurrent(urls, max_workers=self.max_workers)

                # Process each result
                for j, result in enumerate(results):
                    section = batch[j]
                    processed += 1

                    try:
                        # Check if valid result
                        if not result or not result.get("success") or "data" not in result:
                            logger.error(f"Invalid result for {section.code} §{section.section}")
                            failed_sections.append(f"{section.code}:{section.section}")
                            continue

                        # Extract data
                        markdown = result["data"].get("markdown", "")
                        source_url = result["data"].get("metadata", {}).get("url", section.url)

                        # Check if multi-version
                        is_multi_version = ContentParser.is_multi_version(source_url, markdown)

                        if is_multi_version and not skip_multi_version:
                            # Multi-version section
                            logger.debug(f"Multi-version detected: {section.code} §{section.section}")
                            multi_version_count += 1

                            update = SectionUpdate(
                                is_multi_version=True,
                                url=source_url
                            )
                            self.db.update_section(section.code, section.section, update)

                        elif is_multi_version and skip_multi_version:
                            # Skip multi-version
                            logger.debug(f"Skipping multi-version: {section.code} §{section.section}")
                            multi_version_count += 1

                        else:
                            # Single-version section
                            content, legislative_history = ContentParser.extract_section_content(
                                markdown, section.section
                            )

                            if content:
                                single_version_count += 1
                                update = SectionUpdate(
                                    content=content,
                                    raw_content=content,
                                    legislative_history=legislative_history,
                                    raw_legislative_history=legislative_history,
                                    has_content=True,
                                    content_cleaned=False,
                                    content_length=len(content),
                                    raw_content_length=len(content),
                                    has_legislative_history=bool(legislative_history),
                                    is_multi_version=False,
                                    is_current=True,
                                    version_number=1,
                                    url=source_url
                                )
                                self.db.update_section(section.code, section.section, update)
                                logger.debug(f"Extracted: {section.code} §{section.section} ({len(content)} chars)")
                            else:
                                logger.warning(f"No content for {section.code} §{section.section}")
                                failed_sections.append(f"{section.code}:{section.section}")

                    except Exception as e:
                        logger.error(f"Error processing {section.code} §{section.section}: {e}")
                        failed_sections.append(f"{section.code}:{section.section}")

                    # Progress callback
                    if progress_callback:
                        progress_callback(processed, total_sections)

            except Exception as e:
                logger.error(f"Batch scraping failed: {e}")
                for section in batch:
                    failed_sections.append(f"{section.code}:{section.section}")
                processed += len(batch)

        # Update database - mark stage 2 completed
        finish_time = datetime.now()
        self.db.update_code(
            code,
            CodeUpdate(
                single_version_count=single_version_count,
                multi_version_count=multi_version_count,
                processed_sections=processed,
                stage2_completed=True,
                stage2_finished=finish_time
            )
        )

        result = {
            "code": code,
            "total_sections": total_sections,
            "single_version_count": single_version_count,
            "multi_version_count": multi_version_count,
            "failed_sections": failed_sections
        }

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Concurrent Stage 2 complete for {code}: "
            f"{single_version_count} single-version, "
            f"{multi_version_count} multi-version, "
            f"{len(failed_sections)} failed "
            f"in {duration:.2f}s ({duration/60:.2f} minutes)"
        )

        return result

"""Content extractor for Stage 2: Batch section content extraction."""

import logging
from typing import List, Dict, Optional, Callable
from datetime import datetime

from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.services.multi_version_handler import MultiVersionHandler
from pipeline.core.database import DatabaseManager
from pipeline.core.config import get_settings
from pipeline.models.section import SectionUpdate, Section, Version

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Extractor for batch section content extraction (Stage 2)."""

    def __init__(
        self,
        firecrawl_service: Optional[FirecrawlService] = None,
        multi_version_handler: Optional[MultiVersionHandler] = None,
        db_manager: Optional[DatabaseManager] = None,
        batch_size: Optional[int] = None
    ):
        """Initialize the content extractor.

        Args:
            firecrawl_service: Firecrawl service instance
            multi_version_handler: Multi-version handler instance
            db_manager: Database manager instance
            batch_size: Batch size for processing (default from settings)
        """
        self.firecrawl = firecrawl_service or FirecrawlService()
        self.multi_version_handler = multi_version_handler or MultiVersionHandler(
            firecrawl_service=self.firecrawl
        )
        self.db = db_manager
        settings = get_settings()
        self.batch_size = batch_size or settings.BATCH_SIZE

    def extract(
        self,
        code: str,
        skip_multi_version: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """Extract content for all sections of a code (Stage 2).

        Args:
            code: Code abbreviation (e.g., 'EVID', 'FAM')
            skip_multi_version: If True, skip multi-version sections (for Stage 3)
            progress_callback: Optional callback function(processed, total)

        Returns:
            Dictionary containing:
                - code: Code abbreviation
                - total_sections: Total sections processed
                - single_version_count: Number of single-version sections
                - multi_version_count: Number of multi-version sections
                - failed_sections: List of failed section identifiers
        """
        logger.info(f"Starting Stage 2 for code: {code}")
        start_time = datetime.utcnow()

        # Get all sections from database
        if not self.db:
            raise ValueError("Database manager required for content extraction")

        sections = self.db.get_sections_by_code(code, skip=0, limit=10000)
        total_sections = len(sections)
        logger.info(f"Found {total_sections} sections to process")

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

        # Process in batches
        single_version_count = 0
        multi_version_count = 0
        failed_sections = []
        processed = 0

        for i in range(0, total_sections, self.batch_size):
            batch = sections[i:i + self.batch_size]
            logger.info(f"Processing batch {i // self.batch_size + 1}: sections {i+1}-{min(i+self.batch_size, total_sections)}")

            # Extract URLs for batch
            urls = [section.url for section in batch]

            # Batch scrape with Firecrawl
            try:
                results = self.firecrawl.batch_scrape(urls)

                # Process each result
                for j, result in enumerate(results):
                    section = batch[j]
                    processed += 1

                    try:
                        # Check if this is a valid result
                        if not result or "data" not in result:
                            logger.error(f"Invalid result for {section.code} §{section.section}")
                            failed_sections.append(f"{section.code}:{section.section}")
                            continue

                        # Extract data
                        markdown = result["data"].get("markdown", "")
                        source_url = result["data"].get("metadata", {}).get("url", section.url)

                        # Check if multi-version
                        is_multi_version = ContentParser.is_multi_version(source_url, markdown)

                        if is_multi_version and not skip_multi_version:
                            # Multi-version section - handle separately
                            logger.debug(f"Multi-version detected: {section.code} §{section.section}")
                            multi_version_count += 1

                            # Just mark as multi-version for now (Stage 3 will extract content)
                            update = SectionUpdate(
                                is_multi_version=True,
                                url=source_url
                            )
                            self.db.update_section(section.code, section.section, update)

                        elif is_multi_version and skip_multi_version:
                            # Skip multi-version in this pass
                            logger.debug(f"Skipping multi-version: {section.code} §{section.section}")
                            multi_version_count += 1

                        else:
                            # Single-version section - extract content
                            content, legislative_history = ContentParser.extract_section_content(
                                markdown, section.section
                            )

                            if content:
                                single_version_count += 1
                                # Update with old pipeline compatible fields
                                update = SectionUpdate(
                                    content=content,
                                    raw_content=content,  # Same for now (cleaning not implemented yet)
                                    legislative_history=legislative_history,
                                    raw_legislative_history=legislative_history,
                                    has_content=True,
                                    content_cleaned=False,  # Not implementing cleaning yet
                                    content_length=len(content) if content else 0,
                                    raw_content_length=len(content) if content else 0,
                                    has_legislative_history=bool(legislative_history),
                                    is_multi_version=False,
                                    is_current=True,
                                    version_number=1,
                                    url=source_url
                                )
                                self.db.update_section(section.code, section.section, update)
                                logger.debug(f"Extracted: {section.code} §{section.section} ({len(content)} chars)")
                            else:
                                logger.warning(f"No content extracted for {section.code} §{section.section}")
                                failed_sections.append(f"{section.code}:{section.section}")

                    except Exception as e:
                        logger.error(f"Error processing {section.code} §{section.section}: {e}")
                        failed_sections.append(f"{section.code}:{section.section}")

                    # Progress callback
                    if progress_callback:
                        progress_callback(processed, total_sections)

            except Exception as e:
                logger.error(f"Batch scraping failed: {e}")
                # Mark all sections in batch as failed
                for section in batch:
                    failed_sections.append(f"{section.code}:{section.section}")
                processed += len(batch)

        # Update database - mark stage 2 completed
        finish_time = datetime.utcnow()
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

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Stage 2 complete for {code}: "
            f"{single_version_count} single-version, "
            f"{multi_version_count} multi-version, "
            f"{len(failed_sections)} failed "
            f"in {duration:.2f}s"
        )

        return result

    def extract_multi_version_sections(
        self,
        code: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        """Extract content for multi-version sections (Stage 3).

        Args:
            code: Code abbreviation
            progress_callback: Optional callback function(processed, total)

        Returns:
            Dictionary containing extraction results
        """
        logger.info(f"Starting Stage 3 (multi-version) for code: {code}")
        start_time = datetime.utcnow()

        if not self.db:
            raise ValueError("Database manager required for multi-version extraction")

        # Update database - mark stage 3 started
        from pipeline.models.code import CodeUpdate
        self.db.update_code(code, CodeUpdate(stage3_started=start_time))

        # Get all multi-version sections
        sections = self.db.get_multi_version_sections(code=code)
        total_sections = len(sections)
        logger.info(f"Found {total_sections} multi-version sections to process")

        if total_sections == 0:
            logger.info(f"No multi-version sections found for code {code}")
            return {
                "code": code,
                "total_sections": 0,
                "extracted_count": 0,
                "failed_sections": []
            }

        # Process each multi-version section
        extracted_count = 0
        failed_sections = []

        for i, section in enumerate(sections):
            try:
                logger.info(f"Extracting multi-version: {section.code} §{section.section} ({i+1}/{total_sections})")

                # Extract all versions
                result = self.multi_version_handler.extract_all_versions(
                    section.code,
                    section.section
                )

                if result.get("is_multi_version") and result.get("versions"):
                    # Convert versions to Version objects
                    versions = [
                        Version(
                            operative_date=v["operative_date"],
                            content=v["content"],
                            legislative_history=v.get("legislative_history"),
                            status=v.get("status", "current"),
                            url=v.get("url")
                        )
                        for v in result["versions"]
                    ]

                    # Update section in database
                    update = SectionUpdate(
                        is_multi_version=True,
                        versions=versions
                    )
                    self.db.update_section(section.code, section.section, update)
                    extracted_count += 1

                    total_chars = sum(len(v.content) for v in versions)
                    logger.info(
                        f"Extracted {len(versions)} versions for {section.code} §{section.section} "
                        f"({total_chars} chars)"
                    )
                else:
                    logger.warning(f"No versions extracted for {section.code} §{section.section}")
                    failed_sections.append(f"{section.code}:{section.section}")

            except Exception as e:
                logger.error(f"Error extracting multi-version {section.code} §{section.section}: {e}")
                failed_sections.append(f"{section.code}:{section.section}")

            # Progress callback
            if progress_callback:
                progress_callback(i + 1, total_sections)

        # Update database - mark stage 3 completed
        finish_time = datetime.utcnow()
        self.db.update_code(
            code,
            CodeUpdate(
                stage3_completed=True,
                stage3_finished=finish_time
            )
        )

        result = {
            "code": code,
            "total_sections": total_sections,
            "extracted_count": extracted_count,
            "failed_sections": failed_sections
        }

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Stage 3 complete for {code}: "
            f"{extracted_count}/{total_sections} extracted "
            f"in {duration:.2f}s"
        )

        return result

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
from pipeline.models.checkpoint import ProcessingCheckpoint, CheckpointUpdate, ProcessingStage, CheckpointStatus

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
        max_workers: int = 10,
        enable_checkpointing: bool = True
    ):
        """
        Initialize concurrent content extractor

        Args:
            db_manager: Database manager instance
            batch_size: Batch size for processing (default from settings)
            max_workers: Max concurrent workers (default: 10, max: 50)
            enable_checkpointing: Enable checkpoint saving for pause/resume
        """
        self.firecrawl = ConcurrentFirecrawlService(max_workers=max_workers)
        self.multi_version_handler = MultiVersionHandler()
        self.db = db_manager
        settings = get_settings()
        self.batch_size = batch_size or settings.BATCH_SIZE
        self.max_workers = max_workers
        self.enable_checkpointing = enable_checkpointing

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

        # Get total count to check for truncation
        total_in_db = self.db.count_sections(code)

        # Fetch sections (will use config limit and log warning if truncated)
        sections = self.db.get_sections_by_code(code, skip=0, limit=None)
        total_sections = len(sections)

        # Check if we hit the limit
        incomplete_processing = total_sections < total_in_db
        if incomplete_processing:
            logger.error(
                f"❌ INCOMPLETE PROCESSING: Only fetched {total_sections:,} of {total_in_db:,} sections for {code}. "
                f"Missing {total_in_db - total_sections:,} sections ({(total_in_db - total_sections)/total_in_db*100:.1f}%). "
                f"💡 Increase MAX_SECTIONS_QUERY_LIMIT in config to process all sections."
            )

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

        # Initialize or load checkpoint
        checkpoint = None
        if self.enable_checkpointing:
            checkpoint = self._get_or_create_checkpoint(code, total_sections, ProcessingStage.STAGE2_CONTENT)
            logger.info(f"Checkpoint: {checkpoint.processed_sections}/{checkpoint.total_sections} already processed")

        # Process in batches with concurrent requests
        single_version_count = 0
        multi_version_count = 0
        failed_sections = []
        processed = checkpoint.processed_sections if checkpoint else 0
        total_batches = (total_sections + self.batch_size - 1) // self.batch_size

        for i in range(0, total_sections, self.batch_size):
            batch_num = i // self.batch_size + 1

            # Skip already processed batches if resuming
            if checkpoint and batch_num <= checkpoint.current_batch:
                logger.info(f"Skipping already processed batch {batch_num}")
                continue

            batch = sections[i:i + self.batch_size]

            # Enhanced progress logging
            batch_progress = (batch_num / total_batches * 100) if total_batches > 0 else 0
            overall_progress = (processed / total_sections * 100) if total_sections > 0 else 0

            logger.info(
                f"{'='*80}\n"
                f"Batch {batch_num}/{total_batches} ({batch_progress:.1f}%) | "
                f"Overall: {processed}/{total_sections} ({overall_progress:.1f}%)\n"
                f"Sections {i+1}-{min(i+self.batch_size, total_sections)} | "
                f"Workers: {self.max_workers}\n"
                f"{'='*80}"
            )

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

            # Save checkpoint after each batch
            if checkpoint:
                self._save_checkpoint(checkpoint, batch_num, processed, failed_sections)

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
            "total_in_database": total_in_db,
            "incomplete_processing": incomplete_processing,
            "single_version_count": single_version_count,
            "multi_version_count": multi_version_count,
            "failed_sections": failed_sections
        }

        duration = (datetime.now() - start_time).total_seconds()
        completion_msg = f"Concurrent Stage 2 complete for {code}: "
        if incomplete_processing:
            completion_msg += f"⚠️ INCOMPLETE ({total_sections:,}/{total_in_db:,} sections) - "
        completion_msg += (
            f"{single_version_count} single-version, "
            f"{multi_version_count} multi-version, "
            f"{len(failed_sections)} failed "
            f"in {duration:.2f}s ({duration/60:.2f} minutes)"
        )
        logger.info(completion_msg)

        # Mark checkpoint as completed
        if checkpoint:
            self._complete_checkpoint(checkpoint)

        return result

    def _get_or_create_checkpoint(self, code: str, total_sections: int, stage: ProcessingStage) -> ProcessingCheckpoint:
        """
        Get existing checkpoint or create new one

        Args:
            code: Code abbreviation
            total_sections: Total sections to process
            stage: Current processing stage

        Returns:
            ProcessingCheckpoint instance
        """
        # Try to load existing checkpoint
        existing = self.db.db['processing_checkpoints'].find_one({
            'code': code,
            'stage': stage,
            'status': {'$in': [CheckpointStatus.IN_PROGRESS, CheckpointStatus.PAUSED]}
        })

        if existing:
            logger.info(f"Resuming from checkpoint: batch {existing.get('current_batch', 0)}")
            return ProcessingCheckpoint(**existing)

        # Create new checkpoint
        checkpoint = ProcessingCheckpoint(
            code=code,
            stage=stage,
            total_sections=total_sections,
            total_batches=(total_sections + self.batch_size - 1) // self.batch_size,
            batch_size=self.batch_size,
            workers=self.max_workers
        )

        # Save to database
        checkpoint_dict = checkpoint.dict()
        self.db.db['processing_checkpoints'].insert_one(checkpoint_dict)

        logger.info(f"Created new checkpoint for {code}")
        return checkpoint

    def _save_checkpoint(self, checkpoint: ProcessingCheckpoint, current_batch: int, processed: int, failed: List[str]) -> None:
        """
        Save checkpoint to database

        Args:
            checkpoint: Checkpoint instance
            current_batch: Current batch number
            processed: Number of processed sections
            failed: List of failed sections
        """
        update = CheckpointUpdate(
            current_batch=current_batch,
            processed_sections=processed,
            failed_sections=failed,
            last_updated=datetime.now()
        )

        self.db.db['processing_checkpoints'].update_one(
            {'code': checkpoint.code, 'stage': checkpoint.stage},
            {'$set': update.dict(exclude_none=True)}
        )

        logger.debug(f"Checkpoint saved: batch {current_batch}, {processed} processed")

    def _complete_checkpoint(self, checkpoint: ProcessingCheckpoint) -> None:
        """
        Mark checkpoint as completed

        Args:
            checkpoint: Checkpoint instance
        """
        update = CheckpointUpdate(
            status=CheckpointStatus.COMPLETED,
            stage2_completed=True,
            completed_at=datetime.now()
        )

        self.db.db['processing_checkpoints'].update_one(
            {'code': checkpoint.code, 'stage': checkpoint.stage},
            {'$set': update.dict(exclude_none=True)}
        )

        logger.info(f"Checkpoint marked as completed for {checkpoint.code}")

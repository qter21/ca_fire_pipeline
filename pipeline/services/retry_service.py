"""
Retry Service
Handles manual retry of failed sections
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from pipeline.core.database import DatabaseManager
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.services.multi_version_handler import MultiVersionHandler
from pipeline.models.section import SectionUpdate
from pipeline.models.failed_section import (
    FailedSection, FailedSectionUpdate, RetryStatus, FailureType, FailureReport
)

logger = logging.getLogger(__name__)


class RetryService:
    """
    Service for retrying failed section extractions
    Supports both single-version and multi-version sections
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize retry service"""
        self.db = db_manager
        self.firecrawl = FirecrawlService()
        self.multi_version_handler = MultiVersionHandler()

    def retry_failed_section(
        self,
        code: str,
        section: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Retry extraction for a single failed section

        Args:
            code: Code abbreviation
            section: Section number
            force: Force retry even if already succeeded

        Returns:
            Retry result dictionary
        """
        # Get failure record
        failure = self.db.db['failed_sections'].find_one({
            'code': code,
            'section': section
        })

        if not failure and not force:
            logger.warning(f"No failure record found for {code} §{section}")
            return {'success': False, 'error': 'No failure record found'}

        # Check retry status
        if failure and failure.get('retry_status') == RetryStatus.SUCCEEDED and not force:
            logger.info(f"{code} §{section} already successfully retried")
            return {'success': True, 'message': 'Already succeeded', 'cached': True}

        # Get section info
        section_doc = self.db.section_contents.find_one({
            'code': code,
            'section': section
        })

        if not section_doc:
            logger.error(f"Section not found in database: {code} §{section}")
            return {'success': False, 'error': 'Section not in database'}

        url = section_doc.get('url')
        is_multi_version = section_doc.get('is_multi_version', False)

        logger.info(f"Retrying {code} §{section} ({'multi-version' if is_multi_version else 'single-version'})")

        # Update retry status
        if failure:
            self._update_failure_status(code, section, RetryStatus.RETRYING)

        try:
            if is_multi_version:
                result = self._retry_multi_version(code, section, url)
            else:
                result = self._retry_single_version(code, section, url)

            # Log retry attempt
            if failure:
                self._log_retry_attempt(code, section, result)

            if result.get('success'):
                # Mark as succeeded
                if failure:
                    self._update_failure_status(
                        code, section, RetryStatus.SUCCEEDED,
                        resolved_at=datetime.now()
                    )
                logger.info(f"✅ Successfully retried {code} §{section}")
            else:
                # Mark as failed again
                if failure:
                    self._update_failure_status(code, section, RetryStatus.FAILED)
                logger.warning(f"❌ Retry failed for {code} §{section}")

            return result

        except Exception as e:
            logger.error(f"Exception during retry of {code} §{section}: {e}")
            if failure:
                self._update_failure_status(code, section, RetryStatus.FAILED)
                self._log_retry_attempt(code, section, {
                    'success': False,
                    'error': str(e)
                })
            return {'success': False, 'error': str(e)}

    def _retry_single_version(
        self,
        code: str,
        section: str,
        url: str
    ) -> Dict[str, Any]:
        """Retry single-version section extraction"""
        try:
            # Scrape with Firecrawl
            result = self.firecrawl.scrape_url(url)

            if not result or not result.get('markdown'):
                return {'success': False, 'error': 'No markdown content'}

            markdown = result['markdown']

            # Parse content
            content, legislative_history = ContentParser.extract_section_content(
                markdown, section
            )

            if not content:
                return {
                    'success': False,
                    'error': 'No content extracted',
                    'may_be_repealed': True
                }

            # Update database
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
                url=url
            )

            self.db.update_section(code, section, update)

            return {
                'success': True,
                'content_length': len(content),
                'has_legislative_history': bool(legislative_history)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _retry_multi_version(
        self,
        code: str,
        section: str,
        url: str
    ) -> Dict[str, Any]:
        """Retry multi-version section extraction"""
        try:
            # Extract all versions
            result = self.multi_version_handler.extract_all_versions(code, section)

            versions = result.get('versions', [])

            if not versions:
                return {'success': False, 'error': 'No versions extracted'}

            # Update database
            self.db.db['section_contents'].update_one(
                {'code': code, 'section': section},
                {'$set': {
                    'versions': versions,
                    'is_multi_version': True,
                    'has_content': False,
                    'url': url
                }}
            )

            return {
                'success': True,
                'version_count': len(versions),
                'total_content_length': sum(len(v.get('content', '')) for v in versions)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def retry_all_failed_sections(
        self,
        code: str,
        max_retries: Optional[int] = None,
        failure_types: Optional[List[FailureType]] = None
    ) -> Dict[str, Any]:
        """
        Retry all failed sections for a code

        Args:
            code: Code abbreviation
            max_retries: Maximum sections to retry (None = all)
            failure_types: Only retry specific failure types

        Returns:
            Summary of retry results
        """
        query = {'code': code, 'retry_status': RetryStatus.PENDING}

        if failure_types:
            query['failure_type'] = {'$in': failure_types}

        failed_sections = list(self.db.db['failed_sections'].find(query))

        if max_retries:
            failed_sections = failed_sections[:max_retries]

        logger.info(f"Retrying {len(failed_sections)} failed sections for {code}")

        results = {
            'total': len(failed_sections),
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }

        for failure in failed_sections:
            section = failure['section']
            result = self.retry_failed_section(code, section)

            if result.get('success'):
                results['succeeded'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'section': section,
                    'error': result.get('error')
                })

        logger.info(
            f"Retry complete: {results['succeeded']}/{results['total']} succeeded, "
            f"{results['failed']} failed"
        )

        return results

    def mark_as_abandoned(
        self,
        code: str,
        section: str,
        reason: str
    ) -> None:
        """
        Mark a failed section as abandoned (unretrievable)

        Args:
            code: Code abbreviation
            section: Section number
            reason: Reason for abandonment (e.g., "repealed", "does not exist")
        """
        self._update_failure_status(
            code, section, RetryStatus.ABANDONED,
            notes=reason,
            resolved_at=datetime.now()
        )

        # Also mark in section_contents
        self.db.db['section_contents'].update_one(
            {'code': code, 'section': section},
            {'$set': {
                'has_content': False,
                'notes': f'Abandoned: {reason}'
            }}
        )

        logger.info(f"Marked {code} §{section} as abandoned: {reason}")

    def generate_failure_report(self, code: str) -> FailureReport:
        """
        Generate comprehensive failure report for a code

        Args:
            code: Code abbreviation

        Returns:
            FailureReport instance
        """
        # Get all failures
        failures = list(self.db.db['failed_sections'].find({'code': code}))

        # Get section counts
        total = self.db.section_contents.count_documents({'code': code})
        successful = self.db.section_contents.count_documents({
            'code': code,
            '$or': [
                {'has_content': True},
                {'versions.0': {'$exists': True}}
            ]
        })

        # Count by type
        failures_by_type = {}
        for f in failures:
            ftype = f.get('failure_type', 'unknown')
            failures_by_type[ftype] = failures_by_type.get(ftype, 0) + 1

        # Count by stage
        failures_by_stage = {}
        for f in failures:
            stage = f.get('stage', 'unknown')
            failures_by_stage[stage] = failures_by_stage.get(stage, 0) + 1

        # Count by retry status
        pending_retry = sum(1 for f in failures if f.get('retry_status') == RetryStatus.PENDING)
        retry_succeeded = sum(1 for f in failures if f.get('retry_status') == RetryStatus.SUCCEEDED)
        retry_failed = sum(1 for f in failures if f.get('retry_status') == RetryStatus.FAILED)
        abandoned = sum(1 for f in failures if f.get('retry_status') == RetryStatus.ABANDONED)

        # Build failed section list
        failed_section_list = []
        for f in failures:
            failed_section_list.append({
                'section': f['section'],
                'url': f.get('url', ''),
                'failure_type': f.get('failure_type'),
                'retry_status': f.get('retry_status'),
                'error_message': f.get('error_message', '')[:200],  # Truncate
                'failed_at': f.get('failed_at')
            })

        report = FailureReport(
            code=code,
            total_sections=total,
            successful_sections=successful,
            failed_sections=len(failures),
            completion_rate=(successful / total * 100) if total > 0 else 0,
            failures_by_type=failures_by_type,
            failures_by_stage=failures_by_stage,
            failed_section_list=failed_section_list,
            pending_retry=pending_retry,
            retry_succeeded=retry_succeeded,
            retry_failed=retry_failed,
            abandoned=abandoned
        )

        # Save to MongoDB
        report_dict = report.dict()
        self.db.db['failure_reports'].update_one(
            {'code': code},
            {'$set': report_dict},
            upsert=True
        )

        logger.info(f"Generated failure report for {code}: {len(failures)} failures")

        return report

    def _update_failure_status(
        self,
        code: str,
        section: str,
        status: RetryStatus,
        notes: Optional[str] = None,
        resolved_at: Optional[datetime] = None
    ) -> None:
        """Update failure record status"""
        update = {
            'retry_status': status,
            'last_retry_at': datetime.now()
        }

        if status in [RetryStatus.SUCCEEDED, RetryStatus.ABANDONED]:
            update['retry_count'] = self.db.db['failed_sections'].find_one(
                {'code': code, 'section': section}
            ).get('retry_count', 0) + 1

        if notes:
            update['notes'] = notes

        if resolved_at:
            update['resolved_at'] = resolved_at

        self.db.db['failed_sections'].update_one(
            {'code': code, 'section': section},
            {'$set': update}
        )

    def _log_retry_attempt(
        self,
        code: str,
        section: str,
        result: Dict[str, Any]
    ) -> None:
        """Log a retry attempt to the failure record"""
        attempt = {
            'timestamp': datetime.now(),
            'success': result.get('success', False),
            'error': result.get('error'),
            'details': {k: v for k, v in result.items() if k not in ['success', 'error']}
        }

        self.db.db['failed_sections'].update_one(
            {'code': code, 'section': section},
            {
                '$push': {'retry_attempts': attempt},
                '$inc': {'retry_count': 1}
            }
        )

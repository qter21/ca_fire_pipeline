"""
Reconciliation Service
Automatically detects missing sections and retries with adaptive concurrency
Logs failures to MongoDB for tracking
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from pipeline.core.database import DatabaseManager
from pipeline.services.firecrawl_concurrent import ConcurrentFirecrawlService
from pipeline.services.content_parser import ContentParser
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.models.section import SectionUpdate

logger = logging.getLogger(__name__)


class ReconciliationService:
    """
    Service for detecting and fixing missing/incomplete sections

    Implements adaptive retry strategy:
    1. Check for missing sections
    2. Retry with reduced concurrency (avoid rate limits)
    3. Log permanent failures to MongoDB
    4. Generate reconciliation report
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize reconciliation service"""
        self.db = db_manager

    def reconcile_code(
        self,
        code: str,
        max_retry_attempts: int = 2,
        initial_workers: int = 10,
        min_workers: int = 5
    ) -> Dict:
        """
        Reconcile a code by finding and retrying missing sections

        Args:
            code: Code abbreviation
            max_retry_attempts: Maximum retry attempts
            initial_workers: Initial concurrent workers
            min_workers: Minimum concurrent workers (fallback)

        Returns:
            Reconciliation report dictionary
        """
        logger.info(f"Starting reconciliation for {code}")

        report = {
            'code': code,
            'started_at': datetime.now().isoformat(),
            'attempts': [],
            'final_status': {}
        }

        # Initial assessment
        initial_status = self._assess_code_completeness(code)
        report['initial_status'] = initial_status

        logger.info(
            f"Initial: {initial_status['complete']}/{initial_status['total']} "
            f"({initial_status['completion_rate']:.2f}%)"
        )

        # If 100% complete, no retry needed
        if initial_status['completion_rate'] >= 100.0:
            logger.info(f"{code} is 100% complete, no reconciliation needed")
            report['final_status'] = initial_status
            report['finished_at'] = datetime.now().isoformat()
            report['success'] = True
            return report

        # Retry missing sections
        current_workers = initial_workers

        for attempt in range(1, max_retry_attempts + 1):
            logger.info(f"Retry attempt {attempt}/{max_retry_attempts} with {current_workers} workers")

            # Get missing sections
            missing_sections = self._get_missing_sections(code)

            if not missing_sections:
                logger.info("No missing sections found")
                break

            # Retry with current worker count
            attempt_result = self._retry_missing_sections(
                code,
                missing_sections,
                workers=current_workers
            )

            report['attempts'].append({
                'attempt': attempt,
                'workers': current_workers,
                'missing_before': len(missing_sections),
                'success': attempt_result['success'],
                'failed': attempt_result['failed'],
                'duration': attempt_result['duration']
            })

            # Check if complete now
            current_status = self._assess_code_completeness(code)

            if current_status['completion_rate'] >= 100.0:
                logger.info(f"Reconciliation successful after attempt {attempt}")
                report['final_status'] = current_status
                report['success'] = True
                break

            # Reduce workers for next attempt (avoid rate limits)
            current_workers = max(min_workers, current_workers // 2)

        # Final assessment
        if 'final_status' not in report:
            report['final_status'] = self._assess_code_completeness(code)
            report['success'] = report['final_status']['completion_rate'] >= 100.0

        # Log permanent failures to MongoDB
        if not report['success']:
            self._log_failures_to_db(code, report)

        report['finished_at'] = datetime.now().isoformat()

        return report

    def _assess_code_completeness(self, code: str) -> Dict:
        """
        Assess completeness of a code

        Returns:
            Dictionary with completeness metrics
        """
        total = self.db.section_contents.count_documents({'code': code})

        # Count complete sections (has content OR has versions)
        single_complete = self.db.section_contents.count_documents({
            'code': code,
            'has_content': True,
            'is_multi_version': False
        })

        multi_complete = self.db.section_contents.count_documents({
            'code': code,
            'versions': {'$ne': None, '$exists': True}
        })

        complete = single_complete + multi_complete
        completion_rate = (complete / total * 100) if total > 0 else 0

        return {
            'total': total,
            'single_version': single_complete,
            'multi_version': multi_complete,
            'complete': complete,
            'missing': total - complete,
            'completion_rate': completion_rate
        }

    def _get_missing_sections(self, code: str) -> List[Dict]:
        """
        Get sections that are missing content or versions

        Returns:
            List of section documents
        """
        # Find sections that don't have content AND don't have versions
        missing = list(self.db.section_contents.find({
            'code': code,
            'has_content': False,
            '$or': [
                {'versions': None},
                {'versions': {'$exists': False}}
            ]
        }, {'section': 1, 'url': 1}))

        return missing

    def _retry_missing_sections(
        self,
        code: str,
        missing_sections: List[Dict],
        workers: int = 10
    ) -> Dict:
        """
        Retry extraction for missing sections

        Args:
            code: Code abbreviation
            missing_sections: List of missing section documents
            workers: Number of concurrent workers

        Returns:
            Retry result dictionary
        """
        start_time = datetime.now()

        if not missing_sections:
            return {
                'success': 0,
                'failed': 0,
                'duration': 0
            }

        logger.info(f"Retrying {len(missing_sections)} missing sections with {workers} workers")

        # Extract URLs
        urls = [sec['url'] for sec in missing_sections]

        # Use concurrent service
        concurrent_service = ConcurrentFirecrawlService(max_workers=workers)
        results = concurrent_service.batch_scrape_concurrent(urls, max_workers=workers)

        # Process results
        success_count = 0
        failed_count = 0

        for i, result in enumerate(results):
            section_doc = missing_sections[i]
            section_num = section_doc['section']

            if result.get('success') and result.get('data'):
                markdown = result['data'].get('markdown', '')
                source_url = result['data'].get('metadata', {}).get('url', section_doc['url'])

                # Check if multi-version
                is_multi = ContentParser.is_multi_version(source_url, markdown)

                if not is_multi:
                    # Extract content
                    content, history = ContentParser.extract_section_content(markdown, section_num)

                    if content:
                        # Update section
                        update = SectionUpdate(
                            content=content,
                            raw_content=content,
                            legislative_history=history,
                            raw_legislative_history=history,
                            has_content=True,
                            content_cleaned=False,
                            content_length=len(content),
                            raw_content_length=len(content),
                            has_legislative_history=bool(history),
                            is_multi_version=False,
                            is_current=True,
                            version_number=1,
                            url=source_url
                        )

                        self.db.update_section(code, section_num, update)
                        success_count += 1
                else:
                    # Multi-version - flag it
                    update = SectionUpdate(is_multi_version=True, url=source_url)
                    self.db.update_section(code, section_num, update)
                    success_count += 1
            else:
                failed_count += 1

        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Retry complete: {success_count} success, {failed_count} failed in {duration:.2f}s")

        return {
            'success': success_count,
            'failed': failed_count,
            'duration': duration
        }

    def _log_failures_to_db(self, code: str, report: Dict) -> None:
        """
        Log permanent failures to MongoDB for tracking

        Args:
            code: Code abbreviation
            report: Reconciliation report
        """
        # Get still-missing sections
        missing_sections = self._get_missing_sections(code)

        if not missing_sections:
            return

        # Create failure log document
        failure_log = {
            'code': code,
            'type': 'reconciliation_failure',
            'timestamp': datetime.now(),
            'total_sections': report['final_status']['total'],
            'missing_count': len(missing_sections),
            'missing_sections': [sec['section'] for sec in missing_sections],
            'attempts': report['attempts'],
            'completion_rate': report['final_status']['completion_rate']
        }

        # Save to processing_status collection
        self.db.processing_status.insert_one(failure_log)

        logger.warning(
            f"Logged {len(missing_sections)} permanent failures for {code} "
            f"to processing_status collection"
        )

    def generate_reconciliation_report(self, code: str) -> str:
        """
        Generate human-readable reconciliation report

        Args:
            code: Code abbreviation

        Returns:
            Report string
        """
        status = self._assess_code_completeness(code)

        report_lines = [
            "=" * 80,
            f"Reconciliation Report - {code}",
            "=" * 80,
            "",
            f"Total sections: {status['total']:,}",
            f"Complete: {status['complete']:,} ({status['completion_rate']:.2f}%)",
            f"  Single-version: {status['single_version']:,}",
            f"  Multi-version: {status['multi_version']}",
            f"Missing: {status['missing']}",
            ""
        ]

        if status['completion_rate'] >= 100.0:
            report_lines.append("✅ STATUS: 100% COMPLETE")
        else:
            report_lines.append(f"⚠️  STATUS: {status['completion_rate']:.2f}% COMPLETE")
            report_lines.append(f"   {status['missing']} sections need attention")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)


def reconcile_all_codes(db_manager: DatabaseManager) -> Dict:
    """
    Reconcile all codes in the database

    Args:
        db_manager: Database manager instance

    Returns:
        Summary report for all codes
    """
    service = ReconciliationService(db_manager)

    # Get all codes
    code_docs = db_manager.code_architectures.find({}, {'code': 1})
    codes = [doc['code'] for doc in code_docs]

    summary = {
        'timestamp': datetime.now().isoformat(),
        'codes_processed': [],
        'total_sections': 0,
        'total_complete': 0,
        'codes_100_percent': 0
    }

    print("=" * 80)
    print("RECONCILING ALL CODES")
    print("=" * 80)
    print()

    for code in codes:
        print(f"Reconciling {code}...")
        report = service.reconcile_code(code, max_retry_attempts=2)

        summary['codes_processed'].append({
            'code': code,
            'completion_rate': report['final_status']['completion_rate'],
            'success': report['success']
        })

        summary['total_sections'] += report['final_status']['total']
        summary['total_complete'] += report['final_status']['complete']

        if report['success']:
            summary['codes_100_percent'] += 1

        # Print report
        print(service.generate_reconciliation_report(code))
        print()

    # Overall summary
    overall_rate = (summary['total_complete'] / summary['total_sections'] * 100) if summary['total_sections'] > 0 else 0

    print("=" * 80)
    print("RECONCILIATION SUMMARY")
    print("=" * 80)
    print(f"Codes processed: {len(codes)}")
    print(f"Codes at 100%: {summary['codes_100_percent']}/{len(codes)}")
    print(f"Total sections: {summary['total_sections']:,}")
    print(f"Total complete: {summary['total_complete']:,}")
    print(f"Overall rate: {overall_rate:.2f}%")
    print("=" * 80)

    return summary

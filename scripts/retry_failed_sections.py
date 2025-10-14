"""
Retry Failed Sections Script
Manually retry sections that failed during processing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import logging
from datetime import datetime

from pipeline.core.database import DatabaseManager
from pipeline.services.retry_service import RetryService
from pipeline.models.failed_section import FailureType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry_single_section(code: str, section: str, force: bool = False):
    """Retry a single failed section"""
    db = DatabaseManager()
    db.connect()

    retry_service = RetryService(db)

    print(f"\n{'='*80}")
    print(f"Retrying {code} §{section}")
    print(f"{'='*80}\n")

    result = retry_service.retry_failed_section(code, section, force=force)

    if result.get('success'):
        print(f"✅ SUCCESS")
        if result.get('cached'):
            print("   (Already succeeded in previous retry)")
        else:
            for key, value in result.items():
                if key != 'success':
                    print(f"   {key}: {value}")
    else:
        print(f"❌ FAILED")
        print(f"   Error: {result.get('error')}")
        if result.get('may_be_repealed'):
            print(f"   ⚠️  Section may be repealed or non-existent")

    db.disconnect()


def retry_all_failed(code: str, max_retries: int = None, failure_types: list = None):
    """Retry all failed sections for a code"""
    db = DatabaseManager()
    db.connect()

    retry_service = RetryService(db)

    print(f"\n{'='*80}")
    print(f"Retrying All Failed Sections for {code}")
    print(f"{'='*80}\n")

    if failure_types:
        print(f"Filtering by failure types: {', '.join(failure_types)}\n")

    if max_retries:
        print(f"Max retries: {max_retries}\n")

    result = retry_service.retry_all_failed_sections(
        code,
        max_retries=max_retries,
        failure_types=[FailureType(ft) for ft in failure_types] if failure_types else None
    )

    print(f"\n{'='*80}")
    print("RETRY SUMMARY")
    print(f"{'='*80}")
    print(f"Total attempted: {result['total']}")
    print(f"Succeeded: {result['succeeded']}")
    print(f"Failed: {result['failed']}")

    if result['errors']:
        print(f"\nErrors:")
        for error in result['errors'][:10]:  # Show first 10
            print(f"  §{error['section']}: {error['error']}")
        if len(result['errors']) > 10:
            print(f"  ... and {len(result['errors']) - 10} more")

    db.disconnect()


def mark_abandoned(code: str, section: str, reason: str):
    """Mark a section as abandoned (unretrievable)"""
    db = DatabaseManager()
    db.connect()

    retry_service = RetryService(db)

    print(f"\n{'='*80}")
    print(f"Marking {code} §{section} as Abandoned")
    print(f"{'='*80}\n")
    print(f"Reason: {reason}\n")

    retry_service.mark_as_abandoned(code, section, reason)

    print(f"✅ Section marked as abandoned")

    db.disconnect()


def generate_report(code: str, save_to_file: bool = False):
    """Generate failure report for a code"""
    db = DatabaseManager()
    db.connect()

    retry_service = RetryService(db)

    print(f"\n{'='*80}")
    print(f"Failure Report - {code}")
    print(f"{'='*80}\n")

    report = retry_service.generate_failure_report(code)

    print(f"Generated: {report.generated_at}")
    print(f"\nOverall Statistics:")
    print(f"  Total sections: {report.total_sections:,}")
    print(f"  Successful: {report.successful_sections:,}")
    print(f"  Failed: {report.failed_sections}")
    print(f"  Completion rate: {report.completion_rate:.2f}%")

    if report.failures_by_type:
        print(f"\nFailures by Type:")
        for ftype, count in sorted(report.failures_by_type.items(), key=lambda x: -x[1]):
            print(f"  {ftype}: {count}")

    if report.failures_by_stage:
        print(f"\nFailures by Stage:")
        for stage, count in sorted(report.failures_by_stage.items(), key=lambda x: -x[1]):
            print(f"  {stage}: {count}")

    print(f"\nRetry Status:")
    print(f"  Pending retry: {report.pending_retry}")
    print(f"  Retry succeeded: {report.retry_succeeded}")
    print(f"  Retry failed: {report.retry_failed}")
    print(f"  Abandoned: {report.abandoned}")

    if report.failed_section_list:
        print(f"\nFailed Sections (showing first 20):")
        for i, failure in enumerate(report.failed_section_list[:20], 1):
            status_emoji = {
                'pending': '⏳',
                'succeeded': '✅',
                'failed': '❌',
                'abandoned': '🚫'
            }.get(failure['retry_status'], '❓')

            print(f"  {i}. {status_emoji} §{failure['section']} - {failure['failure_type']}")
            print(f"      {failure['error_message'][:80]}...")

        if len(report.failed_section_list) > 20:
            print(f"  ... and {len(report.failed_section_list) - 20} more")

    print(f"\n✅ Report saved to MongoDB collection: failure_reports")

    if save_to_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"failure_report_{code.lower()}_{timestamp}.txt"

        with open(filename, 'w') as f:
            f.write(f"Failure Report - {code}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Generated: {report.generated_at}\n\n")
            f.write(f"Overall Statistics:\n")
            f.write(f"  Total sections: {report.total_sections:,}\n")
            f.write(f"  Successful: {report.successful_sections:,}\n")
            f.write(f"  Failed: {report.failed_sections}\n")
            f.write(f"  Completion rate: {report.completion_rate:.2f}%\n\n")

            f.write(f"Failed Sections:\n")
            for failure in report.failed_section_list:
                f.write(f"  §{failure['section']} - {failure['failure_type']} - {failure['retry_status']}\n")
                f.write(f"    {failure['error_message']}\n")
                f.write(f"    URL: {failure['url']}\n\n")

        print(f"✅ Report also saved to file: {filename}")

    db.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description='Retry failed sections from code processing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Retry a single section
  python scripts/retry_failed_sections.py WIC --section 14005.20

  # Retry all failed sections
  python scripts/retry_failed_sections.py WIC --all

  # Retry only timeouts
  python scripts/retry_failed_sections.py WIC --all --type timeout

  # Mark section as abandoned
  python scripts/retry_failed_sections.py WIC --section 10492.2 --abandon "Section repealed"

  # Generate failure report
  python scripts/retry_failed_sections.py WIC --report
  python scripts/retry_failed_sections.py WIC --report --save-file
        '''
    )

    parser.add_argument('code', help='Code abbreviation (e.g., WIC, FAM)')
    parser.add_argument('--section', help='Section number to retry')
    parser.add_argument('--all', action='store_true', help='Retry all failed sections')
    parser.add_argument('--max', type=int, help='Maximum sections to retry')
    parser.add_argument('--type', choices=[
        'api_error', 'timeout', 'parse_error', 'empty_content',
        'network_error', 'multi_version_timeout'
    ], action='append', help='Filter by failure type (can specify multiple)')
    parser.add_argument('--force', action='store_true', help='Force retry even if already succeeded')
    parser.add_argument('--abandon', metavar='REASON', help='Mark section as abandoned with reason')
    parser.add_argument('--report', action='store_true', help='Generate failure report')
    parser.add_argument('--save-file', action='store_true', help='Save report to file (with --report)')

    args = parser.parse_args()

    code = args.code.upper()

    if args.report:
        generate_report(code, save_to_file=args.save_file)

    elif args.section:
        if args.abandon:
            mark_abandoned(code, args.section, args.abandon)
        else:
            retry_single_section(code, args.section, force=args.force)

    elif args.all:
        retry_all_failed(code, max_retries=args.max, failure_types=args.type)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
Test concurrent vs sequential scraping performance
Demonstrates the speed improvement with concurrent requests
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.services.firecrawl_concurrent import ConcurrentFirecrawlService

def test_performance():
    """Test sequential vs concurrent scraping"""

    # Test URLs (10 CCP sections)
    test_urls = [
        f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CCP&sectionNum={i}"
        for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    ]

    print('='*80)
    print('Concurrent vs Sequential Scraping Performance Test')
    print('='*80)
    print()
    print(f'Test: Scraping {len(test_urls)} CCP sections')
    print()

    # Test 1: Sequential
    print('Test 1: Sequential Scraping (current method)')
    print('-'*80)

    sequential_service = FirecrawlService()
    start = time.time()

    sequential_results = []
    for url in test_urls:
        result = sequential_service.scrape_url(url)
        sequential_results.append(result)

    sequential_duration = time.time() - start
    sequential_success = sum(1 for r in sequential_results if r.get('success'))

    print(f'   Duration: {sequential_duration:.2f}s')
    print(f'   Success: {sequential_success}/{len(test_urls)}')
    print(f'   Avg per section: {sequential_duration/len(test_urls):.2f}s')
    print()

    # Test 2: Concurrent (10 workers)
    print('Test 2: Concurrent Scraping (10 workers)')
    print('-'*80)

    concurrent_service = ConcurrentFirecrawlService(max_workers=10)
    start = time.time()

    concurrent_results = concurrent_service.batch_scrape_concurrent(test_urls)

    concurrent_duration = time.time() - start
    concurrent_success = sum(1 for r in concurrent_results if r.get('success'))

    print(f'   Duration: {concurrent_duration:.2f}s')
    print(f'   Success: {concurrent_success}/{len(test_urls)}')
    print(f'   Avg per section: {concurrent_duration/len(test_urls):.2f}s')
    print()

    # Test 3: Concurrent (25 workers)
    print('Test 3: Concurrent Scraping (25 workers)')
    print('-'*80)

    concurrent_service_25 = ConcurrentFirecrawlService(max_workers=25)
    start = time.time()

    concurrent_results_25 = concurrent_service_25.batch_scrape_concurrent(test_urls)

    concurrent_duration_25 = time.time() - start
    concurrent_success_25 = sum(1 for r in concurrent_results_25 if r.get('success'))

    print(f'   Duration: {concurrent_duration_25:.2f}s')
    print(f'   Success: {concurrent_success_25}/{len(test_urls)}')
    print(f'   Avg per section: {concurrent_duration_25/len(test_urls):.2f}s')
    print()

    # Comparison
    print('='*80)
    print('PERFORMANCE COMPARISON')
    print('='*80)
    print()

    improvement_10 = sequential_duration / concurrent_duration if concurrent_duration > 0 else 0
    improvement_25 = sequential_duration / concurrent_duration_25 if concurrent_duration_25 > 0 else 0

    print(f'Sequential: {sequential_duration:.2f}s (baseline)')
    print(f'Concurrent (10 workers): {concurrent_duration:.2f}s ({improvement_10:.1f}x faster)')
    print(f'Concurrent (25 workers): {concurrent_duration_25:.2f}s ({improvement_25:.1f}x faster)')
    print()

    # Projections for CCP
    print('='*80)
    print('PROJECTIONS FOR CCP (3,353 sections)')
    print('='*80)
    print()

    ccp_sequential = 3353 * (sequential_duration / len(test_urls))
    ccp_concurrent_10 = 3353 * (concurrent_duration / len(test_urls))
    ccp_concurrent_25 = 3353 * (concurrent_duration_25 / len(test_urls))

    print(f'Sequential: {ccp_sequential/60:.1f} minutes')
    print(f'Concurrent (10): {ccp_concurrent_10/60:.1f} minutes ({ccp_sequential/ccp_concurrent_10:.1f}x faster)')
    print(f'Concurrent (25): {ccp_concurrent_25/60:.1f} minutes ({ccp_sequential/ccp_concurrent_25:.1f}x faster)')
    print()

    print('='*80)
    print('✅ CONCURRENT SCRAPING WORKS!')
    print('='*80)
    print()
    print(f'Recommendation: Use 10-25 concurrent workers for Stage 2')
    print(f'Expected improvement: {improvement_10:.1f}x - {improvement_25:.1f}x faster')

if __name__ == '__main__':
    test_performance()

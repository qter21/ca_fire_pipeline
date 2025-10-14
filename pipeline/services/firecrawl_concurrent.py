"""
Concurrent Firecrawl Service
Optimized for high-throughput scraping using concurrent requests
"""

import logging
import time
import asyncio
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from firecrawl import FirecrawlApp
from pipeline.core.config import get_settings

logger = logging.getLogger(__name__)


class ConcurrentFirecrawlService:
    """Concurrent version of Firecrawl service for high-throughput scraping"""

    def __init__(self, api_key: Optional[str] = None, max_workers: int = 10, timeout: Optional[int] = None):
        """
        Initialize concurrent Firecrawl client

        Args:
            api_key: Firecrawl API key
            max_workers: Maximum concurrent workers (default: 10, max: 50)
            timeout: Request timeout in seconds (default from config)
        """
        settings = get_settings()
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.max_workers = min(max_workers, 50)  # Cap at API limit
        self.timeout = timeout or settings.FIRECRAWL_TIMEOUT
        logger.info(f"Concurrent Firecrawl service initialized with {self.max_workers} workers, {self.timeout}s timeout")

    def scrape_url_with_retry(
        self,
        url: str,
        formats: List[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Scrape a single URL with retry logic (thread-safe)

        Args:
            url: URL to scrape
            formats: Output formats
            max_retries: Maximum retry attempts

        Returns:
            Scrape result
        """
        # Create new FirecrawlApp instance per thread (thread-safe)
        app = FirecrawlApp(api_key=self.api_key)
        formats = formats or ["markdown", "html"]
        params = {"formats": formats}

        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt
                    logger.debug(f"Retry {attempt + 1}/{max_retries} for {url} after {wait_time}s")
                    time.sleep(wait_time)

                result = app.scrape_url(url, params=params)

                return {
                    "success": True,
                    "url": url,
                    "data": result,
                    "attempts": attempt + 1
                }

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Check if retriable
                is_retriable = any(keyword in error_msg.lower() for keyword in [
                    'ssl', 'connection', 'timeout', 'network', 'max retries',
                    'expecting value', 'json', 'parse', 'invalid', 'rate limit'
                ])

                if attempt < max_retries - 1 and is_retriable:
                    logger.warning(f"Retriable error on attempt {attempt + 1}: {error_msg[:100]}")
                    continue
                else:
                    break

        logger.error(f"Failed after {max_retries} attempts: {url}")
        return {
            "success": False,
            "url": url,
            "error": str(last_error),
            "attempts": max_retries
        }

    def batch_scrape_concurrent(
        self,
        urls: List[str],
        formats: List[str] = None,
        max_workers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently with timeout handling

        Args:
            urls: List of URLs to scrape
            formats: Output formats
            max_workers: Override default max_workers

        Returns:
            List of scrape results (in same order as input URLs)
        """
        if not urls:
            return []

        workers = max_workers or self.max_workers
        logger.info(f"Concurrent batch scraping {len(urls)} URLs with {workers} workers")

        start_time = time.time()

        # Use ThreadPoolExecutor for concurrent scraping
        results_dict = {}
        timeout_count = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self.scrape_url_with_retry, url, formats): (i, url)
                for i, url in enumerate(urls)
            }

            # Track pending futures
            pending = set(future_to_url.keys())
            completed = 0

            # Process with timeout
            while pending:
                # Wait for any future to complete, with timeout
                done, pending = wait(pending, timeout=self.timeout, return_when=FIRST_COMPLETED)

                # Process completed futures
                for future in done:
                    i, url = future_to_url[future]
                    try:
                        result = future.result(timeout=1)  # Quick timeout for already-done future
                        results_dict[i] = result
                        completed += 1

                        if completed % 5 == 0 or completed == len(urls):
                            elapsed = time.time() - start_time
                            rate = completed / elapsed if elapsed > 0 else 0
                            remaining = len(urls) - completed
                            eta_seconds = remaining / rate if rate > 0 else 0
                            eta_min = eta_seconds / 60

                            success_count = sum(1 for i in results_dict.values() if i.get("success"))
                            success_rate = (success_count / completed * 100) if completed > 0 else 0

                            logger.info(
                                f"Progress: {completed}/{len(urls)} ({completed/len(urls)*100:.1f}%) | "
                                f"Rate: {rate:.1f}/s | Success: {success_rate:.1f}% | "
                                f"ETA: {eta_min:.1f}min"
                            )

                    except Exception as e:
                        logger.error(f"Future failed for {url}: {e}")
                        results_dict[i] = {
                            "success": False,
                            "url": url,
                            "error": str(e)
                        }
                        completed += 1

                # Handle hung futures (still pending after timeout)
                if pending:
                    # Check if any futures have been pending for too long
                    current_time = time.time()
                    for future in list(pending):
                        future_age = current_time - start_time
                        i, url = future_to_url[future]

                        # If a future has been pending for > 2x timeout, cancel it
                        if future_age > (self.timeout * 2):
                            logger.warning(f"Canceling hung request after {future_age:.1f}s: {url}")
                            future.cancel()
                            pending.remove(future)
                            results_dict[i] = {
                                "success": False,
                                "url": url,
                                "error": f"Request timeout after {future_age:.1f}s"
                            }
                            timeout_count += 1
                            completed += 1

        # Return results in original order
        results = [results_dict.get(i, {
            "success": False,
            "url": urls[i],
            "error": "Unknown error"
        }) for i in range(len(urls))]

        duration = time.time() - start_time
        successful = sum(1 for r in results if r.get("success"))
        logger.info(f"Concurrent batch complete: {successful}/{len(urls)} successful in {duration:.2f}s")

        if timeout_count > 0:
            logger.warning(f"Canceled {timeout_count} hung requests")

        return results


# Async version (alternative implementation using asyncio)
class AsyncFirecrawlService:
    """Async version using asyncio (alternative to ThreadPoolExecutor)"""

    def __init__(self, api_key: Optional[str] = None, max_concurrent: int = 10):
        settings = get_settings()
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.max_concurrent = min(max_concurrent, 50)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        logger.info(f"Async Firecrawl service initialized with {self.max_concurrent} concurrent")

    async def scrape_url_async(self, url: str, formats: List[str] = None) -> Dict[str, Any]:
        """Async scrape with semaphore for rate limiting"""
        async with self.semaphore:
            # Note: FirecrawlApp is sync, so we'd need to use run_in_executor
            # For now, ThreadPoolExecutor version above is simpler
            pass

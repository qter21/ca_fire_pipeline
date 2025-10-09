"""
Firecrawl Service Client
Wrapper around Firecrawl API for California Legal Codes scraping
"""

import logging
import time
from typing import List, Dict, Optional, Any
from firecrawl import FirecrawlApp
from pipeline.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirecrawlService:
    """Service for interacting with Firecrawl API"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Firecrawl client"""
        self.api_key = api_key or settings.FIRECRAWL_API_KEY
        self.app = FirecrawlApp(api_key=self.api_key)
        logger.info("Firecrawl service initialized")

    def scrape_url(
        self,
        url: str,
        formats: List[str] = None,
        max_age: Optional[int] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Scrape a single URL with retry logic

        Args:
            url: URL to scrape
            formats: Output formats (markdown, html, links, etc.)
            max_age: Cache max age in milliseconds
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Scrape result with content and metadata
        """
        formats = formats or ["markdown", "html"]
        params = {"formats": formats}

        if max_age is not None:
            params["maxAge"] = max_age

        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff: 2, 4, 8 seconds
                    wait_time = 2 ** attempt
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {url} after {wait_time}s")
                    time.sleep(wait_time)

                logger.debug(f"Scraping URL (attempt {attempt + 1}): {url}")
                result = self.app.scrape_url(url, params=params)

                logger.info(f"Successfully scraped: {url}")
                return {
                    "success": True,
                    "url": url,
                    "data": result,
                    "attempts": attempt + 1
                }

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Check if it's a retriable error
                is_retriable = any(keyword in error_msg.lower() for keyword in [
                    'ssl', 'connection', 'timeout', 'network', 'max retries'
                ])

                if attempt < max_retries - 1 and is_retriable:
                    logger.warning(f"Retriable error on attempt {attempt + 1} for {url}: {error_msg}")
                else:
                    logger.error(f"Error scraping {url} after {attempt + 1} attempts: {error_msg}")
                    break

        return {
            "success": False,
            "url": url,
            "error": str(last_error),
            "attempts": max_retries
        }

    def batch_scrape(
        self,
        urls: List[str],
        formats: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in batch

        Args:
            urls: List of URLs to scrape
            formats: Output formats

        Returns:
            List of scrape results
        """
        try:
            formats = formats or ["markdown", "html"]
            logger.info(f"Batch scraping {len(urls)} URLs")

            # Firecrawl batch scrape
            results = []
            for url in urls:
                result = self.scrape_url(url, formats=formats)
                results.append(result)

            successful = sum(1 for r in results if r.get("success"))
            logger.info(f"Batch scrape complete: {successful}/{len(urls)} successful")

            return results

        except Exception as e:
            logger.error(f"Batch scrape error: {e}")
            return []

    def scrape_with_actions(
        self,
        url: str,
        actions: List[Dict[str, Any]],
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape URL with page interactions (for multi-version sections)

        Args:
            url: URL to scrape
            actions: List of actions to perform (click, wait, etc.)
            formats: Output formats

        Returns:
            Scrape result after performing actions
        """
        try:
            formats = formats or ["markdown", "html"]
            params = {
                "formats": formats,
                "actions": actions
            }

            logger.info(f"Scraping with actions: {url}")
            result = self.app.scrape_url(url, params=params)

            return {
                "success": True,
                "url": url,
                "data": result
            }

        except Exception as e:
            logger.error(f"Error scraping with actions {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

    def extract_structured_data(
        self,
        url: str,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured data using schema

        Args:
            url: URL to scrape
            schema: JSON schema for extraction

        Returns:
            Structured data matching schema
        """
        try:
            logger.info(f"Extracting structured data from: {url}")

            params = {
                "formats": [{
                    "type": "json",
                    "schema": schema
                }]
            }

            result = self.app.scrape_url(url, params=params)

            return {
                "success": True,
                "url": url,
                "data": result
            }

        except Exception as e:
            logger.error(f"Error extracting structured data from {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }

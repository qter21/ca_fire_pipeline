"""
Mock Firecrawl API for unit testing.

Provides realistic mock responses without hitting real API endpoints.
"""

from typing import Dict, List, Optional
import time


class MockFirecrawlApp:
    """Mock Firecrawl API client for testing"""
    
    def __init__(self, api_key: str = "test-key"):
        self.api_key = api_key
        self.scrape_calls = []
        self.scrape_delay = 0.0  # Simulate API latency
    
    def scrape_url(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Mock scrape_url method"""
        # Record the call
        self.scrape_calls.append((url, params))
        
        # Simulate API delay
        if self.scrape_delay > 0:
            time.sleep(self.scrape_delay)
        
        # Return mock response based on URL pattern
        if "codes_displaySection" in url:
            return self._mock_section_response(url, params)
        elif "codedisplayexpand" in url or "codes_displayexpandedbranch" in url:
            return self._mock_architecture_response(url, params)
        else:
            return self._mock_default_response(url, params)
    
    def _mock_section_response(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Generate mock response for section pages"""
        # Extract section number from URL
        import re
        section_match = re.search(r'sectionNum=([^&]+)', url)
        section_num = section_match.group(1) if section_match else "1"
        
        # Extract code from URL
        code_match = re.search(r'lawCode=([^&]+)', url)
        code = code_match.group(1) if code_match else "TEST"
        
        # Check if multi-version (sections ending in 44 or 35)
        is_multi_version = section_num.endswith('44') or section_num.endswith('35')
        
        if is_multi_version:
            return {
                "markdown": f"# Multiple Versions Available\n\nSection {section_num} has multiple versions.",
                "html": f"<h1>Multiple Versions</h1>",
                "metadata": {
                    "title": f"{code} Code, Section {section_num}",
                    "url": url.replace("codes_displaySection", "codes_selectFromMultiples"),
                    "statusCode": 200
                },
                "linksOnPage": [
                    f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?version=2023&sectionNum={section_num}&lawCode={code}",
                    f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?version=2024&sectionNum={section_num}&lawCode={code}"
                ]
            }
        
        return {
            "markdown": f"""###### **{section_num}.**

This is mock content for section {section_num} of the {code} code.

_(Added by Stats. 2023, Ch. 100, Sec. 1. Operative January 1, 2024.)_
""",
            "html": f"<h6><strong>{section_num}.</strong></h6><p>This is mock content...</p>",
            "metadata": {
                "title": f"{code} Code, Section {section_num}",
                "url": url,
                "statusCode": 200
            },
            "linksOnPage": []
        }
    
    def _mock_architecture_response(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Generate mock response for architecture pages"""
        # Extract code from URL
        import re
        code_match = re.search(r'tocCode=([^&]+)', url)
        code = code_match.group(1) if code_match else "TEST"
        
        # Generate mock text page links
        num_divisions = 5
        text_links = [
            f"https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division={i}&lawCode={code}"
            for i in range(1, num_divisions + 1)
        ]
        
        return {
            "markdown": f"# {code} Code\n\n## Table of Contents\n\nDivision 1\nDivision 2\nDivision 3",
            "html": f"<h1>{code} Code</h1>",
            "metadata": {
                "title": f"California {code} Code",
                "url": url,
                "statusCode": 200
            },
            "linksOnPage": text_links
        }
    
    def _mock_default_response(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Generate default mock response"""
        return {
            "markdown": "# Mock Page\n\nThis is a mock response.",
            "html": "<h1>Mock Page</h1><p>This is a mock response.</p>",
            "metadata": {
                "title": "Mock Page",
                "url": url,
                "statusCode": 200
            },
            "linksOnPage": []
        }
    
    def set_delay(self, delay: float):
        """Set artificial delay to simulate API latency"""
        self.scrape_delay = delay
    
    def get_call_count(self) -> int:
        """Get number of scrape_url calls"""
        return len(self.scrape_calls)
    
    def reset(self):
        """Reset call history"""
        self.scrape_calls = []


class MockFirecrawlError(MockFirecrawlApp):
    """Mock Firecrawl that always fails (for error testing)"""
    
    def scrape_url(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Always raise an error"""
        self.scrape_calls.append((url, params))
        raise Exception("Mock API error: Service unavailable")


class MockFirecrawlRateLimited(MockFirecrawlApp):
    """Mock Firecrawl that simulates rate limiting"""
    
    def __init__(self, api_key: str = "test-key", max_calls_per_second: int = 2):
        super().__init__(api_key)
        self.max_calls_per_second = max_calls_per_second
        self.call_times = []
    
    def scrape_url(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Enforce rate limiting"""
        import time
        
        current_time = time.time()
        
        # Remove calls older than 1 second
        self.call_times = [t for t in self.call_times if current_time - t < 1.0]
        
        # Check if rate limited
        if len(self.call_times) >= self.max_calls_per_second:
            raise Exception("Rate limit exceeded: 429 Too Many Requests")
        
        # Record call time
        self.call_times.append(current_time)
        
        return super().scrape_url(url, params)


#!/usr/bin/env python3
"""
Proof of Concept: Firecrawl-based CA Legal Codes Scraper
Tests Firecrawl capabilities for replacing Playwright pipeline
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.services.firecrawl_service import FirecrawlService
from bs4 import BeautifulSoup
import re


class FirecrawlPOC:
    """POC for testing Firecrawl with CA legal codes"""

    BASE_URL = "https://leginfo.legislature.ca.gov/faces"
    EXPAND_URL = f"{BASE_URL}/codedisplayexpand.xhtml"
    SECTION_URL = f"{BASE_URL}/codes_displaySection.xhtml"
    MULTI_VERSION_URL = f"{BASE_URL}/selectFromMultiples.xhtml"

    def __init__(self):
        self.service = FirecrawlService()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }

    def test_1_architecture_scraping(self, code: str = "EVID"):
        """Test 1: Scrape code architecture/structure page"""
        print("\n" + "=" * 60)
        print("TEST 1: Architecture Scraping (Stage 1)")
        print("=" * 60)

        url = f"{self.EXPAND_URL}?tocCode={code}"
        print(f"URL: {url}")
        print("Note: Architecture page contains text page URLs, not direct section links")

        start_time = time.time()
        result = self.service.scrape_url(url, formats=["markdown"])
        duration = time.time() - start_time

        test_result = {
            "test": "architecture_scraping",
            "code": code,
            "url": url,
            "duration": duration,
            "success": result.get("success", False)
        }

        if result.get("success"):
            # Firecrawl returns content in markdown format
            markdown_content = result["data"].get("markdown", "")
            links_on_page = result["data"].get("linksOnPage", [])

            # The architecture page has text page links (divisions/parts/chapters)
            # These need to be scraped to get actual section URLs
            text_page_links = [link for link in links_on_page if 'codes_displayText' in link]

            test_result["text_page_links_found"] = len(text_page_links)
            test_result["markdown_length"] = len(markdown_content)
            test_result["total_links_on_page"] = len(links_on_page)

            # Sample first 5 text page links
            sample_links = text_page_links[:5]
            test_result["sample_links"] = sample_links

            print(f"✅ Success! Found {len(text_page_links)} text page URLs")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📝 Markdown length: {len(markdown_content):,} chars")
            print(f"🔗 Total links on page: {len(links_on_page)}")
            print(f"\nSample text page URLs (these contain section links):")
            for i, link in enumerate(sample_links, 1):
                print(f"  {i}. {link[:90]}...")
            print(f"\n💡 Stage 2 would scrape these {len(text_page_links)} pages to get actual section URLs")

        else:
            print(f"❌ Failed: {result.get('error')}")

        self.results["tests"].append(test_result)
        return test_result

    def test_2_section_content_extraction(self, code: str = "EVID", section: str = "1"):
        """Test 2: Extract content from a single section"""
        print("\n" + "=" * 60)
        print("TEST 2: Section Content Extraction")
        print("=" * 60)

        url = f"{self.SECTION_URL}?sectionNum={section}&lawCode={code}"
        print(f"URL: {url}")
        print(f"Section: {code} {section}")

        start_time = time.time()
        result = self.service.scrape_url(url, formats=["markdown", "html"])
        duration = time.time() - start_time

        test_result = {
            "test": "section_content_extraction",
            "code": code,
            "section": section,
            "url": url,
            "duration": duration,
            "success": result.get("success", False)
        }

        if result.get("success"):
            markdown_content = result["data"].get("markdown", "")

            # Extract section content from markdown
            # Look for the section number pattern (e.g., "1." or "3044.")
            section_pattern = rf"#{{6}}\s+\*\*{section}\.?\*\*\s*\n\n(.+?)(?=\n_\(|$)"
            match = re.search(section_pattern, markdown_content, re.DOTALL)

            section_content = ""
            if match:
                section_content = match.group(1).strip()
                test_result["section_content"] = section_content

            # Try alternative pattern - just get text after the section header
            if not section_content:
                # Look for section number in markdown
                lines = markdown_content.split('\n')
                capture = False
                content_lines = []
                for line in lines:
                    if f'**{section}.**' in line or f'**{section}' in line:
                        capture = True
                        continue
                    if capture:
                        if line.startswith('_') or line.startswith('##'):
                            break
                        if line.strip():
                            content_lines.append(line)

                section_content = '\n'.join(content_lines).strip()
                test_result["section_content"] = section_content

            test_result["content_length"] = len(section_content)
            test_result["markdown_length"] = len(markdown_content)

            # Extract legislative history (text in parentheses with italics)
            history_pattern = r'_\(([^)]+)\)_'
            history_matches = re.findall(history_pattern, markdown_content)
            if history_matches:
                test_result["legislative_history"] = history_matches[-1]  # Last one is usually the most recent

            # Sample content
            if section_content:
                test_result["sample_content"] = section_content[:200] + "..."

            print(f"✅ Success!")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📄 Content length: {test_result['content_length']:,} chars")
            print(f"📝 Markdown length: {test_result['markdown_length']:,} chars")
            if test_result.get('legislative_history'):
                print(f"📜 Legislative history: {test_result['legislative_history']}")
            print(f"\nSample content:")
            print(f"  {test_result.get('sample_content', 'N/A')}")

        else:
            print(f"❌ Failed: {result.get('error')}")

        self.results["tests"].append(test_result)
        return test_result

    def test_3_batch_scraping(self, code: str = "EVID", sections: list = None):
        """Test 3: Batch scrape multiple sections"""
        print("\n" + "=" * 60)
        print("TEST 3: Batch Section Scraping")
        print("=" * 60)

        sections = sections or ["1", "2", "3", "4", "5"]
        urls = [
            f"{self.SECTION_URL}?sectionNum={s}&lawCode={code}"
            for s in sections
        ]

        print(f"Scraping {len(urls)} sections: {', '.join(sections)}")

        start_time = time.time()
        results = self.service.batch_scrape(urls, formats=["markdown", "html"])
        duration = time.time() - start_time

        successful = sum(1 for r in results if r.get("success"))
        avg_time_per_section = duration / len(urls) if urls else 0

        test_result = {
            "test": "batch_scraping",
            "code": code,
            "sections": sections,
            "total_sections": len(sections),
            "successful": successful,
            "failed": len(sections) - successful,
            "duration": duration,
            "avg_time_per_section": avg_time_per_section,
            "success": successful == len(sections)  # Fix: mark as success if all sections processed
        }

        print(f"✅ Batch complete!")
        print(f"⏱️  Total duration: {duration:.2f}s")
        print(f"📊 Success rate: {successful}/{len(sections)} ({successful/len(sections)*100:.1f}%)")
        print(f"⚡ Avg time per section: {avg_time_per_section:.2f}s")

        self.results["tests"].append(test_result)
        return test_result

    def test_4_multi_version_detection(self, code: str = "FAM", section: str = "3044"):
        """Test 4: Detect and handle multi-version sections"""
        print("\n" + "=" * 60)
        print("TEST 4: Multi-Version Section Detection")
        print("=" * 60)

        url = f"{self.SECTION_URL}?sectionNum={section}&lawCode={code}"
        print(f"URL: {url}")
        print(f"Section: {code} {section} (known multi-version)")

        start_time = time.time()
        result = self.service.scrape_url(url, formats=["markdown", "html"])
        duration = time.time() - start_time

        test_result = {
            "test": "multi_version_detection",
            "code": code,
            "section": section,
            "url": url,
            "duration": duration,
            "success": result.get("success", False)
        }

        if result.get("success"):
            markdown_content = result["data"].get("markdown", "")
            source_url = result["data"].get("metadata", {}).get("url", "")

            # Check if redirected to multi-version selector
            is_multi_version = "selectFromMultiples" in source_url.lower() or "selectFromMultiples" in markdown_content
            test_result["is_multi_version"] = is_multi_version

            if is_multi_version:
                # Extract version links from markdown or linksOnPage
                links_on_page = result["data"].get("linksOnPage", [])
                version_links = [link for link in links_on_page if 'nodeTreePath' in link]
                test_result["versions_found"] = len(version_links)

                # Extract version descriptions from markdown
                # Look for patterns like "(Amended by Stats. 2024, Ch. 544, Sec. 6.)"
                version_pattern = r'\(([^)]+Stats[^)]+)\)'
                version_descriptions = re.findall(version_pattern, markdown_content)

                version_info = []
                for i, link in enumerate(version_links):
                    desc = version_descriptions[i] if i < len(version_descriptions) else f"Version {i+1}"
                    version_info.append({"description": desc, "url": link})

                test_result["version_info"] = version_info

                print(f"✅ Multi-version section detected!")
                print(f"⏱️  Duration: {duration:.2f}s")
                print(f"🔢 Versions found: {len(version_links)}")
                print(f"\nVersion details:")
                for i, v in enumerate(version_info, 1):
                    print(f"  {i}. {v['description']}")

            else:
                print(f"ℹ️  Single version section")
                print(f"⏱️  Duration: {duration:.2f}s")

        else:
            print(f"❌ Failed: {result.get('error')}")

        self.results["tests"].append(test_result)
        return test_result

    def test_5_structured_extraction(self, code: str = "EVID", section: str = "1"):
        """Test 5: Extract structured data using schema"""
        print("\n" + "=" * 60)
        print("TEST 5: Structured Data Extraction")
        print("=" * 60)

        url = f"{self.SECTION_URL}?sectionNum={section}&lawCode={code}"
        print(f"URL: {url}")

        # Define extraction schema
        schema = {
            "type": "object",
            "properties": {
                "section_number": {"type": "string"},
                "section_content": {"type": "string"},
                "legislative_history": {"type": "string"}
            }
        }

        start_time = time.time()
        result = self.service.extract_structured_data(url, schema)
        duration = time.time() - start_time

        test_result = {
            "test": "structured_extraction",
            "code": code,
            "section": section,
            "url": url,
            "duration": duration,
            "success": result.get("success", False)
        }

        if result.get("success"):
            extracted_data = result.get("data", {})
            test_result["extracted_data"] = extracted_data

            print(f"✅ Structured extraction successful!")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"📦 Extracted data:")
            print(json.dumps(extracted_data, indent=2))

        else:
            print(f"❌ Failed: {result.get('error')}")

        self.results["tests"].append(test_result)
        return test_result

    def run_all_tests(self):
        """Run all POC tests"""
        print("\n" + "=" * 60)
        print("🔥 FIRECRAWL POC - California Legal Codes")
        print("=" * 60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Test 1: Architecture scraping
            self.test_1_architecture_scraping("EVID")

            # Test 2: Single section extraction
            self.test_2_section_content_extraction("EVID", "1")

            # Test 3: Batch scraping
            self.test_3_batch_scraping("EVID", ["1", "2", "3", "4", "5"])

            # Test 4: Multi-version detection
            self.test_4_multi_version_detection("FAM", "3044")

            # Test 5: Structured extraction
            # self.test_5_structured_extraction("EVID", "1")  # Skip for now - may not work with all formats

        except Exception as e:
            print(f"\n❌ Error during tests: {e}")
            import traceback
            traceback.print_exc()

        # Print summary
        self.print_summary()

        # Save results
        self.save_results()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        total_tests = len(self.results["tests"])
        successful_tests = sum(1 for t in self.results["tests"] if t.get("success", False))
        total_duration = sum(t.get("duration", 0) for t in self.results["tests"])

        print(f"Total tests: {total_tests}")
        print(f"Successful: {successful_tests}/{total_tests}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Average per test: {total_duration/total_tests if total_tests else 0:.2f}s")

        print("\nTest breakdown:")
        for i, test in enumerate(self.results["tests"], 1):
            status = "✅" if test.get("success") else "❌"
            print(f"  {i}. {status} {test['test']}: {test.get('duration', 0):.2f}s")

    def save_results(self):
        """Save results to file"""
        results_dir = Path(__file__).parent.parent / "poc_results"
        results_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = results_dir / f"firecrawl_poc_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    poc = FirecrawlPOC()
    poc.run_all_tests()

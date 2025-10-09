#!/usr/bin/env python3
"""
Debug architecture page to understand link structure
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.services.firecrawl_service import FirecrawlService

service = FirecrawlService()

url = "https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode=EVID"

print("Fetching architecture page...")
result = service.scrape_url(url, formats=["markdown"])

if result.get("success"):
    markdown = result["data"].get("markdown", "")
    links = result["data"].get("linksOnPage", [])

    print(f"\nTotal links: {len(links)}")
    print("\nLink types:")

    # Categorize links
    section_links = [l for l in links if 'codes_displaySection' in l]
    text_links = [l for l in links if 'codes_displayText' in l]
    expand_links = [l for l in links if 'codedisplayexpand' in l]
    other_links = [l for l in links if l not in section_links + text_links + expand_links]

    print(f"  codes_displaySection: {len(section_links)}")
    print(f"  codes_displayText: {len(text_links)}")
    print(f"  codedisplayexpand: {len(expand_links)}")
    print(f"  Other: {len(other_links)}")

    print("\nSample section links:")
    for link in section_links[:5]:
        print(f"  {link}")

    print("\nSample text links:")
    for link in text_links[:5]:
        print(f"  {link}")

    # Search markdown for section patterns
    print("\n" + "=" * 60)
    print("Markdown analysis:")
    print("=" * 60)

    # Look for section numbers in markdown
    import re
    section_pattern = r'\[(\d+\.?)\]'
    sections = re.findall(section_pattern, markdown)
    print(f"Found {len(sections)} potential section numbers in markdown")
    print(f"Sample: {sections[:10]}")

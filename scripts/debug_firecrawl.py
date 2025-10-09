#!/usr/bin/env python3
"""
Debug script to inspect Firecrawl response structure
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.services.firecrawl_service import FirecrawlService

service = FirecrawlService()

# Test with a simple section
url = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID"

print("Testing Firecrawl response structure...")
print(f"URL: {url}\n")

result = service.scrape_url(url, formats=["markdown", "html"])

print("=" * 60)
print("FULL RESPONSE STRUCTURE:")
print("=" * 60)
print(json.dumps(result, indent=2, default=str))

print("\n" + "=" * 60)
print("RESPONSE KEYS:")
print("=" * 60)
if result.get("success"):
    data = result.get("data", {})
    print(f"Data type: {type(data)}")
    print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

    # Check what's actually in the response
    for key in data.keys() if isinstance(data, dict) else []:
        value = data[key]
        if isinstance(value, str):
            print(f"\n{key}: {len(value)} chars")
            print(f"  Preview: {value[:200]}...")
        else:
            print(f"\n{key}: {type(value)}")

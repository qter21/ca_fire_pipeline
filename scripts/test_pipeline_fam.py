"""Test complete pipeline with Family Code (FAM)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Just change code parameter and import the test function
from test_complete_pipeline import run_complete_pipeline

if __name__ == '__main__':
    # Test with FAM code
    # FAM is larger, so test with 10 text pages and 20 sections
    run_complete_pipeline('FAM', max_text_pages=10, max_sections=20)

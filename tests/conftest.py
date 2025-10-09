"""
Pytest configuration and fixtures
"""

import pytest
import yaml
from pathlib import Path
from pipeline.services.firecrawl_service import FirecrawlService


@pytest.fixture
def test_sections_data():
    """Load test sections data from YAML file"""
    data_file = Path(__file__).parent / "fixtures" / "test_sections_data.yaml"
    with open(data_file, 'r') as f:
        data = yaml.safe_load(f)
    return data['test_sections']


@pytest.fixture
def firecrawl_service():
    """Create FirecrawlService instance"""
    return FirecrawlService()


@pytest.fixture
def sample_section_data():
    """Sample section for quick tests"""
    return {
        "code": "EVID",
        "section": "1",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
        "expected_content": "This code shall be known as the Evidence Code.",
        "expected_history": "Enacted by Stats. 1965, Ch. 299."
    }


@pytest.fixture
def sample_multi_version_section():
    """Sample multi-version section for testing"""
    return {
        "code": "FAM",
        "section": "3044",
        "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3044&lawCode=FAM",
        "is_multi_version": True,
        "expected_versions": 2
    }


@pytest.fixture
def mock_firecrawl_response():
    """Mock Firecrawl API response"""
    return {
        "success": True,
        "data": {
            "content": "Sample markdown content",
            "markdown": "Sample markdown content",
            "linksOnPage": [
                "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
                "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=2&lawCode=EVID"
            ],
            "metadata": {
                "title": "California Code, EVID 1",
                "url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=EVID",
                "cacheState": "hit",
                "creditsUsed": 1
            }
        }
    }

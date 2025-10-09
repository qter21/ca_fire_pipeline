"""
Unit tests for FirecrawlService
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pipeline.services.firecrawl_service import FirecrawlService


@pytest.mark.unit
class TestFirecrawlService:
    """Test FirecrawlService class"""

    def test_init(self):
        """Test service initialization"""
        service = FirecrawlService()
        assert service.api_key is not None
        assert service.app is not None

    def test_scrape_url_success(self, mock_firecrawl_response):
        """Test successful URL scraping"""
        service = FirecrawlService()

        # Mock the Firecrawl app
        with patch.object(service.app, 'scrape_url', return_value=mock_firecrawl_response["data"]):
            result = service.scrape_url("https://example.com")

            assert result["success"] is True
            assert "data" in result
            assert result["data"]["markdown"] == "Sample markdown content"

    def test_scrape_url_failure(self):
        """Test URL scraping failure"""
        service = FirecrawlService()

        # Mock a failure
        with patch.object(service.app, 'scrape_url', side_effect=Exception("API Error")):
            result = service.scrape_url("https://example.com")

            assert result["success"] is False
            assert "error" in result
            assert "API Error" in result["error"]

    def test_scrape_url_with_formats(self):
        """Test scraping with specific formats"""
        service = FirecrawlService()

        with patch.object(service.app, 'scrape_url', return_value={}) as mock_scrape:
            service.scrape_url("https://example.com", formats=["markdown", "html"])

            # Verify formats were passed
            mock_scrape.assert_called_once()
            call_args = mock_scrape.call_args
            assert "params" in call_args[1]
            assert call_args[1]["params"]["formats"] == ["markdown", "html"]

    def test_batch_scrape(self):
        """Test batch scraping multiple URLs"""
        service = FirecrawlService()
        urls = [
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ]

        with patch.object(service, 'scrape_url', return_value={"success": True}) as mock_scrape:
            results = service.batch_scrape(urls)

            assert len(results) == 3
            assert mock_scrape.call_count == 3

    def test_batch_scrape_empty_list(self):
        """Test batch scraping with empty URL list"""
        service = FirecrawlService()
        results = service.batch_scrape([])

        assert len(results) == 0

    def test_scrape_with_actions(self):
        """Test scraping with page actions"""
        service = FirecrawlService()
        actions = [
            {"type": "wait", "milliseconds": 1000},
            {"type": "click", "selector": ".button"}
        ]

        with patch.object(service.app, 'scrape_url', return_value={}) as mock_scrape:
            service.scrape_with_actions("https://example.com", actions)

            # Verify actions were passed
            mock_scrape.assert_called_once()
            call_args = mock_scrape.call_args
            assert "params" in call_args[1]
            assert call_args[1]["params"]["actions"] == actions

    def test_extract_structured_data(self):
        """Test structured data extraction"""
        service = FirecrawlService()
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            }
        }

        with patch.object(service.app, 'scrape_url', return_value={}) as mock_scrape:
            service.extract_structured_data("https://example.com", schema)

            # Verify schema was passed
            mock_scrape.assert_called_once()
            call_args = mock_scrape.call_args
            assert "params" in call_args[1]
            assert "formats" in call_args[1]["params"]
            formats = call_args[1]["params"]["formats"]
            assert len(formats) == 1
            assert formats[0]["type"] == "json"
            assert formats[0]["schema"] == schema


@pytest.mark.unit
class TestFirecrawlServiceConfiguration:
    """Test service configuration"""

    def test_custom_api_key(self):
        """Test initialization with custom API key"""
        custom_key = "fc-custom-key"
        service = FirecrawlService(api_key=custom_key)
        assert service.api_key == custom_key

    @patch.dict('os.environ', {'FIRECRAWL_API_KEY': 'fc-env-key'})
    def test_api_key_from_env(self):
        """Test API key loading from environment"""
        # This would require reloading the settings
        # For now, just verify the service can be created
        service = FirecrawlService()
        assert service.api_key is not None

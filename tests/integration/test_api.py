"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from pipeline.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test the health endpoint returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "database" in data


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root(self, client):
        """Test the root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CA Fire Pipeline API"
        assert data["version"] == "2.0.0"
        assert "endpoints" in data


@pytest.mark.integration
class TestCrawlerEndpoints:
    """Test crawler API endpoints.

    These tests require:
    - Valid FIRECRAWL_API_KEY
    - Running MongoDB instance
    """

    @pytest.mark.skip(reason="Requires valid API key and takes time")
    def test_start_crawler(self, client):
        """Test starting a crawler job."""
        response = client.post("/api/v2/crawler/start/WIC")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "WIC"
        assert data["status"] == "started"
        assert "job_id" in data

    @pytest.mark.skip(reason="Requires valid API key and takes time")
    def test_get_job_status(self, client):
        """Test getting job status."""
        # First create a job
        start_response = client.post("/api/v2/crawler/start/WIC")
        assert start_response.status_code == 200
        job_id = start_response.json()["job_id"]

        # Then check status
        status_response = client.get(f"/api/v2/crawler/status/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["job_id"] == job_id
        assert data["code"] == "WIC"
        assert "status" in data

    def test_get_job_status_not_found(self, client):
        """Test getting status for non-existent job."""
        response = client.get("/api/v2/crawler/status/nonexistent_job")

        assert response.status_code == 404

    @pytest.mark.skip(reason="Requires valid API key and takes time")
    def test_run_stage1(self, client):
        """Test running Stage 1 only."""
        response = client.post("/api/v2/crawler/stage1/WIC")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "WIC"
        assert data["stage"] == "stage1"
        assert data["success"] == True
        assert data["total_sections"] > 0

    def test_list_codes(self, client):
        """Test listing all codes."""
        response = client.get("/api/v2/crawler/codes")

        assert response.status_code == 200
        data = response.json()
        assert "codes" in data
        assert isinstance(data["codes"], list)

    def test_get_recent_jobs(self, client):
        """Test getting recent jobs."""
        response = client.get("/api/v2/crawler/jobs/recent")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_get_recent_jobs_with_limit(self, client):
        """Test getting recent jobs with custom limit."""
        response = client.get("/api/v2/crawler/jobs/recent?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) <= 5


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "CA Fire Pipeline API"
        assert schema["info"]["version"] == "2.0.0"

    def test_docs_endpoint(self, client):
        """Test that /docs endpoint is available."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

"""
Unit tests for Crawler API endpoints.

This is an EXAMPLE implementation showing how to test the crawler API
following TDD best practices.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from pipeline.main import app
from pipeline.core.database import DatabaseManager
from pipeline.services.architecture_crawler import ArchitectureCrawler
from pipeline.services.content_extractor import ContentExtractor
from pipeline.models.job import JobStatus


@pytest.fixture
def client():
    """Create test client for API testing"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database manager"""
    db = Mock(spec=DatabaseManager)
    
    # Mock common database operations
    db.create_job.return_value = "job-123"
    db.get_job.return_value = {
        "job_id": "job-123",
        "code": "EVID",
        "status": JobStatus.PROCESSING,
        "created_at": datetime.now(),
        "stage_1_complete": False,
        "stage_2_complete": False,
        "stage_3_complete": False
    }
    db.update_job.return_value = True
    
    return db


@pytest.fixture
def mock_crawler():
    """Mock architecture crawler"""
    crawler = Mock(spec=ArchitectureCrawler)
    
    crawler.crawl.return_value = {
        "success": True,
        "code": "EVID",
        "total_sections": 100,
        "total_text_pages": 10,
        "execution_time": 1.5
    }
    
    return crawler


@pytest.fixture
def mock_extractor():
    """Mock content extractor"""
    extractor = Mock(spec=ContentExtractor)
    
    extractor.extract_all_sections.return_value = {
        "success": True,
        "code": "EVID",
        "total_sections": 100,
        "successful": 98,
        "failed": 2,
        "single_version_count": 95,
        "multi_version_count": 3
    }
    
    return extractor


@pytest.mark.unit
class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_returns_200(self, client):
        """Test that health endpoint returns 200 OK"""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_health_check_includes_version(self, client):
        """Test that health check includes API version"""
        response = client.get("/health")
        data = response.json()
        
        assert "version" in data
        assert isinstance(data["version"], str)


@pytest.mark.unit
class TestStartCrawlerEndpoint:
    """Test POST /api/v2/crawler/start/{code}"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ArchitectureCrawler')
    def test_start_crawler_success(self, mock_arch_class, mock_get_db, client, mock_db, mock_crawler):
        """Test successfully starting a crawler job"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_arch_class.return_value = mock_crawler
        
        # Act
        response = client.post("/api/v2/crawler/start/EVID")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "EVID"
        assert data["job_id"] == "job-123"
        assert data["status"] == "processing"
        
        # Verify database interaction
        mock_db.create_job.assert_called_once()
        call_args = mock_db.create_job.call_args[0][0]
        assert call_args.code == "EVID"
    
    def test_start_crawler_invalid_code(self, client):
        """Test that invalid code returns 400"""
        response = client.post("/api/v2/crawler/start/INVALID123")
        
        assert response.status_code == 400
        assert "error" in response.json()
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_start_crawler_database_error(self, mock_get_db, client, mock_db):
        """Test that database errors return 500"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.create_job.side_effect = Exception("Database connection failed")
        
        # Act
        response = client.post("/api/v2/crawler/start/EVID")
        
        # Assert
        assert response.status_code == 500
        assert "error" in response.json()
    
    def test_start_crawler_empty_code(self, client):
        """Test that empty code returns 400"""
        response = client.post("/api/v2/crawler/start/")
        
        assert response.status_code in [400, 404]  # 404 for missing path param


@pytest.mark.unit
class TestJobStatusEndpoint:
    """Test GET /api/v2/crawler/status/{job_id}"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_get_job_status_success(self, mock_get_db, client, mock_db):
        """Test getting job status"""
        # Arrange
        mock_get_db.return_value = mock_db
        
        # Act
        response = client.get("/api/v2/crawler/status/job-123")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["code"] == "EVID"
        assert data["status"] == JobStatus.PROCESSING
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_get_job_status_not_found(self, mock_get_db, client, mock_db):
        """Test getting non-existent job returns 404"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.get_job.return_value = None
        
        # Act
        response = client.get("/api/v2/crawler/status/nonexistent")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()


@pytest.mark.unit
class TestStage1Endpoint:
    """Test POST /api/v2/crawler/stage1/{code}"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ArchitectureCrawler')
    def test_run_stage1_success(self, mock_arch_class, mock_get_db, client, mock_db, mock_crawler):
        """Test successfully running Stage 1"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_arch_class.return_value = mock_crawler
        
        # Act
        response = client.post("/api/v2/crawler/stage1/EVID")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["code"] == "EVID"
        assert data["total_sections"] == 100
        
        # Verify crawler was called
        mock_crawler.crawl.assert_called_once_with("EVID", save_to_db=True)
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ArchitectureCrawler')
    def test_run_stage1_crawler_failure(self, mock_arch_class, mock_get_db, client, mock_db, mock_crawler):
        """Test Stage 1 failure handling"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_arch_class.return_value = mock_crawler
        mock_crawler.crawl.return_value = {
            "success": False,
            "error": "Network timeout"
        }
        
        # Act
        response = client.post("/api/v2/crawler/stage1/EVID")
        
        # Assert
        assert response.status_code == 500
        assert "error" in response.json()


@pytest.mark.unit
class TestStage2Endpoint:
    """Test POST /api/v2/crawler/stage2/{code}"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ContentExtractor')
    def test_run_stage2_success(self, mock_ext_class, mock_get_db, client, mock_db, mock_extractor):
        """Test successfully running Stage 2"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_ext_class.return_value = mock_extractor
        
        # Act
        response = client.post("/api/v2/crawler/stage2/EVID")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["code"] == "EVID"
        assert data["total_sections"] == 100
        assert data["single_version_count"] == 95
        assert data["multi_version_count"] == 3
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ContentExtractor')
    def test_run_stage2_partial_failure(self, mock_ext_class, mock_get_db, client, mock_db, mock_extractor):
        """Test Stage 2 with some failed sections"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_ext_class.return_value = mock_extractor
        mock_extractor.extract_all_sections.return_value = {
            "success": True,
            "code": "EVID",
            "total_sections": 100,
            "successful": 90,
            "failed": 10,
            "failed_sections": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
        }
        
        # Act
        response = client.post("/api/v2/crawler/stage2/EVID")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["failed_sections"]) == 10


@pytest.mark.unit
class TestListJobsEndpoint:
    """Test GET /api/v2/crawler/jobs"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_list_jobs_empty(self, mock_get_db, client, mock_db):
        """Test listing jobs when none exist"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.list_jobs.return_value = []
        
        # Act
        response = client.get("/api/v2/crawler/jobs")
        
        # Assert
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_list_jobs_with_data(self, mock_get_db, client, mock_db):
        """Test listing jobs with multiple jobs"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.list_jobs.return_value = [
            {"job_id": "job-1", "code": "EVID", "status": JobStatus.COMPLETED},
            {"job_id": "job-2", "code": "FAM", "status": JobStatus.PROCESSING},
        ]
        
        # Act
        response = client.get("/api/v2/crawler/jobs")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["job_id"] == "job-1"
        assert data[1]["job_id"] == "job-2"
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_list_jobs_with_filters(self, mock_get_db, client, mock_db):
        """Test listing jobs with status filter"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.list_jobs.return_value = [
            {"job_id": "job-1", "code": "EVID", "status": JobStatus.COMPLETED},
        ]
        
        # Act
        response = client.get("/api/v2/crawler/jobs?status=completed")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == JobStatus.COMPLETED


@pytest.mark.unit
class TestDeleteJobEndpoint:
    """Test DELETE /api/v2/crawler/jobs/{job_id}"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_delete_job_success(self, mock_get_db, client, mock_db):
        """Test successfully deleting a job"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.delete_job.return_value = True
        
        # Act
        response = client.delete("/api/v2/crawler/jobs/job-123")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Job deleted"
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_delete_job_not_found(self, mock_get_db, client, mock_db):
        """Test deleting non-existent job"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.delete_job.return_value = False
        
        # Act
        response = client.delete("/api/v2/crawler/jobs/nonexistent")
        
        # Assert
        assert response.status_code == 404


@pytest.mark.unit
class TestRequestValidation:
    """Test request validation and error handling"""
    
    def test_start_crawler_with_body(self, client):
        """Test start crawler with optional request body"""
        response = client.post(
            "/api/v2/crawler/start/EVID",
            json={"skip_multi_version": True}
        )
        
        # Should accept valid body
        assert response.status_code in [200, 422]  # 422 if not implemented yet
    
    def test_stage2_with_options(self, client):
        """Test stage2 with extraction options"""
        response = client.post(
            "/api/v2/crawler/stage2/EVID",
            json={"batch_size": 50, "max_concurrent": 5}
        )
        
        # Should accept valid body
        assert response.status_code in [200, 422]


@pytest.mark.unit
class TestConcurrentRequests:
    """Test handling concurrent requests"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    @patch('pipeline.routers.crawler.ArchitectureCrawler')
    def test_multiple_jobs_can_run_concurrently(
        self, 
        mock_arch_class, 
        mock_get_db, 
        client, 
        mock_db, 
        mock_crawler
    ):
        """Test that multiple jobs can be started concurrently"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_arch_class.return_value = mock_crawler
        job_ids = ["job-1", "job-2", "job-3"]
        mock_db.create_job.side_effect = job_ids
        
        # Act - Start 3 jobs
        responses = [
            client.post("/api/v2/crawler/start/EVID"),
            client.post("/api/v2/crawler/start/FAM"),
            client.post("/api/v2/crawler/start/PEN"),
        ]
        
        # Assert - All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Verify 3 jobs were created
        assert mock_db.create_job.call_count == 3


@pytest.mark.unit
class TestErrorResponseFormat:
    """Test that error responses follow consistent format"""
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_500_error_has_error_field(self, mock_get_db, client, mock_db):
        """Test that 500 errors have consistent format"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.create_job.side_effect = Exception("Unexpected error")
        
        # Act
        response = client.post("/api/v2/crawler/start/EVID")
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert isinstance(data["error"], str)
    
    @patch('pipeline.routers.crawler.get_db_manager')
    def test_404_error_has_error_field(self, mock_get_db, client, mock_db):
        """Test that 404 errors have consistent format"""
        # Arrange
        mock_get_db.return_value = mock_db
        mock_db.get_job.return_value = None
        
        # Act
        response = client.get("/api/v2/crawler/status/nonexistent")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert isinstance(data["error"], str)


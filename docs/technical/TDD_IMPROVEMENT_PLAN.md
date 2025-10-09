# TDD Improvement Plan - CA Fire Pipeline

**Date:** October 8, 2025  
**Current Coverage:** 27%  
**Target Coverage:** 85%+  
**Status:** 🔴 Needs Significant Improvement

---

## Executive Summary

While the project has made good initial progress with TDD (36 unit tests, test fixtures, pytest configuration), there are significant gaps that need to be addressed. The current test coverage of **27%** is far below industry standards (80-90%), and critical components like routers, database operations, and content extraction are undertested or completely untested.

### Key Issues Identified

1. **Low Coverage (27%)** - Most production code paths untested
2. **Tests Written After Code** - Not following true TDD red-green-refactor cycle
3. **Missing Critical Tests** - 0% coverage on routers, main.py, and key services
4. **No Integration Test Isolation** - Tests hit real external APIs (expensive & slow)
5. **No CI/CD Pipeline** - Tests not running automatically
6. **Incomplete Error Handling Tests** - Edge cases not covered
7. **No Performance/Load Tests** - No baseline metrics

---

## Current State Analysis

### Coverage Breakdown

| Component | Coverage | Lines | Missing | Status |
|-----------|----------|-------|---------|--------|
| **Models** | 100% | 165/165 | 0 | ✅ Excellent |
| **Firecrawl Service** | 21% | 12/57 | 45 | 🔴 Critical |
| **Architecture Crawler** | 18% | 22/124 | 102 | 🔴 Critical |
| **Content Parser** | 26% | 17/66 | 49 | 🔴 Poor |
| **Content Extractor** | 11% | 14/122 | 108 | 🔴 Critical |
| **Database Manager** | 23% | 49/214 | 165 | 🔴 Critical |
| **Routers (API)** | 0% | 0/144 | 144 | 🔴 Missing |
| **Main App** | 0% | 0/35 | 35 | 🔴 Missing |
| **Multi-Version Handler** | 18% | 24/133 | 109 | 🔴 Critical |
| **Overall** | **27%** | 341/1283 | 942 | 🔴 **Poor** |

### Test Organization

```
tests/
├── unit/ (36 tests)
│   ├── test_firecrawl_service.py     ✅ Good coverage
│   ├── test_content_parser.py        ⚠️ Partial coverage
│   ├── test_architecture_crawler.py  ⚠️ Partial coverage
│   └── test_database.py              ⚠️ Model tests only
├── integration/ (14 tests, 1 broken)
│   ├── test_section_extraction.py    ⚠️ Hits real API
│   ├── test_yaml_data.py             ✅ Good
│   ├── test_pipeline.py              ⚠️ Unknown
│   └── test_api.py                   🔴 Collection error
└── fixtures/
    └── test_sections_data.yaml       ✅ Good test data

Missing:
├── e2e/                              ❌ No end-to-end tests
├── performance/                       ❌ No performance tests
└── contract/                         ❌ No API contract tests
```

### Test Quality Issues

**❌ Violations of TDD Principles:**
1. Tests written after implementation (not test-first)
2. No red-green-refactor cycle documented
3. Tests don't drive design decisions
4. Coverage added as afterthought

**⚠️ Testing Anti-Patterns:**
1. Integration tests hitting real APIs (slow, expensive, brittle)
2. No clear mocking strategy
3. Tests coupled to implementation details
4. Missing boundary condition tests

**✅ What's Working:**
1. Good test organization (unit/integration separation)
2. Descriptive test names
3. Parametrized tests where appropriate
4. Shared fixtures in conftest.py
5. pytest markers for test categorization

---

## Improvement Plan

### Phase 1: Foundation (Week 1) 🎯 Priority: CRITICAL

**Goal:** Establish true TDD workflow and increase coverage to 50%

#### 1.1 Set Up CI/CD Pipeline

```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/unit/ -v --cov=pipeline --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v3
```

**Tasks:**
- [ ] Create GitHub Actions workflow
- [ ] Set up Codecov integration
- [ ] Add coverage badges to README
- [ ] Configure branch protection (require tests to pass)
- [ ] Set minimum coverage threshold (start at 50%, increase to 80%)

#### 1.2 Add Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/unit/ -x
        language: system
        pass_filenames: false
      - id: black
        name: black
        entry: black
        language: system
        types: [python]
      - id: flake8
        name: flake8
        entry: flake8
        language: system
        types: [python]
```

**Tasks:**
- [ ] Install pre-commit framework
- [ ] Create pre-commit configuration
- [ ] Add to developer setup guide
- [ ] Run `pre-commit install` in all dev environments

#### 1.3 Create Test Doubles/Mocks for External Services

**Problem:** Integration tests are slow and hit real Firecrawl API

**Solution:** Create comprehensive mocks

```python
# tests/mocks/mock_firecrawl.py
class MockFirecrawlApp:
    """Mock Firecrawl API for unit tests"""
    
    def __init__(self):
        self.scrape_calls = []
    
    def scrape_url(self, url: str, params: dict = None):
        self.scrape_calls.append((url, params))
        # Return realistic test data based on URL pattern
        if "codes_displaySection" in url:
            return self._mock_section_response(url)
        elif "codedisplayexpand" in url:
            return self._mock_architecture_response(url)
        return self._mock_default_response()
```

**Tasks:**
- [ ] Create `tests/mocks/` directory
- [ ] Implement `MockFirecrawlApp`
- [ ] Implement `MockDatabaseManager`
- [ ] Create fixture library for common responses
- [ ] Update existing tests to use mocks

#### 1.4 Write Missing Unit Tests for Critical Paths

**Priority Order:**

1. **Routers (0% → 80%)**
   - [ ] `test_routers/test_crawler_api.py` (all 8 endpoints)
   - [ ] `test_routers/test_health_api.py`
   
2. **Database Manager (23% → 80%)**
   - [ ] CRUD operations for all models
   - [ ] Connection error handling
   - [ ] Transaction rollback scenarios
   - [ ] Query performance tests

3. **Firecrawl Service (21% → 90%)**
   - [ ] All scraping methods
   - [ ] Error handling and retries
   - [ ] Rate limiting behavior
   - [ ] Batch processing edge cases

4. **Content Services (11-26% → 80%)**
   - [ ] Content parser edge cases
   - [ ] Content extractor full workflow
   - [ ] Multi-version handler complete coverage

**Example Test Structure:**

```python
# tests/unit/test_routers/test_crawler_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

@pytest.fixture
def mock_db():
    """Mock database manager"""
    return Mock(spec=DatabaseManager)

@pytest.fixture
def mock_crawler():
    """Mock architecture crawler"""
    return Mock(spec=ArchitectureCrawler)

@pytest.mark.unit
class TestCrawlerStartEndpoint:
    """Test /api/v2/crawler/start/{code}"""
    
    def test_start_crawler_success(self, client, mock_db, mock_crawler):
        """Test successful crawler start"""
        # Arrange
        mock_crawler.crawl.return_value = {"success": True, "sections": 100}
        
        # Act
        response = client.post("/api/v2/crawler/start/EVID")
        
        # Assert
        assert response.status_code == 200
        assert response.json()["code"] == "EVID"
        assert mock_crawler.crawl.called_once_with("EVID")
    
    def test_start_crawler_invalid_code(self, client):
        """Test invalid code returns 400"""
        response = client.post("/api/v2/crawler/start/INVALID")
        assert response.status_code == 400
    
    def test_start_crawler_db_error(self, client, mock_db):
        """Test database error returns 500"""
        mock_db.create_job.side_effect = Exception("DB connection failed")
        response = client.post("/api/v2/crawler/start/EVID")
        assert response.status_code == 500
```

---

### Phase 2: TDD Workflow Implementation (Week 2) 🎯 Priority: HIGH

**Goal:** Establish red-green-refactor cycle and increase coverage to 70%

#### 2.1 Implement True TDD for New Features

**TDD Workflow Template:**

```python
# Example: Adding rate limiting to Firecrawl service

# STEP 1: RED - Write failing test first
def test_firecrawl_respects_rate_limit():
    """Test that service respects rate limit"""
    service = FirecrawlService(rate_limit=2)  # 2 requests per second
    
    urls = ["url1", "url2", "url3"]
    start = time.time()
    service.batch_scrape(urls)
    duration = time.time() - start
    
    # Should take at least 1 second due to rate limiting
    assert duration >= 1.0

# STEP 2: GREEN - Implement minimal code to pass
class FirecrawlService:
    def __init__(self, rate_limit: Optional[int] = None):
        self.rate_limit = rate_limit
        self._last_request_time = 0
    
    def _enforce_rate_limit(self):
        if self.rate_limit:
            elapsed = time.time() - self._last_request_time
            if elapsed < (1.0 / self.rate_limit):
                time.sleep((1.0 / self.rate_limit) - elapsed)
        self._last_request_time = time.time()

# STEP 3: REFACTOR - Improve design
# - Add async rate limiting
# - Add token bucket algorithm
# - Add backoff strategy
```

**Process:**
1. Write test first (RED)
2. Run test, verify it fails
3. Write minimal code to pass (GREEN)
4. Run test, verify it passes
5. Refactor while keeping tests green
6. Commit with descriptive message

**Tasks:**
- [ ] Create `docs/TDD_WORKFLOW.md` guide
- [ ] Set up TDD pair programming sessions
- [ ] Record TDD examples for team training
- [ ] Create test template snippets for common patterns

#### 2.2 Add Property-Based Testing

**Install Hypothesis:**
```bash
pip install hypothesis
```

**Example Property Tests:**

```python
# tests/unit/test_content_parser_properties.py
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
def test_extract_section_never_crashes(markdown_content):
    """Property: Parser should never crash regardless of input"""
    try:
        result = ContentParser.extract_section_content(markdown_content, "1")
        # Should always return tuple
        assert isinstance(result, tuple)
        assert len(result) == 2
    except Exception as e:
        pytest.fail(f"Parser crashed on input: {e}")

@given(st.integers(min_value=1, max_value=99999))
def test_section_number_extraction_is_idempotent(section_num):
    """Property: Extracting section number twice gives same result"""
    url = f"https://example.com?sectionNum={section_num}&lawCode=TEST"
    result1 = ContentParser.extract_section_number(url)
    result2 = ContentParser.extract_section_number(url)
    assert result1 == result2
```

**Tasks:**
- [ ] Add hypothesis to requirements-dev.txt
- [ ] Write property tests for parsers
- [ ] Write property tests for URL generation
- [ ] Write property tests for data models

#### 2.3 Improve Test Data Management

**Current Issue:** Test data scattered, hard to maintain

**Solution:** Centralized test data factory

```python
# tests/factories.py
from dataclasses import dataclass
from typing import Dict, List

class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_section_markdown(
        section_num: str = "1",
        content: str = "Test content",
        history: str = "Stats. 2023"
    ) -> str:
        """Create realistic section markdown"""
        return f"""
###### **{section_num}.**

{content}

_(Added by {history})_
"""
    
    @staticmethod
    def create_architecture_response(
        code: str = "EVID",
        num_divisions: int = 5
    ) -> Dict:
        """Create realistic architecture API response"""
        return {
            "success": True,
            "data": {
                "markdown": f"# California {code} Code",
                "linksOnPage": [
                    f"https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?division={i}&lawCode={code}"
                    for i in range(1, num_divisions + 1)
                ]
            }
        }

# Usage in tests:
def test_parse_section():
    markdown = TestDataFactory.create_section_markdown(
        section_num="100",
        content="This is a test section"
    )
    result = ContentParser.extract_section_content(markdown, "100")
    assert "test section" in result[0]
```

**Tasks:**
- [ ] Create `tests/factories.py`
- [ ] Migrate YAML data to factory methods
- [ ] Create builders for complex models
- [ ] Add randomization with Faker

---

### Phase 3: Advanced Testing (Week 3) 🎯 Priority: MEDIUM

**Goal:** Add comprehensive test types and reach 85% coverage

#### 3.1 Add Integration Tests with Test Containers

**Problem:** Integration tests hit real APIs, no real database testing

**Solution:** Use pytest-docker or testcontainers

```python
# tests/integration/test_database_integration.py
import pytest
from testcontainers.mongodb import MongoDbContainer

@pytest.fixture(scope="module")
def mongodb_container():
    """Start MongoDB in Docker for tests"""
    with MongoDbContainer("mongo:7.0") as mongo:
        yield mongo

@pytest.fixture
def test_db(mongodb_container):
    """Create test database connection"""
    connection_url = mongodb_container.get_connection_url()
    db = DatabaseManager(connection_url)
    yield db
    # Cleanup after test
    db.drop_database()

@pytest.mark.integration
class TestDatabaseIntegration:
    """Real database integration tests"""
    
    def test_create_and_retrieve_section(self, test_db):
        """Test full CRUD workflow"""
        # Create
        section = SectionCreate(
            code="TEST",
            section_num="1",
            content="Test content"
        )
        section_id = test_db.create_section(section)
        
        # Retrieve
        retrieved = test_db.get_section(section_id)
        assert retrieved.content == "Test content"
        
        # Update
        test_db.update_section(section_id, {"content": "Updated"})
        updated = test_db.get_section(section_id)
        assert updated.content == "Updated"
        
        # Delete
        test_db.delete_section(section_id)
        assert test_db.get_section(section_id) is None
```

**Tasks:**
- [ ] Add testcontainers to requirements-dev.txt
- [ ] Create MongoDB test container fixture
- [ ] Write integration tests for all database operations
- [ ] Test transaction rollback scenarios
- [ ] Test connection pooling and timeout behavior

#### 3.2 Add End-to-End Tests

```python
# tests/e2e/test_complete_pipeline.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.e2e
@pytest.mark.slow
class TestCompletePipeline:
    """End-to-end pipeline tests"""
    
    def test_complete_code_extraction_workflow(
        self, 
        client: TestClient,
        test_db,
        mock_firecrawl
    ):
        """Test extracting a small code from start to finish"""
        # Start job
        response = client.post("/api/v2/crawler/start/EVID")
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Check status - should be processing
        status = client.get(f"/api/v2/crawler/status/{job_id}")
        assert status.json()["status"] == "processing"
        
        # Wait for completion (with timeout)
        import time
        for _ in range(60):  # Max 60 seconds
            status = client.get(f"/api/v2/crawler/status/{job_id}")
            if status.json()["status"] in ["completed", "failed"]:
                break
            time.sleep(1)
        
        # Verify completion
        final_status = client.get(f"/api/v2/crawler/status/{job_id}")
        assert final_status.json()["status"] == "completed"
        
        # Verify data in database
        sections = test_db.list_sections(code="EVID")
        assert len(sections) > 0
        
        # Verify at least one section has content
        assert any(s.content for s in sections)
```

**Tasks:**
- [ ] Create `tests/e2e/` directory
- [ ] Write complete pipeline test
- [ ] Test multi-version extraction workflow
- [ ] Test error recovery scenarios
- [ ] Add performance assertions (SLAs)

#### 3.3 Add Performance Tests

```python
# tests/performance/test_performance.py
import pytest
import time

@pytest.mark.performance
class TestPerformance:
    """Performance and load tests"""
    
    def test_batch_scraping_performance(self, firecrawl_service):
        """Test batch scraping meets performance SLA"""
        urls = [f"https://example.com/{i}" for i in range(50)]
        
        start = time.time()
        results = firecrawl_service.batch_scrape(urls)
        duration = time.time() - start
        
        # SLA: Should process 50 URLs in under 60 seconds
        assert duration < 60, f"Batch took {duration}s, expected <60s"
        
        # Success rate should be >95%
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        assert success_rate >= 0.95
    
    def test_database_query_performance(self, test_db):
        """Test database queries meet performance SLA"""
        # Create 1000 test sections
        for i in range(1000):
            test_db.create_section(SectionCreate(
                code="TEST",
                section_num=str(i),
                content=f"Content {i}"
            ))
        
        # Query should be fast
        start = time.time()
        sections = test_db.list_sections(code="TEST", limit=100)
        duration = time.time() - start
        
        # SLA: Query 100 sections in under 100ms
        assert duration < 0.1, f"Query took {duration}s, expected <0.1s"
```

**Tasks:**
- [ ] Create `tests/performance/` directory
- [ ] Define performance SLAs
- [ ] Write performance tests for critical paths
- [ ] Set up performance monitoring
- [ ] Create performance regression alerts

#### 3.4 Add Contract Tests for API

```python
# tests/contract/test_api_contracts.py
import pytest
from pydantic import ValidationError

@pytest.mark.contract
class TestAPIContracts:
    """Test API request/response contracts"""
    
    def test_start_crawler_request_contract(self):
        """Test start crawler request validation"""
        # Valid request
        valid = {"code": "EVID", "skip_multi_version": False}
        request = StartCrawlerRequest(**valid)
        assert request.code == "EVID"
        
        # Invalid request - missing required field
        with pytest.raises(ValidationError):
            StartCrawlerRequest(**{})
        
        # Invalid request - wrong type
        with pytest.raises(ValidationError):
            StartCrawlerRequest(**{"code": 123})
    
    def test_job_response_contract(self):
        """Test job response structure"""
        response = {
            "job_id": "test-123",
            "code": "EVID",
            "status": "processing",
            "message": "Started"
        }
        
        job_response = JobResponse(**response)
        assert job_response.job_id == "test-123"
        
        # Verify JSON serialization
        json_data = job_response.model_dump_json()
        assert "job_id" in json_data
```

**Tasks:**
- [ ] Create `tests/contract/` directory
- [ ] Write contract tests for all API endpoints
- [ ] Test all Pydantic models with edge cases
- [ ] Add schema validation tests
- [ ] Generate OpenAPI spec tests

---

### Phase 4: Quality Assurance (Week 4) 🎯 Priority: MEDIUM

**Goal:** Ensure test quality and maintainability

#### 4.1 Add Mutation Testing

**Install mutation testing tool:**
```bash
pip install mutmut
```

**Run mutation tests:**
```bash
mutmut run --paths-to-mutate=pipeline/
```

**What it does:**
- Introduces small bugs (mutations) in your code
- Runs your test suite
- Tests should fail if they're good
- If tests pass with bugs, they're not thorough enough

**Tasks:**
- [ ] Install mutmut
- [ ] Run initial mutation testing
- [ ] Fix tests that don't catch mutations
- [ ] Add mutation testing to CI
- [ ] Aim for >80% mutation score

#### 4.2 Add Test Quality Metrics

```python
# tests/conftest.py
import pytest
import time

# Track test metrics
test_metrics = {
    "total_tests": 0,
    "passed_tests": 0,
    "failed_tests": 0,
    "skipped_tests": 0,
    "total_duration": 0,
    "slow_tests": []
}

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Track test results"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call":
        test_metrics["total_tests"] += 1
        
        if report.passed:
            test_metrics["passed_tests"] += 1
        elif report.failed:
            test_metrics["failed_tests"] += 1
        elif report.skipped:
            test_metrics["skipped_tests"] += 1
        
        # Track slow tests (>1s)
        if report.duration > 1.0:
            test_metrics["slow_tests"].append({
                "name": item.nodeid,
                "duration": report.duration
            })

def pytest_sessionfinish(session, exitstatus):
    """Print test metrics summary"""
    print("\n" + "="*70)
    print("TEST METRICS SUMMARY")
    print("="*70)
    print(f"Total tests: {test_metrics['total_tests']}")
    print(f"Passed: {test_metrics['passed_tests']}")
    print(f"Failed: {test_metrics['failed_tests']}")
    print(f"Skipped: {test_metrics['skipped_tests']}")
    
    if test_metrics['slow_tests']:
        print(f"\nSlow tests (>1s): {len(test_metrics['slow_tests'])}")
        for test in sorted(test_metrics['slow_tests'], 
                          key=lambda x: x['duration'], 
                          reverse=True)[:5]:
            print(f"  - {test['name']}: {test['duration']:.2f}s")
```

**Tasks:**
- [ ] Add test metrics tracking
- [ ] Create test dashboard
- [ ] Track test execution time trends
- [ ] Identify and fix slow tests
- [ ] Monitor test flakiness

#### 4.3 Improve Test Documentation

**Create comprehensive test documentation:**

```markdown
# tests/README.md

## Test Organization

### Unit Tests (`tests/unit/`)
Fast, isolated tests that test individual functions/classes.
- Run before every commit
- Should complete in <5 seconds
- Use mocks for external dependencies

### Integration Tests (`tests/integration/`)
Tests that verify component interactions.
- Run before every push
- May use test containers
- Should complete in <2 minutes

### E2E Tests (`tests/e2e/`)
Full workflow tests from API to database.
- Run in CI before merge
- Use realistic test data
- Should complete in <5 minutes

### Performance Tests (`tests/performance/`)
Tests that verify performance SLAs.
- Run nightly in CI
- Compare against baselines
- Alert on regressions

## Running Tests

# Fast feedback loop (unit tests only)
pytest tests/unit/ -v

# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=pipeline --cov-report=html

# Only fast tests
pytest tests/ -m "not slow"

# Specific test file
pytest tests/unit/test_firecrawl_service.py -v

## Writing Tests

1. Follow TDD: Write test first (RED)
2. Write minimal code to pass (GREEN)
3. Refactor while keeping tests green
4. Use descriptive test names: `test_[what]_[when]_[expected]`
5. Arrange-Act-Assert pattern
6. One assertion per test (usually)
7. Use fixtures for setup
8. Mock external dependencies

## Test Naming Convention

```python
def test_firecrawl_scrape_url_with_invalid_url_returns_error():
    """
    What: Testing firecrawl scrape_url
    When: Given an invalid URL
    Expected: Returns error response
    """
```
```

**Tasks:**
- [ ] Create comprehensive test README
- [ ] Document all test fixtures
- [ ] Create test writing guide
- [ ] Add examples for common test patterns
- [ ] Create troubleshooting guide

---

### Phase 5: Maintenance & Culture (Ongoing) 🎯 Priority: LOW

**Goal:** Sustain TDD practices long-term

#### 5.1 Establish Testing Culture

**Team Practices:**
1. **No Code Without Tests** - Enforce with CI checks
2. **Test Reviews** - Review tests as carefully as code
3. **Test-First Mindset** - Always write test before code
4. **Coverage Goals** - 85% minimum, 95% target
5. **Performance SLAs** - Define and monitor

**Code Review Checklist:**
- [ ] Are there tests for new code?
- [ ] Do tests follow TDD principles?
- [ ] Are edge cases covered?
- [ ] Are tests readable and maintainable?
- [ ] Do tests use appropriate test doubles?
- [ ] Is test execution time reasonable?

#### 5.2 Continuous Improvement

**Monthly Activities:**
- Review test coverage reports
- Identify untested critical paths
- Refactor brittle tests
- Update test documentation
- Share testing wins and learnings

**Quarterly Activities:**
- Performance baseline updates
- Test suite optimization
- Testing tool evaluation
- Team training sessions

#### 5.3 Testing Metrics Dashboard

**Track Over Time:**
- Overall coverage %
- Coverage by component
- Test execution time
- Test flakiness rate
- Mutation score
- Bug escape rate (bugs found in production)
- Mean time to test (how long to write tests)

---

## Implementation Roadmap

### Week 1: Foundation
- [ ] Day 1-2: Set up CI/CD pipeline
- [ ] Day 2-3: Create test doubles/mocks
- [ ] Day 3-5: Add pre-commit hooks and missing unit tests

**Deliverables:**
- CI pipeline running
- 50% code coverage
- All routers tested

### Week 2: TDD Workflow
- [ ] Day 1-2: Property-based testing
- [ ] Day 3-4: Test data factories
- [ ] Day 5: TDD training and documentation

**Deliverables:**
- 70% code coverage
- Property tests for parsers
- TDD workflow guide

### Week 3: Advanced Testing
- [ ] Day 1-2: Integration tests with containers
- [ ] Day 3: E2E tests
- [ ] Day 4-5: Performance tests

**Deliverables:**
- 85% code coverage
- Full integration test suite
- Performance baseline

### Week 4: Quality Assurance
- [ ] Day 1-2: Mutation testing
- [ ] Day 3-4: Test quality metrics
- [ ] Day 5: Documentation and training

**Deliverables:**
- >80% mutation score
- Test metrics dashboard
- Comprehensive test documentation

---

## Success Metrics

### Coverage Targets

| Timeframe | Overall | Unit | Integration | E2E |
|-----------|---------|------|-------------|-----|
| Week 1 | 50% | 70% | 30% | 0% |
| Week 2 | 70% | 85% | 50% | 20% |
| Week 3 | 85% | 90% | 80% | 60% |
| Week 4 | 90% | 95% | 90% | 80% |

### Quality Targets

| Metric | Current | Target |
|--------|---------|--------|
| Test Pass Rate | ~98% | 100% |
| Test Execution Time (unit) | 0.69s | <2s |
| Test Execution Time (all) | ~40s | <3min |
| Mutation Score | Unknown | >80% |
| Test Flakiness | Unknown | <1% |
| Bug Escape Rate | Unknown | <5% |

---

## Estimated Effort

| Phase | Time | Priority | Resources |
|-------|------|----------|-----------|
| Phase 1: Foundation | 40 hours | Critical | 1 dev |
| Phase 2: TDD Workflow | 40 hours | High | 1 dev |
| Phase 3: Advanced Testing | 40 hours | Medium | 1 dev |
| Phase 4: Quality Assurance | 32 hours | Medium | 1 dev |
| Phase 5: Maintenance | Ongoing | Low | Team |
| **Total** | **152 hours** (~4 weeks) | | |

---

## Benefits

### Short-term (1 month)
- ✅ 3x fewer bugs in development
- ✅ Faster debugging (failing tests pinpoint issues)
- ✅ Confidence in refactoring
- ✅ Better code design

### Medium-term (3 months)
- ✅ 50% reduction in bug escape rate
- ✅ 30% faster feature development
- ✅ Living documentation via tests
- ✅ Easier onboarding for new developers

### Long-term (6+ months)
- ✅ Maintainable codebase
- ✅ Regression-free releases
- ✅ Technical excellence culture
- ✅ Lower technical debt

---

## Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Team resistance to TDD | High | Medium | Training, pair programming, show wins |
| Slow tests | Medium | High | Optimize, parallelize, use mocks |
| Brittle tests | Medium | Medium | Follow best practices, regular refactoring |
| Over-testing | Low | Low | Focus on critical paths, not 100% |
| Maintenance overhead | Medium | Low | Good test organization, documentation |

---

## Resources

### Tools
- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **pytest-asyncio**: Async test support
- **hypothesis**: Property-based testing
- **mutmut**: Mutation testing
- **testcontainers**: Integration test containers
- **locust**: Load testing (future)

### Learning Resources
- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) - Kent Beck
- [pytest documentation](https://docs.pytest.org/)
- [Property-Based Testing with Hypothesis](https://hypothesis.readthedocs.io/)
- [Testing FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)

### Team Support
- Weekly TDD office hours
- Pair programming sessions
- Test review in code reviews
- Monthly testing retrospectives

---

## Next Steps

1. **Review this plan** with team and stakeholders
2. **Prioritize phases** based on project needs
3. **Allocate resources** (1 developer for 4 weeks)
4. **Set up tracking** (create project board for tasks)
5. **Start Week 1** - Foundation phase
6. **Schedule weekly check-ins** to track progress

---

**Status:** 📋 Draft - Ready for Review  
**Owner:** Development Team  
**Reviewers:** Tech Lead, QA Lead  
**Approval Date:** TBD  
**Start Date:** TBD


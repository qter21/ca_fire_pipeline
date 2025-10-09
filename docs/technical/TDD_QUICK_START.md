# TDD Quick Start Guide

**Goal:** Get developers practicing true TDD immediately

---

## The Red-Green-Refactor Cycle

```
1. 🔴 RED: Write a failing test first
   ↓
2. 🟢 GREEN: Write minimal code to pass
   ↓
3. 🔵 REFACTOR: Improve while keeping tests green
   ↓
4. ✅ COMMIT: Save your work
   ↓
5. 🔄 REPEAT
```

---

## Example 1: Adding Rate Limiting

### Step 1: 🔴 RED - Write the Test First

```python
# tests/unit/test_firecrawl_service.py

def test_firecrawl_respects_rate_limit():
    """Test that service respects rate limit of 2 requests per second"""
    import time
    
    # Arrange
    service = FirecrawlService(rate_limit=2)
    urls = ["url1", "url2", "url3"]
    
    # Act
    start = time.time()
    with patch.object(service.app, 'scrape_url', return_value={}):
        service.batch_scrape(urls)
    duration = time.time() - start
    
    # Assert - Should take at least 1 second for 3 requests at 2 req/s
    assert duration >= 1.0, f"Expected ≥1s, got {duration:.2f}s"
```

**Run the test:**
```bash
pytest tests/unit/test_firecrawl_service.py::test_firecrawl_respects_rate_limit -v
```

**Expected:** ❌ Test fails (feature doesn't exist yet)

---

### Step 2: 🟢 GREEN - Minimal Implementation

```python
# pipeline/services/firecrawl_service.py

import time
from typing import Optional

class FirecrawlService:
    def __init__(self, api_key: Optional[str] = None, rate_limit: Optional[int] = None):
        self.api_key = api_key or settings.firecrawl_api_key
        self.app = FirecrawlApp(api_key=self.api_key)
        self.rate_limit = rate_limit  # NEW
        self._last_request_time = 0    # NEW
    
    def _enforce_rate_limit(self):     # NEW
        """Enforce rate limit if configured"""
        if self.rate_limit:
            elapsed = time.time() - self._last_request_time
            min_interval = 1.0 / self.rate_limit
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_time = time.time()
    
    def batch_scrape(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple URLs with rate limiting"""
        results = []
        for url in urls:
            self._enforce_rate_limit()  # NEW
            results.append(self.scrape_url(url))
        return results
```

**Run the test:**
```bash
pytest tests/unit/test_firecrawl_service.py::test_firecrawl_respects_rate_limit -v
```

**Expected:** ✅ Test passes

---

### Step 3: 🔵 REFACTOR - Improve Design

```python
# Add more tests for edge cases
def test_rate_limit_with_zero_raises_error():
    """Test that rate_limit=0 raises ValueError"""
    with pytest.raises(ValueError, match="Rate limit must be positive"):
        FirecrawlService(rate_limit=0)

def test_no_rate_limit_by_default():
    """Test that rate limiting is disabled by default"""
    service = FirecrawlService()
    assert service.rate_limit is None

# Improve implementation
class FirecrawlService:
    def __init__(self, api_key: Optional[str] = None, rate_limit: Optional[int] = None):
        self.api_key = api_key or settings.firecrawl_api_key
        self.app = FirecrawlApp(api_key=self.api_key)
        
        if rate_limit is not None and rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
        
        self.rate_limit = rate_limit
        self._last_request_time = 0
        self._rate_limiter = self._create_rate_limiter() if rate_limit else None
    
    def _create_rate_limiter(self):
        """Create rate limiter instance (can be swapped for token bucket, etc.)"""
        # Future: Use more sophisticated algorithm
        return SimpleRateLimiter(self.rate_limit)
```

**Run all tests:**
```bash
pytest tests/unit/test_firecrawl_service.py -v
```

**Expected:** ✅ All tests pass

---

### Step 4: ✅ COMMIT

```bash
git add tests/unit/test_firecrawl_service.py pipeline/services/firecrawl_service.py
git commit -m "feat: add rate limiting to Firecrawl service

- Add configurable rate_limit parameter
- Implement simple rate limiting in batch_scrape
- Add validation for rate limit value
- Add comprehensive tests

Closes #123"
```

---

## Example 2: Adding Database Query Optimization

### Step 1: 🔴 RED - Performance Test

```python
# tests/performance/test_database_performance.py

import pytest
import time
from pipeline.core.database import DatabaseManager

@pytest.mark.performance
def test_list_sections_performance(test_db):
    """Test that listing sections meets 100ms SLA"""
    # Arrange - Create 10,000 sections
    for i in range(10000):
        test_db.create_section(SectionCreate(
            code="PERF",
            section_num=str(i),
            content=f"Content {i}"
        ))
    
    # Act - Query 100 sections
    start = time.time()
    sections = test_db.list_sections(code="PERF", limit=100)
    duration = time.time() - start
    
    # Assert - Should be under 100ms
    assert duration < 0.1, f"Query took {duration*1000:.0f}ms, expected <100ms"
    assert len(sections) == 100
```

**Run:** ❌ Test fails (too slow without indexes)

---

### Step 2: 🟢 GREEN - Add Index

```python
# pipeline/core/database.py

class DatabaseManager:
    def __init__(self, mongodb_uri: str):
        # ... existing code ...
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        # Index on code for fast filtering
        self.sections_collection.create_index([("code", 1)])
        
        # Compound index for code + section_num (unique constraint)
        self.sections_collection.create_index(
            [("code", 1), ("section_num", 1)],
            unique=True
        )
        
        logger.info("Database indexes created")
```

**Run:** ✅ Test passes (fast with indexes)

---

### Step 3: 🔵 REFACTOR - Add More Indexes

```python
# Add test for section lookup by ID
def test_get_section_by_id_performance(test_db):
    """Test that getting section by ID is fast"""
    section_id = test_db.create_section(SectionCreate(code="TEST", section_num="1"))
    
    start = time.time()
    section = test_db.get_section(section_id)
    duration = time.time() - start
    
    assert duration < 0.01, f"Lookup took {duration*1000:.0f}ms, expected <10ms"

# Add more indexes
def _create_indexes(self):
    """Create database indexes for performance"""
    # Existing indexes...
    
    # Index for searching by content (text search)
    self.sections_collection.create_index([("content", "text")])
    
    # Index for filtering by version status
    self.sections_collection.create_index([("is_multi_version", 1)])
    
    # Index for job status queries
    self.jobs_collection.create_index([("status", 1), ("created_at", -1)])
```

---

## Common Patterns

### Pattern 1: Testing Error Handling

```python
# 1. RED - Test the error case
def test_scrape_url_with_network_error_retries():
    """Test that network errors trigger retry logic"""
    service = FirecrawlService()
    
    with patch.object(service.app, 'scrape_url') as mock_scrape:
        # Fail twice, succeed third time
        mock_scrape.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            {"success": True, "data": {}}
        ]
        
        result = service.scrape_url_with_retry("https://example.com", max_retries=3)
        
        assert result["success"] is True
        assert mock_scrape.call_count == 3

# 2. GREEN - Implement retry logic
def scrape_url_with_retry(self, url: str, max_retries: int = 3) -> Dict:
    """Scrape URL with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return self.scrape_url(url)
        except Exception as e:
            if attempt == max_retries - 1:
                return {"success": False, "error": str(e)}
            time.sleep(2 ** attempt)  # Exponential backoff

# 3. REFACTOR - Improve retry logic
def scrape_url_with_retry(self, url: str, max_retries: int = 3) -> Dict:
    """Scrape URL with exponential backoff retry"""
    backoff_strategy = ExponentialBackoff(base=2, max_delay=60)
    
    for attempt in range(max_retries):
        try:
            result = self.scrape_url(url)
            if result.get("success"):
                return result
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                delay = backoff_strategy.get_delay(attempt)
                time.sleep(delay)
            else:
                return {"success": False, "error": str(e)}
```

---

### Pattern 2: Testing Async Code

```python
# 1. RED - Test async function
@pytest.mark.asyncio
async def test_async_batch_scrape():
    """Test parallel scraping with asyncio"""
    service = AsyncFirecrawlService()
    urls = [f"https://example.com/{i}" for i in range(10)]
    
    start = time.time()
    results = await service.async_batch_scrape(urls)
    duration = time.time() - start
    
    # Should be faster than sequential (10 * 0.5s = 5s)
    assert duration < 2.0, "Async should be faster than sequential"
    assert len(results) == 10

# 2. GREEN - Implement async version
import asyncio
import aiohttp

class AsyncFirecrawlService:
    async def async_scrape_url(self, url: str) -> Dict:
        """Async version of scrape_url"""
        async with aiohttp.ClientSession() as session:
            # Implementation
            pass
    
    async def async_batch_scrape(self, urls: List[str]) -> List[Dict]:
        """Scrape multiple URLs in parallel"""
        tasks = [self.async_scrape_url(url) for url in urls]
        return await asyncio.gather(*tasks)

# 3. REFACTOR - Add semaphore for concurrency control
async def async_batch_scrape(
    self, 
    urls: List[str],
    max_concurrent: int = 5
) -> List[Dict]:
    """Scrape with controlled concurrency"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def scrape_with_semaphore(url):
        async with semaphore:
            return await self.async_scrape_url(url)
    
    tasks = [scrape_with_semaphore(url) for url in urls]
    return await asyncio.gather(*tasks)
```

---

### Pattern 3: Testing Data Transformations

```python
# 1. RED - Test transformation
def test_parse_legislative_history_extracts_year():
    """Test extracting year from legislative history"""
    history = "Enacted by Stats. 2023, Ch. 123, Sec. 5."
    
    result = ContentParser.extract_year_from_history(history)
    
    assert result == 2023

def test_parse_legislative_history_handles_multiple_years():
    """Test handling multiple years in history"""
    history = "Enacted by Stats. 2020, Ch. 1. Amended by Stats. 2023, Ch. 5."
    
    result = ContentParser.extract_years_from_history(history)
    
    assert result == [2020, 2023]

# 2. GREEN - Simple implementation
import re

class ContentParser:
    @staticmethod
    def extract_year_from_history(history: str) -> Optional[int]:
        """Extract year from legislative history"""
        match = re.search(r'Stats\.\s+(\d{4})', history)
        return int(match.group(1)) if match else None
    
    @staticmethod
    def extract_years_from_history(history: str) -> List[int]:
        """Extract all years from legislative history"""
        matches = re.findall(r'Stats\.\s+(\d{4})', history)
        return [int(year) for year in matches]

# 3. REFACTOR - Handle edge cases
@dataclass
class LegislativeHistory:
    """Structured legislative history"""
    years: List[int]
    chapters: List[str]
    original_text: str

class ContentParser:
    @staticmethod
    def parse_legislative_history(history: str) -> LegislativeHistory:
        """Parse legislative history into structured format"""
        # Extract years
        years = [int(y) for y in re.findall(r'Stats\.\s+(\d{4})', history)]
        
        # Extract chapters
        chapters = re.findall(r'Ch\.\s+(\d+)', history)
        
        return LegislativeHistory(
            years=years,
            chapters=chapters,
            original_text=history
        )
```

---

## Test Templates

### Unit Test Template

```python
# tests/unit/test_<component>.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from pipeline.<module> import <Class>

@pytest.fixture
def <fixture_name>():
    """Describe what this fixture provides"""
    return <Class>()

@pytest.mark.unit
class Test<Feature>:
    """Test <Feature> functionality"""
    
    def test_<what>_<when>_<expected>(self, <fixture>):
        """Test that <specific behavior>"""
        # Arrange
        input_data = {...}
        expected_output = {...}
        
        # Act
        result = <fixture>.method(input_data)
        
        # Assert
        assert result == expected_output
    
    def test_<what>_with_invalid_input_raises_error(self, <fixture>):
        """Test error handling for invalid input"""
        # Arrange
        invalid_input = {...}
        
        # Act & Assert
        with pytest.raises(ValueError, match="Expected error message"):
            <fixture>.method(invalid_input)
```

---

### Integration Test Template

```python
# tests/integration/test_<component>_integration.py

import pytest

@pytest.fixture(scope="module")
def test_database():
    """Provide test database for integration tests"""
    # Setup
    db = DatabaseManager(test_connection_string)
    yield db
    # Teardown
    db.drop_database()

@pytest.mark.integration
@pytest.mark.slow
class Test<Component>Integration:
    """Integration tests for <Component>"""
    
    def test_<workflow>_end_to_end(self, test_database):
        """Test complete workflow from A to Z"""
        # Arrange
        initial_state = ...
        
        # Act
        component = <Component>(database=test_database)
        result = component.execute_workflow(initial_state)
        
        # Assert
        assert result.success is True
        
        # Verify database state
        saved_data = test_database.get(...)
        assert saved_data == expected_data
```

---

## TDD Best Practices

### ✅ DO

1. **Write test first** - Always red before green
2. **One assertion per test** - Test one thing
3. **Descriptive names** - `test_what_when_expected`
4. **Arrange-Act-Assert** - Clear test structure
5. **Fast tests** - Unit tests in milliseconds
6. **Independent tests** - No test dependencies
7. **Mock external services** - Don't hit real APIs
8. **Test behavior, not implementation** - Test what, not how
9. **Refactor tests** - Keep them clean too
10. **Commit often** - Each red-green-refactor cycle

### ❌ DON'T

1. **Don't skip the red phase** - Always see it fail first
2. **Don't write too much code** - Minimal to pass
3. **Don't test implementation details** - Test interface
4. **Don't have slow tests** - Use mocks for unit tests
5. **Don't ignore failing tests** - Fix or remove
6. **Don't have flaky tests** - Tests must be deterministic
7. **Don't over-mock** - Mock only external dependencies
8. **Don't test third-party code** - Trust it works
9. **Don't write tests without value** - Test important behavior
10. **Don't skip refactoring** - Clean code matters

---

## Keyboard Shortcuts (pytest)

```bash
# Run specific test
pytest tests/unit/test_file.py::TestClass::test_method -v

# Run with keyword
pytest -k "test_keyword" -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Run last failed tests only
pytest --lf

# Run tests that failed, then all others
pytest --ff

# Run in parallel (requires pytest-xdist)
pytest -n auto

# Watch mode (requires pytest-watch)
ptw -- tests/unit/ -v
```

---

## Daily TDD Workflow

### Morning (15 min)
```bash
# 1. Pull latest code
git pull origin main

# 2. Run full test suite
pytest tests/ -v

# 3. Check coverage
pytest tests/ --cov=pipeline --cov-report=term-missing

# 4. Review failures (if any)
```

### During Development
```bash
# 1. Write failing test
vim tests/unit/test_feature.py

# 2. Run test (watch it fail)
pytest tests/unit/test_feature.py::test_new_feature -v

# 3. Write minimal code
vim pipeline/module.py

# 4. Run test (watch it pass)
pytest tests/unit/test_feature.py::test_new_feature -v

# 5. Refactor
vim pipeline/module.py

# 6. Run tests (keep them green)
pytest tests/unit/test_feature.py -v

# 7. Commit
git commit -m "feat: add new feature"
```

### Before Push
```bash
# 1. Run all tests
pytest tests/ -v

# 2. Check coverage
pytest tests/ --cov=pipeline

# 3. Run linters
black pipeline/ tests/
flake8 pipeline/ tests/

# 4. Push
git push origin feature-branch
```

---

## Troubleshooting

### Test is Slow (>100ms for unit test)

**Problem:** Test takes too long

**Solution:**
```python
# Before (slow - hits real database)
def test_create_section():
    db = DatabaseManager(real_connection_string)
    section = db.create_section(...)
    assert section.id is not None

# After (fast - uses mock)
def test_create_section():
    db = Mock(spec=DatabaseManager)
    db.create_section.return_value = Section(id="123")
    section = db.create_section(...)
    assert section.id == "123"
```

---

### Test is Flaky (Sometimes Passes, Sometimes Fails)

**Problem:** Non-deterministic test

**Common Causes:**
1. Time-dependent logic
2. Random data
3. Race conditions
4. External dependencies

**Solutions:**
```python
# 1. Mock time
from freezegun import freeze_time

@freeze_time("2023-01-01 12:00:00")
def test_with_fixed_time():
    # Time is now frozen at 2023-01-01 12:00:00
    pass

# 2. Seed random
import random
random.seed(42)

# 3. Use deterministic test data
def test_with_deterministic_data():
    # Don't use: random.choice(data)
    # Use: specific_test_data[0]
    pass

# 4. Mock external services
with patch('external.api.call') as mock:
    mock.return_value = fixed_response
```

---

### Test Passes but Feature Doesn't Work

**Problem:** Test doesn't actually test the feature

**Solution:**
```python
# Bad test (tests nothing)
def test_scrape_url():
    service = FirecrawlService()
    result = service.scrape_url("https://example.com")
    # Missing assertions!

# Good test (verifies behavior)
def test_scrape_url_returns_markdown():
    service = FirecrawlService()
    result = service.scrape_url("https://example.com")
    
    assert result["success"] is True
    assert "markdown" in result["data"]
    assert len(result["data"]["markdown"]) > 0
```

---

## Getting Help

### In the Codebase
- Review existing tests in `tests/unit/` for patterns
- Check `tests/conftest.py` for available fixtures
- Read test docstrings for examples

### Team Resources
- Weekly TDD office hours (schedule TBD)
- Pair programming sessions
- Code review feedback
- Team Slack channel: #testing

### External Resources
- [pytest documentation](https://docs.pytest.org/)
- [TDD by Kent Beck](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [pytest examples](https://docs.pytest.org/en/stable/example/index.html)

---

**Remember:** TDD is a discipline. It feels slow at first, but leads to faster development and fewer bugs in the long run. Stick with it!

🔴 **RED** → 🟢 **GREEN** → 🔵 **REFACTOR** → ✅ **COMMIT** → 🔄 **REPEAT**


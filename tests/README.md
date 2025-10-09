# Testing Guide - CA Fire Pipeline

Welcome to the testing documentation for the CA Fire Pipeline project. This guide will help you understand our testing strategy, write effective tests, and maintain high code quality.

---

## 📂 Test Organization

```
tests/
├── unit/                           # Fast, isolated tests
│   ├── test_firecrawl_service.py  # Firecrawl client tests
│   ├── test_content_parser.py     # Parsing logic tests
│   ├── test_architecture_crawler.py # Crawler tests
│   ├── test_database.py           # Database model tests
│   └── test_routers/              # API endpoint tests
│       └── test_crawler_api.py
│
├── integration/                    # Component interaction tests
│   ├── test_section_extraction.py # Section extraction workflow
│   ├── test_yaml_data.py          # Real data validation
│   ├── test_pipeline.py           # Full pipeline tests
│   └── test_api.py                # API integration tests
│
├── e2e/                           # End-to-end tests (planned)
│   └── test_complete_pipeline.py
│
├── performance/                    # Performance & load tests (planned)
│   └── test_performance.py
│
├── contract/                       # API contract tests (planned)
│   └── test_api_contracts.py
│
├── mocks/                         # Mock implementations
│   ├── mock_firecrawl.py         # Mock Firecrawl API
│   └── mock_database.py          # Mock database (planned)
│
├── fixtures/                      # Test data
│   └── test_sections_data.yaml   # Real section data
│
├── conftest.py                    # Shared pytest fixtures
└── README.md                      # This file
```

---

## 🎯 Test Types

### Unit Tests (Fast, Isolated)
- **Purpose:** Test individual functions/classes in isolation
- **Speed:** <5 seconds for entire suite
- **Dependencies:** Use mocks for external services
- **Run:** On every commit

```bash
pytest tests/unit/ -v
```

### Integration Tests (Component Interaction)
- **Purpose:** Test how components work together
- **Speed:** <2 minutes
- **Dependencies:** May use test containers or test databases
- **Run:** Before every push

```bash
pytest tests/integration/ -v -m "not slow"
```

### E2E Tests (Complete Workflows)
- **Purpose:** Test entire user workflows
- **Speed:** <5 minutes
- **Dependencies:** Full system required
- **Run:** In CI before merge

```bash
pytest tests/e2e/ -v
```

### Performance Tests (SLA Validation)
- **Purpose:** Ensure performance requirements are met
- **Speed:** Varies
- **Dependencies:** Realistic data volumes
- **Run:** Nightly in CI

```bash
pytest tests/performance/ -v
```

---

## 🚀 Quick Start

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests (fast)
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_firecrawl_service.py -v

# Run specific test
pytest tests/unit/test_firecrawl_service.py::TestFirecrawlService::test_init -v

# Run with keyword filter
pytest -k "firecrawl" -v

# Stop on first failure
pytest tests/unit/ -x

# Show print statements
pytest tests/unit/ -s

# Run last failed tests
pytest --lf
```

### Coverage

```bash
# Run with coverage
pytest tests/ --cov=pipeline --cov-report=html

# View coverage report
open htmlcov/index.html

# Check coverage meets threshold
pytest tests/unit/ --cov=pipeline --cov-fail-under=80
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run multi-version tests
pytest -m multi_version
```

---

## ✍️ Writing Tests

### TDD Workflow (Red-Green-Refactor)

1. **🔴 RED:** Write a failing test first
2. **🟢 GREEN:** Write minimal code to pass
3. **🔵 REFACTOR:** Improve while keeping tests green
4. **✅ COMMIT:** Save your work

See [TDD_QUICK_START.md](../docs/technical/TDD_QUICK_START.md) for detailed examples.

### Test Naming Convention

```python
def test_<what>_<when>_<expected>():
    """Docstring: Describe the specific behavior being tested"""
    pass
```

**Examples:**
- `test_firecrawl_scrape_url_with_valid_url_returns_success()`
- `test_content_parser_with_empty_markdown_returns_none()`
- `test_database_create_section_with_duplicate_raises_error()`

### Test Structure (Arrange-Act-Assert)

```python
def test_example():
    """Test that example function works correctly"""
    # Arrange - Set up test data and preconditions
    input_data = {"key": "value"}
    expected_result = {"processed": "value"}
    
    # Act - Execute the function being tested
    result = example_function(input_data)
    
    # Assert - Verify the results
    assert result == expected_result
```

---

## 🛠️ Testing Tools & Fixtures

### Available Fixtures

```python
# Defined in conftest.py

@pytest.fixture
def test_sections_data():
    """Load test sections from YAML file"""
    # Returns list of test section data

@pytest.fixture
def firecrawl_service():
    """Create FirecrawlService instance"""
    # Returns configured FirecrawlService

@pytest.fixture
def sample_section_data():
    """Sample section for quick tests"""
    # Returns single test section

@pytest.fixture
def sample_multi_version_section():
    """Sample multi-version section"""
    # Returns multi-version test data

@pytest.fixture
def mock_firecrawl_response():
    """Mock Firecrawl API response"""
    # Returns mock API response
```

### Using Mocks

```python
from unittest.mock import Mock, patch
from tests.mocks.mock_firecrawl import MockFirecrawlApp

# Mock external API
def test_with_mock():
    mock_api = MockFirecrawlApp()
    service = FirecrawlService()
    service.app = mock_api  # Replace real API with mock
    
    result = service.scrape_url("https://example.com")
    assert mock_api.get_call_count() == 1

# Patch at import
@patch('pipeline.services.firecrawl_service.FirecrawlApp')
def test_with_patch(mock_app_class):
    mock_app_class.return_value = MockFirecrawlApp()
    service = FirecrawlService()
    # Uses mock automatically
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("section_num,expected", [
    ("1", True),
    ("100", True),
    ("73d", True),
    ("", False),
])
def test_section_number_validation(section_num, expected):
    """Test section number validation with multiple inputs"""
    result = is_valid_section_number(section_num)
    assert result == expected
```

---

## 📊 Coverage Goals

| Component | Current | Target | Priority |
|-----------|---------|--------|----------|
| Models | 100% | 100% | ✅ Met |
| Services | 25% | 90% | 🔴 Critical |
| Routers | 0% | 85% | 🔴 Critical |
| Database | 23% | 85% | 🔴 Critical |
| Utils | - | 80% | ⚠️ Medium |
| **Overall** | **27%** | **85%** | 🔴 **Critical** |

---

## 🐛 Debugging Tests

### Common Issues

**Test is slow (>100ms for unit test)**
```python
# Problem: Hitting real API
result = firecrawl.scrape_url("https://example.com")

# Solution: Use mock
from tests.mocks.mock_firecrawl import MockFirecrawlApp
firecrawl.app = MockFirecrawlApp()
result = firecrawl.scrape_url("https://example.com")
```

**Test is flaky (sometimes passes, sometimes fails)**
```python
# Problem: Time-dependent code
timestamp = datetime.now()

# Solution: Freeze time
from freezegun import freeze_time

@freeze_time("2023-01-01 12:00:00")
def test_with_fixed_time():
    timestamp = datetime.now()  # Always 2023-01-01 12:00:00
```

**Test passes but code is broken**
```python
# Problem: Missing assertions
def test_scrape():
    result = scrape_url("url")
    # Missing: assert statements!

# Solution: Add assertions
def test_scrape():
    result = scrape_url("url")
    assert result["success"] is True
    assert "data" in result
    assert len(result["data"]) > 0
```

---

## 🔧 Test Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests (require API calls)
    multi_version: Tests for multi-version sections
```

### Coverage Configuration

```ini
# .coveragerc
[run]
source = pipeline
omit =
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

## 📝 Best Practices

### ✅ DO

1. **Write tests first** (TDD red-green-refactor)
2. **One assertion per test** (usually)
3. **Use descriptive names** (`test_what_when_expected`)
4. **Keep tests fast** (unit tests <100ms)
5. **Make tests independent** (no test dependencies)
6. **Mock external services** (APIs, databases)
7. **Test behavior, not implementation**
8. **Use fixtures for setup**
9. **Clean up after tests**
10. **Document complex tests**

### ❌ DON'T

1. **Don't skip red phase** (always see it fail)
2. **Don't test implementation details**
3. **Don't have slow unit tests**
4. **Don't ignore failing tests**
5. **Don't have flaky tests**
6. **Don't over-mock** (only external deps)
7. **Don't test third-party code**
8. **Don't write tests without value**
9. **Don't have test dependencies**
10. **Don't commit broken tests**

---

## 🔄 Continuous Integration

### GitHub Actions

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Nightly (for slow tests)

### CI Pipeline

1. **Lint & Format Check**
   - flake8 for linting
   - black for formatting
   - mypy for type checking

2. **Unit Tests**
   - Run on Python 3.11 & 3.12
   - Must maintain 80% coverage
   - Must complete in <2 minutes

3. **Integration Tests**
   - Run on Python 3.12 only
   - Use test containers (MongoDB)
   - Must complete in <5 minutes

4. **Coverage Report**
   - Upload to Codecov
   - Fail if below threshold

See [.github/workflows/tests.yml](../.github/workflows/tests.yml) for details.

---

## 📚 Resources

### Documentation
- [TDD Improvement Plan](../docs/technical/TDD_IMPROVEMENT_PLAN.md) - Comprehensive plan
- [TDD Quick Start](../docs/technical/TDD_QUICK_START.md) - Practical examples
- [pytest documentation](https://docs.pytest.org/) - Official docs

### Books
- [Test-Driven Development by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530) - Kent Beck
- [Growing Object-Oriented Software, Guided by Tests](http://www.growing-object-oriented-software.com/)

### Training
- Weekly TDD office hours
- Pair programming sessions
- Code review feedback

---

## 🆘 Getting Help

- **Team Slack:** #testing
- **Code Reviews:** Ask for test feedback
- **Office Hours:** Weekly TDD session
- **Documentation:** This file and linked docs
- **Examples:** Look at existing tests in `tests/unit/`

---

## 📈 Test Metrics

Track these metrics over time:
- Overall coverage %
- Coverage by component
- Test execution time
- Test flakiness rate
- Bug escape rate

View current metrics: [Coverage Report](../htmlcov/index.html)

---

**Remember:** Good tests are the foundation of maintainable software. Invest time in testing now to save time debugging later!

🔴 RED → 🟢 GREEN → 🔵 REFACTOR → ✅ COMMIT


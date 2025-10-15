# CA Fire Pipeline

Firecrawl-based data pipeline for fetching California legal codes from [leginfo.legislature.ca.gov](https://leginfo.legislature.ca.gov/faces/home.xhtml).

## 🎉 Status: v0.3.1 - PROB Code Added!

**Current Status:** ✅ **v0.3.1 Production** - 6 codes live on codecond.com
**Latest Update:** Added PROB (Probate Code) - 2,710 sections processed successfully
**Production Codes:** CCP (3,354), EVID (506), FAM (1,626), GOV (21,418), PEN (5,660), PROB (2,710) = **35,274 sections**
**Live URL:** https://www.codecond.com
**Architecture:** All code hierarchies correctly match official website structure
**Testing:** 26/26 unit tests passing, 100% section preservation
**Performance:** **10x faster than old pipeline** with accurate tree structures
**Progress:** 6/30 codes (20%) | **24 codes remaining**

## 🎯 Project Goal

Replace the existing Playwright-based `legal-codes-pipeline` with a faster, more efficient Firecrawl-based solution that:
- ✅ Reduces processing time by 6-10x (achieved!)
- ✅ Hybrid architecture (Firecrawl + Playwright for multi-version)
- ✅ Full MongoDB integration
- ✅ REST API with 8 endpoints
- ✅ Production-ready code structure

## 🚀 Quick Start

### Prerequisites

- **Python 3.12** (recommended) or Python 3.11+
- Firecrawl API key ([get one here](https://firecrawl.dev))
- MongoDB (optional for POC, required for production)

### Installation

```bash
# Clone/navigate to project
cd ca_fire_pipeline

# Create virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your FIRECRAWL_API_KEY
```

**Note:** Python 3.12 provides ~25% better performance and improved error messages compared to older versions.

### Run the API Server

```bash
# Start the API server
python pipeline/main.py

# Server will start on http://localhost:8001
# API documentation available at http://localhost:8001/docs
```

### Run Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=pipeline --cov-report=html

# Run POC script
python scripts/poc_firecrawl.py
```

### Use the API

```bash
# Start a pipeline job
curl -X POST http://localhost:8001/api/v2/crawler/start/EVID

# Check job status
curl http://localhost:8001/api/v2/crawler/status/{job_id}

# Health check
curl http://localhost:8001/health
```

## 🏗️ Architecture

```
ca_fire_pipeline/
├── pipeline/
│   ├── core/
│   │   ├── config.py                      # Configuration settings
│   │   └── database.py                    # MongoDB operations
│   ├── models/
│   │   ├── section.py                     # Section & Version models
│   │   ├── code.py                        # Code metadata model
│   │   └── job.py                         # Job tracking model
│   ├── services/
│   │   ├── architecture_crawler.py        # Stage 1: URL discovery
│   │   ├── content_extractor.py           # Stage 2 & 3: Content extraction
│   │   ├── firecrawl_service.py           # Firecrawl API client
│   │   ├── content_parser.py              # Content parsing utilities
│   │   └── multi_version_handler.py       # Multi-version handler
│   ├── routers/
│   │   ├── health.py                      # Health check endpoint
│   │   └── crawler.py                     # Crawler API endpoints
│   └── main.py                            # FastAPI application
├── tests/
│   ├── unit/                              # 36 unit tests
│   ├── integration/                       # Integration tests
│   └── fixtures/                          # Test data
├── docs/
│   ├── technical/                         # Architecture, setup guides
│   └── reports/                           # Status updates, test results
├── scripts/
│   └── poc_firecrawl.py                   # POC test script
└── requirements.txt
```

## 📈 Performance (Validated at Scale)

### Actual Test Results (4 Codes)

| Code | Sections | Stage 1 | Stage 2 | Stage 3 | Total | Success |
|------|----------|---------|---------|---------|-------|---------|
| **FAM** | 1,626 | 3.28 min | 69.91 min | 0.98 min | **74.2 min** | 100% |
| **CCP** | 3,353 | 6.62 min | 16.10 min | 0.92 min | **23.6 min** | 99.8% |
| **EVID** | 506 | 0.96 min | 2.47 min | 0 | **3.4 min** | 100% |
| **PEN** | 5,660 | 8.06 min | 24.24 min | 5.66 min | **38.0 min** | 100% |
| **Total** | **11,145** | **~19 min** | **~113 min** | **~8 min** | **~140 min** | **99.95%** |

**Average with Concurrent (25 workers):** 0.75s per section (9x faster than sequential)

### All 30 California Codes (Projected from 4-Code Results)

| Metric | Old Pipeline | New Pipeline (Concurrent) | Improvement |
|--------|--------------|---------------------------|-------------|
| Total Time | 60-100 hours | **4-6 hours** 🚀 | **10-25x faster** ✅ |
| Stage 1 | ~10-20 hours | ~2 hours | Tree + requests |
| Stage 2 | ~40-70 hours | ~1.5-2 hours | Concurrent (25 workers) 🚀 |
| Stage 3 | ~10-20 hours | ~1-2 hours | Playwright |
| Success Rate | ~95% | **99.95%** | Better ✅ |
| Throughput | ~3-5 sec/section | ~0.75 sec/section | 4-7x faster |

**Confidence:** VERY HIGH (validated with 11,145 sections across 4 diverse codes)

## 🔧 Configuration

Edit `.env` file:

```bash
# Firecrawl API
FIRECRAWL_API_KEY=your-api-key-here

# MongoDB (for production)
MONGODB_URI=mongodb://admin:legalcodes123@mongodb:27017/ca_codes_db

# Pipeline Settings
BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=5
```

## 📝 Development Status

### ✅ Phase 1: Core Pipeline (COMPLETE)

- [x] Project structure setup
- [x] Firecrawl service client
- [x] Content parser utilities
- [x] Multi-version handler (Playwright)
- [x] **Architecture crawler with tree structure** ✅
- [x] **Concurrent content extractor (9x faster)** ✅
- [x] **MongoDB integration (100% compatible)** ✅
- [x] **Complete legislative history extraction** ✅
- [x] **Pydantic models (Section, Code, Job)** ✅
- [x] **FastAPI application (8 endpoints)** ✅
- [x] **36 unit tests (100% pass rate)** ✅
- [x] **4 codes processed (11,145 sections)** ✅
- [x] **10 bugs found and fixed** ✅

### 📋 Phase 2: Production Deployment (COMPLETE ✅)

- [x] ✅ Concurrent scraping (implemented - 9x faster)
- [x] ✅ Error handling & retry logic (10 error types)
- [x] ✅ Tree structure (implemented)
- [x] ✅ **Docker deployment** (Ubuntu 22.04 + Playwright)
- [x] ✅ **Production validation** (EVID + FAM processed successfully)
- [x] ✅ **GCloud deployment** (codecond instance, us-west2-a)
- [x] ✅ **API integration** (legal-codes-api serving data)
- [x] ✅ **Website integration** (https://www.codecond.com live)
- [ ] Process remaining 26 codes (ready to start)

### ✅ Phase 3: Architecture Parser Fix (COMPLETE)

- [x] ✅ **Identified node type classification bug** (word boundary issue)
- [x] ✅ **Fixed `_determine_node_type()` method** (regex word boundaries)
- [x] ✅ **Re-crawled all 4 codes** (CCP, FAM, EVID, PEN)
- [x] ✅ **55 nodes correctly reclassified** (PART → CHAPTER/ARTICLE/TITLE)
- [x] ✅ **Zero data loss** (11,146 sections preserved)
- [x] ✅ **All tests passing** (26/26 unit tests)
- [x] ✅ **Comprehensive documentation** (3 new technical docs)

**See:** `docs/reports/ARCHITECTURE_PARSER_FIX.md` for details

### 🔜 Phase 4: Complete Dataset

- [x] ✅ Production validation (4 codes, 11,146 sections, 100% success)
- [ ] Process remaining 25 California codes
- [ ] Complete all 30 codes dataset

## 🔗 Related Projects

- **legal-codes-pipeline** - Current Playwright-based pipeline (to be replaced)
- **legal-codes-api** - Read-only API serving the data
- **codecond-ca** - Frontend application

## 🧪 Testing & Quality

### Current Test Status
- **Coverage:** 27% (target: 85%)
- **Unit Tests:** 36 tests
- **Integration Tests:** 14 tests
- **Status:** TDD improvement plan ready for implementation

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only (fast)
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=pipeline --cov-report=html

# View coverage report
open htmlcov/index.html
```

### TDD Resources

- **[Testing Guide](tests/README.md)** - Complete testing documentation
- **[TDD Executive Summary](docs/technical/TDD_EXECUTIVE_SUMMARY.md)** - Quick overview & ROI
- **[TDD Improvement Plan](docs/technical/TDD_IMPROVEMENT_PLAN.md)** - Comprehensive 4-phase plan
- **[TDD Quick Start](docs/technical/TDD_QUICK_START.md)** - Practical examples & workflow

## 📖 Documentation

### Project Documentation

- **[Technical Docs](docs/technical/)** - Architecture, setup guides, configuration
  - [PROJECT_STATUS.md](docs/technical/PROJECT_STATUS.md) - Current status & roadmap
  - [SETUP.md](docs/technical/SETUP.md) - Detailed setup instructions
  - [PYTHON_UPGRADE.md](docs/technical/PYTHON_UPGRADE.md) - Python 3.12 upgrade guide
  - [TDD_EXECUTIVE_SUMMARY.md](docs/technical/TDD_EXECUTIVE_SUMMARY.md) - TDD improvement overview ⭐ NEW
  - [TDD_IMPROVEMENT_PLAN.md](docs/technical/TDD_IMPROVEMENT_PLAN.md) - Complete TDD plan ⭐ NEW
  - [TDD_QUICK_START.md](docs/technical/TDD_QUICK_START.md) - TDD workflow guide ⭐ NEW

- **[Reports & Status](docs/reports/)** - Test results, achievements, summaries
  - [PHASE1_COMPLETE.md](docs/reports/PHASE1_COMPLETE.md) - Phase 1 completion ⭐
  - [SUCCESS_SUMMARY.md](docs/reports/SUCCESS_SUMMARY.md) - 100% test achievement
  - [POC_RESULTS_FINAL.md](docs/reports/POC_RESULTS_FINAL.md) - POC analysis
  - [MULTI_VERSION_STATUS.md](docs/reports/MULTI_VERSION_STATUS.md) - Multi-version implementation

### External Documentation

- [Firecrawl API Docs](https://docs.firecrawl.dev)
- [California Legislative Info](https://leginfo.legislature.ca.gov)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [pytest Documentation](https://docs.pytest.org/)

## 🛠️ Tech Stack

- **Python 3.12** - Latest stable Python (25% faster than 3.9)
- **Firecrawl** - Web scraping API
- **FastAPI** - API framework
- **MongoDB** - Database
- **Pydantic** - Data validation
- **pytest** - Testing framework (TDD approach)

## 📄 License

See main project for license information.

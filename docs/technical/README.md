# Technical Documentation

This folder contains technical documentation including architecture, design decisions, setup guides, and configuration.

## 📚 Documents

### Project Status & Architecture
**[PROJECT_STATUS.md](PROJECT_STATUS.md)**
- Current project status and phases
- Architecture overview
- Implementation roadmap (Phase 1-4)
- Performance metrics
- Risk assessment
- Success criteria

**Key Sections:**
- POC completion summary
- Architecture stack (Firecrawl + Playwright)
- Performance vs old pipeline (6-8x faster)
- 4-phase implementation plan
- Cost estimates

---

### Setup & Installation
**[SETUP.md](SETUP.md)**
- Step-by-step installation guide
- Environment configuration
- Dependency installation
- Database setup
- API key configuration
- Testing instructions

**Quick Start:**
```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/
```

---

### Python Upgrade
**[PYTHON_UPGRADE.md](PYTHON_UPGRADE.md)**
- Python 3.12 upgrade details
- Performance improvements (25% faster)
- Compatibility notes
- Migration guide
- Test results comparison

**Benefits:**
- 25% faster execution
- 37% faster unit tests
- Better error messages
- Modern tooling support

---

## 🔗 Related Documentation

- **Reports:** See `../reports/` for test results and status updates
- **Main README:** See `../../README.md` for project overview
- **API Docs:** Run server and visit `http://localhost:8001/docs`

---

**Last Updated:** October 8, 2025

# Setup Guide - CA Fire Pipeline POC

## Step 1: Get Firecrawl API Key

1. Visit [https://firecrawl.dev](https://firecrawl.dev)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Free tier includes 500 credits/month

## Step 2: Install Dependencies

```bash
# Install Python 3.12 (if not already installed)
# On macOS with Homebrew:
brew install python@3.12

# Create virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Why Python 3.12?

- **25% faster** than Python 3.9
- **Better error messages** for debugging
- **Improved type hints** for better IDE support
- **Latest security patches**

## Step 3: Configure API Key

Edit `.env` file and replace the API key:

```bash
FIRECRAWL_API_KEY=fc-your-actual-api-key-here
```

## Step 4: Run POC Tests

```bash
# Make sure virtual environment is activated
python scripts/poc_firecrawl.py
```

## What the POC Tests

The POC will run 5 tests to validate Firecrawl capabilities:

### Test 1: Architecture Scraping
- Scrapes the EVID code structure page
- Extracts all section links
- Validates HTML/Markdown output
- **Expected time:** ~2-5 seconds

### Test 2: Section Content Extraction
- Scrapes a single section (EVID §1)
- Extracts section text and metadata
- **Expected time:** ~1-2 seconds

### Test 3: Batch Scraping
- Scrapes 5 sections in sequence
- Measures batch performance
- **Expected time:** ~5-10 seconds total

### Test 4: Multi-Version Detection
- Tests with FAM §3044 (known multi-version)
- Detects version selector page
- Extracts version options
- **Expected time:** ~2-3 seconds

### Test 5: Structured Extraction (Optional)
- Uses JSON schema to extract structured data
- May be skipped in initial POC

## Expected Output

```
============================================================
🔥 FIRECRAWL POC - California Legal Codes
============================================================
Start time: 2025-10-08 10:30:00

============================================================
TEST 1: Architecture Scraping
============================================================
URL: https://leginfo.legislature.ca.gov/faces/codedisplayexpand.xhtml?tocCode=EVID
✅ Success! Found 350 section links
⏱️  Duration: 2.34s
📄 HTML length: 125,432 chars
📝 Markdown length: 45,678 chars

Sample links:
  1. 1. Scope of code.
  2. 2. Construction of code.
  3. 3. Severability.
  ...

[Additional tests follow...]

============================================================
📊 TEST SUMMARY
============================================================
Total tests: 4
Successful: 4/4
Total duration: 12.45s
Average per test: 3.11s

💾 Results saved to: poc_results/firecrawl_poc_20251008_103012.json
```

## Troubleshooting

### "FIRECRAWL_API_KEY not set" error
- Make sure you edited `.env` file
- Check the API key is correct (starts with `fc-`)
- Make sure `.env` is in the project root

### Import errors
- Activate virtual environment: `source venv/bin/activate`
- Reinstall: `pip install -r requirements.txt`

### Connection errors
- Check internet connection
- Verify Firecrawl API is accessible
- Check API key is valid

## Next Steps

After successful POC:
1. Review results in `poc_results/` directory
2. Compare performance with current Playwright pipeline
3. Decide on full implementation
4. Implement Stage 1 (URL discovery)
5. Implement Stage 2 (content extraction)
6. Implement Stage 3 (multi-version handling)

## API Usage

The POC will use approximately:
- **Test 1:** 1 API call (architecture page)
- **Test 2:** 1 API call (single section)
- **Test 3:** 5 API calls (batch of 5 sections)
- **Test 4:** 1 API call (multi-version section)

**Total:** ~8 API calls ≈ 8 credits from your free tier

## Cost Estimation

For full production use:
- Small code (500 sections): ~500 credits ≈ $0.50-2.50
- Large code (1600 sections): ~1600 credits ≈ $1.60-8.00
- All 30 codes (~20,000 sections): ~20,000 credits ≈ $20-100

Compare to current costs:
- Server time savings: 75% reduction
- Infrastructure: Simpler (no Chromium/Playwright)

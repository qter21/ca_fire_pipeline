#!/bin/bash
# Quick start script for CA Fire Pipeline POC

echo "================================================"
echo "CA Fire Pipeline - Quick Start"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt -q

# Check if API key is set
if grep -q "REPLACE_WITH_YOUR_API_KEY" .env; then
    echo ""
    echo "⚠️  WARNING: Firecrawl API key not configured!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Get API key from https://firecrawl.dev"
    echo "2. Edit .env file and replace FIRECRAWL_API_KEY"
    echo "3. Run this script again"
    echo ""
    exit 1
fi

# Run POC
echo ""
echo "🚀 Running POC tests..."
echo ""
python scripts/poc_firecrawl.py

echo ""
echo "================================================"
echo "✅ POC Complete!"
echo "================================================"
echo "Check poc_results/ directory for detailed results"
echo ""

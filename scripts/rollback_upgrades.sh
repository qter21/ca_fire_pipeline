#!/bin/bash
# Rollback script for pipeline upgrades
# Run this script to restore to the state before upgrades

echo "=========================================="
echo "Pipeline Upgrade Rollback Script"
echo "=========================================="
echo ""
echo "This will restore all files to their state before the upgrades."
echo "Modified files:"
echo "  - pipeline/core/config.py"
echo "  - pipeline/services/content_extractor_concurrent.py"
echo "  - pipeline/services/firecrawl_concurrent.py"
echo "  - scripts/process_code_with_reconciliation.py"
echo "  - pipeline/models/checkpoint.py (will be deleted)"
echo ""
read -p "Continue with rollback? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled."
    exit 1
fi

echo ""
echo "Creating backup of current state..."
BACKUP_BRANCH="upgrade-backup-$(date +%Y%m%d_%H%M%S)"
git checkout -b "$BACKUP_BRANCH" 2>/dev/null
git add -A
git commit -m "Backup: Pipeline upgrades before rollback" 2>/dev/null

echo ""
echo "Switching back to main..."
git checkout main

echo ""
echo "Restoring files..."
git restore pipeline/core/config.py
git restore pipeline/services/content_extractor_concurrent.py
git restore pipeline/services/firecrawl_concurrent.py
git restore scripts/process_code_with_reconciliation.py

echo ""
echo "Removing new files..."
if [ -f "pipeline/models/checkpoint.py" ]; then
    rm pipeline/models/checkpoint.py
    echo "  ✓ Removed checkpoint.py"
fi

echo ""
echo "=========================================="
echo "Rollback Complete!"
echo "=========================================="
echo ""
echo "Your changes have been saved to branch: $BACKUP_BRANCH"
echo "To restore the upgrades later, run:"
echo "  git checkout $BACKUP_BRANCH"
echo ""
echo "Current status:"
git status

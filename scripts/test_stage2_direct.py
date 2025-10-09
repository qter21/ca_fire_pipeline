"""Test Stage 2 directly with known section URLs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager
from pipeline.services.content_extractor import ContentExtractor
from pipeline.services.firecrawl_service import FirecrawlService
from pipeline.models.section import SectionCreate
from pipeline.models.code import CodeCreate, CodeUpdate
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print('='*80)
print('TASK 2: Testing Stage 2 (Content Extractor) Directly')
print('='*80)
print()

# Connect to database
db = DatabaseManager()
db.connect()
logger.info('✅ Connected to MongoDB')

# Create test sections manually (from YAML test data)
test_sections = [
    {'code': 'EVID', 'section': '100', 'url': 'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=100&lawCode=EVID'},
    {'code': 'EVID', 'section': '110', 'url': 'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=110&lawCode=EVID'},
    {'code': 'EVID', 'section': '120', 'url': 'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=120&lawCode=EVID'},
    {'code': 'FAM', 'section': '1', 'url': 'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1&lawCode=FAM'},
    {'code': 'FAM', 'section': '400', 'url': 'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=400&lawCode=FAM'},
]

# Clear and create sections
db.sections.delete_many({'code': {'$in': ['EVID', 'FAM']}})
logger.info(f'Creating {len(test_sections)} test sections...')
for sec in test_sections:
    section_create = SectionCreate(**sec)
    db.create_section(section_create)
logger.info(f'✅ Created {len(test_sections)} sections')

# Update code metadata
db.codes.delete_many({'code': {'$in': ['EVID', 'FAM']}})
db.create_code(CodeCreate(code='EVID', url='https://test.com'))
db.update_code('EVID', CodeUpdate(total_sections=3, stage1_completed=True))
db.create_code(CodeCreate(code='FAM', url='https://test.com'))
db.update_code('FAM', CodeUpdate(total_sections=2, stage1_completed=True))

print()
print('🚀 Starting Stage 2 for test sections...')
print()

# Create extractor
firecrawl = FirecrawlService()
extractor = ContentExtractor(
    firecrawl_service=firecrawl,
    db_manager=db,
    batch_size=5
)

# Track progress
def progress_callback(processed, total):
    pct = (processed/total*100) if total > 0 else 0
    print(f'   Progress: {processed}/{total} ({pct:.1f}%)')

# Run Stage 2 for EVID
start_time = datetime.now()
result_evid = extractor.extract('EVID', skip_multi_version=True, progress_callback=progress_callback)
duration_evid = (datetime.now() - start_time).total_seconds()

print()
print('✅ EVID EXTRACTION COMPLETE')
print(f'   Duration: {duration_evid:.2f} seconds')
print(f'   Single-version: {result_evid["single_version_count"]}')
print(f'   Multi-version: {result_evid["multi_version_count"]}')
print(f'   Failed: {len(result_evid["failed_sections"])}')

# Run Stage 2 for FAM
print()
print('🚀 Starting Stage 2 for FAM sections...')
print()
start_time = datetime.now()
result_fam = extractor.extract('FAM', skip_multi_version=True, progress_callback=progress_callback)
duration_fam = (datetime.now() - start_time).total_seconds()

print()
print('✅ FAM EXTRACTION COMPLETE')
print(f'   Duration: {duration_fam:.2f} seconds')
print(f'   Single-version: {result_fam["single_version_count"]}')
print(f'   Multi-version: {result_fam["multi_version_count"]}')
print(f'   Failed: {len(result_fam["failed_sections"])}')

# Show extracted content
print()
print('📝 Extracted Content Samples:')
sections_with_content = list(db.sections.find({'content': {'$ne': None}}).limit(3))
for i, sec in enumerate(sections_with_content, 1):
    print(f'   {i}. {sec["code"]} §{sec["section"]}')
    if sec.get('content'):
        print(f'      Content: {len(sec["content"])} chars')
        preview = sec["content"][:100].replace('\n', ' ')
        print(f'      Preview: {preview}...')
    if sec.get('legislative_history'):
        history = sec["legislative_history"][:80].replace('\n', ' ')
        print(f'      History: {history}...')
    print()

db.disconnect()

print('='*80)
print('✅ TASK 2 COMPLETE')
print('='*80)

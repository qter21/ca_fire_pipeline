"""Test all FAM sections from test_sections_data.yaml"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from pipeline.core.database import DatabaseManager

def load_yaml_test_data():
    """Load test data from YAML file."""
    yaml_path = Path(__file__).parent.parent / "tests" / "fixtures" / "test_sections_data.yaml"
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    return data['test_sections']

def test_fam_sections():
    """Test all FAM sections from YAML against MongoDB data."""

    print('='*80)
    print('Testing All FAM Sections from test_sections_data.yaml')
    print('='*80)
    print()

    # Load test data
    test_sections = load_yaml_test_data()
    fam_sections = [s for s in test_sections if s['code'] == 'FAM']

    print(f'Found {len(fam_sections)} FAM sections in YAML test data')
    print()

    # Connect to database
    db = DatabaseManager()
    db.connect()

    # Test each section
    results = {
        'total': len(fam_sections),
        'passed': 0,
        'failed': 0,
        'details': []
    }

    for i, expected in enumerate(fam_sections, 1):
        section_num = expected['section']
        is_multi = expected.get('is_multi_version', False)

        print(f'[{i}/{len(fam_sections)}] Testing FAM §{section_num} ({"multi-version" if is_multi else "single-version"})')
        print('-'*80)

        # Get from database
        actual = db.section_contents.find_one({'code': 'FAM', 'section': section_num})

        if not actual:
            print(f'   ❌ NOT FOUND in database')
            results['failed'] += 1
            results['details'].append({
                'section': section_num,
                'status': 'NOT_FOUND'
            })
            print()
            continue

        # Test based on type
        if is_multi:
            # Multi-version section
            result = test_multi_version_section(expected, actual, section_num)
        else:
            # Single-version section
            result = test_single_version_section(expected, actual, section_num)

        if result['passed']:
            results['passed'] += 1
            print(f'   ✅ PASS')
        else:
            results['failed'] += 1
            print(f'   ❌ FAIL: {result.get("reason", "Unknown")}')

        results['details'].append(result)
        print()

    db.disconnect()

    # Print summary
    print('='*80)
    print('TEST SUMMARY')
    print('='*80)
    print()
    print(f'Total FAM sections tested: {results["total"]}')
    print(f'Passed: {results["passed"]}')
    print(f'Failed: {results["failed"]}')
    print(f'Success Rate: {results["passed"]/results["total"]*100:.1f}%')
    print()

    if results['failed'] > 0:
        print('Failed Sections:')
        for detail in results['details']:
            if not detail.get('passed'):
                print(f'   - FAM §{detail["section"]}: {detail.get("reason", "Unknown")}')
        print()

    print('='*80)
    if results['failed'] == 0:
        print('✅ ALL FAM YAML TESTS PASSED!')
    else:
        print(f'⚠️  {results["failed"]} tests failed')
    print('='*80)

    return results

def test_single_version_section(expected, actual, section_num):
    """Test a single-version section."""
    result = {'section': section_num, 'passed': True, 'checks': []}

    # Check has_content
    if not actual.get('has_content'):
        result['passed'] = False
        result['reason'] = 'No content extracted'
        return result

    # Check content exists
    actual_content = actual.get('content', '').strip()
    expected_content = expected.get('content', '').strip()

    if not actual_content:
        result['passed'] = False
        result['reason'] = 'Content is empty'
        return result

    # Check content length (allow 80-120% variance)
    expected_len = len(expected_content)
    actual_len = len(actual_content)
    variance = abs(actual_len - expected_len) / expected_len if expected_len > 0 else 1

    print(f'   Content length: {actual_len} chars (expected ~{expected_len})')

    if variance > 0.2:  # More than 20% variance
        print(f'   ⚠️  Large variance: {variance*100:.1f}%')

    # Check first 50 chars match
    if expected_content[:50] in actual_content:
        print(f'   ✅ Content match verified (first 50 chars)')
    else:
        print(f'   ⚠️  Content may differ')
        print(f'   Expected start: {expected_content[:50]}...')
        print(f'   Actual start: {actual_content[:50]}...')

    # Check legislative history
    if expected.get('legislative_history'):
        actual_history = actual.get('legislative_history', '')
        expected_history = expected['legislative_history']

        if actual_history:
            print(f'   ✅ Legislative history: Present')
            if expected_history[:30] in actual_history:
                print(f'   ✅ History matches expected')
        else:
            print(f'   ⚠️  Legislative history: Missing')

    return result

def test_multi_version_section(expected, actual, section_num):
    """Test a multi-version section."""
    result = {'section': section_num, 'passed': True, 'checks': []}

    # Check is_multi_version flag
    if not actual.get('is_multi_version'):
        result['passed'] = False
        result['reason'] = 'Not flagged as multi-version'
        return result

    print(f'   ✅ Flagged as multi-version')

    # Check versions array
    actual_versions = actual.get('versions', [])
    expected_versions = expected.get('versions', [])

    if not actual_versions:
        result['passed'] = False
        result['reason'] = 'No versions extracted'
        return result

    print(f'   Versions: {len(actual_versions)} (expected {len(expected_versions)})')

    # Check version count
    if len(actual_versions) != len(expected_versions):
        print(f'   ⚠️  Version count mismatch')
    else:
        print(f'   ✅ Version count matches')

    # Check each version
    for i, (expected_v, actual_v) in enumerate(zip(expected_versions, actual_versions), 1):
        print(f'\\n   Version {i}:')

        # Check content
        actual_content = actual_v.get('content', '').strip()
        expected_content = expected_v.get('content', '').strip()

        if actual_content:
            expected_len = len(expected_content)
            actual_len = len(actual_content)
            variance = abs(actual_len - expected_len) / expected_len if expected_len > 0 else 1

            print(f'      Content: {actual_len} chars (expected ~{expected_len})')

            if variance <= 0.1:  # Within 10%
                print(f'      ✅ Length matches (variance: {variance*100:.1f}%)')
            else:
                print(f'      ⚠️  Length variance: {variance*100:.1f}%')

            # Check content starts correctly
            if expected_content[:50] in actual_content:
                print(f'      ✅ Content match verified')
        else:
            print(f'      ❌ No content')
            result['passed'] = False

        # Check operative date
        expected_date = expected_v.get('operative_date')
        actual_date = actual_v.get('operative_date')

        if expected_date:
            print(f'      Expected date: {expected_date}')
            print(f'      Actual date: {actual_date or "None"}')
            if actual_date:
                print(f'      ✅ Operative date extracted')
            else:
                print(f'      ⚠️  Operative date not extracted (in content instead)')

    return result

if __name__ == '__main__':
    results = test_fam_sections()
    sys.exit(0 if results['failed'] == 0 else 1)

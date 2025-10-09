"""
Sync multi_version_sections array in code_architectures from section_contents

This utility reads the is_multi_version flags from section_contents
and updates the multi_version_sections array in code_architectures
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.core.database import DatabaseManager

def sync_multi_version_data(code: str = None):
    """
    Sync multi_version_sections array for one or all codes

    Args:
        code: Specific code to sync, or None for all codes
    """
    db = DatabaseManager()
    db.connect()

    # Get codes to process
    if code:
        codes_to_process = [code]
    else:
        # Get all codes from code_architectures
        code_docs = db.code_architectures.find({}, {'code': 1})
        codes_to_process = [doc['code'] for doc in code_docs]

    print('='*80)
    print('Syncing multi_version_sections from section_contents')
    print('='*80)
    print()

    for code_name in codes_to_process:
        print(f'{code_name}:')

        # Get multi-version sections from section_contents
        multi_sections = list(db.section_contents.find(
            {'code': code_name, 'is_multi_version': True},
            {'section': 1}
        ))

        mv_list = sorted([sec['section'] for sec in multi_sections])

        # Get sections with versions array (more accurate)
        with_versions = list(db.section_contents.find(
            {'code': code_name, 'versions': {'$ne': None, '$exists': True}},
            {'section': 1}
        ))
        versions_list = sorted([sec['section'] for sec in with_versions])

        # Use the versions list (more reliable)
        final_list = versions_list if versions_list else mv_list

        # Update code_architectures
        result = db.code_architectures.update_one(
            {'code': code_name},
            {'$set': {'multi_version_sections': final_list}}
        )

        print(f'   Multi-version sections: {len(final_list)}')
        if final_list:
            print(f'   Sections: {final_list}')
        print(f'   Updated: {result.modified_count > 0}')
        print()

    db.disconnect()

    print('='*80)
    print('✅ Sync Complete')
    print('='*80)

if __name__ == '__main__':
    # Sync all codes
    sync_multi_version_data()

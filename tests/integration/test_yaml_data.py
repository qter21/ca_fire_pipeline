"""
Integration tests using YAML test data
Validates extraction against known good data from test_sections_data.yaml
"""

import pytest
import re
from pipeline.services.firecrawl_service import FirecrawlService


@pytest.mark.integration
@pytest.mark.slow
class TestYAMLDataValidation:
    """Test extraction against YAML test data"""

    def extract_section_content(self, markdown, section):
        """Helper to extract section content"""
        section_pattern = rf'#{{6}}\s+\*\*{section}\.?\*\*\s*\n\n(.+?)(?=\n_\(|$)'
        match = re.search(section_pattern, markdown, re.DOTALL)

        if match:
            return match.group(1).strip()

        # Alternative line-based extraction
        lines = markdown.split('\n')
        capture = False
        content_lines = []

        for line in lines:
            if f'**{section}.**' in line or f'**{section}' in line:
                capture = True
                continue
            if capture:
                if line.startswith('_') or line.startswith('##'):
                    break
                if line.strip():
                    content_lines.append(line)

        return '\n'.join(content_lines).strip()

    def normalize_text(self, text):
        """Normalize text for comparison"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove newlines
        text = text.replace('\n', ' ')
        return text.strip()

    def test_single_version_sections(self, firecrawl_service, test_sections_data):
        """Test all single-version sections from YAML data"""
        # Filter single-version sections
        single_version = [s for s in test_sections_data if not s.get('is_multi_version', False)]

        failures = []
        successes = 0

        for section_data in single_version:
            code = section_data['code']
            section = section_data['section']
            expected_content = section_data.get('content', '').strip()

            # Skip if no expected content
            if not expected_content:
                continue

            url = f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={section}&lawCode={code}"

            try:
                result = firecrawl_service.scrape_url(url)

                if not result["success"]:
                    failures.append(f"{code} {section}: API call failed")
                    continue

                markdown = result["data"].get("markdown", "")
                extracted_content = self.extract_section_content(markdown, section)

                if not extracted_content:
                    failures.append(f"{code} {section}: No content extracted")
                    continue

                # Normalize both texts for comparison
                normalized_expected = self.normalize_text(expected_content)
                normalized_extracted = self.normalize_text(extracted_content)

                # Check if extracted content starts with expected content
                # (allowing for extra content after the main text)
                if not normalized_extracted.startswith(normalized_expected[:100]):
                    failures.append(
                        f"{code} {section}: Content mismatch\n"
                        f"  Expected: {normalized_expected[:100]}...\n"
                        f"  Got: {normalized_extracted[:100]}..."
                    )
                    continue

                successes += 1

            except Exception as e:
                failures.append(f"{code} {section}: Exception - {str(e)}")

        # Print results
        total = len([s for s in single_version if s.get('content')])
        print(f"\n\nResults: {successes}/{total} sections validated successfully")

        if failures:
            print("\nFailures:")
            for failure in failures:
                print(f"  - {failure}")

        # Assert at least 80% success rate
        if total > 0:
            success_rate = successes / total
            assert success_rate >= 0.8, \
                f"Success rate too low: {success_rate:.1%} ({successes}/{total})\n" + \
                "\n".join(failures)

    @pytest.mark.multi_version
    def test_multi_version_detection(self, firecrawl_service, test_sections_data):
        """Test multi-version section detection from YAML data"""
        # Filter multi-version sections
        multi_version = [s for s in test_sections_data if s.get('is_multi_version', False)]

        failures = []
        successes = 0

        for section_data in multi_version:
            code = section_data['code']
            section = section_data['section']
            url = f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={section}&lawCode={code}"

            try:
                result = firecrawl_service.scrape_url(url)

                if not result["success"]:
                    failures.append(f"{code} {section}: API call failed")
                    continue

                markdown = result["data"].get("markdown", "")
                source_url = result["data"].get("metadata", {}).get("url", "")

                # Check if detected as multi-version
                is_multi_version = "selectFromMultiples" in source_url.lower() or \
                                  "selectFromMultiples" in markdown

                if not is_multi_version:
                    failures.append(f"{code} {section}: Not detected as multi-version")
                    continue

                successes += 1

            except Exception as e:
                failures.append(f"{code} {section}: Exception - {str(e)}")

        total = len(multi_version)
        print(f"\n\nMulti-version detection: {successes}/{total} sections detected")

        if failures:
            print("\nFailures:")
            for failure in failures:
                print(f"  - {failure}")

        # Assert 100% detection for multi-version sections
        assert successes == total, \
            f"Multi-version detection failed for {total - successes} sections:\n" + \
            "\n".join(failures)

    @pytest.mark.multi_version
    @pytest.mark.slow
    def test_multi_version_content_extraction(self, test_sections_data):
        """Test extracting actual content for multi-version sections"""
        from pipeline.services.multi_version_handler import MultiVersionHandler

        handler = MultiVersionHandler()

        # Filter multi-version sections
        multi_version = [s for s in test_sections_data if s.get('is_multi_version', False)]

        failures = []
        successes = 0

        for section_data in multi_version:
            code = section_data['code']
            section = section_data['section']
            expected_versions = section_data.get('versions', [])

            try:
                # Extract all versions
                result = handler.extract_all_versions(code, section)

                if not result.get("is_multi_version"):
                    failures.append(f"{code} {section}: Not detected as multi-version")
                    continue

                actual_versions = result.get("versions", [])

                # Validate version count
                if len(actual_versions) != len(expected_versions):
                    failures.append(
                        f"{code} {section}: Version count mismatch - "
                        f"expected {len(expected_versions)}, got {len(actual_versions)}"
                    )
                    continue

                # Validate each version's content
                all_versions_valid = True
                for i, expected in enumerate(expected_versions):
                    if i >= len(actual_versions):
                        failures.append(f"{code} {section}: Missing version {i+1}")
                        all_versions_valid = False
                        break

                    actual = actual_versions[i]
                    expected_content = self.normalize_text(expected.get('content', '').strip())
                    actual_content = self.normalize_text(actual.get('content', ''))

                    # Validate content exists and matches expected
                    if not actual_content:
                        failures.append(f"{code} {section} v{i+1}: No content extracted")
                        all_versions_valid = False
                        break

                    # Check if content is similar (allow for minor formatting differences)
                    # Content should be at least 90% of expected length
                    min_expected_length = len(expected_content) * 0.9
                    if len(actual_content) < min_expected_length:
                        failures.append(
                            f"{code} {section} v{i+1}: Content too short - "
                            f"expected ~{len(expected_content)} chars, got {len(actual_content)} chars"
                        )
                        all_versions_valid = False
                        break

                    # Check if key phrases from expected content appear in actual
                    # Use first 100 chars as validation
                    if expected_content[:100] not in actual_content:
                        failures.append(
                            f"{code} {section} v{i+1}: Content mismatch\n"
                            f"  Expected start: {expected_content[:100]}...\n"
                            f"  Actual start: {actual_content[:100]}..."
                        )
                        all_versions_valid = False
                        break

                if all_versions_valid:
                    successes += 1

            except Exception as e:
                import traceback
                failures.append(f"{code} {section}: Exception - {str(e)}\n{traceback.format_exc()}")

        total = len(multi_version)
        print(f"\n\nMulti-version content extraction: {successes}/{total} sections validated")

        if failures:
            print("\nFailures:")
            for failure in failures:
                print(f"  - {failure}")

        # Assert 100% extraction for multi-version sections
        assert successes == total, \
            f"Multi-version content extraction failed for {total - successes} sections:\n" + \
            "\n".join(failures)

    def test_legislative_history_extraction(self, firecrawl_service, test_sections_data):
        """Test legislative history extraction from YAML data"""
        sections_with_history = [
            s for s in test_sections_data
            if not s.get('is_multi_version', False) and s.get('legislative_history')
        ]

        failures = []
        successes = 0

        for section_data in sections_with_history:
            code = section_data['code']
            section = section_data['section']
            expected_history = section_data['legislative_history']

            url = f"https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum={section}&lawCode={code}"

            try:
                result = firecrawl_service.scrape_url(url)

                if not result["success"]:
                    failures.append(f"{code} {section}: API call failed")
                    continue

                markdown = result["data"].get("markdown", "")

                # Extract legislative history
                history_pattern = r'_\(([^)]+)\)_'
                history_matches = re.findall(history_pattern, markdown)

                if not history_matches:
                    failures.append(f"{code} {section}: No legislative history found")
                    continue

                extracted_history = history_matches[-1]

                # Check if key parts of expected history are present
                # (normalize and check for key year/stat numbers)
                expected_normalized = self.normalize_text(expected_history)
                extracted_normalized = self.normalize_text(extracted_history)

                # Extract year from expected
                import re as regex
                year_match = regex.search(r'(\d{4})', expected_normalized)
                if year_match:
                    year = year_match.group(1)
                    if year not in extracted_normalized:
                        failures.append(
                            f"{code} {section}: History mismatch (year {year} not found)\n"
                            f"  Expected: {expected_normalized}\n"
                            f"  Got: {extracted_normalized}"
                        )
                        continue

                successes += 1

            except Exception as e:
                failures.append(f"{code} {section}: Exception - {str(e)}")

        total = len(sections_with_history)
        print(f"\n\nLegislative history: {successes}/{total} sections validated")

        if failures:
            print("\nFailures:")
            for failure in failures:
                print(f"  - {failure}")

        # Assert at least 80% success rate
        if total > 0:
            success_rate = successes / total
            assert success_rate >= 0.8, \
                f"Success rate too low: {success_rate:.1%} ({successes}/{total})"

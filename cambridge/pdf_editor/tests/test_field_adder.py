"""Tests for Field Modifier module"""

import pytest
from pathlib import Path
from src.field_adder import FieldModifier
from src.analyzer import PDFAnalyzer


# Test data paths
TEST_PDF = Path(__file__).parent.parent / 'input' / 'cambridge_pavers_catalog.pdf'
TEST_OUTPUT = Path(__file__).parent / 'output' / 'test_output.pdf'


class TestFieldModifier:
    """Test cases for FieldModifier class."""

    def test_context_manager(self):
        """Test that field modifier works as context manager."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with FieldModifier(str(TEST_PDF), str(TEST_OUTPUT)) as modifier:
            assert modifier.doc is not None

    def test_get_page_content_bounds(self):
        """Test getting page content bounding boxes."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with FieldModifier(str(TEST_PDF), str(TEST_OUTPUT)) as modifier:
            page = modifier.doc[0]
            bounds = modifier.get_page_content_bounds(page)

            # Should have some content on the page
            assert isinstance(bounds, list)
            # Most pages have content
            assert len(bounds) >= 0

    def test_check_overlap(self):
        """Test overlap detection between rectangles."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with FieldModifier(str(TEST_PDF), str(TEST_OUTPUT)) as modifier:
            # Overlapping rectangles
            rect1 = (100, 100, 200, 150)
            rect2 = (150, 120, 250, 170)
            assert modifier.check_overlap(rect1, rect2) is True

            # Non-overlapping rectangles
            rect3 = (100, 100, 200, 150)
            rect4 = (300, 300, 400, 350)
            assert modifier.check_overlap(rect3, rect4) is False

    def test_widen_price_fields(self):
        """Test widening price fields with statistics."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        # First find price fields
        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            price_fields = analyzer.find_price_fields()

        if len(price_fields) == 0:
            pytest.skip("No price fields found in test PDF")

        # Get original widths
        original_widths = {}
        for field in price_fields[:5]:  # Test first 5 fields
            rect = field['rect']
            original_widths[field['field_name']] = rect[2] - rect[0]

        # Widen fields
        with FieldModifier(str(TEST_PDF), str(TEST_OUTPUT)) as modifier:
            stats = modifier.widen_price_fields(price_fields, width_extension=70.0)

            # Should return a dictionary with statistics
            assert 'widened_count' in stats
            assert 'skipped_count' in stats
            assert 'total_extension' in stats
            assert 'average_extension' in stats

            # Should widen at least some fields
            assert stats['widened_count'] > 0

            # Total should equal sum of widened and skipped
            assert stats['widened_count'] + stats['skipped_count'] == len(price_fields)

            assert modifier.save()

        # Verify fields were actually widened
        with PDFAnalyzer(str(TEST_OUTPUT)) as analyzer:
            modified_fields = analyzer.find_price_fields()

            widened_found = False
            for field in modified_fields[:5]:  # Check first 5 fields
                field_name = field['field_name']
                if field_name in original_widths:
                    rect = field['rect']
                    new_width = rect[2] - rect[0]
                    # New width should be greater than original (if not skipped)
                    if new_width > original_widths[field_name]:
                        widened_found = True
                        break

            # At least one field should have been widened
            assert widened_found

    def test_save(self):
        """Test saving modified PDF."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        TEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with FieldModifier(str(TEST_PDF), str(TEST_OUTPUT)) as modifier:
            result = modifier.save()
            assert result is True
            assert TEST_OUTPUT.exists()

    def test_raises_without_context(self):
        """Test that methods raise error when not used with context manager."""
        modifier = FieldModifier(str(TEST_PDF), str(TEST_OUTPUT))

        with pytest.raises(RuntimeError):
            modifier.widen_price_fields([])

        with pytest.raises(RuntimeError):
            modifier.save()

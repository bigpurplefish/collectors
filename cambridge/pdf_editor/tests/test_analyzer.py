"""Tests for PDF Analyzer module"""

import pytest
from pathlib import Path
from src.analyzer import PDFAnalyzer


# Test data paths
TEST_PDF = Path(__file__).parent.parent / 'input' / 'cambridge_pavers_catalog.pdf'


class TestPDFAnalyzer:
    """Test cases for PDFAnalyzer class."""

    def test_context_manager(self):
        """Test that analyzer works as context manager."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            assert analyzer.doc is not None

    def test_get_document_info(self):
        """Test getting basic document information."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            info = analyzer.get_document_info()

            assert 'page_count' in info
            assert 'has_forms' in info
            assert 'field_count' in info
            assert info['page_count'] > 0

    def test_get_all_fields(self):
        """Test getting all form fields."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            fields = analyzer.get_all_fields()

            assert isinstance(fields, list)
            # Each field should have required properties
            for field in fields:
                assert 'page_num' in field
                assert 'field_name' in field
                assert 'field_type' in field
                assert 'rect' in field
                assert 'value' in field

    def test_find_price_fields(self):
        """Test finding price-related fields."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            price_fields = analyzer.find_price_fields()

            assert isinstance(price_fields, list)
            # If price fields exist, they should have valid names
            for field in price_fields:
                name_lower = field['field_name'].lower()
                assert any(keyword in name_lower for keyword in
                          ['price', 'cost', 'amount', 'total', 'unit_price'])

    def test_calculate_item_field_position(self):
        """Test calculation of item field position."""
        if not TEST_PDF.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF}")

        with PDFAnalyzer(str(TEST_PDF)) as analyzer:
            # Test with sample rectangle
            price_rect = (100, 100, 200, 120)
            item_rect = analyzer.calculate_item_field_position(price_rect, offset=70)

            assert len(item_rect) == 4
            x0, y0, x1, y1 = item_rect

            # Item field should be to the left of price field
            assert x1 < price_rect[0]
            # Y coordinates should match
            assert y0 == price_rect[1]
            assert y1 == price_rect[3]
            # Width should be 60 points for 5 digits
            assert abs((x1 - x0) - 60.0) < 0.1

    def test_raises_without_context(self):
        """Test that methods raise error when not used with context manager."""
        analyzer = PDFAnalyzer(str(TEST_PDF))

        with pytest.raises(RuntimeError):
            analyzer.get_all_fields()

        with pytest.raises(RuntimeError):
            analyzer.get_document_info()

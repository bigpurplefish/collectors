"""PDF Field Detection and Analysis Module

This module handles detection and analysis of existing form fields in PDF documents.
It identifies price fields and their positions to determine where item number fields
should be added.
"""

import pymupdf
from typing import List, Dict, Tuple


class PDFAnalyzer:
    """Analyzes PDF documents to detect form fields and their properties."""

    def __init__(self, pdf_path: str):
        """Initialize analyzer with PDF document path.

        Args:
            pdf_path: Path to the PDF file to analyze
        """
        self.pdf_path = pdf_path
        self.doc = None

    def __enter__(self):
        """Context manager entry - opens PDF document."""
        self.doc = pymupdf.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes PDF document."""
        if self.doc:
            self.doc.close()

    def get_all_fields(self) -> List[Dict]:
        """Get all form fields from the PDF document.

        Returns:
            List of dictionaries containing field information:
            - page_num: Page number (0-indexed)
            - field_name: Name of the form field
            - field_type: Type of field (text, checkbox, etc.)
            - rect: Field rectangle (x0, y0, x1, y1)
            - value: Current field value
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened. Use context manager.")

        fields = []
        for page_num, page in enumerate(self.doc):
            for widget in page.widgets():
                fields.append({
                    'page_num': page_num,
                    'field_name': widget.field_name,
                    'field_type': widget.field_type_string,
                    'rect': tuple(widget.rect),
                    'value': widget.field_value
                })
        return fields

    def find_price_fields(self) -> List[Dict]:
        """Find form fields that are likely price fields.

        Identifies price fields by looking for common naming patterns
        like 'price', 'cost', 'amount', etc.

        Returns:
            List of price field dictionaries with same structure as get_all_fields()
        """
        all_fields = self.get_all_fields()
        price_keywords = ['price', 'cost', 'amount', 'total', 'unit_price']

        price_fields = []
        for field in all_fields:
            field_name_lower = field['field_name'].lower()
            if any(keyword in field_name_lower for keyword in price_keywords):
                price_fields.append(field)

        return price_fields

    def calculate_item_field_position(self, price_field_rect: Tuple[float, float, float, float],
                                     offset: float = 70.0) -> Tuple[float, float, float, float]:
        """Calculate position for item number field to the left of a price field.

        Args:
            price_field_rect: Rectangle of the price field (x0, y0, x1, y1)
            offset: Distance to the left of price field (default: 70 points)

        Returns:
            Rectangle tuple (x0, y0, x1, y1) for the item number field
        """
        x0, y0, x1, y1 = price_field_rect
        field_width = 60.0  # Width for 5-digit item numbers

        # Position to the left of price field
        item_x0 = x0 - offset - field_width
        item_x1 = x0 - offset

        return (item_x0, y0, item_x1, y1)

    def get_document_info(self) -> Dict:
        """Get basic information about the PDF document.

        Returns:
            Dictionary with document metadata:
            - page_count: Number of pages
            - has_forms: Whether document contains form fields
            - field_count: Total number of form fields
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened. Use context manager.")

        all_fields = self.get_all_fields()

        return {
            'page_count': len(self.doc),
            'has_forms': len(all_fields) > 0,
            'field_count': len(all_fields)
        }

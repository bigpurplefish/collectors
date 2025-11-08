"""PDF Field Modification Module

This module handles widening existing price form fields to accommodate
both item numbers and prices in the format: #####/###.##
"""

import pymupdf
from typing import List, Dict, Tuple, Set


class FieldModifier:
    """Modifies existing form fields in PDF documents to make them wider."""

    def __init__(self, pdf_path: str, output_path: str):
        """Initialize field modifier with input and output paths.

        Args:
            pdf_path: Path to the input PDF file
            output_path: Path where modified PDF will be saved
        """
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.doc = None

    def __enter__(self):
        """Context manager entry - opens PDF document."""
        self.doc = pymupdf.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes PDF document."""
        if self.doc:
            self.doc.close()

    def get_page_content_bounds(self, page) -> List[Tuple[float, float, float, float]]:
        """Get bounding boxes of all text content on a page.

        Args:
            page: PyMuPDF page object

        Returns:
            List of bounding box tuples (x0, y0, x1, y1)
        """
        bounds = []
        try:
            # Get text blocks
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    bbox = block.get("bbox")
                    if bbox:
                        bounds.append(tuple(bbox))
        except Exception:
            pass
        return bounds

    def check_overlap(self, rect1: Tuple[float, float, float, float],
                     rect2: Tuple[float, float, float, float],
                     margin: float = 2.0) -> bool:
        """Check if two rectangles overlap with a margin.

        Args:
            rect1: First rectangle (x0, y0, x1, y1)
            rect2: Second rectangle (x0, y0, x1, y1)
            margin: Extra margin to consider (default: 2.0 points)

        Returns:
            True if rectangles overlap, False otherwise
        """
        x0_1, y0_1, x1_1, y1_1 = rect1
        x0_2, y0_2, x1_2, y1_2 = rect2

        # Add margin to rect1 (the field being extended)
        x0_1 -= margin
        y0_1 -= margin
        x1_1 += margin
        y1_1 += margin

        # Check if rectangles don't overlap (then invert)
        no_overlap = (x1_1 < x0_2 or x1_2 < x0_1 or y1_1 < y0_2 or y1_2 < y0_1)
        return not no_overlap

    def calculate_safe_extension(self, page, widget_rect: Tuple[float, float, float, float],
                                desired_extension: float) -> float:
        """Calculate safe field extension that won't overlap content.

        Args:
            page: PyMuPDF page object
            widget_rect: Current widget rectangle (x0, y0, x1, y1)
            desired_extension: Desired extension to the left (points)

        Returns:
            Safe extension amount (may be less than desired)
        """
        x0, y0, x1, y1 = widget_rect

        # Get all content bounds on the page
        content_bounds = self.get_page_content_bounds(page)

        # Start with desired extension
        safe_extension = desired_extension

        # Proposed new rectangle
        new_x0 = x0 - safe_extension
        proposed_rect = (new_x0, y0, x1, y1)

        # Check for overlaps with content
        for content_rect in content_bounds:
            if self.check_overlap(proposed_rect, content_rect):
                # Calculate maximum safe extension to just before this content
                content_x1 = content_rect[2]
                # Only consider content to the left of the field
                if content_x1 < x0:
                    # Add small buffer (3 points) between field and content
                    max_safe = x0 - content_x1 - 3
                    if max_safe > 0 and max_safe < safe_extension:
                        safe_extension = max_safe

        # Ensure we don't go off the page
        if new_x0 < 0:
            safe_extension = x0  # At most, extend to page edge

        return safe_extension

    def widen_field(self, page_num: int, widget, width_extension: float = 70.0,
                    min_extension: float = 1.0) -> Tuple[bool, float]:
        """Widen an existing form field to the left, avoiding content overlap.

        Args:
            page_num: Page number (0-indexed)
            widget: The widget to widen
            width_extension: How many points to extend to the left (default: 70)
            min_extension: Minimum extension required to proceed (default: 1)

        Returns:
            Tuple of (success: bool, actual_extension: float)
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened. Use context manager.")

        if page_num >= len(self.doc):
            return False, 0.0

        try:
            page = self.doc[page_num]

            # Get current rectangle
            rect = widget.rect
            x0, y0, x1, y1 = rect

            # Calculate safe extension
            safe_extension = self.calculate_safe_extension(
                page, (x0, y0, x1, y1), width_extension
            )

            # Only proceed if we can extend at least the minimum
            if safe_extension < min_extension:
                return False, 0.0

            # Extend field to the left
            new_x0 = x0 - safe_extension
            new_rect = pymupdf.Rect(new_x0, y0, x1, y1)

            # Update widget rectangle
            widget.rect = new_rect

            # Set right justification (align=2 means right)
            widget.text_format = 2  # Right justified

            # Remove text length limit to accommodate #####/###.##
            widget.text_maxlen = 0  # No limit

            # Update the widget
            widget.update()

            return True, safe_extension
        except Exception:
            return False, 0.0

    def widen_price_fields(self, price_fields: List[Dict],
                           width_extension: float = 70.0,
                           min_extension: float = None) -> Dict:
        """Widen price fields to accommodate item# and price format.

        Args:
            price_fields: List of price field dictionaries from PDFAnalyzer
            width_extension: How many points to extend to the left (default: 70)
            min_extension: Minimum extension required (default: 10% of width_extension or 1pt, whichever is larger)

        Returns:
            Dictionary with statistics:
            - widened_count: Number of fields successfully widened
            - skipped_count: Number of fields skipped (overlap issues)
            - total_extension: Total extension applied
            - average_extension: Average extension per widened field
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened. Use context manager.")

        # Calculate intelligent minimum if not provided
        if min_extension is None:
            # Use 10% of desired width, with absolute minimum of 1 point
            min_extension = max(1.0, width_extension * 0.1)

        widened_count = 0
        skipped_count = 0
        total_extension = 0.0

        # Group fields by page for efficient processing
        fields_by_page = {}
        for field in price_fields:
            page_num = field['page_num']
            if page_num not in fields_by_page:
                fields_by_page[page_num] = []
            fields_by_page[page_num].append(field)

        # Process each page
        for page_num, page_fields in fields_by_page.items():
            page = self.doc[page_num]

            # Get all widgets on the page
            widgets = list(page.widgets())

            # Create a mapping of field names to widgets
            widget_map = {w.field_name: w for w in widgets}

            # Widen each matching field
            for field in page_fields:
                field_name = field['field_name']
                if field_name in widget_map:
                    success, extension = self.widen_field(
                        page_num, widget_map[field_name], width_extension, min_extension
                    )
                    if success:
                        widened_count += 1
                        total_extension += extension
                    else:
                        skipped_count += 1

        average_extension = total_extension / widened_count if widened_count > 0 else 0.0

        return {
            'widened_count': widened_count,
            'skipped_count': skipped_count,
            'total_extension': total_extension,
            'average_extension': average_extension
        }

    def save(self) -> bool:
        """Save the modified PDF to the output path.

        Returns:
            True if save was successful, False otherwise
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened. Use context manager.")

        try:
            self.doc.save(self.output_path, garbage=4, deflate=True, incremental=False)
            return True
        except Exception:
            return False


# Keep old class name for backward compatibility
FieldAdder = FieldModifier

"""
Table parsing module.

This module handles parsing of tables from the PDF, including:
- Color category table from page 2
- Product tables from pages 4-5
"""

from typing import List, Tuple
from src.models import ColorCategory, Product
from src.pdf_extractor import PDFExtractor
from utils.text_utils import clean_text, split_color_list, is_empty_cell
import src.config as config


class TableParser:
    """
    Handles parsing of tables from the PDF.
    """

    def __init__(self, extractor: PDFExtractor):
        """
        Initialize the table parser.

        Args:
            extractor: PDFExtractor instance
        """
        self.extractor = extractor

    def parse_color_categories(self) -> List[ColorCategory]:
        """
        Parse color category table from page 2.

        Returns:
            List of ColorCategory objects
        """
        tables = self.extractor.extract_tables(config.PAGE_COLOR_CATEGORIES)

        if not tables:
            raise ValueError(f"No tables found on page {config.PAGE_COLOR_CATEGORIES}")

        # Get the last table on the page (color categories table is at bottom)
        table = tables[-1]

        categories = []

        # Skip header row (first row)
        for row in table[1:]:
            if len(row) < 3:
                continue

            category_name = clean_text(row[0]) if row[0] else ""
            reason = clean_text(row[1]) if row[1] else ""
            colors_text = clean_text(row[2]) if row[2] else ""

            # Skip empty rows
            if not category_name or not colors_text:
                continue

            # Split comma-separated colors into list
            colors = split_color_list(colors_text)

            if colors:
                categories.append(ColorCategory(
                    category=category_name,
                    reason=reason,
                    colors=colors
                ))

        return categories

    def parse_product_tables(self) -> List[Product]:
        """
        Parse product tables from pages 4-5.

        Returns:
            List of Product objects
        """
        products = []

        # Parse paving stones from page 4
        paving_products = self._parse_product_page(
            config.PAGE_PAVING_STONES,
            "paving_stone"
        )
        products.extend(paving_products)

        # Parse wall stones from page 5
        # Adjust order_index to continue from paving products
        wall_products = self._parse_product_page(
            config.PAGE_WALL_STONES,
            "wall_stone"
        )
        offset = len(paving_products)
        for product in wall_products:
            product.order_index += offset
        products.extend(wall_products)

        return products

    def _parse_product_page(self, page_number: int, product_type: str) -> List[Product]:
        """
        Parse product information from pages 4-5.

        Based on the actual PDF structure:
        - Page has 3 columns of tables
        - Grey background rectangles mark product name cells
        - Colors are in adjacent white cells to the right of each product
        - Use rectangle positions to extract text from each cell

        Args:
            page_number: Page number to parse
            product_type: "paving_stone" or "wall_stone"

        Returns:
            List of Product objects from this page
        """
        page = self.extractor.get_page(page_number)

        # Get rectangles (grey background cells marking product names)
        rects = page.rects

        # Filter rectangles - product name cells are approximately:
        # - Width of ~174 pixels
        # - Height of ~12-21 pixels (longer product names have taller cells)
        # - Located in main content area (y > 140)

        product_cells = []
        for rect in rects:
            width = rect['x1'] - rect['x0']
            height = rect['bottom'] - rect['top']

            # Product cells are roughly 174 wide and 12-21 tall
            if 173 < width < 175 and 10 < height < 22 and rect['top'] > 140:
                product_cells.append(rect)

        # Sort cells by position (left to right, then top to bottom within each column)
        product_cells.sort(key=lambda r: (r['x0'], r['top']))

        products = []

        # Process each product cell
        for i, cell in enumerate(product_cells):
            # Extract product name from grey cell
            product_bbox = (cell['x0'], cell['top'], cell['x1'], cell['bottom'])
            product_crop = page.crop(product_bbox)
            product_text = clean_text(product_crop.extract_text() or "")

            if not product_text or product_text in config.TABLE_PATTERNS["ignore_headers"]:
                continue

            # Determine the vertical range for colors: from this cell's bottom
            # to the next grey cell's top (or page bottom if this is the last cell)
            color_y_start = cell['bottom']
            if i + 1 < len(product_cells):
                # Find next cell in same column (similar x0)
                next_cell_in_column = None
                for j in range(i + 1, len(product_cells)):
                    if abs(product_cells[j]['x0'] - cell['x0']) < 10:  # Same column
                        next_cell_in_column = product_cells[j]
                        break

                if next_cell_in_column:
                    color_y_end = next_cell_in_column['top']
                else:
                    color_y_end = page.height
            else:
                color_y_end = page.height

            # Extract colors from the area below this product cell
            # Colors are in a 2-column layout within each product section
            # We need to extract words by position to separate left and right columns

            colors = []

            if color_y_end > color_y_start:
                # Get all words in the color region
                color_bbox = (cell['x0'], color_y_start, cell['x1'], color_y_end)
                color_crop = page.crop(color_bbox)
                words = color_crop.extract_words()

                if words:
                    # Detect vertical dotted lines that separate columns
                    # Get all lines in the color region
                    lines = color_crop.lines
                    vertical_lines = []
                    for line in lines:
                        # Check if it's a vertical line (height > 10 pixels)
                        if abs(line['top'] - line['bottom']) > 10:
                            x_rel = line['x0'] - color_bbox[0]
                            # Avoid duplicates
                            if not any(abs(x_rel - existing) < 1 for existing in vertical_lines):
                                vertical_lines.append(x_rel)

                    vertical_lines.sort()

                    # Create column boundaries from vertical lines
                    # Boundaries are: [0, line1, line2, ..., width]
                    column_boundaries = vertical_lines
                    num_columns = len(column_boundaries) + 1

                    # Group words by line (y position) and column
                    lines_dict = {}
                    y_tolerance = 2  # Tighter tolerance for same line

                    for word in words:
                        # y position relative to cropped area
                        y_rel = word['top'] - color_bbox[1]

                        # Skip words that are too close to the top (< 2 pixels)
                        # These are likely product name text that extends beyond the grey rectangle
                        if y_rel < 2:
                            continue

                        y = round(y_rel / y_tolerance) * y_tolerance
                        # x position relative to cropped area
                        x = word['x0'] - color_bbox[0]

                        if y not in lines_dict:
                            lines_dict[y] = {col: [] for col in range(num_columns)}

                        # Determine which column the word belongs to
                        col_idx = num_columns - 1  # Default to rightmost column
                        for col, boundary in enumerate(column_boundaries):
                            if x < boundary:
                                col_idx = col
                                break

                        lines_dict[y][col_idx].append({'x': x, 'text': word['text']})

                    # Extract colors from each line
                    for y in sorted(lines_dict.keys()):
                        line_data = lines_dict[y]

                        # Process each column
                        for col_idx in range(num_columns):
                            if line_data[col_idx]:
                                # Combine all words in this column in x-order
                                col_words = sorted(line_data[col_idx], key=lambda w: w['x'])
                                color_text = clean_text(' '.join([w['text'] for w in col_words]))

                                # Skip if it looks like a note or instruction
                                # Common patterns: "NOTE:", "corners/", "used as", "make ", "in cube", "be used"
                                skip_patterns = ['NOTE:', 'corners/', 'used as', 'make ', 'in cube', 'be used', 'the cube']
                                if color_text and not any(pattern in color_text for pattern in skip_patterns):
                                    colors.append(color_text)

            # Only add product if it has colors
            if colors:
                products.append(Product(
                    title=product_text,
                    colors=colors,
                    product_type=product_type,
                    order_index=i  # Preserve order from PDF
                ))

        return products

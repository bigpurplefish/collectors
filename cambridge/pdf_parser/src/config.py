"""
Configuration for PDF parsing.

This module contains all configuration constants for parsing the Cambridge
pavers catalog PDF, including page mappings, table patterns, and output settings.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"

# PDF file paths
PDF_INPUT_FILE = INPUT_DIR / "cambridge_pavers_catalog.pdf"
EXCEL_OUTPUT_FILE = OUTPUT_DIR / "cambridge_products.xlsx"

# Page mappings (1-indexed to match PDF page numbers)
PAGE_COLOR_CATEGORIES = 2
PAGE_PAVING_STONES = 4
PAGE_WALL_STONES = 5

# Table detection patterns
# These patterns help identify different types of content in the PDF
TABLE_PATTERNS = {
    # Product header styling (bold text on blue background)
    "product_header_bg_color": "blue",
    "product_header_style": "bold",

    # Color cell styling (regular text on white background)
    "color_cell_bg_color": "white",

    # Category headers to ignore (on page 5)
    "ignore_headers": ["PLUS", "CLASSIC"],
}

# Page layout configuration
COLUMN_COUNT = 3  # Pages 4-5 have 3-column layout

# Excel output configuration
EXCEL_CONFIG = {
    "font_name": "Arial",
    "font_size": 11,
    "columns": ["vendor_type", "title", "color_category", "color", "item_#", "price"],
    "sort_columns": ["vendor_type", "title", "color_category", "color"],
    "auto_fit_columns": True,
}

# Vendor type mappings
VENDOR_TYPE_PAVING = "Paving Stones"
VENDOR_TYPE_WALL = "Wall Stones"

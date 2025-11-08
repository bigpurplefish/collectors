# PDF Editor - Cambridge Catalog Price Field Widener

A modular Python application that widens existing price form fields in the Cambridge Pavers catalog PDF to accommodate both 5-digit item numbers and prices in a single field using the format: `#####/###.##`

## Features

- Automatically detects existing price form fields in PDF
- Widens price fields to the left to make room for item numbers
- **Smart overlap detection**: Prevents fields from overlapping existing page content
- **Right-justified text alignment**: All fields use right alignment for consistent formatting
- Single field format: `#####/###.##` (e.g., `12345/$999.99`)
- OCR-friendly formatting maintained:
  - Black text on white background
  - Clear black borders
  - Appropriate font sizing
  - Right-aligned text
- Modular architecture with separate analyzer and field modifier components
- Command-line interface with flexible options
- Comprehensive test suite

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Process the default Cambridge catalog:
```bash
python3 main.py
```

This will:
- Read `input/cambridge_pavers_catalog.pdf`
- Widen all price fields by 70 points to the left
- Save to `output/cambridge_pavers_catalog_edited.pdf`

### Custom Input/Output

Specify custom file paths:
```bash
python3 main.py --input path/to/input.pdf --output path/to/output.pdf
```

### Adjust Field Width Extension

Change how much to extend the fields (in points):
```bash
python3 main.py --width 80
```

### Analyze Only (No Changes)

View all form fields in the PDF without making changes:
```bash
python3 main.py --analyze-only
```

## Project Structure

```
pdf_editor/
├── main.py              # CLI entry point
├── src/                 # Application source code
│   ├── analyzer.py      # PDF field detection and analysis
│   └── field_adder.py   # Price field widening (FieldModifier)
├── utils/               # Project-specific utilities
├── tests/               # Test suite
│   ├── test_analyzer.py
│   └── test_field_adder.py
├── input/               # Input PDF files
│   └── cambridge_pavers_catalog.pdf
├── output/              # Processed PDFs (gitignored)
├── requirements.txt     # Python dependencies
└── README.md
```

## Architecture

### PDFAnalyzer (`src/analyzer.py`)

Handles PDF analysis and field detection:
- `get_all_fields()` - Extract all form fields from PDF
- `find_price_fields()` - Identify price-related fields
- `calculate_item_field_position()` - Calculate positioning for new fields
- `get_document_info()` - Get basic PDF metadata

### FieldModifier (`src/field_adder.py`)

Handles widening existing form fields with smart overlap detection:
- `get_page_content_bounds()` - Extract bounding boxes of all page content
- `check_overlap()` - Check if two rectangles overlap
- `calculate_safe_extension()` - Calculate maximum safe field extension
- `widen_field()` - Widen a single form field safely, avoiding content overlap
- `widen_price_fields()` - Batch widen all price fields, returns statistics
- `save()` - Save modified PDF

Both classes use context managers for proper resource management.

## Testing

Run all tests:
```bash
python3 -m pytest
```

Run specific test file:
```bash
python3 -m pytest tests/test_analyzer.py
```

Run with coverage:
```bash
python3 -m pytest --cov=src
```

## Requirements

- Python 3.8+
- PyMuPDF >= 1.23.0

## How It Works

1. **Analysis Phase**: The `PDFAnalyzer` scans the PDF to find all form fields and identifies which ones are price fields (by matching common keywords like "price", "cost", "amount")

2. **Content Detection**: For each page, the `FieldModifier` extracts bounding boxes of all text content to detect potential overlaps

3. **Safe Field Widening**: For each price field:
   - Calculates the desired extension to the left (default 70 points)
   - Checks for overlaps with existing page content
   - Adjusts the extension if needed to avoid overlaps (minimum 30 points)
   - Skips fields that don't have sufficient space
   - Applies right-justified text alignment

4. **Text Limit Removal**: Removes the character limit on fields so they can accommodate the full format `#####/###.##`

5. **Output**: Saves the modified PDF with all successfully widened fields, maintaining:
   - Original formatting (colors, borders, fonts)
   - OCR-friendly properties
   - No content overlaps
   - Right-aligned text
   - All other PDF content unchanged

## Field Format

Users can now enter data in widened fields using this format:

**Format:** `#####/###.##`

**Examples:**
- `12345/$999.99`
- `00001/$1.50`
- `99999/$12345.67`

The slash (/) separates the 5-digit item number from the price.

## OCR-Friendly Features

The widened fields maintain OCR-friendly properties:
- High contrast (black on white)
- Clear borders defining field boundaries
- Appropriate font size (maintained from original)
- **Right-justified text alignment** for consistent number positioning
- Consistent positioning
- Single field entry reduces scanning complexity
- No overlap with existing content ensures clean scans

## License

Internal use only - Cambridge Pavers catalog processing

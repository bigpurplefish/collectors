# CLAUDE.md - Development Notes

This document contains notes and context for Claude Code to understand the project quickly.

## Project Purpose

This PDF editor widens existing price form fields in the Cambridge Pavers catalog PDF to accommodate both 5-digit item numbers and prices in a single field using the format: `#####/###.##`

## Key Design Decisions

1. **PyMuPDF (fitz) Library**: Chosen for robust PDF form field manipulation capabilities
2. **Modular Architecture**: Separate modules for analysis (analyzer.py) and modification (field_adder.py)
3. **Context Managers**: Both main classes use context managers for proper PDF resource cleanup
4. **OCR-Friendly Formatting**: Maintains original field formatting (black text, white background, clear borders)
5. **Keyword-Based Detection**: Price fields identified by common keywords (price, cost, amount, total, unit_price)
6. **Field Widening (Not Adding)**: Extends existing fields to the left rather than creating new fields
7. **Smart Overlap Detection**: Analyzes page content to prevent field/text overlaps
8. **Right Justification**: All fields use right-aligned text (text_format=2)

## Design Changes

### November 2025 - Change 1: Single Field Approach
**Original**: Add separate 5-digit item number fields to the left of price fields
**Updated**: Widen existing price fields to accommodate both item# and price in format `#####/###.##`

**Rationale**:
- Simpler data entry (one field instead of two)
- Easier for OCR scanning (single field to parse)
- Less complex PDF structure

### November 2025 - Change 2: Overlap Detection & Right Justification
**Added Features**:
- Content overlap detection and prevention
- Right-justified text alignment
- Adaptive field extension (adjusts width to avoid overlaps)
- Statistics reporting (widened/skipped counts)

**Rationale**:
- Prevent fields from covering existing text/content
- Right alignment provides consistent number positioning
- Better OCR accuracy with proper alignment
- User visibility into which fields were modified

## Quick Start

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Analyze PDF structure (no changes)
python3 main.py --analyze-only

# Process PDF with default settings
python3 main.py

# Custom width extension
python3 main.py --width 80
```

## Project Structure

- `src/analyzer.py` - PDF field detection and analysis (117 lines)
- `src/field_adder.py` - Price field widening via FieldModifier class (258 lines)
- `main.py` - CLI entry point with argparse (147 lines)
- `tests/` - Pytest test suite (12 tests, all passing)

## Test Results

All 12 tests passing:
- PDFAnalyzer: 6 tests
- FieldModifier: 6 tests (includes new overlap detection tests)
- Test coverage: analyzer.py and field_adder.py

## Current Status

**FULLY FUNCTIONAL WITH SMART FEATURES** - Processed the Cambridge catalog:
- Input: 36 pages, 702 existing price fields
- **Widened: 523 fields** (average extension: 64.3 points)
- **Skipped: 179 fields** (insufficient space due to nearby content)
- Output location: `output/cambridge_pavers_catalog_edited.pdf` (11MB)
- New field format: `#####/###.##` (e.g., `12345/$999.99`)
- All fields: Right-justified text alignment

## Dependencies

- PyMuPDF >= 1.23.0 (PDF manipulation)
- pytest >= 7.0.0 (testing)

## Field Modification Details

**Default width extension**: 70 points to the left
**Minimum safe extension**: Adaptive (10% of desired width, minimum 1 point)
**Content buffer**: 3 points between field and content
**Text alignment**: Right-justified (text_format=2)
**Character limit**: Removed (allows full `#####/###.##` format)

## Overlap Detection Algorithm

1. Extract all text block bounding boxes from the page
2. For each field, calculate proposed extended rectangle
3. Check for overlaps with all content rectangles (with 2pt margin)
4. If overlap detected, calculate maximum safe extension
5. Only widen if safe extension ≥ 30 points
6. Apply right justification to widened fields

## Known Limitations

1. Price field detection relies on keyword matching in field names
2. Only detects text block overlaps (not images or vector graphics)
3. Minimum extension is adaptive: 10% of desired width (min 1pt)
4. Field extension assumes left-to-right layout with space available to the left
5. Right justification applied to all fields (not configurable per-field)

## Performance Notes

- Content extraction uses `get_text("dict")` for efficient bounding box retrieval
- Fields grouped by page to minimize page access
- Single pass through content per page
- Processing time: ~60-90 seconds for 702 fields across 36 pages

## Future Enhancements

- Support for custom field naming patterns
- Image and vector graphics overlap detection
- Batch processing of multiple PDFs
- GUI for visual field adjustment
- Configurable minimum safe extension threshold
- Per-field text alignment control
- Field validation for the #####/###.## format
- Export skip report (which fields and why)

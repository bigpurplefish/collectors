# Claude Code Development Notes

## Project Overview

This project was created to parse the Cambridge pavers catalog PDF and extract product information into an Excel spreadsheet. The tool is specific to this particular catalog format.

## Implementation Decisions

### Library Choices

- **pdfplumber** - Chosen for PDF parsing due to:
  - Trust score: 9.6/10 on Context7
  - Excellent table extraction capabilities
  - 88 code examples available
  - Support for custom table detection settings

- **openpyxl** - Chosen for Excel generation due to:
  - Native .xlsx format support
  - Font formatting capabilities (Arial 11pt requirement)
  - Column width auto-fit support
  - Rich formatting options

### PDF Structure

- **Page 2**: Color pricing categories table (3 columns: category, reason, colors list)
- **Pages 4-5**: Product tables in 3-column layout
  - Page 4: Paving stones
  - Page 5: Wall stones
  - Tables flow column-by-column, top-to-bottom, left-to-right
  - Product headers: Bold text on blue background
  - Color cells: Regular text on white background
  - Some cells may be empty

### Data Flow

1. Extract color categories from page 2 → ColorCategory objects
2. Parse product tables from pages 4-5 → Product objects with color lists
3. Map each product-color combination to pricing category
4. Generate Excel with sorted output (title → color_category → color)
5. Apply Arial 11pt font and auto-fit column widths

## Key Requirements

- Python 3.13.0 via pyenv virtual environment named "pdf_parser"
- Only include colors that appear in product tables (pages 4-5)
- Ignore "PLUS"/"CLASSIC" category headers on page 5
- Sort output: title (asc) → color_category (asc) → color (asc)
- Excel formatting: Arial 11pt, auto-fit columns
- Leave price and item_# columns blank

## Development Notes

- Project follows Python best practices from /Users/moosemarketer/Code/shared-docs/python
- Context7 documentation retrieved before implementation
- Modular design with separation of concerns
- Thin orchestration layer in main.py

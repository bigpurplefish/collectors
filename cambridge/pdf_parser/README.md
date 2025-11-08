# Cambridge Pavers Catalog PDF Parser

Parses the Cambridge pavers catalog PDF to extract product information and generate an Excel spreadsheet with product colors and pricing categories.

## Setup

1. Create and activate the pyenv virtual environment:
```bash
pyenv virtualenv 3.13.0 pdf_parser
pyenv activate pdf_parser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Place the Cambridge pavers catalog PDF in the `input/` directory, then run:

```bash
python main.py
```

The output Excel file will be generated in the `output/` directory.

## Project Structure

- `main.py` - Entry point for the application
- `src/` - Main application code
  - `config.py` - PDF structure configuration
  - `models.py` - Data models (Product, ColorCategory)
  - `pdf_extractor.py` - PDF reading and page extraction
  - `table_parser.py` - Table structure parsing
  - `color_mapper.py` - Color-to-category mapping
  - `excel_generator.py` - Excel file creation with formatting
- `utils/` - Utility functions
  - `text_utils.py` - Text cleaning functions
  - `validators.py` - Data validation
- `input/` - Input PDF files
- `output/` - Generated Excel files
- `tests/` - Test files

## Output Format

The generated Excel file contains the following columns:
- `title` - Product name
- `color_category` - Color pricing category
- `color` - Product color
- `price` - (blank, for manual entry)
- `item_#` - (blank, for manual entry)

Rows are sorted by title, color_category, and color (all ascending).
Font: Arial 11pt with auto-fit column widths.

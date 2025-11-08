# Tests

This directory contains all test files for the pdf_parser project.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_table_parser.py
```

## Test Structure

- `test_table_parser.py` - Tests for table parsing functionality
- `test_color_mapper.py` - Tests for color-to-category mapping
- `test_excel_generator.py` - Tests for Excel generation
- `output/` - Test output files (gitignored)

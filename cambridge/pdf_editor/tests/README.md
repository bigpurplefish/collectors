# Tests

This directory contains all tests for the PDF Editor project.

## Structure

- `samples/` - Sample PDF files and test data
- `output/` - Test outputs (gitignored)
- Test files follow the pattern `test_*.py`

## Running Tests

```bash
# Run all tests
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_analyzer.py

# Run with coverage
python3 -m pytest --cov=src
```

## Test Organization

Tests are organized by module:
- `test_analyzer.py` - Tests for PDF field detection and analysis
- `test_field_adder.py` - Tests for item number field addition
- `test_formatting.py` - Tests for OCR-friendly formatting

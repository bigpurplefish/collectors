# Tests Directory

This directory contains test scripts and their outputs for the Purinamills collector.

## Structure

```
tests/
├── README.md           # This file
├── .gitignore          # Ignores test outputs
├── output/             # Test output files (ignored by git)
│   └── .gitkeep
├── samples/            # Sample HTML pages for testing
│   ├── shop.purina.com/
│   └── www.purina.com/
└── test_*.py           # Test scripts
```

## Purpose

- **Isolate test artifacts** from production code
- **Prevent test data pollution** in main output directory
- **Follow Python best practices** for test organization

## Usage

Run tests from the project root:

```bash
cd /Users/moosemarketer/Code/Python/collectors/purinamills
python3 tests/test_workflow.py
python3 tests/test_www_search.py
```

All test outputs will be written to `tests/output/` and automatically ignored by git.

## Test Scripts

- `test_workflow.py` - End-to-end workflow testing
- `test_www_search.py` - WWW site search testing
- `test_www_search_direct.py` - Direct WWW search testing
- `test_www_playwright.py` - Playwright-based testing
- `test_variants.py` - Variant handling testing
- `test_variant_images.py` - Variant image testing

## Sample Data

The `samples/` directory contains sample HTML pages from:
- `shop.purina.com/` - E-commerce site samples
- `www.purina.com/` - Information site samples

These samples are used for offline testing and development.

## Best Practices

✅ **Do:**
- Place all test scripts in `tests/` directory
- Write test outputs to `tests/output/`
- Use descriptive names: `test_www_search.py`
- Document what each test does

❌ **Don't:**
- Commit test output files
- Mix test files with production code
- Write test outputs to main `output/` directory

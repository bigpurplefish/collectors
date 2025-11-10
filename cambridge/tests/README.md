# Tests Directory

This directory contains test scripts and their outputs for the Cambridge collector.

## Structure

```
tests/
├── README.md           # This file
├── .gitignore          # Ignores test outputs
├── output/             # Test output files (ignored by git)
│   └── .gitkeep
├── samples/            # Sample HTML pages for testing
│   └── cambridge/
└── test_*.py           # Test scripts
```

## Purpose

- **Isolate test artifacts** from production code
- **Prevent test data pollution** in main output directory
- **Follow Python best practices** for test organization

## Usage

Run tests from the project root:

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/cambridge
python3 tests/test_workflow.py
python3 tests/test_index_builder.py
```

All test outputs will be written to `tests/output/` and automatically ignored by git.

## Test Scripts

- `test_workflow.py` - End-to-end workflow testing
- `test_index_builder.py` - Product index building and caching
- `test_search.py` - Search and matching functionality
- `test_parser.py` - Parser testing

## Sample Data

The `samples/` directory contains sample HTML pages from Cambridge sites for offline testing.

## Best Practices

✅ **Do:**
- Place all test scripts in `tests/` directory
- Write test outputs to `tests/output/`
- Use descriptive names: `test_feature_name.py`
- Document what each test does

❌ **Don't:**
- Commit test output files
- Mix test files with production code
- Write test outputs to main `output/` directory

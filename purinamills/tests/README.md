# Tests Directory

This directory contains test scripts and their outputs for the Purinamills collector.

## Structure

```
tests/
├── README.md           # This file
├── .gitignore          # Ignores test outputs
├── output/             # Test output files (ignored by git)
│   └── .gitkeep
└── test_*.py           # Test scripts (tracked by git)
```

## Purpose

- **Isolate test artifacts** from production code
- **Prevent test data pollution** in main output directory
- **Follow Python best practices** for test organization

## Usage

Run tests from the project root:

```bash
cd /Users/moosemarketer/Code/Python/collectors/purinamills
python3 tests/test_example.py
```

All test outputs will be written to `tests/output/` and automatically ignored by git.

## Moving Existing Test Files

If you have test files in the project root, move them here:

```bash
mv test_*.py tests/
mv test_*.html tests/output/
```

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

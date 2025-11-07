# Tests Directory

This directory contains test scripts and their outputs for the ethical collector.

## Structure

```
tests/
├── README.md           # This file
├── .gitignore          # Ignores test outputs
├── output/             # Test output files (ignored by git)
│   └── .gitkeep
└── test_*.py           # Test scripts
```

## Purpose

- **Isolate test artifacts** from production code
- **Prevent test data pollution** in main output directory
- **Follow Python best practices** for test organization

## Usage

Run tests from the project root:

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/ethical
python3 tests/test_workflow.py
```

All test outputs will be written to `tests/output/` and automatically ignored by git.

## Best Practices

✅ **Do:**
- Place all test scripts in `tests/` directory
- Write test outputs to `tests/output/`
- Use descriptive names: `test_workflow.py`
- Document what each test does

❌ **Don't:**
- Commit test output files
- Mix test files with production code
- Write test outputs to main `output/` directory

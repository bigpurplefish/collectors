# Cambridge Collector - Quick Start Guide

## Installation (5 minutes)

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/cambridge

# Set Python version (already configured)
pyenv local 3.12.9

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements-gui.txt

# Install Playwright browser
playwright install chromium
```

## First Run

```bash
# Launch GUI
python3 gui.py
```

**In GUI:**
1. Portal Username: `markjr@garoppos.com`
2. Portal Password: `Garoppos2025!`
3. Input File: Browse to `pdf_parser/output/cambridge_products.xlsx`
4. Output File: `output/cambridge_products.json`
5. Log File: `logs/cambridge.log`
6. Click "Start Processing"

**First run will:**
- Build product index (~2-3 minutes)
- Cache index to `cache/product_index.json`
- Process products
- Generate output

## Subsequent Runs

Index is cached! Subsequent runs are much faster (no 2-3 minute wait).

## Test with Small Sample

Set record range in GUI:
- Start Record: 1
- End Record: 2

This processes only 2 records for quick testing.

## Rebuild Index

Check "Force Rebuild Product Index" if:
- Cambridge adds new products
- Index is stale
- Index seems incomplete

## Troubleshooting

### "Playwright browser not found"
```bash
playwright install chromium
```

### "Login failed"
- Verify credentials in GUI
- Try logging in manually at https://shop.cambridgepavers.com

### "Product not found"
- Rebuild index (check box in GUI)
- Verify product title in input file

## Next Steps

- Review README.md for full documentation
- Review CLAUDE.md for development guide
- Check logs in `logs/cambridge.log`

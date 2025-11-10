# Cambridge Collector - Quick Start Guide

## Installation (5 minutes)

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/cambridge

# Create pyenv virtualenv named "cambridge"
pyenv virtualenv 3.12.9 cambridge

# Activate (or it's already active via .python-version)
pyenv local cambridge

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
1. Click "⚙️ Settings" button (or Settings menu → Portal Credentials)
2. Enter Portal Username: `markjr@garoppos.com`
3. Enter Portal Password: `Garoppos2025!`
4. Click "Save"
5. Input File: Browse to `pdf_parser/output/cambridge_products.xlsx`
6. Output File: `output/cambridge_products.json`
7. Log File: `logs/cambridge.log`
8. Click "Start Processing"

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

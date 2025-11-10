# Cambridge Product Collector

Collects product data from Cambridge Pavers public website and dealer portal, generating Shopify-compatible product data in GraphQL 2025-10 format.

## Overview

The Cambridge collector:
1. Reads product data from Excel input file
2. Searches for products using cached product index
3. Collects lifestyle images and descriptions from public website
4. Collects product images, pricing, and specifications from dealer portal
5. Groups products by title (color variants)
6. Generates Shopify GraphQL-compatible output

**Key Features:**
- ✅ Cached product index (auto-refreshes if stale)
- ✅ Fuzzy title matching for product search
- ✅ Automatic variant grouping by title
- ✅ Dealer portal authentication (Playwright-based)
- ✅ Skip/overwrite processing modes
- ✅ Record range selection
- ✅ Thread-safe GUI with real-time status updates

---

## Requirements

### System Requirements
- Python 3.8+
- Internet connection
- Cambridge dealer portal credentials

### Dependencies
Core dependencies are listed in `requirements.txt`:
- requests, beautifulsoup4, lxml
- pandas, openpyxl (Excel support)
- rapidfuzz (fuzzy matching)
- playwright (browser automation)

---

## Installation

### 1. Setup Python Environment

This project requires Python 3.12.9 managed with pyenv, with a virtualenv named "cambridge".

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/cambridge

# Create pyenv virtualenv named "cambridge"
pyenv virtualenv 3.12.9 cambridge

# Set as local environment (already configured via .python-version)
pyenv local cambridge

# Verify correct environment
python --version  # Should show Python 3.12.9

# Upgrade pip
pip install --upgrade pip
```

**Note:** The `.python-version` file is already configured to use the `cambridge` virtualenv.

### 2. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# GUI dependencies (if using GUI)
pip install -r requirements-gui.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

---

## Project Structure

```
cambridge/
├── README.md                   # This file
├── CLAUDE.md                   # Development guidance
├── main.py                     # CLI entry point
├── gui.py                      # GUI entry point
├── config.json                 # Configuration (auto-generated)
├── requirements.txt            # Core dependencies
├── requirements-gui.txt        # GUI dependencies
├── requirements-dev.txt        # Development dependencies
│
├── src/                        # Application code
│   ├── __init__.py
│   ├── collector.py            # Main collector orchestration
│   ├── config.py               # Configuration management
│   ├── index_builder.py        # Product index builder
│   ├── search.py               # Search and fuzzy matching
│   ├── public_parser.py        # Public website parser
│   ├── portal_parser.py        # Dealer portal parser (Playwright)
│   ├── product_generator.py   # Shopify product generator
│   └── processor.py            # Processing workflow
│
├── scripts/                    # Utility scripts
│   └── build_index.py          # Standalone index builder
│
├── cache/                      # Cached data
│   └── product_index.json      # Cached product index
│
├── input/                      # Input files
│   └── .gitkeep
│
├── output/                     # Output files
│   └── .gitkeep
│
└── tests/                      # Test scripts
    ├── README.md
    ├── output/                 # Test outputs (ignored)
    └── samples/                # Sample data
```

---

## Usage

### GUI Mode (Recommended)

```bash
python3 gui.py
```

**Configuration:**
1. Click "⚙️ Settings" button (or Settings menu → Portal Credentials)
   - Enter dealer portal username
   - Enter dealer portal password
   - Click "Save"
2. Select input Excel file
3. Select output JSON file location
4. Choose processing mode (Skip/Overwrite)
5. Optional: Set record range (start/end)
6. Optional: Force rebuild product index
7. Click "Start Processing"

### CLI Mode

```bash
# First, configure settings in config.json
python3 main.py
```

### Rebuild Product Index

```bash
# Standalone script to rebuild cached index
python3 scripts/build_index.py
```

---

## Input File Format

The input file must be an Excel file (.xlsx) with the following columns:

| Column          | Description                    | Required |
|-----------------|--------------------------------|----------|
| `vendor_type`   | Product category               | Yes      |
| `title`         | Product title                  | Yes      |
| `color_category`| Color category (STANDARD, etc) | Yes      |
| `color`         | Color variant name             | Yes      |
| `item_#`        | Item number / SKU              | No       |
| `price`         | Retail price                   | No       |

**Example:**

```
vendor_type      | title                            | color_category | color          | item_# | price
Paving Stones    | Sherwood Ledgestone 3-Pc. Kit   | STANDARD      | Onyx/Natural   |        |
Paving Stones    | Sherwood Ledgestone 3-Pc. Kit   | STANDARD      | Driftwood      |        |
```

**Important:** Records with the same `title` are treated as color variants of the same product.

---

## Output File Format

The output is a JSON file containing Shopify products in GraphQL 2025-10 format:

```json
{
  "products": [
    {
      "title": "Sherwood Ledgestone 3-Pc. Design Kit",
      "descriptionHtml": "<p>Product description...</p>",
      "vendor": "Cambridge Pavers",
      "status": "ACTIVE",
      "options": [
        {
          "name": "Color",
          "position": 1,
          "values": ["Onyx/Natural", "Driftwood"]
        }
      ],
      "variants": [
        {
          "sku": "",
          "price": "0.00",
          "option1": "Onyx/Natural",
          "metafields": [...]
        }
      ],
      "images": [
        {
          "position": 1,
          "src": "https://...",
          "alt": "..."
        }
      ],
      "metafields": [...]
    }
  ]
}
```

**Image Ordering:**
1. Product images from dealer portal (all colors)
2. Hero image from public website
3. Gallery images from public website

---

## Configuration

Configuration is stored in `config.json` (auto-generated on first run).

### Portal Credentials
```json
{
  "portal_username": "your-email@example.com",
  "portal_password": "your-password"
}
```

### File Paths
```json
{
  "input_file": "/path/to/cambridge_products.xlsx",
  "output_file": "/path/to/output.json",
  "log_file": "logs/cambridge.log"
}
```

### Processing Options
```json
{
  "processing_mode": "skip",     // "skip" or "overwrite"
  "start_record": "",            // Leave blank to start from beginning
  "end_record": "",              // Leave blank to process all
  "rebuild_index": false,        // Force rebuild product index
  "index_max_age_days": 7        // Auto-rebuild if older than 7 days
}
```

---

## Product Indexes

The collector builds TWO searchable product indexes:

1. **Public Site Index** (`cache/product_index.json`) - Crawls www.cambridgepavers.com
2. **Portal Index** (`cache/portal_product_index.json`) - Crawls shop.cambridgepavers.com

Both indexes are cached and auto-refresh when stale.

### Index Management

**Auto-refresh:** Indexes automatically rebuild if older than `index_max_age_days` (default: 7 days)

**Manual rebuild:**
- GUI: Check "Force Rebuild Product Index"
- CLI: Set `"rebuild_index": true` in config.json
- Script: Run `python3 scripts/build_index.py`

**Public Index Structure:**
```json
{
  "last_updated": "2025-11-10T12:00:00",
  "total_products": 150,
  "products": [
    {
      "prodid": 64,
      "title": "Sherwood Ledgestone 3-Pc. Design Kit",
      "url": "/pavers-details?prodid=64",
      "category": "Sherwood Collection"
    }
  ]
}
```

**Portal Index Structure:**
```json
{
  "last_updated": "2025-11-10T12:00:00",
  "total_products": 120,
  "products": [
    {
      "title": "Sherwood Ledgestone 3-Pc. Design Kit",
      "url": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit",
      "category": "/pavers/sherwood"
    }
  ]
}
```

**Note:** Portal uses SEO-friendly URLs (e.g., `/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit`), unlike the public site which uses `prodid` parameters.

---

## Data Collection

### Public Website (www.cambridgepavers.com)
- Hero image (top of page)
- Gallery images (carousel)
- Product description
- Specifications
- Collection name
- Available colors

### Dealer Portal (shop.cambridgepavers.com)
- Product gallery images
- Item weight
- Sales unit (unit of sale)
- Cost/price
- Vendor SKU (model number)

---

## Processing Modes

### Skip Mode (Default)
- Skips products that already exist in output file
- Resume interrupted processing
- Safe for incremental updates

### Overwrite Mode
- Re-processes all products
- Overwrites existing data
- Use when updating all products

---

## Error Handling

### Common Issues

**Portal Login Fails:**
- Verify credentials in config.json
- Check network connection
- Ensure Playwright browsers are installed: `playwright install chromium`

**Product Not Found:**
- Product may not exist on Cambridge website
- Try rebuilding product index
- Check product title spelling in input file

**Index Build Fails:**
- Check network connection
- Verify Cambridge website is accessible
- Check logs for specific errors

### Logs

Logs are written to the configured log file (default: `logs/cambridge.log`):
- INFO: Processing progress
- WARNING: Non-fatal issues
- ERROR: Processing errors
- EXCEPTION: Stack traces

---

## Development

### Code Style
- Follow PEP 8
- Use type hints where possible
- Document all public functions

### Testing

**Run Individual Tests:**

```bash
# Test parsers and search (fast, ~5 seconds)
python3 tests/test_parsers.py

# Test index building (slow, ~2-3 minutes)
python3 tests/test_index_builder.py

# Test end-to-end workflow (moderate, ~30 seconds)
python3 tests/test_workflow.py
```

**What Each Test Does:**

1. **test_parsers.py**
   - Tests public website parser with sample HTML
   - Tests search/fuzzy matching with mock data
   - No network required (uses sample files)

2. **test_index_builder.py**
   - Tests cache save/load functionality
   - Tests live product index building (requires network)
   - Prompts before running slow network test

3. **test_workflow.py**
   - Tests complete workflow with first 2 products
   - Requires network and cached index
   - Skips portal (no credentials needed)
   - Generates test output JSON

**Run All Tests:**

```bash
# Quick tests only (no slow network tests)
python3 tests/test_parsers.py

# Full test suite (includes slow tests)
python3 tests/test_index_builder.py
python3 tests/test_workflow.py
```

### Debugging
```bash
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Troubleshooting

### Problem: "Product index is stale"
**Solution:** Check "Force Rebuild Product Index" or run `scripts/build_index.py`

### Problem: "Portal login failed"
**Solution:**
1. Verify credentials in config.json
2. Try logging in manually at https://shop.cambridgepavers.com
3. Check if account is active

### Problem: "No products found"
**Solution:**
1. Verify input file format
2. Check product titles match Cambridge website
3. Try rebuilding product index

### Problem: "Playwright browser not found"
**Solution:** Run `playwright install chromium`

---

## Support

For issues or questions:
1. Check logs in configured log file
2. Review CLAUDE.md for development guidance
3. Check shared-docs for requirements

---

## Version History

### v1.0.0 (2025-11-10)
- Initial release
- Public website parsing
- Dealer portal integration (Playwright)
- Cached product index
- GUI with thread-safe status updates
- Variant grouping by title
- Shopify GraphQL 2025-10 output format

---

## License

Internal use only - Garoppos

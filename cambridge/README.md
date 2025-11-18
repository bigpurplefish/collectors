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
- ✅ Alternate title fallback for portal search
- ✅ Portal-only fallback when public site fails
- ✅ Automatic variant grouping by title
- ✅ Automatic SKU generation (cross-collector uniqueness)
- ✅ Dealer portal authentication (Playwright-based)
- ✅ Skip/overwrite processing modes
- ✅ Record range selection
- ✅ Thread-safe GUI with real-time status updates
- ✅ Shopify variant image filtering (alt tag generation)
- ✅ Image URL cleaning and deduplication
- ✅ Standard weight fields (value + unit)
- ✅ Unit of sale as variant option
- ✅ Cost and price from input file
- ✅ Graceful error handling with detailed reporting
- ✅ Data validation and missing field tracking

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
6. Review **Product Indexes** status (shows both indexes):
   - **Public Site Index**: Products from www.cambridgepavers.com (60 products)
   - **Portal Index**: Products from shop.cambridgepavers.com (362 products)
7. Optional: Check "Force Rebuild Both Product Indexes" to rebuild
8. Click "Start Processing"

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

| Column          | Description                                | Required |
|-----------------|-------------------------------------------|----------|
| `vendor_type`   | Product category                          | Yes      |
| `title`         | Product title                             | Yes      |
| `title_alt`     | Alternate title for portal search fallback | No       |
| `color_category`| Color category (STANDARD, etc)             | Yes      |
| `color`         | Color variant name                        | Yes      |
| `item_#`        | Item number / SKU                         | No       |
| `price`         | Retail price                              | No       |

**Example:**

```
vendor_type   | title                          | title_alt                    | color_category | color        | item_# | price
Paving Stones | Sherwood Ledgestone 3-Pc. Kit | Sherwood Ledgestone Design  | STANDARD      | Onyx/Natural |        |
Paving Stones | Sherwood Ledgestone 3-Pc. Kit | Sherwood Ledgestone Design  | STANDARD      | Driftwood    |        |
```

**Important Notes:**
- Records with the same `title` are treated as color variants of the same product
- `title_alt` is used as a fallback when searching the dealer portal - if the primary title doesn't find a match in the portal index, the alternate title will be tried automatically
- If a product is not found on the public website, the collector will attempt to use portal data only (see Fallback Behavior below)

---

## Output File Format

The collector generates two output files:

### 1. Product Data File (`output.json`)
Main JSON file containing Shopify products in GraphQL 2025-10 format:

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

### 2. Processing Report (`output_report.json`)
Detailed report of processing results, failures, and warnings:

```json
{
  "summary": {
    "total_products": 100,
    "successful": 95,
    "skipped": 0,
    "failed": 3,
    "with_warnings": 2
  },
  "failures": [
    {
      "title": "Product Name",
      "reason": "Product URL not found in public index",
      "colors": ["Red", "Blue"],
      "search_color": "Red",
      "variant_count": 2
    },
    {
      "title": "Another Product",
      "reason": "Public data validation failed",
      "missing_critical_fields": ["title"],
      "missing_important_fields": ["description", "hero_image"],
      "public_data_summary": {
        "has_title": false,
        "has_description": false,
        "gallery_image_count": 0
      }
    }
  ],
  "warnings": [
    {
      "title": "Product with Partial Data",
      "reason": "Product generated with incomplete portal data",
      "portal_warnings": [
        {
          "color": "Red",
          "missing_fields": ["model_number", "weight"],
          "summary": {
            "has_gallery_images": true,
            "gallery_image_count": 3,
            "has_cost": true,
            "has_model_number": false,
            "has_weight": false
          }
        }
      ]
    }
  ]
}
```

**Report Details:**
- **Failures**: Products that were skipped due to missing critical data
- **Warnings**: Products that were processed but have missing portal data for some colors
- **Summary**: Overall processing statistics

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

1. **Public Site Index** (`cache/product_index.json`) - Crawls www.cambridgepavers.com to find product detail pages
2. **Portal Index** (`cache/portal_product_index.json`) - Uses two-stage authenticated API to fetch individual product variants from shop.cambridgepavers.com

Both indexes are cached and auto-refresh when stale.

**Portal Index Two-Stage Approach:**
1. **Stage 1 (Navigation API)** - Fetches category URLs (no auth required, ~362 categories)
2. **Stage 2 (Search API)** - Authenticates with Playwright and fetches individual products with SKUs, prices, stock, and images for each category

**Important:** Portal index building requires dealer portal credentials and takes several minutes to complete (queries 362 categories via authenticated search API). The resulting index contains complete product data including SKUs, prices, stock levels, and images.

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
  "last_updated": "2025-11-10T12:00:00Z",
  "total_products": 850,
  "products": [
    {
      "title": "Sherwood Ledgestone 3-Pc. Design Kit - Driftwood",
      "url": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit/Driftwood_6",
      "category": "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit",
      "sku": "ITEM123456",
      "price": "5.99",
      "stock": 1250,
      "images": [
        "https://shop.cambridgepavers.com/...",
        "https://shop.cambridgepavers.com/..."
      ]
    }
  ]
}
```

**Notes:**
- Portal uses SEO-friendly URLs with `urlcomponent` (e.g., `/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit/Driftwood_6`)
- Each product includes SKU, price, stock level, and image URLs from the search API
- Product titles include color variant names
- Index contains individual products, not category pages

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

## SKU Generation

Cambridge products do not have SKUs in the source data. The collector uses a **shared SKU generator utility** that ensures unique SKU assignment across all collectors in the Garoppos project.

### How It Works

1. **Automatic Generation**: Every product variant automatically receives a unique 5-digit SKU starting from 50000
2. **Cross-Collector Uniqueness**: Uses a persistent registry file (`cache/sku_registry.json`) shared across all collectors
3. **Thread-Safe**: Safe for concurrent use across multiple collector instances
4. **Barcode Assignment**: The generated SKU is also used as the product barcode

### Implementation

The SKU generator is implemented in `/shared/utils/sku_generator.py` and is automatically initialized when the product generator starts.

```python
# Example usage (handled automatically)
from shared.utils.sku_generator import SKUGenerator

generator = SKUGenerator()
sku = generator.generate_unique_sku()  # Returns "50000", "50001", etc.
```

### Registry Location

The SKU registry is stored at `/collectors/cache/sku_registry.json` (parent-level cache) to ensure uniqueness across:
- Cambridge collector
- TechoBlocskirt collector
- All other collectors in the project

### Persistence

- SKUs are persisted immediately upon generation
- If a collector crashes, the registry ensures no SKU duplication on restart
- The registry tracks both used SKUs and the next available SKU number

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

The collector implements **graceful error handling** that continues processing even when individual products fail. Products with missing critical data are skipped and tracked in a detailed report.

### Data Validation

The collector validates collected data and categorizes fields as:

**Critical Fields (Public Data):**
- `title` - Product must have a title to be processed

**Important Fields (Public Data):**
- `description` - Product description text
- `hero_image` - Main product image
- `gallery_images` - Lifestyle/gallery images

**Important Fields (Portal Data):**
- `gallery_images` - Product-specific images per color
- `cost` - Product cost
- `model_number` - Vendor SKU

### Fallback Behavior

The collector implements a **two-tier fallback system** to maximize product recovery:

**1. Alternate Title Fallback (Portal Search):**
- When searching the portal index by primary title + color fails
- If `title_alt` column has a value, automatically tries searching with alternate title
- Logs which title was used for the match
- Helps handle products with different naming between public site and portal

**2. Portal-Only Fallback (Public Site Missing):**
- When product is not found on public website (www.cambridgepavers.com)
- Automatically searches dealer portal (shop.cambridgepavers.com) for all color variants
- If portal data found, creates product using portal data only
- Product is **included in output** with available data
- Tracked in warnings report as "portal only" with missing public fields
- Missing public data: description, hero image, gallery images, specifications

**Result:** Products are only excluded from output if they cannot be found on either the public site OR the dealer portal.

### Processing Behavior

**When Product URL Not Found on Public Site:**
- Portal search attempted as fallback
- If found in portal: Product **included** with portal data only (tracked in warnings)
- If not found in portal: Product **skipped** (logged as failure)
- Processing continues with next product

**When Public Data Validation Fails:**
- Product is **skipped** (not included in output)
- Missing critical fields logged in report
- Processing continues with next product

**When Public Data Missing Important Fields:**
- Warning logged but product is **still processed**
- Missing fields tracked in console output
- Product included in output with available data

**When Portal Data Missing or Incomplete:**
- Warning logged but product is **still processed**
- Missing portal data tracked per color in warnings report
- Product included in output with public data and partial portal data

**When Exception Occurs:**
- Product is **skipped** (not included in output)
- Exception details logged in report
- Processing continues with next product

### Output Report

After processing, a detailed report (`output_report.json`) is generated containing:

1. **Summary Statistics**
   - Total products processed
   - Successful products
   - Skipped products (already in output file)
   - Failed products (missing critical data)
   - Products with warnings (incomplete portal data)

2. **Failures List**
   - Products that were skipped
   - Reason for failure
   - Missing critical/important fields
   - Data summary showing what was/wasn't collected

3. **Warnings List**
   - Products that were processed but have incomplete data
   - Portal data issues per color
   - Which specific fields are missing
   - Summary of what portal data was collected

### Common Issues

**Portal Login Fails:**
- Verify credentials in config.json
- Check network connection
- Ensure Playwright browsers are installed: `playwright install chromium`

**Product Not Found:**
- Product may not exist on Cambridge website
- Check processing report for specific failure reason
- Try rebuilding product index: GUI checkbox or `"rebuild_index": true`
- Check product title spelling in input file

**Index Build Fails:**
- Check network connection
- Verify Cambridge website is accessible
- Check logs for specific errors

**Products Missing Portal Data:**
- Check warnings section in processing report
- Verify portal credentials are correct
- Some colors may not be available in dealer portal
- Products are still included in output with available data

### Logs

Logs are written to the configured log file (default: `logs/cambridge.log`):
- INFO: Processing progress
- WARNING: Non-fatal issues (missing important fields)
- ERROR: Processing errors (validation failures)
- EXCEPTION: Stack traces

---

## Failure Tracking and Reporting

The collector now tracks both successful and failed products, generating comprehensive reports:

### Automatic Failure Tracking

When products fail to process, the collector:
1. **Records failure details** to `output/cambridge_failures.json`
2. **Logs the reason** (Product URL not found, data collection failed, etc.)
3. **Saves color and variant information** for troubleshooting

### Generating Comprehensive Reports

Generate a complete report showing both failures and data quality issues:

```bash
python3 generate_comprehensive_report.py
```

This creates `output/comprehensive_report.md` with:

**Section 1: Failed Products**
- Products that couldn't be processed
- Failure reasons (e.g., "Product URL not found in public index")
- Color variants and search details
- Troubleshooting recommendations

**Section 2: Data Quality Issues**
- Successfully processed products with missing data
- **Each variant listed once** with all missing fields together
- **Individual variant details** with SKU, color, and unit
- **Missing fields highlighted** at the top of each variant entry
- **Current values shown** only for missing fields
- **Both public and portal URLs** for manual verification and troubleshooting
- **Field count summary** showing how many variants are affected by each field type

### Report Contents

The comprehensive report includes:
- **Total products attempted** (successful + failed)
- **Processing summary** with counts
- **Failed products grouped by failure reason**
- **Consolidated variant list** - each variant appears once with all missing fields
- **Field count summary** - shows how many variants are missing each field type
- **Data quality details** for each variant with missing data
- **Troubleshooting recommendations** for each issue type

### Files Generated

| File | Contents |
|------|----------|
| `output/cambridge.json` | Successfully processed products (Shopify format) |
| `output/cambridge_failures.json` | Failed products with failure details |
| `output/comprehensive_report.md` | Complete report (failures + data quality) |

### Example Failure Report

```markdown
## SECTION 1: FAILED PRODUCTS

### Failure Reason: Product URL not found in public index

**Count**: 8 products

#### Sherwood Brick Alley
- **Variant Count**: 1
- **Colors**: Brandywine
- **Search Color**: Brandywine

#### RoundTable 6 x 6
- **Variant Count**: 1
- **Colors**: Onyx
- **Search Color**: Onyx
```

### Example Data Quality Report

The report shows each variant once with all missing fields listed together:

```markdown
### 2.3. Variants with Missing Data

#### Edgestone Plus

**Total variants with missing data**: 4

##### Variant 1: Toffee/Onyx Lite - Sq Ft

- **SKU**: `56730`
- **Color**: Toffee/Onyx Lite
- **Unit of Sale**: Sq Ft
- **Missing Fields**: `weight, model_number, color_swatch`
- **Weight**: 0 (missing or zero)
- **Model Number**: N/A (missing)
- **Color Swatch**: N/A (missing)
- **Public URL**: https://www.cambridgepavers.com/pavers-details?prodid=123
- **Portal URL**: https://shop.cambridgepavers.com/pavers/edgestone-plus
```

**Key Features:**
- **Each variant listed once** with all missing fields together
- **SKU for easy identification** and reference
- **Missing fields highlighted** at the top of each variant entry
- **Current values displayed** for each missing field
- **Both public and portal URLs** for manual verification
- **Grouped by product** for easier navigation
- **Field count summary** shows how many variants are affected by each field type

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

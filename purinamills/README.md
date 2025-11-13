# Purinamills Product Collector

Collects and enriches product data from Purina Mills websites for Shopify import.

## Overview

This collector retrieves product information from two Purina Mills websites:
- **shop.purinamills.com** - Primary e-commerce site (Shopify)
- **www.purinamills.com** - Secondary information site (fallback)

It uses a 3-tier fallback strategy:
1. Exact match using `description_1` field on shop site
2. Fuzzy match using description_1/upcitemdb_title on shop site
3. Fallback to www site if shop site has no matches

## Features

### Search & Collection
- **Dual-site support** - Searches shop.purinamills.com first, falls back to www.purinamills.com
- **3-tier search strategy**:
  1. Exact match using `description_1` field (shop site via HTTP)
  2. Fuzzy match with keyword extraction and synonyms (shop site)
  3. WWW site fallback search (requires Playwright)
- **Playwright for JavaScript rendering** - WWW site requires headless browser (Chromium)
- **Headless browser automation** - Launches Chromium, waits for network idle
- **Direct site search** - No index building required
- **Keyword-based scoring** with stop words filtering
- **Configurable match threshold** (default: 0.3)
- **UPCItemDB fallback** - When product not found on manufacturer sites

### Data Processing
- **Dual-site HTML parsing** - Auto-detects Shopify vs WordPress format
- **JSON-LD structured data** extraction from shop site
- **Variant/parent product support** - Groups related SKUs
- **WWW data merging** - Combines shop and www site data when available
- **Field normalization** - Cleans and standardizes all product data
- **PDF document extraction** - Captures product PDFs from "Additional Materials" sections

### Image Processing (UPCItemDB Fallback Only)
- **Image quality assessment** - Laplacian variance (sharpness detection) for UPCItemDB images
- **Placeholder detection** - Perceptual hashing (imagehash library) filters generic images
- **Whitespace cropping** - OpenCV-based border removal
- **Best image selection** - Evaluates dimensions, sharpness, and quality
- **Configurable thresholds** - Laplacian threshold (default: 100, configurable in GUI)
- **Dependencies** - OpenCV, NumPy, Pillow, imagehash for image processing
- **Only used when product not found on manufacturer sites** - Manufacturer images used as-is

### Shopify Output
- **GraphQL-compliant structure** - Ready for Shopify Admin API
- **HTML cleaning** - Removes scripts, styles, non-content elements
- **Media array generation** - Includes images and videos (PDFs stored in metafields)
- **Variant structure** - Properly formatted parent/variant relationships
- **Alt tag generation** - SEO-friendly image descriptions
- **Size normalization** - Standardizes weight/volume formats
- **PDF storage** - Documents stored in custom.documentation metafield as JSON

### User Interfaces
- **Thread-safe GUI** with queue-based communication (follows GUI_DESIGN_REQUIREMENTS.md)
- **CLI interface** for automation and scripting
- **Real-time progress tracking** with detailed status messages
- **Configurable processing modes**:
  - Skip existing records
  - Overwrite all records
- **Record range selection** - Process subset of records (Start/End Record fields)
- **Auto-save configuration** - Persists settings between sessions
- **Error tracking** - Generates error report Excel files
- **Unmatched products handling** - Products with no manufacturer match AND no UPCItemDB data are saved to separate `_unmatched.json` file

### Performance & Reliability
- **Rate limiting** with configurable jitter (200-700ms)
- **Automatic retry logic** with exponential backoff
- **Request timeout handling** (30 second default)
- **HTTP error handling** - Graceful degradation on failures
- **Logging system** - Detailed logs for debugging

## Installation

```bash
# Clone or navigate to project
cd /Users/moosemarketer/Code/Python/collectors/purinamills

# Set up virtual environment
pyenv local purinamills

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for www site search)
playwright install chromium

# For GUI support
pip install -r requirements-gui.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

**Core (requirements.txt):**
- `requests>=2.31.0` - HTTP requests for shop site
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - Fast XML/HTML parsing
- `playwright>=1.40.0` - Headless browser for www site (requires JavaScript)
- `openpyxl>=3.1.0` - Excel file reading
- `Pillow>=10.0.0` - Image processing
- `opencv-python>=4.8.0` - Image quality assessment
- `numpy>=1.24.0` - Numerical operations for image processing
- `imagehash>=4.3.0` - Perceptual hashing for placeholder detection

**GUI (requirements-gui.txt):**
- `ttkbootstrap>=1.10.1` - Modern themed Tkinter widgets

**Development (requirements-dev.txt):**
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.7.0` - Code formatting
- `flake8>=6.1.0` - Linting
- `mypy>=1.5.0` - Type checking

## Usage

### GUI Mode (Recommended)

```bash
python gui.py
```

The GUI provides:
- **File selection dialogs** - Browse for input/output files
- **Real-time progress tracking** - Live status updates during processing
- **Processing modes**:
  - **Skip**: Skip products that already exist in output
  - **Overwrite**: Reprocess all products
- **Record range selection**:
  - **Start Record**: First record to process (leave blank for beginning)
  - **End Record**: Last record to process (leave blank for end)
- **Tooltips** - Helpful hints on every field
- **Auto-save configuration** - All settings persist between sessions
- **Dark theme** - Easy on the eyes for long sessions
- **Thread-safe design** - UI never freezes during processing
- **Queue-based communication** - Status updates via message queues
- **Error handling** - Graceful error messages and recovery
- **Window geometry persistence** - Remembers size and position

### Command Line

**Note:** The CLI (main.py) is currently incomplete and under development. Use GUI for full functionality.

```bash
python main.py --input input/products.xlsx --output output/products.json
```

Currently implements basic structure only. For complete functionality, use the GUI.

### Python API

```python
from src.collector import PurinamillsCollector
import requests

collector = PurinamillsCollector()

# Find product URL
product_url = collector.find_product_url(
    upc="123456789012",
    http_get=requests.get,
    timeout=30,
    log=print,
    product_data={"description_1": "Purina Horse Feed"}
)

# Parse product page
enriched_data = collector.parse_page(html_text)
```

## Project Structure

```
purinamills/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # Product search logic
│   └── parser.py           # HTML parsing
├── utils/                  # Project utilities
│   ├── image_quality.py    # Image assessment
│   └── shopify_output.py   # Shopify format generation
├── tests/                  # Test scripts
│   ├── test_workflow.py    # End-to-end tests
│   └── test_variants.py    # Variant tests
├── input/                  # Input files (gitignored)
├── output/                 # Output files (gitignored)
├── logs/                   # Log files (gitignored)
├── docs/                   # Documentation
│   └── CLAUDE.md           # AI assistant guidance
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── requirements-gui.txt    # GUI dependencies
└── README.md               # This file
```

## Configuration

Site configuration is embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    # Primary shop site
    "shop_origin": "https://shop.purinamills.com",

    # Secondary www site (fallback)
    "www_origin": "https://www.purinamills.com",

    # Search settings
    "max_search_candidates": 10,
    "fuzzy_match_threshold": 0.3,
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
}
```

User settings (file paths, etc.) are stored in `config.json` (auto-generated by GUI).

## Input Format

Excel file (.xlsx) with columns:
- `upc` - Product UPC/barcode
- `description_1` - Product name (exact match preferred)
- `upcitemdb_title` - Alternative name for fuzzy matching
- `parent_upc` - For variant products (optional)

## Output Format

### Primary Output (purinamills.json)

Shopify-compatible JSON with successfully matched products:
- All original input fields preserved
- `manufacturer` object with enriched product data
- `shopify.media` array with image filenames
- Support for parent/variant structure

### Unmatched Products (purinamills_unmatched.json)

**Generated when products cannot be matched**

Products are saved to this separate file when BOTH conditions are true:
- ❌ No manufacturer site match (not found on shop.purinamills.com or www.purinamills.com)
- ❌ No UPCItemDB match (`upcitemdb_status` ≠ "Match found")

**File Structure:**
```json
{
  "unmatched_products": [
    {
      "upc": "012345678901",
      "description_1": "Product Name",
      "item_#": "SKU001",
      "upcitemdb_status": "Lookup failed",
      "error_reason": "No manufacturer match and no UPCItemDB data"
    }
  ]
}
```

**Benefits:**
- Primary output contains only processable products
- Unmatched products preserved for review
- Can be re-imported after fixing data or adding to manufacturer site
- Included in error report Excel for easy analysis

### Error Report (purinamills_errors.xlsx)

Excel file containing all failed products (including unmatched) with error reasons.

## Development

### Running Tests

```bash
# End-to-end workflow test
python tests/test_workflow.py

# Variant structure test
python tests/test_variants.py

# Search functionality test
python tests/test_www_search.py
```

### Code Quality

```bash
# Format code
black src/ utils/ tests/

# Lint code
flake8 src/ utils/ tests/

# Type check
mypy src/
```

## Architecture

### Core Components

**collector.py** - Main orchestration layer
- Embeds `SITE_CONFIG` with dual-site configuration
- `PurinamillsCollector` class coordinates search and parsing
- `find_product_url()` - Searches across both sites with fallback
- `parse_page()` - Parses HTML from either site format
- Thin wrapper (99 lines) - delegates to specialized modules

**search.py** - Product search with 3-tier fallback
- `PurinamillsSearcher` class handles all search logic
- Exact match via site search (`/search?q=description_1`) on shop site
- Fuzzy match with keyword extraction and scoring
- `_fetch_with_playwright()` - Headless Chromium for www site search
- WWW site requires JavaScript rendering (Playwright)
- Waits for "networkidle" to ensure page fully loaded
- Stop words filtering (the, and, or, etc.)
- Synonym expansion (equine→horse, bovine→cattle, canine→dog)
- Configurable threshold (0.3 default)

**parser.py** - Dual-site HTML parsing
- `PurinamillsParser` class with format auto-detection
- Shop site: Parses JSON-LD structured data + Shopify HTML (uses requests)
- WWW site: Parses WordPress/custom HTML structure (uses Playwright)
- `fetch_www_page_with_playwright()` - Headless browser for www pages
- Extracts: title, brand, description, benefits, nutrition, directions, images, PDFs
- `_extract_www_documents()` - Finds PDFs in "Additional Materials" accordion
- `_extract_shop_variant_image_map()` - Maps images to specific variants
- Auto-detects document links (getmedia URLs, .pdf extensions)
- Auto-detects site type from canonical URL or Shopify markers
- Returns unified data structure with `site_source` indicator

**image_quality.py** - Image quality assessment (UPCItemDB fallback only)
- `calculate_laplacian_score()` - Sharpness detection via Laplacian variance
- `crop_whitespace()` - Removes borders from images
- `load_placeholder_images()` - Loads known placeholder images
- `is_placeholder()` - Detects placeholders via perceptual hashing
- `download_image()` - Downloads with retry logic and validation
- `select_best_image()` - Evaluates quality, dimensions, sharpness
- **Only used when product not found** - Manufacturer images accepted without quality checks

**shopify_output.py** - Shopify format generation
- `generate_shopify_product()` - Creates GraphQL-compliant structure
- `merge_www_data()` - Merges shop + www site data
- `_clean_html()` - Removes scripts, styles, non-content elements
- `_normalize_size()` - Standardizes weight/volume formats
- `_format_body_html()` - Cleans HTML for Shopify
- `_generate_alt_tags()` - Creates SEO-friendly image descriptions
- Handles parent/variant relationships
- Generates media array with images and videos
- Stores PDFs in custom metafield (not in media array)

### Data Flow

**Complete Processing Workflow:**

1. **Initialization**
   - Load products from Excel input file (`load_products()` from shared utils)
   - Parse UPCs, descriptions, and parent/variant relationships
   - Initialize collector with site configuration

2. **For Each Product:**

   **Step 1: Search for Product URL**
   - Try exact match: Search shop site with `description_1` field
   - If no results: Try fuzzy match with keyword scoring
   - If still no results: Search www site with same strategies
   - Return product URL or empty string if not found

   **Step 2: Fetch Product Page**
   - HTTP GET request with browser-like headers
   - Rate limiting with jitter (200-700ms delay)
   - Retry logic on transient failures
   - Timeout handling (30 seconds)

   **Step 3: Parse Product Data**
   - Auto-detect site type (shop vs www)
   - Extract JSON-LD structured data (shop site)
   - Parse HTML for additional fields (both sites)
   - Extract: title, brand, description, benefits, nutrition, directions
   - Collect all image URLs
   - Extract PDF documents from "Additional Materials" sections (www site)
   - Normalize data structure

   **Step 4: Handle Variants (if parent product)**
   - Group child products by `parent_upc`
   - Process each variant's product page
   - Extract variant-specific options (size, flavor, etc.)
   - Collect variant images

   **Step 5: Image Quality Assessment (UPCItemDB Fallback Only)**
   - **Only if product not found on manufacturer sites**
   - Download UPCItemDB candidate images
   - Filter out placeholder images (perceptual hashing)
   - Crop whitespace from images
   - Calculate sharpness scores (Laplacian variance)
   - Select best image based on dimensions and quality
   - **Manufacturer images used as-is without quality checks**

   **Step 6: Optional WWW Site Enhancement**
   - If shop site data is minimal, fetch www site
   - Parse www site for additional details (includes PDFs)
   - Merge www data into shop data (preserves shop data priority)
   - Extract PDFs from "Additional Materials" accordion sections

   **Step 7: Generate Shopify Output**
   - Create GraphQL-compliant product structure
   - Clean HTML content for Shopify
   - Generate media array (images and videos)
   - Store PDFs in custom.documentation metafield
   - Format variant structure with options
   - Create SEO-friendly alt tags
   - Normalize sizes/weights

3. **Output Generation**
   - Wrap products in `{ "products": [...] }` structure
   - Write JSON to output file with formatting
   - Generate error report for failed products
   - Update configuration with statistics

### PDF Document Extraction

The collector automatically extracts product documentation PDFs from the www.purinamills.com site.

**Source:** WWW site "Additional Materials" accordion sections

**Detection:**
- Searches for accordion sections with "Additional Materials" title
- Identifies PDF links by URL patterns:
  - Contains "getmedia" (CMS document URLs)
  - Contains ".pdf" extension

**Extraction Process:**
1. Locate accordion structure: `<ul class="accordion">`
2. Find "Additional Materials" accordion item
3. Extract all links from accordion content
4. Filter for document URLs (getmedia or .pdf)
5. Deduplicate URLs
6. Store with title and URL

**Output Format:**
```json
"documents": [
  {
    "title": "Feeding Guide",
    "url": "https://www.purinamills.com/getmedia/abc123.pdf",
    "type": "pdf"
  }
]
```

**Storage in Shopify:**
- Stored in custom metafield: `custom.documentation`
- Type: JSON
- Contains array of document objects
- Accessible via Shopify Admin API

**Implementation:** `src/parser.py:_extract_www_documents()`

PDFs are only extracted from www site as shop site typically doesn't include technical documentation.

### SEO-Friendly Alt Tag Generation

The collector generates intelligent alt tags for product images using a hashtag filter system:

**Format:** `"Product Name #OPTION1#OPTION2#OPTION3"`

**Algorithm:**
1. Starts with product name for SEO keywords
2. Extracts variant options (size, flavor, material, etc.)
3. Filters out meaningless values ("EA", "Each", "None")
4. Converts options to uppercase hashtags with underscores
5. Combines into SEO-friendly alt text

**Examples:**
```
"Premium Horse Feed #50_LB"
"Premium Dog Food #20_LB#CHICKEN"
"Dog Bowl #PLASTIC"  (skips "EA" unit)
```

**Benefits:**
- **SEO:** Product name + descriptive keywords
- **Shopify:** Hashtags enable variant image filtering
- **Accessibility:** Screen readers get meaningful descriptions
- **Uniqueness:** Each variant image has unique alt text

**Implementation:** `utils/shopify_output.py:_generate_alt_tags()`

For variant-specific images, uses that variant's options. For shared images, generates separate entries for each variant with respective tags.

### Shared Dependencies

Imports utilities from `../shared/`:
- `text_only()` - HTML entity decoding
- `load_products()` - Excel file loading
- HTTP utilities, image processing helpers

## Configuration Details

### Site Configuration (src/collector.py)

```python
SITE_CONFIG = {
    "site_key": "purinamills",

    # Primary e-commerce site (Shopify)
    "shop_origin": "https://shop.purinamills.com",
    "shop_search_path": "/search",
    "shop_search_param": "q",

    # Secondary information site (fallback)
    "www_origin": "https://www.purinamills.com",
    "www_search_path": "/search",
    "www_search_param": "s",

    # HTTP settings
    "user_agent": "Mozilla/5.0 ...",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "timeout": 30,

    # Search settings
    "max_search_candidates": 10,
    "fuzzy_match_threshold": 0.3,
}
```

### User Configuration (config.json)

Auto-generated by GUI, stores:
- Input/output file paths
- Processing mode (skip/overwrite)
- Start/End record range
- Window geometry
- Log file path

## Best Practices

### Input File Preparation

**For Best Results:**
- Populate `description_1` with exact product names as they appear on the site
- Include full product names with variants (e.g., "Premium Horse Feed 50 lb")
- Use `upcitemdb_title` as fallback for fuzzy matching
- Mark variant products with `parent_upc` field
- Ensure UPCs are clean (digits only)

**Example Input:**
```excel
upc              | description_1                      | parent_upc       | upcitemdb_title
----------------|-------------------------------------|------------------|------------------
012345678901    | Premium Horse Feed 50 lb            |                  | Horse Feed Large
012345678902    | Premium Horse Feed 25 lb            | 012345678901     | Horse Feed Small
```

### Processing Strategy

**For Large Datasets:**
1. Test with small range first (Start: 1, End: 10)
2. Review output quality
3. Process in batches if needed
4. Use "Skip" mode for resuming interrupted runs

**For Updates:**
1. Use "Skip" mode to only process new products
2. Use "Overwrite" mode when product data has changed
3. Check error report for failed products

## Troubleshooting

### Common Issues

**"No results found for product"**
- Check that `description_1` field contains accurate product name
- Try adding product to `upcitemdb_title` for fuzzy matching
- Verify product exists on shop.purinamills.com or www.purinamills.com
- Check site is accessible (not blocking requests)

**"Image quality too low"**
- **Only applies to UPCItemDB fallback images** (not manufacturer images)
- Manufacturer images are used as-is without quality checks
- Laplacian threshold is 100 (configurable in GUI)
- Placeholder images are filtered by default
- Low-resolution UPCItemDB images may be rejected
- Check `placeholder_images/` directory for known placeholders

**"Timeout errors"**
- Increase timeout in `SITE_CONFIG` (default: 30 seconds)
- Check network connectivity
- Site may be rate-limiting requests
- Try increasing `fetch_jitter_max_ms` for longer delays
- For www site: Playwright may need more time for JavaScript

**"Playwright errors / Browser not found"**
- Run `playwright install chromium` to install browser
- Chromium is required for www.purinamills.com (JavaScript rendering)
- Check that Playwright is installed: `pip install playwright>=1.40.0`
- Verify browser installation: `playwright install --help`

**"Variant structure incorrect"**
- Ensure `parent_upc` field is set correctly
- Parent product must be processed before variants
- Check that parent exists in input file
- Verify UPCs match exactly

**GUI freezes or crashes**
- Check logs in `logs/purinamills.log`
- Ensure Python 3.13+ with latest Tk version
- Try CLI mode as alternative: `python main.py --input file.xlsx --output file.json`
- Report issues with full error traceback

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check logs:
```bash
tail -f logs/purinamills.log
```

## Notes

- **description_1 field**: Should contain exact product names for best exact-match results
- **Fuzzy matching**: Uses keyword extraction with synonyms (equine→horse, bovine→cattle, canine→dog)
- **Rate limiting**: Prevents overwhelming servers with 200-700ms jitter between requests
- **Image normalization**: All images converted to HTTPS with query params stripped
- **Image quality assessment**: Only for UPCItemDB fallback images; manufacturer images used as-is
- **Placeholder detection**: Uses perceptual hashing to identify and filter generic UPCItemDB images
- **Site detection**: Auto-detects Shopify vs WordPress format from canonical URL
- **WWW fallback**: Automatically searches www.purinamills.com if shop site has no results
- **Playwright automation**: Headless Chromium browser for JavaScript-heavy www site
- **Network idle wait**: Waits for page fully loaded before parsing (Playwright feature)
- **Error resilience**: Failed products are logged and reported but don't stop processing
- **Thread safety**: GUI uses queue-based communication, never blocks on long operations
- **CLI limitation**: main.py is incomplete skeleton; use GUI for full functionality

## License

Internal tool - Not for public distribution

## Support

For issues or questions, contact the development team.

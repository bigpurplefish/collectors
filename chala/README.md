# Chala Handbags Product Collector

Collects and enriches product data from Chala Handbags website (Shopify platform) for Shopify import.

## Overview

This collector retrieves product information from:
- **www.chalahandbags.com** - Shopify-based e-commerce site

It uses UPC-based search with full and partial matching strategies.

## Features

### Search & Collection
- **UPC-based search** - Searches by full UPC or last 5 digits
- **UPC override support** - Hardcoded mappings for problematic products
- **Direct site search** - Uses site's /search endpoint
- **Fallback strategy** - Tries full UPC, then partial UPC (last 5 digits)
- **Product page parsing** - Extracts data from Shopify product pages

### Data Processing
- **Shopify HTML parsing** - Extracts JSON-LD structured data
- **Multi-source image collection**:
  - JSON-LD Product images
  - Gallery markup (data-full attributes)
  - OpenGraph fallback images
- **Image normalization** - Strips Shopify size tokens, converts to HTTPS
- **WebP to JPG conversion** - Ensures compatibility
- **Description extraction** - Separates materials/measurements from benefits
- **Brand detection** - Always "Chala" for this site

### Image Processing
- **Shopify URL normalization** - Removes size suffixes (_320x, _960x, etc.)
- **Query parameter removal** - Cleans image URLs
- **Deduplication** - Removes duplicate images
- **CDN support** - Handles both /cdn/shop/ and cdn.shopify.com URLs
- **Srcset parsing** - Extracts largest images from responsive sets

### Shopify Output
- **GraphQL-compliant structure** - Ready for Shopify Admin API
- **Media array generation** - Includes normalized image URLs
- **Field standardization** - Consistent product data structure
- **Preserves input fields** - All original data maintained

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation and scripting
- **Real-time progress tracking** with detailed status messages
- **Auto-save configuration** - Persists settings between sessions
- **Dark theme** - Easy on the eyes for long sessions

## Installation

```bash
# Clone or navigate to project
cd /Users/moosemarketer/Code/garoppos/collectors/chala

# Set up virtual environment
pyenv local chala

# Install dependencies
pip install -r requirements.txt

# For GUI support
pip install -r requirements-gui.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

**Core (requirements.txt):**
- `requests>=2.31.0` - HTTP requests
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - Fast XML/HTML parsing
- `openpyxl>=3.1.0` - Excel file handling

**GUI (requirements-gui.txt):**
- Inherits from requirements.txt
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
- **Auto-save configuration** - All settings persist between sessions
- **Dark theme** - Easy on the eyes for long sessions
- **Thread-safe design** - UI never freezes during processing

### Command Line

```bash
python main.py --input input/products.json --output output/products.json
```

### Python API

```python
from src.collector import ChalaCollector
import requests

collector = ChalaCollector()

# Find product URL
product_url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print
)

# Parse product page
html = requests.get(product_url).text
enriched_data = collector.parse_page(html)
```

## Project Structure

```
chala/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # Product search logic
│   ├── parser.py           # HTML parsing
│   └── image_processor.py  # Image normalization
├── tests/                  # Test scripts
│   ├── __init__.py         # Package marker
│   ├── README.md           # Test documentation
│   ├── .gitignore          # Test output exclusions
│   └── output/             # Test outputs (gitignored)
│       └── .gitkeep
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
    "key": "chala",
    "display_name": "Chala Handbags",
    "origin": "https://www.chalahandbags.com",
    "referer": "https://www.chalahandbags.com/",
    "user_agent": "Mozilla/5.0 ...",
    "search": {
        "html_search_path": "/search?q={QUERY}"
    }
}
```

## Input Format

JSON array of products:
```json
[
  {
    "upc": "012345678901",
    "description_1": "Product Name"
  }
]
```

## Output Format

Shopify-compatible JSON with:
- All original input fields preserved
- `manufacturer` object with enriched product data
- `shopify.media` array with normalized image URLs
- `distributors_or_retailers` array

## Architecture

### Core Components

**collector.py** - Main orchestration layer
- Embeds `SITE_CONFIG` with Chala Handbags configuration
- `ChalaCollector` class coordinates search and parsing
- `find_product_url()` - Searches for product by UPC
- `parse_page()` - Parses Shopify product pages
- Thin wrapper that delegates to specialized modules

**search.py** - Product search with UPC matching
- `ChalaSearcher` class handles product search
- UPC override support for hardcoded mappings
- Full UPC search via site search endpoint
- Partial UPC fallback (last 5 digits)
- Extracts product URLs from search results using regex

**parser.py** - Shopify product page parsing
- `ChalaParser` class extracts product data
- Parses JSON-LD structured data for images
- Extracts gallery images from data-full attributes
- Extracts OpenGraph image as fallback
- Separates description (materials, measurements) from benefits
- Filters out noise lines (Default Title, MSRP, Price)
- Returns unified data structure

**image_processor.py** - Shopify image handling
- `ChalaImageProcessor` class normalizes images
- Strips Shopify size suffixes (_320x, _960x_crop_center, _grande, etc.)
- Converts WebP to JPG for compatibility
- Handles both store CDN and cdn.shopify.com URLs
- Parses srcset attributes for largest images
- Deduplicates normalized URLs

### Data Flow

1. **Initialization**
   - Load products from input JSON
   - Initialize collector with site configuration

2. **For Each Product:**
   - Extract UPC from input record
   - Check UPC overrides for hardcoded mappings
   - Search site by full UPC
   - If not found: Search by partial UPC (last 5 digits)
   - Extract product URL from search results

3. **Page Parsing:**
   - Fetch product page HTML
   - Extract title from H1 tag
   - Extract images from JSON-LD, data-full attributes, and OG tags
   - Extract description and benefits
   - Normalize all image URLs (strip sizes, convert WebP, deduplicate)

4. **Output Generation:**
   - Preserve all original input fields
   - Add manufacturer object with extracted data
   - Add shopify.media array with normalized images
   - Write JSON to output file

### Shared Dependencies

Imports utilities from `../shared/`:
- `load_json_file()` - JSON file loading
- `save_json_file()` - JSON file writing
- `normalize_upc()` - UPC normalization
- `text_only()` - HTML entity decoding
- `normalize_image_url()` - Image URL normalization
- `strip_shopify_size_suffix()` - Remove Shopify size tokens
- `convert_webp_to_jpg()` - WebP to JPG conversion
- `deduplicate_urls()` - Image URL deduplication

## Best Practices

### Input File Preparation

**For Best Results:**
- Use clean, normalized UPCs (digits only)
- Include product names in description_1
- Ensure UPCs match products on site

### Processing Strategy

**For Large Datasets:**
1. Test with small sample first
2. Review output quality
3. Process in batches if needed
4. Use "Skip" mode for resuming interrupted runs

## Troubleshooting

### Common Issues

**"No results found for product"**
- Verify product exists on www.chalahandbags.com
- Check UPC is correct
- Site may not have all products indexed
- Try searching manually on site

**"Product URL extraction failed"**
- Check site HTML structure hasn't changed
- Verify search endpoint is still /search?q=
- Check regex pattern for product URLs

**"No images found"**
- Product page may not have images
- Check JSON-LD structured data exists
- Verify data-full attributes present in gallery
- Check OpenGraph tags as fallback

**"Image URLs invalid"**
- Shopify CDN URLs may have changed format
- Check image processor is handling new URL patterns
- Verify size suffix stripping still works

## Notes

- **Shopify platform** - Site runs on Shopify, uses standard Shopify patterns
- **UPC search** - Uses site's built-in search with UPC query
- **Partial matching** - Falls back to last 5 digits if full UPC fails
- **Image normalization** - Critical for Shopify URLs with size suffixes
- **WebP conversion** - Ensures compatibility by converting to JPG
- **Brand constant** - Brand is always "Chala" for this site
- **JSON-LD parsing** - Primary source for product images
- **Description filtering** - Separates product details from marketing benefits

## License

Internal tool - Not for public distribution

## Support

For issues or questions, contact the development team.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY FOR ALL CODE GENERATION AND CHANGES:**

You MUST follow ALL applicable guidelines in `/Users/moosemarketer/Code/shared-docs/python/` whenever you:
- Generate new code
- Modify existing code
- Refactor code
- Create new files
- Update project structure

This is a **NON-NEGOTIABLE** requirement that applies to **EVERY** coding task, no exceptions.

### Required Pre-Coding Checklist

**Before generating ANY code OR answering questions**, you MUST:

1. **ALWAYS Use Context7 for Current Library Documentation**

   **CRITICAL:** Before writing code OR answering questions about any library, API, or framework, you MUST use Context7 to fetch the latest documentation.

   **Why:** Documentation changes frequently. Context7 provides up-to-date information from official sources, preventing outdated or incorrect guidance.

   **Process:**
   1. Use `mcp__context7__resolve-library-id` to find the library
   2. Use `mcp__context7__get-library-docs` to fetch current documentation
   3. Use the documentation to inform your code or answer

   **Common libraries:**
   - Shopify API: `/websites/shopify_dev`
   - Requests: `/psf/requests`
   - BeautifulSoup: `/wention/beautifulsoup4`
   - Playwright: `/microsoft/playwright-python`
   - Pandas: `/pandas-dev/pandas`

   **When to use:**
   - ✅ Before implementing any API integration
   - ✅ When answering questions about how libraries work
   - ✅ When debugging API-related issues
   - ✅ When checking field names, types, or requirements
   - ✅ When explaining how to use any external library

2. **Read ALL applicable shared-docs requirements**:
   - @~/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md - Project layout, dual entry points, README maintenance
   - @~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md - GUI patterns, threading, StringVar vs IntVar
   - @~/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md - Shopify GraphQL output format
   - @~/Code/shared-docs/python/GIT_WORKFLOW.md - Git commit patterns
   - @~/Code/shared-docs/python/TECHNICAL_DOCS.md - General Python standards
3. **Read collector-specific shared docs**:
   - @~/Code/Python/collectors/shared/docs/README.md - Shared utility documentation
4. **Combine external + internal standards**: Both latest library documentation (from Context7) AND our internal requirements must be met

### Key Requirements to Remember

- **Dual Entry Points**: ALWAYS provide both main.py (CLI) and gui.py (GUI) entry points
- **README Maintenance**: MUST update README.md in the SAME commit as ANY code changes
- **GUI Development**: MUST follow GUI_DESIGN_REQUIREMENTS.md exactly
  - Use `darkly` theme, queue-based threading, tooltips, auto-save config
  - Never update widgets from worker threads - use queues
  - **StringVar for blank-allowed fields** (NOT IntVar) - blank values more intuitive than "0"
- **Project Structure**: Dual entry points (main.py + gui.py), code in /src, follow standard Python layout
- **GraphQL Output**: Follow GRAPHQL_OUTPUT_REQUIREMENTS.md for Shopify API 2025-10 format
- **Shared Utilities**: Import from `../shared/src/` for common functions
- **Git Commits**: Include emoji and Co-Authored-By footer

## Project Overview

Chala Handbags Product Collector - Collects and enriches product data from www.chalahandbags.com (Shopify platform).

**Key Characteristic:** UPC-based search on Shopify site with full/partial matching and comprehensive image normalization.

## Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Components

**collector.py**: Main orchestration layer
- Embeds `SITE_CONFIG` with Chala Handbags configuration
- `ChalaCollector` class coordinates search and parsing
- Provides `find_product_url()` and `parse_page()` public API
- Thin wrapper that delegates to searcher and parser

**search.py**: UPC-based product search
- `ChalaSearcher` class handles product lookup
- UPC override support (hardcoded mappings in config)
- Full UPC search via `/search?q={UPC}`
- Partial UPC fallback (last 5 digits) if full search fails
- Regex extraction of product URLs from search results
- Pattern: `href="(/products/[^"<>]+)"`

**parser.py**: Shopify product page parsing
- `ChalaParser` class extracts product data
- Multi-source image extraction:
  - JSON-LD structured data (Product @type)
  - Gallery markup (data-full attributes)
  - OpenGraph image (fallback)
- Description extraction separates:
  - Details: Materials, Color, Measurements, Strap, Design origin
  - Benefits: Product features and marketing points
- Filters noise: "Default Title", "MSRP", "Price"
- Brand is always "Chala"
- Returns: title, brand_hint, benefits, description, gallery_images

**image_processor.py**: Shopify-specific image handling
- `ChalaImageProcessor` class normalizes Shopify URLs
- Strips size suffixes: _320x, _960x, _960x_crop_center, _grande, etc.
- Converts WebP to JPG for compatibility
- Handles CDN patterns:
  - Store CDN: `/cdn/shop/...`
  - Shopify CDN: `cdn.shopify.com`
- Parses srcset attributes (extracts largest image)
- Deduplicates normalized URLs
- Uses shared utilities: `normalize_image_url()`, `strip_shopify_size_suffix()`, etc.

### Data Flow

1. **Product Search**:
   - Check UPC overrides first
   - Search by full UPC: `/search?q={UPC}`
   - If no results: Search by partial UPC (last 5 digits)
   - Extract product URL from search results

2. **Page Parsing**:
   - Fetch product page HTML
   - Extract title from H1
   - Extract images from JSON-LD, data-full, OG tags
   - Parse description section
   - Separate details from benefits
   - Normalize all image URLs

3. **Image Processing**:
   - Strip Shopify size tokens
   - Convert WebP → JPG
   - Force HTTPS
   - Remove query parameters
   - Deduplicate URLs

4. **Orchestration**: `ChalaCollector` coordinates search and parsing

### Shared Dependencies

The project imports utilities from `../shared/`:
- `load_json_file()`, `save_json_file()` - JSON handling
- `normalize_upc()` - UPC normalization
- `text_only()` - HTML entity decoding
- `normalize_image_url()` - Image URL normalization
- `strip_shopify_size_suffix()` - Remove size tokens
- `convert_webp_to_jpg()` - WebP conversion
- `deduplicate_urls()` - Image deduplication

## Usage

### Command Line

```bash
python main.py --input products.json --output enriched.json
```

### Python API

```python
from src.collector import ChalaCollector
import requests

collector = ChalaCollector()

# Find product URL
url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print
)

# Parse product page
html = requests.get(url).text
data = collector.parse_page(html)
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/chala
pyenv local chala
pip install -r requirements.txt
```

### Dependencies

- `requests>=2.31.0`: HTTP requests
- `beautifulsoup4>=4.12.0`: HTML parsing
- `lxml>=4.9.0`: Fast XML/HTML parser
- `openpyxl>=3.1.0`: Excel handling

## Configuration

Configuration is embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    "key": "chala",
    "display_name": "Chala Handbags",
    "origin": "https://www.chalahandbags.com",
    "search": {
        "html_search_path": "/search?q={QUERY}"
    }
}
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Product data with normalized images
- `shopify.media`: Array of image URLs
- `distributors_or_retailers`: Retailer data if applicable

## Notes

- **Shopify platform**: Standard Shopify patterns and URL structures
- **UPC search**: Full UPC first, then partial (last 5 digits)
- **Image normalization**: Critical for Shopify with size suffixes
- **WebP conversion**: Ensures compatibility across systems
- **Brand constant**: Always "Chala" for this site
- **Multi-source images**: JSON-LD → data-full → OG image priority
- **Description filtering**: Separates materials/measurements from benefits
- **Noise removal**: Filters "Default Title", "MSRP", "Price" from content

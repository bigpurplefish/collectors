# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### CRITICAL: Always Follow These Requirements

**Before generating ANY code**, you MUST:

1. **Check Context7** for up-to-date library documentation (use context7 MCP tool)
2. **Read the shared-docs requirements**:
   - @~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md - GUI patterns and threading
   - @~/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md - Project layout standards
   - @~/Code/shared-docs/python/GIT_WORKFLOW.md - Git commit patterns
   - @~/Code/shared-docs/python/TECHNICAL_DOCS.md - General Python standards
3. **Read collector-specific shared docs**:
   - @~/Code/Python/collectors/shared/docs/README.md - Shared utility documentation
4. **Combine external + internal standards**: Both Context7 patterns AND our requirements must be met

### Key Requirements to Remember

- **GUI Development**: MUST follow GUI_DESIGN_REQUIREMENTS.md exactly
  - Use `darkly` theme, queue-based threading, tooltips, auto-save config
  - Never update widgets from worker threads - use queues
- **Project Structure**: main.py at root, code in /src, follow standard Python layout
- **Shared Utilities**: Import from `../shared/src/` for common functions
- **Git Commits**: Include emoji and Co-Authored-By footer

## Project Overview

Purinamills Product Collector - Collects and enriches product data from https://shop.purinamills.com.

This collector uses a name-based fuzzy matching approach since the site does not expose UPC codes directly in product listings. The collector builds an index of all products and uses keyword matching to find the correct product page.

## Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Components

**collector.py** (45 lines): Main orchestration layer
- Embeds site configuration (`SITE_CONFIG`)
- Coordinates between indexer, searcher, and parser
- Provides `find_product_url()` and `parse_page()` public API
- CLI entry point with argparse

**index.py** (222 lines): Product index management
- `ProductIndexer` class builds runtime product index
- Crawls `/collections/all-products` (configurable pagination)
- Supports `view=all` parameter for single-page indexing
- Extracts product names and URLs into searchable index
- Implements keyword extraction with stop words and synonyms
- Pagination detection (link rel="next", aria-label, CSS selectors)

**search.py** (171 lines): Product discovery
- `PurinamillsSearcher` class handles fuzzy name matching
- Uses keyword-based scoring against product index
- Falls back to site search (`/search?q=...`) if index match fails
- Minimum threshold: 0.3 score for acceptance
- Takes first search result if multiple matches

**parser.py** (180 lines): HTML parsing
- `PurinamillsParser` class extracts product data
- Parses title, brand, description, benefits
- Extracts images from JSON (modelProduct) and DOM
- Normalizes image URLs to HTTPS
- Attempts to parse nutrition and feeding directions
- Returns structured dict with all extracted fields

### Data Flow

1. **Index Building**: `ProductIndexer.build_index()` crawls all-products collection
2. **Product Search**: `PurinamillsSearcher.find_product_url()` fuzzy matches against index
3. **Page Parsing**: `PurinamillsParser.parse_page()` extracts data from HTML
4. **Orchestration**: `PurinamillsCollector` coordinates the three components

### Shared Dependencies

The project imports utilities from `../shared/`:
- `text_only()`: HTML entity decoding and text normalization
- HTTP utilities, image processing, UPC handling (via parent sys.path insertion)

## Usage

### Command Line

```bash
python collector.py --input products.json --output enriched.json
```

### Python API

```python
from collector import PurinamillsCollector

collector = PurinamillsCollector()

# Find product URL by fuzzy name matching
product_url = collector.find_product_url(
    upc="123456789012",
    http_get=requests.get,
    timeout=30,
    log=print,
    product_data={"upcitemdb_title": "Purina Horse Feed"}
)

# Parse product page
enriched_data = collector.parse_page(html_text)
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/Python/collectors/purinamills
pyenv local purinamills
pip install -r requirements.txt
```

### Dependencies

- `requests>=2.31.0`: HTTP requests
- `beautifulsoup4>=4.12.0`: HTML parsing
- `lxml>=4.9.0`: Fast XML/HTML parser backend

## Configuration

Site configuration is embedded in `collector.py`:

```python
SITE_CONFIG = {
    "origin": "https://shop.purinamills.com",
    "all_products_path": "/collections/all-products",
    "index_view_all": True,           # Try ?view=all for single-page index
    "index_page_param": "page",       # Pagination param name
    "max_index_pages": 20,            # Max pages to crawl during indexing
    "max_search_candidates": 30,      # Max results from site search
    "enable_search_fallback": True,   # Fall back to /search if index fails
    # ... rate limiting, candidate caps, etc.
}
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Object with product data and images
- `distributors_or_retailers`: Retailer data if applicable
- `shopify.media`: Array of Shopify image filenames

## Notes

- **Index-based discovery**: Builds product index at runtime, no pre-built catalog needed
- **Fuzzy matching**: Uses keyword extraction with synonyms (equine→horse, bovine→cattle)
- **Rate limiting**: Configured via `fetch_jitter_min_ms` and `fetch_jitter_max_ms`
- **Image normalization**: All images converted to HTTPS, query params stripped
- **Error handling**: Graceful fallback to site search if index matching fails

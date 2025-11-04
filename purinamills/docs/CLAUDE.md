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

Purinamills Product Collector - Collects and enriches product data from two Purina Mills websites:
- **shop.purinamills.com** - E-commerce site (Shopify) - primary source
- **www.purinamills.com** - Information site - fallback

This collector uses direct site search with a 3-tier fallback strategy:
1. Exact match using `description_1` field on shop site
2. Fuzzy match using description_1/upcitemdb_title on shop site
3. Fallback to www site if shop site has no matches

The input file `description_1` field contains exact product names as they appear on the sites, enabling efficient exact-match searching without building a full product index.

## Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Components

**collector.py**: Main orchestration layer
- Embeds dual-site configuration (`SITE_CONFIG`)
- Supports both shop.purinamills.com and www.purinamills.com
- Coordinates between searcher and parser
- Provides `find_product_url()` and `parse_page()` public API

**search.py**: Direct site search with 3-tier fallback
- `PurinamillsSearcher` class handles search across both sites
- **Strategy 1**: Exact match on description_1 (shop site via `/search?q=`)
- **Strategy 2**: Fuzzy match on description_1/upcitemdb_title (shop site)
- **Strategy 3**: Fallback to www site search
- Uses keyword-based scoring with stop words and synonyms
- Minimum threshold: 0.3 score for fuzzy acceptance
- Parses search results to extract product links

**parser.py**: Dual-site HTML parsing
- `PurinamillsParser` class handles both shop and www site formats
- Auto-detects site type from canonical URL/Shopify markers
- **Shop site**: Parses JSON-LD structured data, Shopify product pages
- **WWW site**: Parses information pages with different structure
- Extracts: title, brand, description, benefits, images, nutrition, directions
- Normalizes image URLs to HTTPS
- Returns unified data structure with `site_source` indicator

### Data Flow

1. **Product Search**: `PurinamillsSearcher.find_product_url()` searches shop site first, then www
   - Try exact match with description_1 on shop site
   - Fall back to fuzzy match if no exact match
   - Fall back to www site if shop site fails
2. **Page Parsing**: `PurinamillsParser.parse_page()` auto-detects site type and extracts data
3. **Orchestration**: `PurinamillsCollector` coordinates search and parsing

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

Dual-site configuration is embedded in `collector.py`:

```python
SITE_CONFIG = {
    # Primary e-commerce site (Shopify)
    "shop_origin": "https://shop.purinamills.com",
    "shop_search_path": "/search",
    "shop_search_param": "q",

    # Secondary information site (fallback)
    "www_origin": "https://www.purinamills.com",
    "www_search_path": "/search",
    "www_search_param": "q",

    # Search settings
    "max_search_candidates": 10,      # Max results per search
    "fuzzy_match_threshold": 0.3,     # Minimum score for fuzzy matches
    "fetch_jitter_min_ms": 200,       # Rate limiting
    "fetch_jitter_max_ms": 700,
}
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Object with product data and images
- `distributors_or_retailers`: Retailer data if applicable
- `shopify.media`: Array of Shopify image filenames

## Notes

- **Direct site search**: Uses each site's search functionality instead of building index
- **3-tier fallback**: Exact → Fuzzy → WWW site ensures high match rate
- **description_1 field**: Must contain exact product names for best results
- **Fuzzy matching**: Uses keyword extraction with synonyms (equine→horse, bovine→cattle)
- **Rate limiting**: Configured via `fetch_jitter_min_ms` and `fetch_jitter_max_ms`
- **Image normalization**: All images converted to HTTPS, query params stripped
- **Dual-site support**: Automatically detects and parses both shop and www page formats

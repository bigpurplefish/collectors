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

**Before generating ANY code**, you MUST:

1. **Check Context7** for up-to-date library documentation (use context7 MCP tool)
2. **Read ALL applicable shared-docs requirements**:
   - @~/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md - Project layout, dual entry points, README maintenance
   - @~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md - GUI patterns, threading, StringVar vs IntVar
   - @~/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md - Shopify GraphQL output format
   - @~/Code/shared-docs/python/GIT_WORKFLOW.md - Git commit patterns
   - @~/Code/shared-docs/python/TECHNICAL_DOCS.md - General Python standards
3. **Read collector-specific shared docs**:
   - @~/Code/Python/collectors/shared/docs/README.md - Shared utility documentation
4. **Combine external + internal standards**: Both Context7 patterns AND our requirements must be met

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

Bradley Caldwell Product Collector - Catalog-based product collector that enriches data from a pre-built JSON catalog. This is a zero-scrape collector that performs no web scraping.

**Key Characteristic:** Requires a product catalog JSON file containing all product data (URLs, names, brands, descriptions, images). The collector looks up products by UPC and enriches input records.

## Architecture

The codebase follows a modular architecture with clear separation of concerns:

### Core Components

**collector.py**: Main orchestration layer
- Embeds `SITE_CONFIG` with Bradley Caldwell configuration
- `BradleyCaldwellCollector` class coordinates catalog and enrichment
- Provides `find_product_by_upc()`, `enrich_product()`, and `process_file()` public API
- Thin wrapper that delegates to catalog manager and enricher

**catalog.py**: Catalog management
- `CatalogManager` class handles loading and indexing
- Lazy loads catalog JSON file on first use
- Builds UPC and URL indexes for O(1) lookups
- `ensure_loaded()` - Loads catalog with validation
- `get_by_upc()` - Fast UPC lookup
- `get_by_url()` - Fast URL lookup
- `find_product_url()` - Returns product URL for UPC

**enricher.py**: Product enrichment logic
- `ProductEnricher` class transforms catalog data
- Normalizes descriptions (fixes double periods, adds ending periods)
- Extracts bullet points from descriptions using shared utilities
- Normalizes image URLs to HTTPS
- Generates Shopify media filenames with UPC prefix (e.g., "012345678901_0.jpg")
- Builds manufacturer data structure
- Gracefully handles missing catalog data (returns empty structure)

### Data Flow

1. **Initialization**: Load catalog JSON, build UPC/URL indexes
2. **Product Lookup**: Find product in catalog by normalized UPC
3. **Data Enrichment**:
   - Extract: name, brand, description, ingredients, images
   - Normalize description text (fix periods)
   - Extract bullet points from description
   - Normalize image URLs to HTTPS
   - Deduplicate image URLs
   - Generate Shopify media filenames
4. **Output Generation**: Combine input + manufacturer + shopify data

### Shared Dependencies

The project imports utilities from `../shared/`:
- `load_json_file()` - JSON file loading
- `save_json_file()` - JSON file writing
- `build_catalog_index()` - Catalog indexing (UPC + URL maps)
- `normalize_upc()` - UPC normalization (digits only)
- `text_only()` - HTML entity decoding
- `normalize_to_https()` - URL normalization
- `extract_bullet_points()` - Bullet point extraction
- `deduplicate_urls()` - Image URL deduplication

## Usage

### Command Line

```bash
python main.py --catalog input/catalog.json --input input/products.json --output output/products.json
```

### Python API

```python
from src.collector import BradleyCaldwellCollector

collector = BradleyCaldwellCollector(catalog_path="input/catalog.json")

# Find product URL
product_url = collector.find_product_by_upc("012345678901")

# Enrich product
enriched = collector.enrich_product({
    "upc": "012345678901",
    "description_1": "Product Name"
})
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/bradley_caldwell
pyenv local bradley_caldwell
pip install -r requirements.txt
```

### Dependencies

- `requests>=2.31.0`: Shared dependency
- `ttkbootstrap>=1.10.1`: GUI framework
- `openpyxl>=3.1.0`: Excel handling

## Configuration

Configuration is embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    "key": "bradley_caldwell",
    "display_name": "Bradley Caldwell",
    "origin": "https://www.bradleycaldwell.com",
    "referer": "https://www.bradleycaldwell.com/",
}
```

## Input/Output Format

**Catalog JSON (Required):**
```json
[
  {
    "upc": "012345678901",
    "product_url": "https://www.bradleycaldwell.com/product",
    "product_name": "Product Name",
    "brand": "Brand",
    "description": "Description with benefits",
    "ingredients": "Ingredients",
    "image_urls": ["https://example.com/image.jpg"]
  }
]
```

**Output includes:**
- All original input fields (preserved)
- `manufacturer`: Enriched product data from catalog
- `shopify.media`: Array of image filenames (UPC-based)
- `distributors_or_retailers`: Empty array (catalog-based)

## Notes

- **Zero scraping**: All data from catalog, no web requests
- **Catalog required**: Cannot function without catalog JSON file
- **Fast lookups**: Indexed by UPC and URL for O(1) access
- **Graceful fallback**: Missing products get empty manufacturer data
- **UPC normalization**: Strips non-digits automatically
- **Image deduplication**: Removes duplicate URLs
- **Description cleanup**: Fixes double periods, adds ending periods

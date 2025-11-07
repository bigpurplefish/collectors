# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL applicable guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for code generation, modification, and project structure.

### Required Pre-Coding Checklist

1. **Check Context7** for up-to-date library documentation
2. **Read shared-docs requirements**: PROJECT_STRUCTURE_REQUIREMENTS.md, GUI_DESIGN_REQUIREMENTS.md, GRAPHQL_OUTPUT_REQUIREMENTS.md, GIT_WORKFLOW.md, TECHNICAL_DOCS.md
3. **Read collector-specific docs**: @~/Code/Python/collectors/shared/docs/README.md

### Key Requirements

- **Dual Entry Points**: main.py (CLI) + gui.py (GUI)
- **README Maintenance**: Update in SAME commit as code changes
- **GUI Development**: Follow GUI_DESIGN_REQUIREMENTS.md (darkly theme, queues, tooltips, StringVar for blank fields)
- **GraphQL Output**: Follow GRAPHQL_OUTPUT_REQUIREMENTS.md for Shopify API 2025-10
- **Shared Utilities**: Import from `../shared/src/`

## Project Overview

Coastal Pet Product Collector - Collects data from www.coastalpet.com (custom platform with Bazaarvoice integration).

**Key Characteristic:** Multi-strategy UPC search with modelProduct JSON extraction and Bazaarvoice configuration.

## Architecture

### Core Components

**collector.py**: Main orchestration
- Embeds SITE_CONFIG with Coastal Pet and Bazaarvoice configuration
- `CoastalCollector` coordinates search and parsing

**search.py**: Multi-strategy UPC search
- `CoastalSearcher` class with three strategies:
  1. UPC overrides (hardcoded in config)
  2. HTML search: `/products/search/?q={UPC}`
  3. Autocomplete API: `/product/searchconnection/autocompleteandsuggest?fuzzy=true&term={UPC}`
- Regex extraction: `href="(/products/detail/\?id=[^"<>]+)"`

**parser.py**: Custom HTML parsing
- `CoastalParser` extracts product data
- `extract_json_from_script()` - Parses modelProduct JSON from script tags
- Extracts: title (h4.product-details__product-name), brand (modelProduct or search link), benefits (li.key-benefits), description (h3>Description or div#description)
- Gallery: modelProduct → DOM fallback if <2 images

**image_processor.py**: Image extraction
- `extract_gallery_from_model_product()` - Primary source
- `extract_dom_gallery_fallback()` - Secondary source
- Normalizes URLs to HTTPS, removes query params, deduplicates

### Data Flow

1. **Search**: Overrides → HTML search → Autocomplete API
2. **Parse**: modelProduct JSON → title/brand/benefits/description → images
3. **Images**: modelProduct gallery → DOM if thin → normalize
4. **Output**: input + manufacturer data

### Shared Dependencies

`load_json_file()`, `save_json_file()`, `normalize_upc()`, `text_only()`, `extract_json_from_script()`

## Configuration

```python
SITE_CONFIG = {
    "key": "coastal",
    "origin": "https://www.coastalpet.com",
    "bv": {  # Bazaarvoice integration
        "client": "Coastal",
        "bfd_token": "25877,main_site,en_US"
    },
    "search": {
        "html_search_path": "/products/search/?q={QUERY}",
        "autocomplete_path": "/product/searchconnection/autocompleteandsuggest?fuzzy=true&term={QUERY}",
        "upc_overrides": {
            "076484093722": "https://www.coastalpet.com/products/detail?id=TPC03",
            ...
        }
    }
}
```

## Notes

- **modelProduct JSON**: Primary data source in script tags
- **Bazaarvoice**: Reviews API config available
- **Multi-strategy**: Overrides → HTML → Autocomplete
- **DOM fallback**: Ensures image completeness

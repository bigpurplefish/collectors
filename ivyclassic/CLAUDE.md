# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

## Project Overview

Ivyclassic Collector - Catalog-based, zero-scrape collector requiring pre-built JSON catalog.

## Architecture

**collector.py**: Main orchestration
- Enforces catalog requirement (`requires_catalog: True`)
- No search fallback - catalog-only

**catalog.py**: Catalog management
- `CatalogManager` class for loading and indexing
- UPC-based lookups (O(1) access)
- `lookup()` method for UPC → URL mapping

**parser.py**: HTML parsing (for product pages if needed)

## Configuration

```python
SITE_CONFIG = {
    "site_key": "ivyclassic",
    "origin": "https://ivyclassic.com",
    "requires_catalog": True  # Mandatory catalog
}
```

## Notes

- **Catalog required**: Cannot function without catalog JSON
- **Zero scraping**: No web requests for search
- **Fast lookups**: Indexed by UPC

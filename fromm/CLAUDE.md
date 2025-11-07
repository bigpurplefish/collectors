# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

## Project Overview

Fromm Family Foods Collector - Custom pet food website with UPC override mappings only (no search).

## Architecture

**collector.py**: Main orchestration
**search.py**: UPC override lookup only (no search endpoint available)
**parser.py**: Custom HTML parsing for:
- Product title and brand
- Ingredient lists
- Guaranteed analysis (nutritional data)
- Feeding guidelines
- Product images

**image_processor.py**: Image extraction and normalization

## Configuration

```python
SITE_CONFIG = {
    "key": "fromm",
    "origin": "https://frommfamily.com",
    "search": {
        "upc_overrides": {
            "072705115372": "https://frommfamily.com/products/dog/gold/dry/large-breed-adult-gold/",
            ...
        }
    }
}
```

## Notes

- **UPC overrides required**: No search functionality
- **Custom parsing**: Non-standard HTML structure
- **Pet food focused**: Ingredients, analysis, feeding guidelines

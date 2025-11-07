# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

## Project Overview

Tall Tails Dog Collector - Magento site with intelligent variant matching and token-based detection.

## Architecture

**collector.py**: Main orchestration with variant token extraction
- `_derive_variant_tokens()` - Extracts tokens from product data
- Generates fused labels (highland cow, black bear, cow print)
- Passes variant context to parser

**search.py**: Magento catalogsearch
- Endpoint: `/catalogsearch/result/?q={query}`
- UPC and name-based fallback
- Learning mode: disables UPC after threshold failures
- HTML grid result parsing

**parser.py**: Magento HTML parsing
- Selectors: title, feature_bullets, description_root, materials_root
- Gallery hint: `mage/gallery/gallery`
- Variant-aware parsing with context

**variant_handler.py**: Variant logic
- Token-based variant detection
- Fused label generation
- Variant matching algorithms
- Pattern recognition (highland cow, black bear, etc.)

## Configuration

```python
SITE_CONFIG = {
    "search": {
        "endpoint": "/catalogsearch/result/?q={query}",
        "expects_html_grid": True
    },
    "selectors": {
        "gallery_hint": "mage/gallery/gallery"
    },
    "learning": {
        "upc_disable_after": 5
    }
}
```

## Variant Matching

**Fused Labels:**
- `["cow"]` → "highland cow"
- `["black", "bear"]` → "black bear"
- `["cow", "print"]` → "cow print"

**Process:**
1. Extract tokens from descriptions
2. Generate fused labels
3. Pass to parser with variant context
4. variant_handler matches correct variant

## Notes

- **Magento platform**: Standard structure
- **Variant intelligence**: Token-based with fused labels
- **Learning mode**: Adapts UPC strategy
- **Gallery hints**: Reliable Magento image extraction

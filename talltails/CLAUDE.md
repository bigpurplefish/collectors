# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

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

2. **Read shared-docs requirements**: PROJECT_STRUCTURE_REQUIREMENTS.md, GUI_DESIGN_REQUIREMENTS.md, GRAPHQL_OUTPUT_REQUIREMENTS.md, GIT_WORKFLOW.md, TECHNICAL_DOCS.md
3. **Read collector-specific docs**: @~/Code/Python/collectors/shared/docs/README.md

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

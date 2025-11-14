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

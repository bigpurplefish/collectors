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

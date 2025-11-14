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

KONG Company Collector - Custom WordPress site with HTML search endpoint.

## Architecture

**collector.py**: Main orchestration
**search.py**: HTML search using `/?s={UPC}`
**parser.py**: Custom HTML parsing for product data, descriptions, benefits, images

## Configuration

```python
SITE_CONFIG = {
    "key": "kong",
    "origin": "https://www.kongcompany.com",
    "search": {"html_search_path": "/?s={QUERY}"}
}
```

## Notes

- **WordPress-based**: Custom structure
- **HTML search**: `/?s={UPC}` endpoint

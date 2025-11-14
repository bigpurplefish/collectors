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

Orgill Collector - B2B distributor site requiring authentication with multi-strategy login system.

## Architecture

**collector.py**: Main orchestration with authentication integration

**auth.py**: Authentication system
- `OrgillAuthenticator` class with multi-strategy login
- Session management and cookie persistence
- `login()` with retry logic
- Raises `StrategyLoginError` on failure
- `set_auth()` for credentials
- `attach_session()` for session pooling

**search.py**: Authenticated search
- Uses authenticated session for UPC searches
- B2B-specific search logic

**parser.py**: B2B HTML parsing
- Distributor-specific structure
- Product data, pricing, availability

## Configuration

```python
SITE_CONFIG = {
    "key": "orgill",
    "origin": "https://www.orgill.com",
    "robots": "respect",
    "search": {"upc_overrides": {}}
}
```

## Security

- Credentials NOT persisted in config
- Short-lived sessions
- Explicit `StrategyLoginError` for auth failures

## Notes

- **Authentication required**: Multi-strategy login
- **B2B site**: Different from consumer sites
- **Session management**: Persistent during collection

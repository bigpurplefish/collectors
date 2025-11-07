# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

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

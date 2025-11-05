# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### CRITICAL: Always Follow These Requirements

**Before generating ANY code**, you MUST:

1. **Check Context7** for up-to-date library documentation (use context7 MCP tool)
2. **Read the shared-docs requirements**:
   - @~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md - GUI patterns and threading
   - @~/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md - Project layout standards
   - @~/Code/shared-docs/python/GIT_WORKFLOW.md - Git commit patterns
   - @~/Code/shared-docs/python/TECHNICAL_DOCS.md - General Python standards
3. **Read collector-specific shared docs**:
   - @~/Code/Python/collectors/shared/docs/README.md - Shared utility documentation
4. **Combine external + internal standards**: Both Context7 patterns AND our requirements must be met

### Key Requirements to Remember

- **GUI Development**: MUST follow GUI_DESIGN_REQUIREMENTS.md exactly
  - Use `darkly` theme, queue-based threading, tooltips, auto-save config
  - Never update widgets from worker threads - use queues
- **Project Structure**: main.py at root, code in /src, follow standard Python layout
- **Shared Utilities**: Import from `../shared/src/` for common functions
- **Git Commits**: Include emoji and Co-Authored-By footer


## Project Overview

Fromm Family Foods Product Collector - Collects and enriches product data from https://frommfamily.com.

## Architecture

This project collects product information from Fromm Family Foods's website, including:
- Product titles and descriptions
- Images and media
- Ingredients and nutritional information
- UPC codes and product variants

### Core Components

**collector.py**: Main collector implementation
- Site-specific scraping logic
- Product data extraction
- Image harvesting and normalization

### Site Configuration

The Fromm Family Foods site configuration is embedded directly in `collector.py`.

## Usage

### Command Line

```bash
python collector.py --input products.json --output enriched.json
```

### Python API

```python
from collector import FrommCollector

collector = FrommCollector()
enriched = collector.collect_product(upc="123456789012")
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/Python/collectors/fromm
pyenv local fromm
pip install -r requirements.txt
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Object with product data and images
- `distributors_or_retailers`: Retailer data if applicable
- `shopify.media`: Array of Shopify image filenames

## Notes

- Rate limiting is implemented to respect site resources
- All images are normalized to HTTPS
- UPC matching is flexible (strips non-digits)

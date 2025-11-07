# CLAUDE.md

## Python Development Standards

### ⚠️ CRITICAL: ALWAYS Follow Shared Guidelines ⚠️

**MANDATORY:** Follow ALL guidelines in `/Users/moosemarketer/Code/shared-docs/python/` for all code changes.

### Key Requirements

- **Dual Entry Points**: main.py (CLI) + gui.py (GUI)
- **README Maintenance**: Update in SAME commit as code changes
- **GUI Development**: Follow GUI_DESIGN_REQUIREMENTS.md
- **Shared Utilities**: Import from `../shared/src/`

## Project Overview

Ethical Products (SPOT) Collector - WooCommerce site with Selenium, intelligent text matching, and multi-factor validation.

## Architecture

**collector.py**: Main orchestration with extensive configuration (search, parsing, selenium, images)

**search.py**: Intelligent text matching with:
- Token-based similarity scoring
- Taxonomy validation (dog/cat)
- Flavor matching with aliases
- Size matching with normalization
- Form matching (treats, food, toys)
- Brand alias support (Ethical Products, Ethical Pet, SPOT)
- Multi-factor weighted scoring

**parser.py**: WooCommerce parsing with:
- Selenium page loading (JavaScript-rendered content)
- Elastislide carousel extraction (data-largeimg)
- Multi-selector description parsing
- Strict carousel-only mode

**text_matching.py**: Text matching algorithms
**size_matching.py**: Size validation logic
**image_processor.py**: Carousel image extraction

## Configuration

```python
SITE_CONFIG = {
    "search": {
        "manufacturer_aliases": ["Ethical Products", "Ethical Pet", "Ethical", "SPOT"],
        "verify_min_token_hits": 2,
        "brand_weight": 2
    },
    "parsing": {
        "use_selenium": True,
        "gallery_selectors": {"carousel_images": "div.elastislide-carousel ul.elastislide-list li img[data-largeimg]"},
        "strict_carousel_only": True
    },
    "selenium": {
        "enabled": True,
        "browser": "chrome",
        "headless": True,
        "simulate_click_from_search": True
    }
}
```

## Notes

- **Selenium required**: JavaScript-rendered WooCommerce content
- **Intelligent matching**: Multi-factor scoring (text, taxonomy, flavor, size, form)
- **Carousel-only images**: data-largeimg from Elastislide
- **text_matching.py & size_matching.py**: Specialized validation modules

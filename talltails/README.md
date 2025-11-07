# Tall Tails Dog Product Collector

Collects and enriches product data from Tall Tails Dog website (Magento platform) for Shopify import.

## Overview

This collector retrieves product information from:
- **www.talltailsdog.com** - Magento-based e-commerce site

Uses intelligent variant matching with token-based detection and specialized variant handling.

## Features

### Search & Collection
- **Magento search endpoint** - Uses `/catalogsearch/result/?q={UPC}`
- **Variant token extraction** - Derives variant identifiers from product data
- **Name fallback search** - Uses product name if UPC fails
- **Learning mode** - Disables UPC after failures (configurable threshold)

### Data Processing
- **Magento HTML parsing** - Extracts data from Magento structure
- **Variant detection** - Intelligent variant token matching
- **Feature bullets extraction** - Parses key product features
- **Description extraction** - Multi-selector description parsing
- **Materials extraction** - Captures product materials
- **Gallery hints** - Uses mage/gallery/gallery for image detection

### Variant Handling
- **Token-based matching** - Derives variant tokens from descriptions
- **Fused labels** - Intelligent label fusion (e.g., "highland cow", "black bear")
- **Variant query text** - Preserves original query for matching
- **Variant handler** - Dedicated module for variant logic

### Image Processing
- **Magento gallery extraction** - Uses gallery hints
- **URL normalization** - Converts to HTTPS, removes query params
- **Deduplication** - Removes duplicate images

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation
- **Real-time progress tracking**
- **Auto-save configuration**

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/talltails
pyenv local talltails
pip install -r requirements.txt

# For GUI/development
pip install -r requirements-gui.txt
pip install -r requirements-dev.txt
```

### Dependencies

**Core:** `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`, `openpyxl>=3.1.0`
**GUI:** `ttkbootstrap>=1.10.1`
**Dev:** `pytest>=7.4.0`, `black>=23.7.0`, `flake8>=6.1.0`

## Usage

### GUI Mode

```bash
python gui.py
```

### Command Line

```bash
python main.py --input input/products.json --output output/products.json
```

### Python API

```python
from src.collector import TalltailsCollector
import requests

collector = TalltailsCollector()

# Find product URL with variant matching
product_url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print,
    product_data={
        "description_1": "Tall Tails Highland Cow Toy",
        "upcitemdb_title": "Dog Toy Highland Cow"
    }
)

# Parse product page with variant handling
enriched_data = collector.parse_page(html_text)
```

## Project Structure

```
talltails/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # Magento search
│   ├── parser.py           # HTML parsing
│   └── variant_handler.py  # Variant logic
├── tests/                  # Test scripts
└── README.md               # This file
```

## Configuration

```python
SITE_CONFIG = {
    "site_key": "talltailsdog",
    "origin": "https://www.talltailsdog.com",
    "search": {
        "type": "onsite",
        "endpoint": "/catalogsearch/result/?q={query}",
        "method": "GET",
        "expects_html_grid": True
    },
    "selectors": {
        "title": "h1",
        "feature_bullets": ".product-info-main ul li",
        "description_root": ".product.attribute.description .value",
        "materials_root": "[id*='materials'] .value",
        "gallery_hint": "mage/gallery/gallery"
    },
    "learning": {
        "upc_disable_after": 5  # Disable UPC search after 5 failures
    }
}
```

## Architecture

### Core Components

**collector.py** - Main orchestration with variant token extraction

**search.py** - Magento search:
- Catalog search endpoint
- UPC and name-based search
- HTML grid result parsing
- Learning mode (disables UPC after threshold)

**parser.py** - Magento HTML parsing:
- Title, feature bullets, description, materials
- Gallery extraction with Magento hints
- Variant-aware parsing

**variant_handler.py** - Variant logic:
- Token-based variant detection
- Fused label generation
- Variant matching algorithms
- Highland cow, black bear, cow print patterns

### Data Flow

1. **Variant Token Extraction**: Derive tokens from description_1, upcitemdb_title → Generate fused labels
2. **Search**: Magento catalogsearch → UPC or name fallback → Extract product URL
3. **Parse**: Magento HTML → Extract with variant context → Match variants
4. **Output**: Combine input + manufacturer + variant data

## Variant Matching

The collector uses intelligent variant token matching:

**Token Extraction:**
- Extracts tokens from description_1, upcitemdb_title, title, name
- Generates fused labels for common patterns:
  - `["cow"]` → "highland cow"
  - `["black", "bear"]` → "black bear"
  - `["cow", "print"]` → "cow print"

**Variant Detection:**
- Passes tokens and query text to parser
- Parser uses variant_handler for matching
- Identifies correct variant from multi-variant pages

## Notes

- **Magento platform** - Standard Magento structure and patterns
- **Variant intelligence** - Token-based matching for complex variants
- **Fused labels** - Handles common product patterns (highland cow, black bear)
- **Learning mode** - Adapts search strategy based on UPC failure rate
- **Gallery hints** - Uses mage/gallery/gallery for reliable image extraction

## License

Internal tool - Not for public distribution

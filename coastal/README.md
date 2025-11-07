# Coastal Pet Product Collector

Collects and enriches product data from Coastal Pet website for Shopify import.

## Overview

This collector retrieves product information from:
- **www.coastalpet.com** - Custom e-commerce platform with Bazaarvoice integration

Uses UPC-based search with multiple search strategies and modelProduct JSON extraction.

## Features

### Search & Collection
- **Multi-strategy search** - HTML search, autocomplete API
- **UPC override support** - Hardcoded mappings for problematic products
- **modelProduct JSON parsing** - Extracts embedded product data
- **Bazaarvoice integration** - Configuration for reviews API (if needed)

### Data Processing
- **modelProduct extraction** - Parses embedded JSON from script tags
- **Multi-source image collection**:
  - modelProduct JSON images
  - DOM gallery fallback extraction
- **Key benefits extraction** - Parses bullet point benefits
- **Description parsing** - Extracts product descriptions
- **Brand extraction** - From modelProduct or search links

### Image Processing
- **modelProduct image priority** - Primary source for gallery
- **DOM fallback** - Extracts images from HTML when JSON thin
- **URL normalization** - Converts to HTTPS, removes query params
- **Deduplication** - Removes duplicate images

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation and scripting
- **Real-time progress tracking** with detailed status messages
- **Auto-save configuration** - Persists settings between sessions

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/coastal
pyenv local coastal
pip install -r requirements.txt

# For GUI support
pip install -r requirements-gui.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

**Core:** `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`, `openpyxl>=3.1.0`
**GUI:** `ttkbootstrap>=1.10.1`
**Dev:** `pytest>=7.4.0`, `black>=23.7.0`, `flake8>=6.1.0`, `mypy>=1.5.0`

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
from src.collector import CoastalCollector
import requests

collector = CoastalCollector()

# Find product URL
product_url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print
)

# Parse product page
html = requests.get(product_url).text
enriched_data = collector.parse_page(html)
```

## Project Structure

```
coastal/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # Product search logic
│   ├── parser.py           # HTML parsing
│   └── image_processor.py  # Image extraction
├── tests/                  # Test scripts
├── requirements*.txt       # Dependencies
└── README.md               # This file
```

## Configuration

Site configuration is embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    "key": "coastal",
    "display_name": "Coastal Pet",
    "origin": "https://www.coastalpet.com",
    "bv": {  # Bazaarvoice integration
        "client": "Coastal",
        "bfd_token": "25877,main_site,en_US",
        "api_base_template": "...",
    },
    "search": {
        "html_search_path": "/products/search/?q={QUERY}",
        "autocomplete_path": "/product/searchconnection/autocompleteandsuggest?fuzzy=true&term={QUERY}",
        "upc_overrides": {...}
    }
}
```

## Architecture

### Core Components

**collector.py** - Main orchestration with dual search strategies

**search.py** - Multi-strategy UPC search:
- UPC overrides (hardcoded mappings)
- HTML search endpoint: `/products/search/?q={UPC}`
- Autocomplete API endpoint for fallback

**parser.py** - Custom HTML parsing:
- Extracts modelProduct JSON from script tags
- Parses product title, brand, benefits, description
- Extracts gallery images from modelProduct or DOM

**image_processor.py** - Image extraction:
- `extract_gallery_from_model_product()` - Primary source
- `extract_dom_gallery_fallback()` - Secondary source
- URL normalization and deduplication

### Data Flow

1. **Search**: Check overrides → HTML search → Autocomplete API
2. **Parse**: Extract modelProduct JSON → Parse title/brand/benefits/description → Extract images
3. **Images**: modelProduct gallery → DOM fallback if thin → Normalize URLs
4. **Output**: Combine input + manufacturer data

### Shared Dependencies

Imports from `../shared/`: `load_json_file()`, `save_json_file()`, `normalize_upc()`, `text_only()`, `extract_json_from_script()`

## Notes

- **modelProduct JSON** - Primary data source embedded in page
- **Bazaarvoice config** - Available for reviews integration if needed
- **UPC overrides** - Handles problematic products with hardcoded mappings
- **Multi-strategy search** - Ensures high match rate
- **DOM fallback** - Ensures gallery completeness

## License

Internal tool - Not for public distribution

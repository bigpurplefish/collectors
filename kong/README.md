# KONG Company Product Collector

Collects and enriches product data from KONG Company website for Shopify import.

## Overview

This collector retrieves product information from:
- **www.kongcompany.com** - Custom WordPress-based pet toy website

Uses UPC-based search with HTML search endpoint.

## Features

### Search & Collection
- **HTML search endpoint** - Uses site search: `/?s={UPC}`
- **UPC override support** - Hardcoded mappings for problematic products
- **Product URL extraction** - Regex-based extraction from search results

### Data Processing
- **Custom HTML parsing** - Extracts product data from custom structure
- **Description extraction** - Parses product descriptions
- **Benefit bullets extraction** - Captures key product features
- **Image extraction** - Collects product images

### Image Processing
- **Gallery extraction** - Multi-source image collection
- **URL normalization** - Converts to HTTPS, removes query params
- **Deduplication** - Removes duplicate images

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation
- **Real-time progress tracking**
- **Auto-save configuration**

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/kong
pyenv local kong
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

## Project Structure

```
kong/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # UPC search
│   └── parser.py           # HTML parsing
├── tests/                  # Test scripts
└── README.md               # This file
```

## Configuration

```python
SITE_CONFIG = {
    "key": "kong",
    "display_name": "KONG Company",
    "origin": "https://www.kongcompany.com",
    "search": {
        "html_search_path": "/?s={QUERY}",
        "upc_overrides": {}
    }
}
```

## Architecture

**collector.py** - Main orchestration
**search.py** - HTML search with UPC query
**parser.py** - Custom HTML parsing for product data

## Notes

- **Custom WordPress site** - Non-standard structure
- **HTML search** - Uses `/?s={UPC}` endpoint
- **UPC search** - Direct UPC search on site

## License

Internal tool - Not for public distribution

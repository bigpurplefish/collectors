# Ivyclassic Product Collector

Catalog-based product collector that enriches data from a pre-built JSON catalog. No web scraping is performed.

## Overview

This is a zero-scrape collector that requires a product catalog JSON file containing:
- Product URLs
- Product names and brands
- UPCs
- Descriptions and details
- Image URLs

The collector looks up products by UPC and enriches input records with the catalog data.

## Features

### Catalog-Based Collection
- **Zero web scraping** - All data from pre-built catalog JSON
- **UPC-based lookup** - Fast product matching by UPC
- **Indexed catalog** - Efficient lookups with UPC index
- **Catalog required** - Profile enforces catalog presence
- **Graceful fallback** - Returns None if product not in catalog

### Data Processing
- **Description parsing** - Extracts product descriptions
- **Image URL normalization** - Converts to HTTPS, deduplicates
- **Field standardization** - Consistent manufacturer data structure

### User Interfaces
- **Thread-safe GUI** with catalog path configuration
- **CLI interface** for automation
- **Real-time progress tracking**
- **Auto-save configuration**

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/ivyclassic
pyenv local ivyclassic
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
from src.collector import IvyclassicCollector

# Initialize with catalog
collector = IvyclassicCollector()
collector.set_catalog_path("input/catalog.json")

# Find product URL by UPC
product_url = collector.find_product_url("012345678901", None, 30, print)

# Parse product page
enriched = collector.parse_page(html_text)
```

## Project Structure

```
ivyclassic/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── catalog.py          # Catalog management
│   └── parser.py           # HTML parsing
├── tests/                  # Test scripts
└── README.md               # This file
```

## Configuration

```python
SITE_CONFIG = {
    "site_key": "ivyclassic",
    "origin": "https://ivyclassic.com",
    "requires_catalog": True  # Catalog is mandatory
}
```

## Architecture

**collector.py** - Main orchestration with catalog requirement enforcement
**catalog.py** - Catalog loading, indexing, and UPC lookup
**parser.py** - HTML parsing for product pages (if needed)

### Data Flow

1. **Initialization**: Load catalog JSON, build UPC index
2. **Product Lookup**: Find product in catalog by normalized UPC
3. **Data Enrichment**: Extract data from catalog record
4. **Output**: Combine input + manufacturer data

## Notes

- **Catalog required** - This collector cannot scrape websites
- **Zero web requests** - All data from catalog file
- **Fast processing** - Indexed lookups enable high throughput
- **Graceful degradation** - Missing products return None

## License

Internal tool - Not for public distribution

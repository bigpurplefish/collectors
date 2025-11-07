# Fromm Family Foods Product Collector

Collects and enriches product data from Fromm Family Foods website for Shopify import.

## Overview

This collector retrieves product information from:
- **frommfamily.com** - Custom pet food website

Uses UPC override mappings (no search functionality available).

## Features

### Search & Collection
- **UPC override mappings** - Requires pre-configured URL mappings
- **No search endpoint** - Site does not provide searchable interface
- **Direct URL access** - Uses catalog of product URLs

### Data Processing
- **Custom HTML parsing** - Extracts product data from custom structure
- **Ingredient list extraction** - Parses detailed ingredient information
- **Guaranteed analysis parsing** - Extracts nutritional data
- **Feeding guidelines extraction** - Captures feeding instructions
- **Image extraction** - Collects product images from page

### Image Processing
- **Multi-source extraction** - Gallery images and thumbnails
- **URL normalization** - Converts to HTTPS, removes query params
- **Deduplication** - Removes duplicate images

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation and scripting
- **Real-time progress tracking**
- **Auto-save configuration**

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/fromm
pyenv local fromm
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
fromm/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # UPC override lookup
│   ├── parser.py           # HTML parsing
│   └── image_processor.py  # Image extraction
├── tests/                  # Test scripts
└── README.md               # This file
```

## Configuration

```python
SITE_CONFIG = {
    "key": "fromm",
    "display_name": "Fromm Family Foods",
    "origin": "https://frommfamily.com",
    "search": {
        "upc_overrides": {
            "072705115372": "https://frommfamily.com/products/dog/gold/dry/large-breed-adult-gold/",
            "072705115204": "https://frommfamily.com/products/dog/gold/dry/adult-gold/"
        }
    }
}
```

## Architecture

**collector.py** - Main orchestration
**search.py** - UPC override lookup only (no search endpoint)
**parser.py** - Custom HTML parsing for ingredients, analysis, feeding guidelines
**image_processor.py** - Image extraction and normalization

## Notes

- **UPC overrides required** - No search functionality available
- **Custom structure** - Non-standard HTML parsing
- **Ingredient/nutrition focus** - Detailed pet food data extraction

## License

Internal tool - Not for public distribution

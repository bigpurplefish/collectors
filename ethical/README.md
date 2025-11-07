# Ethical Products (SPOT) Product Collector

Collects and enriches product data from Ethical Pet website (WooCommerce platform) for Shopify import.

## Overview

This collector retrieves product information from:
- **www.ethicalpet.com** - WooCommerce-based e-commerce site

Uses intelligent text matching with taxonomy, flavor, size, and form validation. Requires Selenium for JavaScript-rendered content.

## Features

### Search & Collection
- **Intelligent text matching** - Uses product descriptions with token matching
- **Multi-factor validation** - Taxonomy (dog/cat), flavor, size, and form matching
- **Brand alias support** - Handles multiple brand variations (Ethical Products, Ethical Pet, SPOT)
- **Selenium automation** - Required for JavaScript-rendered WooCommerce content
- **Simulate click from search** - Better loading of dynamic content

### Data Processing
- **WooCommerce HTML parsing** - Extracts product data from WooCommerce structure
- **Elastislide carousel extraction** - Parses carousel gallery images (data-largeimg attributes)
- **Strict carousel mode** - Only uses carousel images for reliability
- **Multi-selector description parsing** - Multiple fallback selectors for descriptions
- **Text-based matching logic** - Sophisticated token matching with weights

### Image Processing
- **Carousel-only mode** - Ensures high-quality images from main carousel
- **data-largeimg extraction** - Gets full-size images from carousel
- **URL normalization** - Converts to HTTPS, removes query params
- **Image validation** - HTTP 200 checks, SHA256 deduplication

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation and scripting
- **Real-time progress tracking** with detailed status messages
- **Auto-save configuration** - Persists settings between sessions

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/ethical
pyenv local ethical
pip install -r requirements.txt

# Install Selenium and WebDriver
pip install selenium
# Chrome WebDriver will be managed by selenium-manager automatically

# For GUI support
pip install -r requirements-gui.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

**Core:** `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`, `openpyxl>=3.1.0`, `selenium>=4.0.0`
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
from src.collector import EthicalCollector
import requests

collector = EthicalCollector()

# Find product URL with intelligent matching
product_url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print,
    product_data={"description_1": "SPOT Ethical Dog Toy", "size": "Large"}
)

# Parse product page (requires Selenium for full content)
enriched_data = collector.parse_page(html_text)
```

## Project Structure

```
ethical/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── search.py           # Intelligent text search
│   ├── parser.py           # WooCommerce parsing
│   ├── image_processor.py  # Image extraction
│   ├── text_matching.py    # Text matching logic
│   └── size_matching.py    # Size validation
├── tests/                  # Test scripts
├── requirements*.txt       # Dependencies
└── README.md               # This file
```

## Configuration

Extensive configuration embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    "site_key": "ethical",
    "display_name": "Ethical Products (SPOT)",
    "origin": "https://www.ethicalpet.com",
    "search": {
        "templates": ["https://www.ethicalpet.com/?s={q}"],
        "manufacturer_aliases": ["Ethical Products", "Ethical Pet", "Ethical", "SPOT"],
        "verify_min_token_hits": 2,
        "brand_weight": 2,
        "prime_homepage": True
    },
    "parsing": {
        "use_selenium": True,
        "gallery_selectors": {
            "carousel_images": "div.elastislide-carousel ul.elastislide-list li img[data-largeimg]"
        },
        "strict_carousel_only": True
    },
    "selenium": {
        "enabled": True,
        "browser": "chrome",
        "headless": True,
        "page_load_timeout_sec": 40,
        "simulate_click_from_search": True
    }
}
```

## Architecture

### Core Components

**collector.py** - Main orchestration with extensive configuration

**search.py** - Intelligent text matching:
- Token-based similarity scoring
- Taxonomy validation (dog/cat products)
- Flavor matching with aliases
- Size matching with normalization
- Form matching (treats, food, toys, etc.)
- Brand alias support
- Multi-factor weighted scoring

**parser.py** - WooCommerce HTML parsing:
- Selenium-based page loading
- Elastislide carousel extraction
- Multi-selector description parsing
- WooCommerce-specific structure handling
- data-largeimg full-size image extraction

**text_matching.py** - Text matching algorithms
**size_matching.py** - Size validation logic
**image_processor.py** - Carousel image extraction

### Data Flow

1. **Search**: Site search → Extract candidates → Text matching → Taxonomy/flavor/size validation → Score and rank
2. **Parse**: Selenium load page → Extract carousel images (data-largeimg) → Parse descriptions → Extract metadata
3. **Images**: Carousel-only extraction → data-largeimg attributes → Normalize URLs → Validate
4. **Output**: Combine input + manufacturer data

### Shared Dependencies

Imports from `../shared/`: `load_json_file()`, `save_json_file()`, `normalize_upc()`, `text_only()`

## Notes

- **Selenium required** - WooCommerce content is JavaScript-rendered
- **Intelligent matching** - Multi-factor scoring (text, taxonomy, flavor, size)
- **Carousel images only** - Strict mode ensures quality
- **data-largeimg extraction** - Gets full-size images from Elastislide carousel
- **Prime homepage** - Loads homepage first for better session state
- **Simulate clicks** - Better content loading in Selenium

## License

Internal tool - Not for public distribution

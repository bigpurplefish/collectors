# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Python Development Standards

### Always Apply
- Use context7 for up-to-date library documentation
- Reference @~/Code/shared-docs/python/ for our internal standards
- Combine external best practices with our internal requirements

### Before Any Code Generation
1. Check Context7 for latest library patterns (use context7)
2. Review our internal requirements @~/Code/shared-docs/python/
3. Ensure both external and internal standards are met

## Project Overview

Bradley Caldwell Product Collector - A catalog-based product enrichment tool that reads from a pre-built JSON catalog file to enrich product records with manufacturer data.

## Architecture

This project uses a **zero-scrape** approach - no web scraping is performed. All product data comes from a pre-built JSON catalog file that maps UPCs to product information.

### Core Components

**collector.py**: Main collector class that:
- Loads product catalog from JSON file
- Maps UPCs to product records
- Enriches input products with manufacturer data (title, brand, description, benefits, ingredients, images)
- Outputs enriched JSON with manufacturer and Shopify media blocks

### Site Configuration

The Bradley Caldwell site configuration is embedded directly in `collector.py`:

```python
SITE_CONFIG = {
    "key": "bradley_caldwell",
    "display_name": "Bradley Caldwell",
    "origin": "https://www.bradleycaldwell.com",
    "referer": "https://www.bradleycaldwell.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    "search": {
        "upc_overrides": {}
    }
}
```

## Usage

### Command Line

```bash
python collector.py --catalog path/to/catalog.json --input products.json --output enriched.json
```

### Python API

```python
from collector import BradleyCaldwellCollector

collector = BradleyCaldwellCollector(catalog_path="catalog.json")
enriched = collector.enrich_product({"upc": "123456789012"})
```

## Catalog Format

The catalog JSON file should be an array of product objects:

```json
[
  {
    "upc": "123456789012",
    "product_url": "https://www.bradleycaldwell.com/products/detail?id=ABC123",
    "product_name": "Product Name",
    "brand": "Bradley Caldwell",
    "description": "Product description...",
    "ingredients": "Ingredient list",
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ]
  }
]
```

## Output Format

Enriched products include:
- All original input fields (preserved)
- `manufacturer`: Object with product data, images, benefits, ingredients
- `distributors_or_retailers`: Empty array (no retailer data for Bradley Caldwell)
- `shopify.media`: Array of suggested Shopify image filenames

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/Python/collectors/bradley_caldwell
pyenv local bradley_caldwell
pip install -r requirements.txt
```

### Key Functions

- `enrich_product(input_row)`: Enriches a single product record
- `process_file(input_path, output_path)`: Processes entire JSON file
- `find_product_by_upc(upc)`: Looks up product URL by UPC
- `_benefits_from_description(desc)`: Extracts bullet points from description

## Error Handling

- Raises `RuntimeError` if catalog path is not provided
- Raises `RuntimeError` if catalog file doesn't exist
- Raises `RuntimeError` if catalog JSON is malformed
- On individual product errors, logs error and preserves original product in output

## Notes

- No web requests are made
- All data must be pre-populated in the catalog JSON
- Images are normalized to HTTPS
- Benefits are automatically extracted from descriptions if they appear to be lists
- UPC matching is fuzzy (strips non-digits)

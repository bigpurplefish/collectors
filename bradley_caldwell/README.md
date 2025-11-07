# Bradley Caldwell Product Collector

Catalog-based product collector that enriches product data from a pre-built JSON catalog. No web scraping is performed - all data comes from the catalog file.

## Overview

This is a zero-scrape collector that requires a product catalog JSON file containing:
- Product URLs
- Product names and brands
- UPCs
- Descriptions and ingredients
- Image URLs

The collector looks up products by UPC and enriches input records with the catalog data.

## Features

### Catalog-Based Collection
- **Zero web scraping** - All data from pre-built catalog JSON
- **UPC-based lookup** - Fast product matching by UPC
- **Indexed catalog** - Efficient lookups with UPC and URL indexes
- **Graceful fallback** - Returns empty manufacturer data if product not in catalog

### Data Processing
- **Description normalization** - Cleans up double periods, adds ending periods
- **Bullet point extraction** - Converts descriptions to benefit bullets
- **Image URL normalization** - Converts to HTTPS, deduplicates
- **Field standardization** - Consistent manufacturer data structure

### Shopify Output
- **GraphQL-compliant structure** - Ready for Shopify Admin API
- **Media array generation** - Includes UPC-based image filenames
- **Clean data structure** - Preserves all original input fields

### User Interfaces
- **Thread-safe GUI** with queue-based communication
- **CLI interface** for automation and scripting
- **Real-time progress tracking** with detailed status messages
- **Auto-save configuration** - Persists settings between sessions
- **Error tracking** - Graceful error handling for missing products

## Installation

```bash
# Clone or navigate to project
cd /Users/moosemarketer/Code/garoppos/collectors/bradley_caldwell

# Set up virtual environment
pyenv local bradley_caldwell

# Install dependencies
pip install -r requirements.txt

# For GUI support
pip install -r requirements-gui.txt

# For development
pip install -r requirements-dev.txt
```

### Dependencies

**Core (requirements.txt):**
- `requests>=2.31.0` - HTTP utilities (shared dependency)
- `ttkbootstrap>=1.10.1` - GUI framework
- `openpyxl>=3.1.0` - Excel file handling

**GUI (requirements-gui.txt):**
- Inherits from requirements.txt
- `ttkbootstrap>=1.10.1` - Modern themed Tkinter widgets

**Development (requirements-dev.txt):**
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting
- `black>=23.7.0` - Code formatting
- `flake8>=6.1.0` - Linting
- `mypy>=1.5.0` - Type checking

## Usage

### GUI Mode (Recommended)

```bash
python gui.py
```

The GUI provides:
- **File selection dialogs** - Browse for catalog, input, and output files
- **Catalog path configuration** - Required product catalog JSON file
- **Real-time progress tracking** - Live status updates during processing
- **Auto-save configuration** - All settings persist between sessions
- **Dark theme** - Easy on the eyes for long sessions
- **Thread-safe design** - UI never freezes during processing

### Command Line

```bash
python main.py --catalog input/catalog.json --input input/products.json --output output/products.json
```

### Python API

```python
from src.collector import BradleyCaldwellCollector

# Initialize with catalog
collector = BradleyCaldwellCollector(catalog_path="input/catalog.json")

# Find product URL by UPC
product_url = collector.find_product_by_upc("012345678901")

# Enrich a single product
enriched = collector.enrich_product({
    "upc": "012345678901",
    "description_1": "Some product"
})

# Process entire file
collector.process_file("input/products.json", "output/enriched.json")
```

## Project Structure

```
bradley_caldwell/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── catalog.py          # Catalog management
│   └── enricher.py         # Product enrichment logic
├── tests/                  # Test scripts
│   ├── __init__.py         # Package marker
│   ├── README.md           # Test documentation
│   ├── .gitignore          # Test output exclusions
│   └── output/             # Test outputs (gitignored)
│       └── .gitkeep
├── input/                  # Input files (gitignored)
├── output/                 # Output files (gitignored)
├── logs/                   # Log files (gitignored)
├── docs/                   # Documentation
│   └── CLAUDE.md           # AI assistant guidance
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── requirements-gui.txt    # GUI dependencies
└── README.md               # This file
```

## Configuration

Site configuration is embedded in `src/collector.py`:

```python
SITE_CONFIG = {
    "key": "bradley_caldwell",
    "display_name": "Bradley Caldwell",
    "origin": "https://www.bradleycaldwell.com",
    "referer": "https://www.bradleycaldwell.com/",
    "user_agent": "Mozilla/5.0 ...",
}
```

## Input Format

**Catalog JSON Format (Required):**
```json
[
  {
    "upc": "012345678901",
    "product_url": "https://www.bradleycaldwell.com/product-name",
    "product_name": "Product Name",
    "brand": "Brand Name",
    "description": "Product description with benefits",
    "ingredients": "Ingredient list",
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg"
    ]
  }
]
```

**Input Products JSON:**
```json
[
  {
    "upc": "012345678901",
    "description_1": "Product Name"
  }
]
```

## Output Format

Shopify-compatible JSON with:
- All original input fields preserved
- `manufacturer` object with enriched product data
- `shopify.media` array with UPC-based image filenames
- `distributors_or_retailers` array (empty for catalog-based)

## Architecture

### Core Components

**collector.py** - Main orchestration layer
- Embeds `SITE_CONFIG` with Bradley Caldwell configuration
- `BradleyCaldwellCollector` class coordinates catalog and enrichment
- `find_product_by_upc()` - Looks up product URL from catalog
- `enrich_product()` - Enriches single product record
- `process_file()` - Processes entire input file

**catalog.py** - Catalog management
- `CatalogManager` class handles catalog loading and indexing
- Builds UPC and URL indexes for fast lookups
- `ensure_loaded()` - Lazy loads catalog on first use
- `get_by_upc()` - Fast UPC lookup
- `get_by_url()` - Fast URL lookup

**enricher.py** - Product enrichment logic
- `ProductEnricher` class handles data transformation
- Normalizes descriptions (fixes double periods, adds ending periods)
- Extracts bullet points from descriptions
- Normalizes image URLs to HTTPS
- Generates Shopify media filenames with UPC prefix
- Gracefully handles missing catalog data

### Data Flow

1. **Initialization**
   - Load catalog JSON file
   - Build UPC and URL indexes
   - Initialize enricher

2. **For Each Product:**
   - Extract UPC from input record
   - Look up product in catalog by UPC
   - If found: Extract name, brand, description, ingredients, images
   - If not found: Return empty manufacturer data
   - Normalize description text
   - Extract bullet points from description
   - Normalize image URLs to HTTPS
   - Generate Shopify media filenames

3. **Output Generation**
   - Preserve all original input fields
   - Add manufacturer object with catalog data
   - Add shopify.media array with image filenames
   - Write JSON to output file

### Shared Dependencies

Imports utilities from `../shared/`:
- `load_json_file()` - JSON file loading
- `save_json_file()` - JSON file writing
- `build_catalog_index()` - Catalog indexing
- `normalize_upc()` - UPC normalization
- `text_only()` - HTML entity decoding
- `normalize_to_https()` - URL normalization
- `extract_bullet_points()` - Bullet point extraction
- `deduplicate_urls()` - Image URL deduplication

## Best Practices

### Catalog Preparation

**For Best Results:**
- Ensure catalog contains all products you need to enrich
- Use clean, normalized UPCs (digits only)
- Include full product URLs
- Provide complete image URL arrays
- Use consistent field names

### Processing Strategy

**For Large Datasets:**
1. Test with small sample first
2. Review output quality
3. Process full dataset
4. Use CLI mode for automation

## Troubleshooting

### Common Issues

**"No Bradley Caldwell product catalog specified"**
- Set catalog path in GUI or pass --catalog to CLI
- Ensure catalog JSON file exists at specified path

**"Product catalog not found"**
- Verify catalog file path is correct
- Check that file has .json extension
- Ensure file is readable

**"Product not found in catalog"**
- Check that product UPC exists in catalog
- Verify UPC format matches (digits only)
- Collector will return empty manufacturer data gracefully

**"Invalid catalog format"**
- Ensure catalog is JSON array of objects
- Each object should have required fields (upc, product_url, etc.)
- Check JSON syntax is valid

## Notes

- **Catalog required** - This collector cannot scrape websites, requires pre-built catalog
- **Zero web requests** - All data comes from catalog file
- **Fast processing** - Indexed lookups enable high throughput
- **Graceful degradation** - Missing products get empty manufacturer data
- **UPC normalization** - Automatically strips non-digits from UPCs
- **Image deduplication** - Removes duplicate image URLs
- **Description cleanup** - Fixes common text issues automatically

## License

Internal tool - Not for public distribution

## Support

For issues or questions, contact the development team.

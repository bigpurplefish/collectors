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

Chala Handbags Product Collector - Collects and enriches product data from https://www.chalahandbags.com.

## Architecture

This project collects product information from Chala Handbags's website, including:
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

The Chala Handbags site configuration is embedded directly in `collector.py`.

## Usage

### Command Line

```bash
python collector.py --input products.json --output enriched.json
```

### Python API

```python
from collector import ChalaCollector

collector = ChalaCollector()
enriched = collector.collect_product(upc="123456789012")
```

## Development

### Setup

```bash
cd /Users/moosemarketer/Code/Python/collectors/chala
pyenv local chala
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

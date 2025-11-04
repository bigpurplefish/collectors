# Product Collectors

This directory contains individual product collector projects for each retailer/manufacturer we scrape.

## Project Structure

Each collector follows Python best practices with a standard directory structure:

```
collector_name/
├── main.py                      # Entry point (at project root)
├── src/                         # All source code
│   ├── __init__.py
│   ├── collector.py             # Main orchestration
│   ├── search.py                # Product discovery
│   ├── parser.py                # HTML/data parsing
│   └── [feature_modules].py     # Additional modules
├── input/                       # Input files
│   └── .gitkeep
├── output/                      # Output files (gitignored)
│   └── .gitkeep
├── tests/                       # Test files
│   └── .gitkeep
├── docs/                        # Documentation
│   └── CLAUDE.md                # AI assistant guidance
├── logs/                        # Log files (gitignored)
│   └── .gitkeep
├── requirements.txt             # Python dependencies
├── .python-version              # pyenv configuration
├── .gitignore                   # Git ignore patterns
└── README.md                    # Project documentation
```

**Key Features:**
- Clean separation of code, data, tests, and docs
- Industry-standard Python layout
- Easy to understand and maintain
- Supports testing and CI/CD

## Available Collectors

| Project | Site | Description |
|---------|------|-------------|
| **bradley_caldwell** | bradleycaldwell.com | Catalog-based (no scraping), requires pre-built JSON catalog |
| **coastal** | coastalpet.com | Bazaarvoice API + page scraping, variant-aware |
| **chala** | chalahandbags.com | Shopify store with gallery extraction |
| **ethical** | ethicalpet.com | WooCommerce site with Selenium support |
| **fromm** | frommfamily.com | Manufacturer site with ingredients/nutrition |
| **ivyclassic** | ivyclassic.com | Catalog-based product enrichment |
| **kong** | kongcompany.com | Product catalog with media variants |
| **orgill** | orgill.com | Requires authentication, portal scraping |
| **purinamills** | shop.purinamills.com | Name index-based discovery |
| **talltails** | talltailsdog.com | Magento/Adobe Commerce with variant galleries |

## Shared Utilities

The `shared/` directory contains utilities used across multiple collectors:

```
shared/
├── src/                         # Core utility modules
│   ├── text_utils.py            # Text processing
│   ├── image_utils.py           # Image URL handling
│   ├── http_utils.py            # HTTP utilities
│   ├── json_utils.py            # JSON operations
│   └── upc_utils.py             # UPC processing
├── utils/                       # Standalone tools
│   ├── batcher.py               # Batch processing
│   └── json_to_excel_converter.py  # Excel conversion
└── docs/
    └── README.md                # Utility documentation
```

## Quick Start

### Setup a Project

```bash
# Navigate to a project
cd /Users/moosemarketer/Code/Python/collectors/bradley_caldwell

# Activate virtual environment (automatically via pyenv local)
# Verify it's activated
python --version  # Should show Python 3.13.0

# Run the collector
python main.py --input input/products.json --output output/enriched.json
```

### Using Shared Utilities

```bash
# From any collector project, reference the shared utilities
python ../shared/utils/batcher.py split --input large.json --outdir batches --size 50

# Convert to Excel
python ../shared/utils/json_to_excel_converter.py
```

## Development

### Python Development Standards

All projects follow these standards:
- Use **context7** for up-to-date library documentation
- Reference **@~/Code/shared-docs/python/** for internal standards
- Combine external best practices with internal requirements

Before any code generation:
1. Check Context7 for latest library patterns
2. Review internal requirements in ~/Code/shared-docs/python/
3. Ensure both external and internal standards are met

### Adding a New Collector

1. Create project directory: `mkdir <site_name>`
2. Create `collector.py` with embedded site configuration
3. Create `requirements.txt` with dependencies
4. Create `CLAUDE.md` documentation
5. Create virtual environment:
   ```bash
   pyenv virtualenv 3.13.0 <site_name>
   pyenv local <site_name>
   pip install -r requirements.txt
   ```

### Virtual Environment Management

Each project uses pyenv for environment isolation:

```bash
# List all collector environments
pyenv versions | grep -E "(bradley|coastal|chala|ethical|fromm|ivy|kong|orgill|purina|talltails)"

# Remove an environment (if needed)
pyenv uninstall <project_name>

# Recreate an environment
pyenv virtualenv 3.13.0 <project_name>
cd /Users/moosemarketer/Code/Python/collectors/<project_name>
pyenv local <project_name>
pip install -r requirements.txt
```

## Configuration

Site-specific configuration (origin, referer, user-agent, search paths, etc.) is embedded directly in each `collector.py` file. No external JSON profiles are needed.

## Output Format

All collectors produce enriched JSON with this structure:

```json
{
  "upc": "123456789012",
  "...": "original fields preserved",
  "manufacturer": {
    "product_url": "https://...",
    "homepage": "https://...",
    "name": "Product Name",
    "brand": "Brand Name",
    "description": "...",
    "benefits_text": ["benefit 1", "benefit 2"],
    "ingredients_text": "...",
    "nutrition_text": {},
    "directions_for_use": "...",
    "media": ["https://image1.jpg", "https://image2.jpg"]
  },
  "distributors_or_retailers": [],
  "shopify": {
    "media": ["123456789012_0.jpg", "123456789012_1.jpg"]
  }
}
```

## Common Workflows

### Batch Processing

```bash
# 1. Split large input file
cd /Users/moosemarketer/Code/Python/collectors/shared
python batcher.py split --input ../all_products.json --outdir ../batches --size 50 --id-field "upc"

# 2. Process each batch (example with coastal)
cd ../coastal
for batch in ../batches/batch_*.json; do
  output="../batches/enriched_$(basename $batch)"
  python collector.py --input "$batch" --output "$output"
done

# 3. Merge enriched batches
cd ../shared
python batcher.py merge --original ../all_products.json --batches-dir ../batches --output ../enriched_all.json --id-field "upc"
```

### Convert to Excel

```bash
cd /Users/moosemarketer/Code/Python/collectors/shared
python json_to_excel_converter.py
# Use GUI to select enriched JSON and output path
```

## Notes

- **Rate Limiting**: All collectors implement polite delays (0.8-1s default)
- **Image Handling**: Images are normalized to HTTPS and de-proxied where applicable
- **Error Handling**: Errors on individual products are logged; original data preserved in output
- **UPC Matching**: Flexible matching (strips non-digits, handles UPC-12/13/14 variants)

## Troubleshooting

### Virtual Environment Issues

```bash
# Environment not activating
pyenv local <project_name>
python --version  # Check Python version

# Dependencies not found
pip install -r requirements.txt

# Environment corrupted
pyenv uninstall <project_name>
pyenv virtualenv 3.13.0 <project_name>
pyenv local <project_name>
pip install -r requirements.txt
```

### Collector Issues

Check the project's CLAUDE.md for site-specific notes and requirements.

## Support

For internal standards and best practices, see:
- `~/Code/shared-docs/python/GIT_WORKFLOW.md`
- `~/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md`
- `~/Code/shared-docs/python/TECHNICAL_DOCS.md`

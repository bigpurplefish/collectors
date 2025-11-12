# CLAUDE.md - Purinamills Product Collector

**AI Assistant Guidance for Purinamills Project**

This is the **reference implementation** for the collectors architecture. It demonstrates the most complete and comprehensive feature set.

---

## AI Assistant Guidelines

### ⚠️ CRITICAL: ALWAYS Follow Shared-Docs Requirements ⚠️

**MANDATORY:** ALL code changes MUST follow the complete requirements in `/Users/moosemarketer/Code/shared-docs/python/`

**This is NOT optional.** The shared-docs contain the authoritative standards for:
- Project structure
- Git workflow
- Code quality
- Testing requirements
- Documentation standards

### Required Reading Before ANY Code Changes

**Read these documents FIRST:**
1. **`COMPLIANCE_CHECKLIST.md`** - Project structure verification
2. **`PROJECT_STRUCTURE_REQUIREMENTS.md`** - Complete project specifications
3. **`GIT_WORKFLOW.md`** - Git commit and branching standards
4. **`GRAPHQL_OUTPUT_REQUIREMENTS.md`** - Shopify API format
5. **`GUI_DESIGN_REQUIREMENTS.md`** - Thread-safe GUI patterns
6. **`TECHNICAL_DOCS.md`** - Technical documentation standards

### Development Workflow Quick Reference

**This is a quick reference only. See shared-docs for complete details.**

1. **Pre-Coding:**
   - Use Context7 for current library documentation
   - Read relevant shared-docs requirements
   - Understand existing code architecture

2. **Coding:**
   - Follow PROJECT_STRUCTURE_REQUIREMENTS.md
   - Follow GUI_DESIGN_REQUIREMENTS.md (if GUI changes)
   - Follow GRAPHQL_OUTPUT_REQUIREMENTS.md (if output changes)

3. **Testing:**
   - Write tests for new features
   - Run all tests: `python tests/test_your_feature.py`
   - **All tests MUST pass** before committing

4. **Git Workflow:**
   - Follow GIT_WORKFLOW.md exactly
   - `git status` → `git add` → `git diff --staged` → `git commit` → `git push`
   - Use conventional commit format (see GIT_WORKFLOW.md)

5. **Documentation:**
   - Update CLAUDE.md for implementation details
   - Update README.md for user-facing changes
   - Follow TECHNICAL_DOCS.md standards

### Context7 Usage

**ALWAYS use Context7 before coding with external libraries:**

```bash
mcp__context7__resolve-library-id → mcp__context7__get-library-docs
```

**Common libraries:**
- Shopify API: `/websites/shopify_dev`
- Requests: `/psf/requests`
- BeautifulSoup: `/wention/beautifulsoup4`
- Playwright: `/microsoft/playwright-python`
- Pandas: `/pandas-dev/pandas`

**Why:** Documentation changes frequently. Context7 provides current, accurate information.

### Task Completion Checklist

Before marking any coding task as complete:

- [ ] Read relevant shared-docs requirements
- [ ] Used Context7 for library documentation
- [ ] Code follows PROJECT_STRUCTURE_REQUIREMENTS.md
- [ ] Tests written and passing ✓
- [ ] Followed GIT_WORKFLOW.md completely
  - [ ] `git status` checked
  - [ ] Files staged with `git add`
  - [ ] Changes reviewed with `git diff --staged`
  - [ ] Committed with conventional format
  - [ ] Pushed to remote with `git push`
- [ ] Documentation updated (CLAUDE.md, README.md)

### Common Mistakes

**DO NOT:**
- Skip reading shared-docs requirements
- Code without Context7 for library docs
- Skip the testing phase
- Skip the git commit phase
- Forget to push commits
- Duplicate content from shared-docs

**DO:**
- Treat shared-docs as the authoritative source
- Reference shared-docs, don't duplicate them
- Follow GIT_WORKFLOW.md exactly
- Ask questions if requirements are unclear

---

## Project Overview

The Purinamills collector retrieves and enriches product data from Purina Mills websites for Shopify import. It's a sophisticated data collection system with dual-site support, intelligent fallback strategies, and comprehensive data enrichment.

**Target Sites:**
- **Primary**: shop.purinamills.com (Shopify e-commerce)
- **Secondary**: www.purinamills.com (Information/marketing site with PDFs)
- **Fallback**: UPCItemDB API (when product not found on manufacturer sites)

**Key Innovation:** This collector uses a 3-tier search strategy with automatic site switching and data merging, making it highly resilient to missing or incomplete product data.

---

## Architecture Overview

### Module Structure

```
purinamills/
├── gui.py                    # GUI entry point (thread-safe, queue-based)
├── main.py                   # CLI entry point (incomplete - use GUI)
├── config.json               # Auto-generated user configuration
│
├── src/                      # Core application modules
│   ├── __init__.py
│   ├── collector.py          # Main orchestration (99 lines)
│   ├── search.py             # 3-tier search with dual-site support (384 lines)
│   └── parser.py             # Dual-format HTML parsing (727 lines)
│
├── utils/                    # Project-specific utilities
│   ├── __init__.py
│   ├── shopify_output.py     # Shopify GraphQL format generation (715 lines)
│   └── image_quality.py      # Image assessment (UPCItemDB fallback only)
│
├── tests/                    # Test scripts
│   ├── test_workflow.py      # End-to-end workflow tests
│   └── test_variants.py      # Variant structure tests
│
├── input/                    # Input files (.gitignored)
├── output/                   # Output files (.gitignored)
├── logs/                     # Log files (.gitignored)
│
├── requirements.txt          # Core dependencies
├── requirements-gui.txt      # GUI dependencies (ttkbootstrap)
├── requirements-dev.txt      # Development tools (pytest, black, mypy)
│
├── README.md                 # User-facing documentation
└── CLAUDE.md                 # This file (AI assistant guidance)
```

### Design Principles

1. **Thin Orchestration Layer**: `collector.py` is only 99 lines - delegates to specialized modules
2. **Separation of Concerns**: Search, parsing, and output generation are independent modules
3. **Dual-Site Architecture**: Seamlessly handles two different site formats
4. **Thread-Safe GUI**: Queue-based communication prevents UI freezing
5. **Comprehensive Fallback**: 3-tier search + UPCItemDB fallback ensures maximum data coverage

---

## Core Modules

### 1. collector.py - Main Orchestration

**Purpose**: Thin wrapper that coordinates search and parsing operations.

**Key Components:**
- `SITE_CONFIG`: Embedded site configuration (origins, paths, timeouts, thresholds)
- `PurinamillsCollector`: Main class that delegates to searcher and parser

**Key Methods:**
```python
def find_product_url(upc, http_get, timeout, log, product_data) -> str:
    """Delegates to searcher.find_product_url()"""

def parse_page(html_text) -> Dict[str, Any]:
    """Delegates to parser.parse_page()"""
```

**Important Notes:**
- Only 99 lines - most logic is in specialized modules
- Config embedded in code (not external file)
- No business logic - pure delegation pattern

---

### 2. search.py - 3-Tier Search Strategy

**Purpose**: Implements intelligent product search across shop and www sites with fuzzy matching.

**Architecture:**
```
PurinamillsSearcher
├── _search_shop_site()        # HTTP search on shop.purinamills.com
├── _search_www_site()          # Playwright search on www.purinamills.com
├── _fetch_with_playwright()    # Headless Chromium browser
├── _keyword_set()              # Keyword extraction with stop words
└── _fuzzy_match_score()        # Similarity scoring algorithm
```

**3-Tier Search Strategy:**

1. **Exact Match (Shop Site)**
   - Search using `description_1` field
   - Look for exact string match in product names
   - Fast, accurate, no JavaScript required

2. **Fuzzy Match (Shop Site)**
   - Extract keywords from `description_1` or `upcitemdb_title`
   - Filter stop words (the, and, or, purina, mills, etc.)
   - Apply synonyms (equine→horse, bovine→cattle)
   - Score candidates based on keyword overlap
   - Return match if score ≥ threshold (default 0.3)

3. **WWW Site Fallback**
   - Use Playwright to render JavaScript-heavy www site
   - Same fuzzy matching algorithm
   - Provides additional product details + PDFs

**Playwright Integration:**
- **Why**: www.purinamills.com requires JavaScript rendering
- **How**: Launches headless Chromium browser
- **Wait Strategy**: `wait_until="networkidle"` ensures page fully loaded
- **Timeout**: 30 seconds default (configurable)

**Stop Words & Synonyms:**
```python
_common_stop = {
    "purina", "mills", "feed", "food", "formula", "complete",
    "with", "and", "for", "high", "fat", "balanced", "supplement",
    "horse", "equine", "active", "senior", "animal", "nutrition"
}

_syn = {
    "equine": "horse",
    "hen": "poultry",
    "chicken": "poultry"
}
```

**Configuration:**
- `fuzzy_match_threshold`: 0.3 (30% keyword overlap required)
- `max_search_candidates`: 10 (limit search results)

**Common Issues:**
- If no matches found: Check `description_1` field accuracy
- If wrong product matched: Lower threshold or improve product names
- If timeout errors: Increase timeout or check network
- If Playwright errors: Run `playwright install chromium`

---

### 3. parser.py - Dual-Format HTML Parsing

**Purpose**: Extracts comprehensive product data from both shop (Shopify) and www (WordPress) sites.

**Architecture:**
```
PurinamillsParser
├── parse_page()                      # Auto-detect site type and delegate
├── _detect_site_type()                # Identify shop vs www format
│
├── SHOP SITE (Shopify)
│   ├── _parse_shop_site()             # Main shop parser
│   ├── _extract_shop_images()         # Gallery images from thumbnails
│   ├── _extract_shop_variants()       # Size/option variants
│   ├── _extract_shop_variant_image_map()  # Variant-to-image mapping
│   └── _extract_shop_tab_content()    # Features, nutrients, directions
│
└── WWW SITE (WordPress/Custom)
    ├── _parse_www_site()              # Main www parser
    ├── _extract_www_images()          # Product images with filters
    └── _extract_www_documents()       # PDFs from accordion sections
```

**Site Detection:**
- Checks for "Shopify" markers in HTML
- Examines canonical URL (`<link rel="canonical">`)
- Checks OG URL meta tags
- Defaults to "shop" if uncertain

**Shop Site Parsing (Shopify):**

1. **Basic Info:**
   - Title: `<h1>` or `.product__title`
   - Description: JSON-LD structured data → DOM fallback
   - Brand: Extract from title (before ®)

2. **Images:**
   - **Primary**: Thumbnail gallery (`<ul class="thumbnail-list">`)
   - **Fallback**: JSON-LD `image` array
   - **Processing**: Remove size parameters (`_300x`) and query strings for full-size
   - **Normalization**: Convert to HTTPS, clean URLs

3. **Variant-Image Mapping:**
   - Extracts JavaScript product JSON from `<script>` tags
   - Maps variant options (50 LB, 25 LB, etc.) to image positions
   - Supports media types: image, external_video (YouTube/Vimeo), video
   - Returns `images_data` with variant associations

4. **Tab Content:**
   - Features & Benefits: Extracts `<ul>` lists or converts text to lists
   - Nutrients: Extracts `<table>` (Guaranteed Analysis)
   - Feeding Directions: Extracts `<ul>` or paragraphs

**WWW Site Parsing (WordPress):**

1. **Basic Info:**
   - Title: `<h1>` tag
   - Description: Meta description → DOM paragraphs with keywords
   - Brand: Extract from title (before ®)

2. **Images:**
   - Searches all `<img>` tags
   - Filters for product images (contains: product, feed, bag, amplify, etc.)
   - Excludes: logo, icon, favicon, banner, mic-w

3. **Accordion Content:**
   - Features & Benefits: `<ul class="accordion">` with "Features" title
     - Extracts `<h3>` + `<p>` structure
     - Formats as `<strong>Title</strong>: Description`
   - Guaranteed Analysis: Searches for table near "guaranteed analysis" text
   - Feeding Directions: Searches for `<ul>` near "feeding directions" text

4. **PDF Documents:**
   - Searches accordion for "Additional Materials" section
   - Identifies PDF links by:
     - Contains "getmedia" (CMS URLs)
     - Contains ".pdf" extension
   - Returns array: `[{title, url, type: 'pdf'}]`

**Output Format:**
```python
{
    "title": "Product Name",
    "brand_hint": "Purina",
    "description": "Product description...",
    "variants": [...],           # Shop site only
    "gallery_images": [...],     # Legacy field
    "images_data": {             # New field with variant mapping
        "images": [{
            "position": 1,
            "src": "https://...",
            "alt": "...",
            "media_type": "image",
            "variant_keys": ["50 LB||"]  # Which variants use this image
        }],
        "variant_image_map": {
            "50 LB||": {
                "position": 1,
                "src": "https://...",
                "options": {"option1": "50 LB", ...}
            }
        }
    },
    "features_benefits": "<ul>...</ul>",
    "nutrients": "<table>...</table>",
    "feeding_directions": "<ul>...</ul>",
    "documents": [{             # WWW site only
        "title": "Feeding Guide",
        "url": "https://.../document.pdf",
        "type": "pdf"
    }],
    "site_source": "shop" | "www"
}
```

**Important Notes:**
- Shop site uses HTTP requests (no JavaScript)
- WWW site requires Playwright (JavaScript rendering)
- Variant-image mapping enables per-variant image display in Shopify
- PDFs only extracted from www site (shop site doesn't have them)
- Clean URLs (remove size params, query strings) to get full-resolution images

---

### 4. shopify_output.py - Shopify GraphQL Format Generation

**Purpose**: Converts parsed product data into Shopify Admin API 2025-10 format.

**Key Functions:**
```
generate_shopify_product()      # Main generator
├── _format_body_html()         # Clean and format description
├── _clean_html()                # Remove scripts, styles, non-content
├── _normalize_size()            # Standardize weight/volume units
├── _parse_weight_from_size()    # Extract weight and unit from size strings
├── _generate_alt_tags()         # SEO-friendly alt text with filters
└── merge_www_data()            # Merge shop + www site data
```

**Variant Generation:**

Variants are built from input file structure:
- Parent product = first variant
- `option_1`, `option_2`, `option_3`, `option_4` fields define variant structure
- If no options defined but product has `size`, auto-use `size` as `option_1`

**Example:**
```
Input File:
- item_#: 001, size: "50 LB", option_1: "size"
- item_#: 002, size: "25 LB", option_1: "size", parent: 001

Output:
options: [
  {name: "Size", position: 1, values: ["50 LB", "25 LB"]}
]
variants: [
  {sku: "001", option1: "50 LB", price: "32.99", image_id: 1},
  {sku: "002", option1: "25 LB", price: "24.99", image_id: 2}
]
```

**Size Normalization:**
- Units remain uppercase: LB, OZ, KG, G, ML, L, GAL, CT, EA
- Other words use title case: Gallon, Pound, Each, Pack
- Examples:
  - "50 LB" → "50 LB"
  - "2 GALLON" → "2 Gallon"
  - "EACH" → "Each"

**Weight Parsing:**

Automatically extracts weight data from the `size` field in input file and populates variant weight fields:

- **Supported Units**: LB, LBS, OZ, KG, G (and variations: Pound, Ounce, Kilogram, Gram)
- **Automatic Conversion**: Calculates `grams` field for Shopify shipping calculations
- **Shopify-Compatible**: Outputs "lb", "oz", "kg", "g" as weight_unit
- **Conditional Fields**: Weight fields only included when successfully parsed (omitted if unknown)

Examples:
- "50 LB" → weight: 50, weight_unit: "lb", grams: 22680
- "16 OZ" → weight: 16, weight_unit: "oz", grams: 454
- "2.5 KG" → weight: 2.5, weight_unit: "kg", grams: 2500
- "500 G" → weight: 500, weight_unit: "g", grams: 500
- "EACH" → weight fields omitted (non-weight units ignored)
- Missing size → weight fields omitted (cleaner data, Shopify handles appropriately)

**Conversion Rates:**
- 1 lb = 453.592 grams
- 1 oz = 28.3495 grams
- 1 kg = 1000 grams
- 1 g = 1 gram

**Why Omit Instead of Zero:**
- More accurate: We don't know the weight, so don't claim it's 0
- Shopify treats weight fields as optional
- Prevents interference with shipping calculations
- Lets Shopify handle missing data appropriately

**Alt Tag Generation:**

Format: `"Product Name #OPTION1#OPTION2#OPTION3"`

- Enables Shopify variant image filtering
- Skips meaningless values: "EA", "Each", "None"
- Converts to uppercase with underscores
- Examples:
  - "Horse Feed #50_LB"
  - "Dog Food #20_LB#CHICKEN"
  - "Dog Bowl #PLASTIC" (skips "EA")

**Image Handling:**

1. **Variant-Specific Images:**
   - Uses `images_data` from parser
   - Maps images to variants via `image_id`
   - Generates per-variant alt tags

2. **Shared Images:**
   - Creates one entry per variant
   - Each entry has that variant's filter tags
   - Enables Shopify theme to filter images

3. **Legacy Mode:**
   - Falls back to `gallery_images` array
   - Uses first variant's options for alt tags

**Video Handling:**

- Videos extracted to separate `media` array
- Requires GraphQL API (can't use JSON import)
- Types supported:
  - `external_video`: YouTube, Vimeo (host + external_id)
  - `video`: Self-hosted videos (sources array)
- Videos NOT included in `images` array

**Metafields (Product-Level):**

```python
"metafields": [
    {
        "namespace": "custom",
        "key": "features",
        "value": "<ul>...</ul>",
        "type": "rich_text_field"
    },
    {
        "namespace": "custom",
        "key": "nutritional_information",
        "value": "<table>...</table>",
        "type": "rich_text_field"
    },
    {
        "namespace": "custom",
        "key": "directions",
        "value": "<ul>...</ul>",
        "type": "rich_text_field"
    },
    {
        "namespace": "custom",
        "key": "documentation",
        "value": "[{\"title\":\"...\",\"url\":\"...\"}]",
        "type": "json"
    }
]
```

**Metafields (Variant-Level):**

```python
"metafields": [
    {
        "namespace": "custom",
        "key": "model_number",
        "value": "ABC123",
        "type": "single_line_text_field"
    },
    {
        "namespace": "custom",
        "key": "size_info",
        "value": "{\"label\":\"50 LB\",\"weight\":\"50 LB\"}",
        "type": "json"
    }
]
```

**HTML Cleaning:**

Removes:
- Scripts, noscripts, iframes
- Images (handled in media array)
- Videos (handled in media array)
- Divs, spans (keeps content)
- Style, class, id attributes
- Event handlers (onclick, etc.)
- Data-* attributes
- Accessibility attributes (role, aria-*)

Preserves:
- Semantic tags: `<strong>`, `<em>`, `<ul>`, `<li>`, `<table>`, `<p>`
- Structure: Lists, tables, paragraphs

**Output Format (GraphQL 2025-10):**

```json
{
  "product": {
    "title": "Product Name",
    "descriptionHtml": "<p>...</p>",
    "vendor": "Purina",
    "status": "ACTIVE",
    "options": [...],
    "variants": [...],
    "images": [...],
    "metafields": [...],
    "media": [...]
  }
}
```

**Important Notes:**
- PDFs stored in metafields, NOT in media array
- Videos require GraphQL upload after product creation
- Variant image_id maps to image position
- Alt tags enable theme-based variant filtering

---

### 5. gui.py - Thread-Safe GUI

**Purpose**: Modern GUI for running the collector with real-time progress tracking.

**Architecture Pattern:** Follows `GUI_DESIGN_REQUIREMENTS.md` from shared-docs.

**Key Features:**

1. **Thread Safety:**
   - Worker thread for processing
   - Queue-based communication (status, buttons, messageboxes)
   - UI never freezes during long operations
   - `process_queues()` runs every 50ms in main thread

2. **Configuration:**
   - Auto-saves all settings to `config.json`
   - Persists window geometry
   - Remembers file paths, processing mode, record ranges

3. **Processing Modes:**
   - **Skip**: Skip products with existing manufacturer data
   - **Overwrite**: Reprocess all products

4. **Record Range:**
   - Start Record: First record to process (1-based)
   - End Record: Last record to process (blank = end)
   - Useful for testing or resuming interrupted runs

5. **Image Quality:**
   - Laplacian Threshold: Minimum sharpness for UPCItemDB images
   - Default: 100 (higher = stricter)
   - Only applies to UPCItemDB fallback images

6. **Real-Time Status:**
   - Live progress updates in status log
   - Console output (for VS Code terminal)
   - Queue-based updates (thread-safe)

7. **Error Handling:**
   - Graceful error messages
   - Failed products logged
   - Error report Excel file generated
   - Processing continues despite errors

**Configuration Structure:**

```json
{
  "INPUT_FILE": "/path/to/input.xlsx",
  "OUTPUT_FILE": "/path/to/output.json",
  "LOG_FILE": "logs/purinamills.log",
  "WINDOW_GEOMETRY": "900x900",
  "PROCESSING_MODE": "skip",
  "START_RECORD": "",
  "END_RECORD": "",
  "LAPLACIAN_THRESHOLD": 100,
  "COLLECTOR_NAME": "Purinamills",
  "COLLECTOR_ORIGIN": "https://shop.purinamills.com"
}
```

**Threading Model:**

```python
# Main Thread: UI operations only
def process_queues():
    """Processes messages from worker thread"""
    while True:
        msg = status_queue.get_nowait()
        status_log.insert("end", msg + "\n")
    app.after(50, process_queues)  # Schedule next check

# Worker Thread: All blocking operations
def worker():
    """Background processing"""
    try:
        status_queue.put("Processing...")
        # ... do work ...
        messagebox_queue.put(("info", "Success", "Done!"))
    finally:
        button_control_queue.put("enable_buttons")
```

**Important Notes:**
- **NEVER** call tkinter from worker thread
- **ALWAYS** use queues for UI updates
- **ALWAYS** re-enable buttons in `finally` block
- Messageboxes must be queued (tkinter requires main thread)

---

## Data Flow

### Complete Processing Workflow

```
1. Load Input File
   ├── Excel (.xlsx) or JSON (.json)
   ├── Parse UPCs, descriptions, parent/variant relationships
   └── Group by parent field

2. For Each Product Group:

   A. Check Skip Mode
      ├── Load existing output file
      ├── Check if product already has manufacturer data
      └── Skip if found, continue if not

   B. Search for Product URL (3-tier strategy)
      ├── Tier 1: Exact match on shop site (description_1)
      ├── Tier 2: Fuzzy match on shop site (keywords)
      └── Tier 3: Fallback to www site (Playwright)

   C. If Product Found:
      ├── Fetch product page (HTTP or Playwright)
      ├── Parse HTML (auto-detect shop vs www)
      ├── Extract: title, brand, description, images, PDFs
      ├── If shop site + minimal data: fetch www site for PDFs
      └── Merge shop + www data

   D. If Product NOT Found:
      ├── Check UPCItemDB fallback status
      ├── If available: Load placeholder images
      ├── Select best image (quality assessment)
      ├── Create fallback product data
      └── Skip if no fallback available

   E. Generate Shopify Output
      ├── Build variants from input file structure
      ├── Map variant images using image_id
      ├── Generate alt tags with filter hashtags
      ├── Clean HTML for Shopify
      ├── Create metafields (features, nutrients, directions, docs)
      └── Separate videos into media array

   F. Rate Limiting
      └── Sleep 200-700ms (jitter)

3. Output Generation
   ├── Wrap in {"products": [...]} structure
   ├── Write JSON to output file
   ├── Generate error report (_errors.xlsx)
   └── Display summary statistics
```

### UPCItemDB Fallback Flow

When product not found on manufacturer sites:

```
1. Check UPCItemDB Status
   └── upcitemdb_status field

2. If "Match found":
   ├── Parse upcitemdb_images field (string → array)
   ├── Load placeholder images for detection
   ├── Download and assess each candidate:
   │   ├── Calculate Laplacian variance (sharpness)
   │   ├── Calculate perceptual hash (placeholder detection)
   │   ├── Crop whitespace borders
   │   └── Score based on dimensions + quality
   ├── Select best image (or reject if too low quality)
   └── Create fallback product data:
       ├── title: description_1
       ├── description: upcitemdb_description
       ├── vendor: "Purina"
       ├── gallery_images: [best_url]
       └── site_source: "upcitemdb"

3. If "Lookup failed":
   └── Add to failed_records (no data available)
```

**Important Notes:**
- Image quality assessment ONLY for UPCItemDB images
- Manufacturer images used as-is (no quality checks)
- Placeholders filtered via perceptual hashing
- Configurable Laplacian threshold (default: 100)

---

## Setup Instructions

### Prerequisites

- Python 3.12.9
- pyenv (recommended for virtual environment)
- Git (for repository access)

### Installation Steps

```bash
# 1. Navigate to project directory
cd /Users/moosemarketer/Code/garoppos/collectors/purinamills

# 2. Set up Python virtual environment
pyenv local purinamills
# Or create new environment:
pyenv virtualenv 3.12.9 purinamills
pyenv local purinamills

# 3. Install core dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers (REQUIRED for www site)
playwright install chromium

# 5. Install GUI dependencies (OPTIONAL - for GUI mode)
pip install -r requirements-gui.txt

# 6. Install development tools (OPTIONAL - for development)
pip install -r requirements-dev.txt

# 7. Verify installation
python gui.py
```

### Requirements Files

**requirements.txt** (Core):
```
requests>=2.31.0           # HTTP requests for shop site
beautifulsoup4>=4.12.0     # HTML parsing
lxml>=4.9.0                # Fast XML/HTML parsing
ttkbootstrap>=1.10.1       # Modern themed Tkinter widgets
openpyxl>=3.1.0            # Excel file reading
playwright>=1.40.0         # Headless browser for www site
Pillow>=10.0.0             # Image processing
opencv-python>=4.8.0       # Image quality assessment
numpy>=1.24.0              # Numerical operations
imagehash>=4.3.0           # Perceptual hashing
```

**requirements-gui.txt** (GUI):
```
ttkbootstrap>=1.10.1       # Modern themed Tkinter widgets
```

**requirements-dev.txt** (Development):
```
-r requirements.txt        # Include core dependencies
pytest>=7.4.0              # Testing framework
pytest-cov>=4.1.0          # Coverage reporting
pytest-mock>=3.11.0        # Mocking for tests
black>=23.7.0              # Code formatting
flake8>=6.1.0              # Linting
mypy>=1.5.0                # Type checking
```

### Playwright Setup

**IMPORTANT:** Playwright requires browser installation:

```bash
# Install Chromium browser
playwright install chromium

# Verify installation
playwright install --help

# Check browser path
playwright --version
```

**Why Playwright?**
- www.purinamills.com requires JavaScript rendering
- Headless Chromium handles dynamic content
- Waits for "networkidle" to ensure page fully loaded

**Common Issues:**
- "Browser not found": Run `playwright install chromium`
- "Timeout": Increase timeout in `SITE_CONFIG`
- "Connection refused": Check network/firewall

---

## Common Tasks

### Running the Collector

**GUI Mode (Recommended):**
```bash
python gui.py
```

**CLI Mode (Incomplete - Use GUI):**
```bash
python main.py --input input/products.xlsx --output output/products.json
```
Note: CLI is skeleton only. Use GUI for full functionality.

**Python API:**
```python
from src.collector import PurinamillsCollector
import requests

collector = PurinamillsCollector()

# Find product
product_url = collector.find_product_url(
    upc="012345678901",
    http_get=requests.get,
    timeout=30,
    log=print,
    product_data={"description_1": "Premium Horse Feed 50 lb"}
)

# Parse page
html = requests.get(product_url).text
parsed_data = collector.parse_page(html)

# Generate Shopify output
from utils.shopify_output import generate_shopify_product
shopify_product = generate_shopify_product(
    parsed_data=parsed_data,
    input_data={"item_#": "001", "size": "50 LB", ...},
    variant_data=[],
    log=print
)
```

### Processing Strategies

**Test Run (Small Dataset):**
```
1. Set Start Record: 1
2. Set End Record: 10
3. Select "Overwrite All Records"
4. Click "Start Processing"
5. Review output quality
```

**Full Run (Production):**
```
1. Clear Start/End Record (process all)
2. Select "Skip Processed Records"
3. Click "Start Processing"
4. Check error report for failures
```

**Resume Interrupted Run:**
```
1. Use "Skip" mode
2. Existing products are detected and skipped
3. Only new/failed products processed
```

**Reprocess Updated Products:**
```
1. Use "Overwrite" mode
2. All products reprocessed
3. Existing output replaced
```

### Testing

**End-to-End Test:**
```bash
python tests/test_workflow.py
```

**Variant Structure Test:**
```bash
python tests/test_variants.py
```

**Search Functionality Test:**
```bash
python tests/test_www_search.py
```

### Code Quality

**Format Code:**
```bash
black src/ utils/ tests/
```

**Lint Code:**
```bash
flake8 src/ utils/ tests/
```

**Type Check:**
```bash
mypy src/
```

---

## Configuration

### Site Configuration (Embedded in collector.py)

```python
SITE_CONFIG = {
    "site_key": "purinamills",

    # Primary e-commerce site (Shopify)
    "shop_origin": "https://shop.purinamills.com",
    "shop_search_path": "/search",
    "shop_search_param": "q",

    # Secondary information site (fallback)
    "www_origin": "https://www.purinamills.com",
    "www_search_path": "/search",
    "www_search_param": "s",

    # Legacy compatibility
    "origin": "https://shop.purinamills.com",
    "referer": "https://shop.purinamills.com/",

    # HTTP settings
    "user_agent": "Mozilla/5.0 ...",
    "fetch_jitter_min_ms": 200,
    "fetch_jitter_max_ms": 700,
    "timeout": 30,

    # Search settings
    "max_search_candidates": 10,
    "fuzzy_match_threshold": 0.3
}
```

**Configuration Notes:**
- Embedded in code (not external config file)
- Shop site = primary (fast, no JavaScript)
- WWW site = fallback (Playwright required)
- Jitter prevents rate limiting
- Threshold 0.3 = 30% keyword overlap required

### User Configuration (config.json)

Auto-generated by GUI:
```json
{
  "INPUT_FILE": "/path/to/input.xlsx",
  "OUTPUT_FILE": "/path/to/output.json",
  "LOG_FILE": "logs/purinamills.log",
  "WINDOW_GEOMETRY": "900x900",
  "PROCESSING_MODE": "skip",
  "START_RECORD": "",
  "END_RECORD": "",
  "LAPLACIAN_THRESHOLD": 100
}
```

---

## Important Implementation Details

### 1. Dual-Site Architecture

**Shop Site (shop.purinamills.com):**
- Shopify e-commerce platform
- Fast HTTP requests (no JavaScript)
- JSON-LD structured data
- Variant support with images
- Clean product data

**WWW Site (www.purinamills.com):**
- WordPress/custom CMS
- Requires Playwright (JavaScript rendering)
- Accordion-based content
- PDF documents in "Additional Materials"
- Marketing-focused descriptions

**Why Both?**
- Shop site: Fast, accurate product data
- WWW site: Additional details, technical documentation
- Fallback: If shop site missing, use www site
- Merge: Combine best of both sources

### 2. 3-Tier Search Strategy

**Tier 1: Exact Match (Shop Site)**
- Search URL: `/search?q={description_1}`
- Look for exact string in product names
- Fastest, most accurate
- No keyword processing needed

**Tier 2: Fuzzy Match (Shop Site)**
- Extract keywords from `description_1` or `upcitemdb_title`
- Filter stop words (purina, mills, feed, etc.)
- Apply synonyms (equine→horse)
- Score based on keyword overlap
- Return if score ≥ 0.3 (configurable)

**Tier 3: WWW Site Fallback**
- Same fuzzy matching algorithm
- Uses Playwright for JavaScript rendering
- Slower but more comprehensive
- Provides PDFs not available on shop site

**Why This Works:**
- Exact match catches 80%+ of products (fast)
- Fuzzy match handles variations (robust)
- WWW fallback ensures maximum coverage

### 3. Variant-Image Mapping

**Problem:** Shopify themes need to show correct image for selected variant.

**Solution:** Extract variant-to-image mapping from Shopify product JSON:

```javascript
// Shop site embeds product data:
var product = {
  variants: [
    {
      id: 123,
      option1: "50 LB",
      featured_image: {position: 1, src: "..."}
    },
    {
      id: 124,
      option1: "25 LB",
      featured_image: {position: 2, src: "..."}
    }
  ]
}
```

**Parser extracts:**
```python
variant_image_map = {
  "50 LB||": {
    "position": 1,
    "src": "https://...",
    "options": {"option1": "50 LB", "option2": "", "option3": ""}
  },
  "25 LB||": {
    "position": 2,
    "src": "https://...",
    "options": {"option1": "25 LB", "option2": "", "option3": ""}
  }
}
```

**Output generator uses:**
```python
variant = {
  "sku": "001",
  "option1": "50 LB",
  "image_id": 1  # Maps to position in images array
}
```

**Result:** Shopify theme displays correct image when variant selected.

### 4. Alt Tag Filter System

**Format:** `"Product Name #OPTION1#OPTION2#OPTION3"`

**Why Hashtags?**
- Shopify themes can filter images by alt text
- Hashtags enable programmatic variant detection
- SEO-friendly (product name + descriptive tags)

**Algorithm:**
1. Start with product name
2. Extract variant options (size, flavor, material)
3. Skip meaningless values ("EA", "Each", "None")
4. Convert to uppercase, replace spaces with underscores
5. Prepend with `#`

**Examples:**
```
"Premium Horse Feed #50_LB"
"Dog Food #20_LB#CHICKEN"
"Dog Bowl #PLASTIC"  (skips "EA" unit)
```

**Shopify Theme Usage:**
```javascript
// Filter images by variant selection
const variantTag = `#${selectedSize.replace(' ', '_')}`;
const matchingImages = images.filter(img => img.alt.includes(variantTag));
```

### 5. PDF Document Extraction

**Source:** WWW site "Additional Materials" accordion

**HTML Structure:**
```html
<ul class="accordion pd banner-accordion">
  <li class="accordion-item">
    <a class="accordion-title">Additional Materials</a>
    <div class="accordion-content">
      <p><a href="/getmedia/abc123.pdf">Feeding Guide PDF</a></p>
      <p><a href="/getmedia/xyz789.pdf">Nutrition Facts PDF</a></p>
    </div>
  </li>
</ul>
```

**Extraction:**
1. Find `<ul class="accordion">`
2. Locate accordion item with "Additional Materials" title
3. Extract all links from content div
4. Filter for document URLs:
   - Contains "getmedia" (CMS document URLs)
   - Contains ".pdf" extension
5. Deduplicate URLs

**Output:**
```json
"documents": [
  {
    "title": "Feeding Guide PDF",
    "url": "https://www.purinamills.com/getmedia/abc123.pdf",
    "type": "pdf"
  }
]
```

**Storage:**
- Shopify metafield: `custom.documentation`
- Type: JSON
- NOT in media array (PDFs are documents, not media)

### 6. Image Quality Assessment (UPCItemDB Only)

**IMPORTANT:** Only applies to UPCItemDB fallback images. Manufacturer images used as-is.

**Metrics:**
1. **Laplacian Variance (Sharpness):**
   - Measures edge definition
   - Higher = sharper image
   - Threshold: 100 (configurable)
   - Formula: `cv2.Laplacian(gray, cv2.CV_64F).var()`

2. **Perceptual Hashing (Placeholder Detection):**
   - Compares against known placeholders
   - Hamming distance < 10 = placeholder
   - Uses imagehash library (pHash algorithm)

3. **Dimensions:**
   - Prefers larger images
   - Minimum acceptable: 200x200
   - Bonus for images > 500x500

**Process:**
```
For each UPCItemDB image:
  1. Download image
  2. Crop whitespace borders
  3. Calculate Laplacian score
  4. Calculate perceptual hash
  5. Compare to placeholder images
  6. Score = (laplacian * 0.5) + (dimensions * 0.3) + (not_placeholder * 0.2)
  7. Select highest scoring image
  8. Reject if score < threshold
```

**Why Not Manufacturer Images?**
- Manufacturer images are authoritative
- Already optimized for e-commerce
- No placeholders from manufacturers
- Quality assessment would be unnecessary overhead

### 7. Thread-Safe GUI Pattern

**Problem:** Long operations freeze Tkinter GUI.

**Solution:** Queue-based worker thread pattern.

**Architecture:**
```
Main Thread (UI):
├── Tkinter event loop
├── process_queues() every 50ms
├── Update status log
├── Control buttons
└── Show messageboxes

Worker Thread (Processing):
├── Load input file
├── Search for products
├── Parse HTML
├── Generate output
└── Queue status messages
```

**Communication:**
```python
# Worker → Main Thread
status_queue.put("Processing product 1...")
button_control_queue.put("enable_buttons")
messagebox_queue.put(("info", "Success", "Done!"))

# Main Thread processes queues
def process_queues():
    while True:
        try:
            msg = status_queue.get_nowait()
            status_log.insert("end", msg + "\n")
        except queue.Empty:
            break
    app.after(50, process_queues)
```

**Critical Rules:**
- **NEVER** call tkinter from worker thread
- **ALWAYS** use queues for updates
- **ALWAYS** re-enable buttons in finally block
- Messageboxes MUST be queued (tkinter requirement)

### 8. GraphQL 2025-10 Format

**Key Changes from REST API:**
- `descriptionHtml` instead of `body_html`
- `status` ("ACTIVE") instead of `published` (boolean)
- Videos require separate GraphQL mutations
- Metafields use namespace/key structure

**Product Structure:**
```json
{
  "product": {
    "title": "...",
    "descriptionHtml": "<p>...</p>",
    "status": "ACTIVE",
    "vendor": "Purina",
    "options": [...],
    "variants": [...],
    "images": [...],
    "metafields": [...],
    "media": [...]  // Videos only
  }
}
```

**Video Upload Process:**
1. Create product (without videos)
2. Call `productCreateMedia` mutation for each video
3. Call `productVariantAppendMedia` to associate with variants

**Why Separate?**
- Videos require file upload or external URL
- Can't be included in JSON import
- GraphQL provides better video control

---

## Troubleshooting

### Product Not Found

**Symptoms:**
- "No results found for product"
- Empty product_url

**Causes & Solutions:**

1. **Inaccurate description_1:**
   - Check product name on shop.purinamills.com
   - Update description_1 to match exactly
   - Include size if part of product name

2. **Product doesn't exist:**
   - Verify product is on shop or www site
   - Check for spelling variations
   - Try searching manually on site

3. **Site blocking requests:**
   - Check network connectivity
   - Verify user agent string
   - Increase rate limiting jitter

4. **Threshold too high:**
   - Lower `fuzzy_match_threshold` from 0.3 to 0.2
   - Add more keywords to product name
   - Use synonyms in product description

### Image Quality Too Low (UPCItemDB Only)

**Symptoms:**
- "No suitable UPCItemDB images found"
- All images rejected

**IMPORTANT:** This only affects UPCItemDB fallback images. Manufacturer images are never rejected.

**Solutions:**

1. **Lower Laplacian threshold:**
   - Default: 100
   - Try: 50 or 75
   - Accessible in GUI

2. **Check placeholder images:**
   - Verify `placeholder_images/` directory exists
   - Ensure known placeholders are loaded
   - Add new placeholders if needed

3. **UPCItemDB image quality:**
   - Some products have low-res images
   - No solution (inherent to UPCItemDB)
   - Consider manual image upload

4. **Product found on manufacturer site:**
   - This issue doesn't occur
   - Manufacturer images always used

### Playwright Errors

**Symptoms:**
- "Browser not found"
- Timeout errors
- Connection refused

**Solutions:**

1. **Browser not installed:**
```bash
playwright install chromium
```

2. **Timeout too short:**
   - Increase in `SITE_CONFIG["timeout"]`
   - Default: 30 seconds
   - Try: 60 seconds

3. **Network issues:**
   - Check firewall settings
   - Verify site is accessible
   - Try manual navigation in browser

4. **JavaScript errors:**
   - Site may have changed structure
   - Check browser console for errors
   - May need parser updates

### Variant Structure Incorrect

**Symptoms:**
- Wrong number of variants
- Missing variant data
- Incorrect parent/child relationships

**Causes & Solutions:**

1. **Missing parent field:**
   - Verify `parent` field in input file
   - Parent should reference parent item_#
   - Parent product must have `parent == item_#`

2. **Parent not in input:**
   - Ensure parent product is included
   - Parent must be processed before children
   - Check input file filtering

3. **Option fields not set:**
   - Define `option_1`, `option_2`, etc. in parent
   - All variants inherit option structure
   - Options map to input file fields (e.g., "size")

4. **UPC mismatch:**
   - Verify UPCs are consistent
   - Check for leading zeros
   - Ensure UPCs are strings, not numbers

### GUI Freezes or Crashes

**Symptoms:**
- UI becomes unresponsive
- Application hangs
- No error message

**Solutions:**

1. **Check logs:**
```bash
tail -f logs/purinamills.log
```

2. **Python/Tk version:**
   - Ensure Python 3.12.9
   - Update Tk: `brew upgrade python-tk@3.12`
   - Verify ttkbootstrap version

3. **Thread issues:**
   - Check for tkinter calls in worker thread
   - Ensure queues are being processed
   - Verify button re-enabling in finally block

4. **Use CLI mode:**
```bash
python main.py --input input.xlsx --output output.json
```
Note: CLI is incomplete, but may help debug

### Rate Limiting / Blocking

**Symptoms:**
- 429 Too Many Requests
- Connection refused
- Slow responses

**Solutions:**

1. **Increase jitter:**
   - Raise `fetch_jitter_max_ms` to 1000+
   - Add random delay variation
   - Respect site rate limits

2. **User agent:**
   - Verify user agent string is valid
   - Update to latest Chrome version
   - Add referer header

3. **IP blocking:**
   - Use VPN or proxy
   - Wait 1 hour and retry
   - Contact site administrator

4. **Concurrent requests:**
   - Ensure single-threaded processing
   - Don't run multiple instances
   - Check for other scrapers

---

## Shared Dependencies

The purinamills collector imports utilities from `../shared/`:

```python
from shared.src.excel_utils import load_products
from shared.src.text_only import text_only
from shared.src.image_quality import (
    load_placeholder_images,
    select_best_image
)
```

**Key Shared Modules:**

1. **excel_utils.py:**
   - `load_products()`: Loads Excel or JSON files
   - Handles both `.xlsx` and `.json` formats
   - Returns list of product dictionaries
   - Normalizes column names

2. **text_only.py:**
   - `text_only()`: Decodes HTML entities
   - Converts `&amp;` → `&`, `&reg;` → `®`
   - Cleans text for display

3. **image_quality.py:**
   - `load_placeholder_images()`: Loads known placeholders
   - `select_best_image()`: Assesses image quality
   - `calculate_laplacian_score()`: Sharpness detection
   - `is_placeholder()`: Perceptual hashing detection
   - `crop_whitespace()`: Border removal

**Shared Documentation:**

Reference these files for cross-project requirements:
- `shared-docs/INPUT_FILE_STRUCTURE.md`: Input file format
- `shared-docs/UPCITEMDB_FALLBACK_REQUIREMENTS.md`: UPCItemDB usage
- `shared-docs/GUI_DESIGN_REQUIREMENTS.md`: GUI patterns

**Important Notes:**
- Always follow shared guidelines
- Don't duplicate shared utilities
- Contribute improvements back to shared
- Keep interfaces consistent across projects

---

## Input File Format

**Supported Formats:**
- Excel: `.xlsx`, `.xlsm`
- JSON: `.json`

**Required Fields:**
- `upc` or `upc_updated`: Product barcode
- `description_1`: Product name (primary search field)
- `item_#`: SKU/item number

**Optional Fields:**
- `upcitemdb_title`: Alternative search name
- `upcitemdb_status`: "Match found" or "Lookup failed"
- `upcitemdb_images`: Array of image URLs (string or list)
- `upcitemdb_description`: Fallback description
- `parent`: Parent item_# for variant products
- `option_1`, `option_2`, `option_3`, `option_4`: Variant option fields
- `size`: Variant size (auto-used as option_1 if no options defined)
- `sold_ext_price_adj`: Variant price
- `sold_ext_cost_adj`: Variant cost
- `inventory_qty`: Inventory quantity
- `sku`: Barcode for Shopify (distinct from item_#)

**Parent/Variant Structure:**

```excel
item_#  | description_1              | size   | parent | option_1
--------|----------------------------|--------|--------|----------
001     | Premium Horse Feed 50 lb   | 50 LB  | 001    | size
002     | Premium Horse Feed 25 lb   | 25 LB  | 001    | size
003     | Premium Dog Food           | 20 LB  |        | size
```

**Notes:**
- Parent = item_# means this is the parent product
- Parent = different item_# means this is a child variant
- Blank parent = standalone product (no variants)

**Example JSON:**
```json
[
  {
    "upc": "012345678901",
    "description_1": "Premium Horse Feed 50 lb",
    "item_#": "001",
    "parent": "001",
    "option_1": "size",
    "size": "50 LB",
    "sold_ext_price_adj": "$32.99",
    "inventory_qty": 100
  },
  {
    "upc": "012345678902",
    "description_1": "Premium Horse Feed 25 lb",
    "item_#": "002",
    "parent": "001",
    "option_1": "size",
    "size": "25 LB",
    "sold_ext_price_adj": "$24.99",
    "inventory_qty": 50
  }
]
```

---

## Output File Format

**Format:** Shopify Admin API 2025-10 GraphQL-compatible JSON

**Structure:**
```json
{
  "products": [
    {
      "product": {
        "title": "Premium Horse Feed",
        "descriptionHtml": "<p>High-quality horse feed...</p>",
        "vendor": "Purina",
        "status": "ACTIVE",
        "options": [
          {
            "name": "Size",
            "position": 1,
            "values": ["50 LB", "25 LB"]
          }
        ],
        "variants": [
          {
            "sku": "001",
            "option1": "50 LB",
            "price": "32.99",
            "cost": "20.00",
            "position": 1,
            "barcode": "012345678901",
            "inventory_quantity": 100,
            "image_id": 1,
            "metafields": [...]
          },
          {
            "sku": "002",
            "option1": "25 LB",
            "price": "24.99",
            "cost": "15.00",
            "position": 2,
            "barcode": "012345678902",
            "inventory_quantity": 50,
            "image_id": 2,
            "metafields": [...]
          }
        ],
        "images": [
          {
            "position": 1,
            "src": "https://shop.purinamills.com/.../image1.jpg",
            "alt": "Premium Horse Feed #50_LB"
          },
          {
            "position": 2,
            "src": "https://shop.purinamills.com/.../image2.jpg",
            "alt": "Premium Horse Feed #25_LB"
          }
        ],
        "metafields": [
          {
            "namespace": "custom",
            "key": "features",
            "value": "<ul><li>Feature 1</li></ul>",
            "type": "rich_text_field"
          },
          {
            "namespace": "custom",
            "key": "nutritional_information",
            "value": "<table>...</table>",
            "type": "rich_text_field"
          },
          {
            "namespace": "custom",
            "key": "documentation",
            "value": "[{\"title\":\"Feeding Guide\",\"url\":\"https://...\"}]",
            "type": "json"
          }
        ],
        "media": [
          {
            "alt": "Product Video",
            "media_content_type": "EXTERNAL_VIDEO",
            "original_source": "https://www.youtube.com/watch?v=...",
            "host": "YOUTUBE",
            "external_id": "..."
          }
        ]
      }
    }
  ]
}
```

**Error Report (_errors.xlsx):**

Generated alongside output file for failed products:
- All original input fields
- Added field: `error_reason`
- One row per failed product
- Easy to re-import after fixing issues

---

## Best Practices

### Input File Preparation

1. **Accurate Product Names:**
   - Use exact names from shop.purinamills.com
   - Include variant size in name if part of product name
   - Example: "Premium Horse Feed 50 lb" not just "Horse Feed"

2. **Complete UPCItemDB Data:**
   - Always include `upcitemdb_status` field
   - Pre-populate `upcitemdb_images` when available
   - Include `upcitemdb_description` for fallback

3. **Clean Parent/Variant Structure:**
   - Parent product must come first in file
   - Set parent = item_# for parent product
   - Set parent = parent_item_# for variants

4. **Option Fields:**
   - Define `option_1`, `option_2`, etc. in parent product
   - Use meaningful field names (size, color, flavor)
   - Ensure all variants have values for option fields

### Processing Strategies

1. **Test First:**
   - Always test with 10-20 products first
   - Review output quality before full run
   - Check error report for common issues

2. **Use Skip Mode:**
   - Resume interrupted runs without reprocessing
   - Only new/failed products are processed
   - Saves time on large datasets

3. **Monitor Errors:**
   - Check error report after each run
   - Fix input data issues
   - Re-run failed products

4. **Batch Processing:**
   - Process 100-500 products at a time
   - Prevents memory issues
   - Easier to track progress

### Performance Optimization

1. **Rate Limiting:**
   - Respect site rate limits
   - Increase jitter if getting blocked
   - Don't run multiple instances

2. **Playwright Performance:**
   - WWW site is slower (JavaScript)
   - Prefer shop site when possible
   - Consider pre-filtering products

3. **Image Quality:**
   - Adjust Laplacian threshold based on results
   - Lower threshold accepts more images
   - Higher threshold rejects low-quality images

4. **Memory Management:**
   - Process in batches
   - Clear browser cache periodically
   - Restart on memory errors

### Code Maintenance

1. **Follow Shared Guidelines:**
   - Always reference `shared-docs/` requirements
   - Don't duplicate shared utilities
   - Keep interfaces consistent

2. **Document Changes:**
   - Update README.md for user-facing changes
   - Update CLAUDE.md for implementation changes
   - Add comments for complex logic

3. **Test Before Commit:**
   - Run test suite
   - Verify GUI still works
   - Check with sample products

4. **Code Quality:**
   - Run black for formatting
   - Run flake8 for linting
   - Run mypy for type checking

---

## Notes for AI Assistants

### When Working on This Project

1. **Reference Implementation:**
   - This is the most complete collector
   - Use as template for new collectors
   - Copy patterns, not just code

2. **Architecture Understanding:**
   - Thin orchestration (collector.py)
   - Specialized modules (search, parser, output)
   - Shared utilities (don't duplicate)
   - Queue-based GUI (thread safety)

3. **Common Modifications:**
   - Adding new search strategies: Edit `search.py`
   - Parsing new fields: Edit `parser.py`
   - Changing output format: Edit `shopify_output.py`
   - GUI changes: Edit `gui.py` (maintain thread safety!)

4. **Testing Changes:**
   - Always test with real products
   - Verify both shop and www site parsing
   - Check variant structure
   - Ensure GUI doesn't freeze

5. **Documentation:**
   - Update README.md for user-facing changes
   - Update CLAUDE.md for implementation details
   - Add docstrings for new functions
   - Comment complex algorithms

### Common Pitfalls

1. **Breaking Thread Safety:**
   - Don't call tkinter from worker thread
   - Always use queues for UI updates
   - Don't forget finally block for re-enabling buttons

2. **Ignoring Shared Guidelines:**
   - Always check `shared-docs/` first
   - Follow INPUT_FILE_STRUCTURE.md
   - Follow GUI_DESIGN_REQUIREMENTS.md
   - Follow UPCITEMDB_FALLBACK_REQUIREMENTS.md

3. **Hardcoding Configuration:**
   - Use `SITE_CONFIG` for site-specific settings
   - Use `config.json` for user settings
   - Don't hardcode paths or URLs

4. **Incomplete Error Handling:**
   - Always handle Playwright timeouts
   - Catch and log all exceptions
   - Add products to failed_records
   - Don't let one failure stop processing

5. **Image Quality Confusion:**
   - Remember: Quality checks ONLY for UPCItemDB
   - Manufacturer images always used as-is
   - Don't reject manufacturer images

### Code Review Checklist

- [ ] Follows shared guidelines
- [ ] Thread-safe (if GUI changes)
- [ ] Handles errors gracefully
- [ ] Logs useful debugging info
- [ ] Doesn't duplicate shared code
- [ ] Tested with real products
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Code formatted (black)
- [ ] No hardcoded values

---

## Support

For questions or issues:
1. Check this document first
2. Review `README.md` for user-facing info
3. Check `shared-docs/` for cross-project requirements
4. Review code comments for implementation details
5. Contact development team if needed

---

## License

Internal tool - Not for public distribution.

---

**Last Updated:** 2025-01-07

**Version:** 1.0.0

**Maintainer:** Development Team

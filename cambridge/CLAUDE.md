# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Cambridge Product Collector - Development Guide

## Overview

The Cambridge collector scrapes product data from two sources:
1. **Public website** (`www.cambridgepavers.com`) - lifestyle images, descriptions, specifications
2. **Dealer portal** (`shop.cambridgepavers.com`) - product images, pricing, SKUs (requires auth)

Products are matched by **title + color** from the input Excel file, grouped into variant families, and output in Shopify GraphQL 2025-10 format.

---

## Common Commands

### Running the Collector

```bash
# CLI mode (requires config.json)
python3 main.py

# GUI mode (recommended)
python3 gui.py
```

### Testing

```bash
# Run fast tests only (~5-10 seconds)
./run_tests.sh

# Run full test suite including slow network tests (~5 minutes)
./run_tests.sh --all

# Run individual test files
python3 tests/test_parsers.py           # Parser and search tests (fast)
python3 tests/test_portal_search.py     # Portal search tests (fast)
python3 tests/test_index_builder.py     # Public index building (slow)
python3 tests/test_portal_index_builder.py  # Portal index building (slow)
python3 tests/test_workflow.py          # End-to-end workflow (moderate)
```

### Index Management

```bash
# Rebuild public product index (crawls www.cambridgepavers.com)
python3 scripts/build_index.py

# Rebuild portal product index (queries shop.cambridgepavers.com API)
python3 scripts/build_portal_index.py

# Inspect cached indexes
cat cache/product_index.json | jq '.total_products'
cat cache/portal_product_index.json | jq '.total_products'
```

### Development Environment

```bash
# Activate pyenv virtualenv (if not auto-activated)
pyenv activate cambridge

# Verify environment
python --version  # Should show Python 3.12.9

# Install/update dependencies
pip install -r requirements.txt          # Core dependencies
pip install -r requirements-gui.txt      # GUI dependencies
pip install -r requirements-dev.txt      # Development tools

# Install Playwright browsers (required for portal scraping)
playwright install chromium
```

---

## Architecture

### Data Flow

```
1. Load Excel Input
   ↓
2. Build/Load TWO Product Indexes (both cached):
   a. Public Index (www.cambridgepavers.com) - 60 products
   b. Portal Index (shop.cambridgepavers.com) - 362 products via API
   ↓
3. Group Records by Title (variant families)
   ↓
4. For each product family:
   a. Search PUBLIC index for product URL (fuzzy match on title)
   b. IF FOUND: Collect public website data (Playwright for gallery images)
      IF NOT FOUND: Set portal-only flag, skip public data
   c. For each color variant:
      - Search PORTAL index by title + color
      - IF NOT FOUND and title_alt exists: Try again with title_alt
      - Collect dealer portal data (authenticated)
   d. IF portal-only and no portal data: Skip product (failure)
      ELSE: Generate Shopify product with variants
   ↓
5. Save JSON Output + Report (failures and warnings)
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `collector.py` | Main orchestration, HTTP session management, coordinates both indexes |
| `index_builder.py` | Crawls public site, builds searchable index (60 products) |
| `portal_index_builder.py` | **Two-stage API**: fetches categories, then queries search API per category (362 products) |
| `search.py` | Fuzzy matching against cached public index |
| `portal_search.py` | Exact matching against cached portal index (title + color) |
| `public_parser.py` | Parses public website HTML (BeautifulSoup + Playwright for gallery) |
| `portal_parser.py` | Parses dealer portal (Playwright + BeautifulSoup) |
| `product_generator.py` | Groups variants, generates Shopify products with multiple unit_of_sale options |
| `processor.py` | Main workflow, file I/O, error handling |
| `config.py` | Configuration management, auto-save |

---

## Key Design Decisions

### 1. Dual Product Index Architecture

**Why:** Public site has limited products (60), portal has full catalog (1000+) with SKUs/prices per color

**Implementation:**
- **Public Index** (`cache/product_index.json`):
  - Crawls category pages on www.cambridgepavers.com
  - Extracts `prodid` and product titles
  - Used for finding product detail URLs
  - ~60 products, auto-rebuilds if older than 7 days

- **Portal Index** (`cache/portal_product_index.json`):
  - **Two-stage API approach** (no Playwright for index building):
    1. Fetch category URLs via navigation API (unauthenticated)
       - Extracts categories at level >= 2 with at least 2 URL slashes
       - Includes both level 2 (e.g., `/wall-plus/edgestone-plus`) and level 3+ categories
    2. Authenticate with Playwright, query search API per category
  - Extracts individual products with SKU, price, stock, images
  - **URL extraction with fallback logic:**
    - Primary: Uses `urlcomponent` field (e.g., `/Sherwood-Ledgestone-3-Pc.-Design-Kit-Onyx-Natural`)
    - Fallback: Uses `/product/{internalid}` format when `urlcomponent` is empty (e.g., `/product/21263`)
    - Last resort: Uses category URL (will fail scraping)
  - Used for matching exact color variants
  - ~1046 products, auto-rebuilds if older than 7 days

**Trade-offs:**
- ✅ Accurate matching (public fuzzy match → portal exact match)
- ✅ Fast subsequent runs (both indexes cached)
- ✅ Handles products with missing urlcomponent via internalid fallback
- ❌ Slow first run (~5-7 minutes to build both indexes)
- ❌ Portal index requires valid dealer credentials

### 2. Title-Based Variant Grouping with Multiple Units

**Why:** Input records with same title are color variants, each color may have multiple unit_of_sale options

**Implementation:**
- `product_generator.group_by_title()` groups records
- Each group becomes one Shopify product
- Colors become `option1` values
- Unit of Sale becomes `option2` values (Sq Ft, Kit, Cube, Piece, Layer, Band)
- Creates cartesian product of color × unit combinations as variants

**Example:**
```
Input Records:
  - title="Sherwood Ledgestone", color="Onyx", sq_ft_cost=5.99, cost_per_cube=299.00
  - title="Sherwood Ledgestone", color="Driftwood", sq_ft_cost=5.99, cost_per_cube=299.00

Output Product:
  - title="Sherwood Ledgestone"
  - options=[
      {name: "Color", values: ["Onyx", "Driftwood"]},
      {name: "Unit of Sale", values: ["Sq Ft", "Cube"]}
    ]
  - variants=[
      {option1: "Onyx", option2: "Sq Ft", price: "5.99"},
      {option1: "Onyx", option2: "Cube", price: "299.00"},
      {option1: "Driftwood", option2: "Sq Ft", price: "5.99"},
      {option1: "Driftwood", option2: "Cube", price: "299.00"}
    ]
```

### 3. Playwright for Dealer Portal AND Public Gallery

**Why:**
- Dealer portal is a SuiteCommerce JavaScript app (no static HTML)
- Public site gallery lightbox requires JavaScript interaction to get all 20+ images

**Implementation:**
- **Portal**: Headless Chromium for authentication + page rendering
- **Public Gallery**: Shares same browser instance to avoid asyncio conflicts
  - Opens lightbox to extract full gallery (20+ images vs 10 in HTML)
- Login with credentials once, reuse session
- Wait for JavaScript to render
- Extract data from rendered DOM

**Trade-offs:**
- ✅ Works with JavaScript apps
- ✅ Gets complete gallery (20+ images instead of 10)
- ❌ Slower than requests library
- ❌ Requires browser install (`playwright install chromium`)

**Alternative Considered:** Direct API calls (found for portal index, but not for product pages)

### 4. Image Ordering with Variant-Specific Alt Tags

**Requirement:** Product images first (per color), then lifestyle images (shared)

**Implementation:**
```python
# Step 1: Deduplicate images (case-insensitive)
# Portal images: deduplicated PER COLOR (different colors have different images)
# Public images: deduplicated GLOBALLY (shared across all colors)

# Step 2: Create variant entries grouped by color × unit combination
# For each variant (color + unit_of_sale):
#   - Add portal images for THIS color only
#   - Add hero image (shared)
#   - Add lifestyle gallery (shared)
#   - Generate alt tags with variant filter: "Color [Onyx] Unit [Sq Ft]"

# Result: Shopify can filter gallery by variant selection
```

**Key Features:**
- Deduplicates images before creating variant entries
- Portal images shown only for matching color
- Public images (hero/lifestyle) shown for all variants
- Alt tags enable Shopify variant filtering
- Images grouped by variant for easier review

---

## Important Requirements

### Always Follow Shared Guidelines

**CRITICAL:** This project MUST comply with ALL shared-docs requirements.

#### Before Writing Any Code OR Answering Questions

1. **ALWAYS Use Context7 for Current Library Documentation**

   **CRITICAL:** Before writing code OR answering questions about any library, API, or framework, you MUST use Context7 to fetch the latest documentation.

   **Why:** Documentation changes frequently. Context7 provides up-to-date information from official sources, preventing outdated or incorrect guidance.

   **Process:**
   1. Use `mcp__context7__resolve-library-id` to find the library
   2. Use `mcp__context7__get-library-docs` to fetch current documentation
   3. Use the documentation to inform your code or answer

   **Common libraries:**
   - Shopify API: `/websites/shopify_dev`
   - Requests: `/psf/requests`
   - BeautifulSoup: `/wention/beautifulsoup4`
   - Playwright: `/microsoft/playwright-python`
   - Pandas: `/pandas-dev/pandas`

   **When to use:**
   - ✅ Before implementing any API integration
   - ✅ When answering questions about how libraries work
   - ✅ When debugging API-related issues
   - ✅ When checking field names, types, or requirements
   - ✅ When explaining how to use any external library

2. **Review All Shared Requirements**
   - **Project Structure**: `/Users/moosemarketer/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md`
     - pyenv virtual environment setup (Python 3.12.9)
     - Module organization (src/, tests/, utils/)
     - Requirements files (requirements.txt, requirements-gui.txt, requirements-dev.txt)
     - Entry points (main.py, gui.py)
     - Comprehensive automated testing
     - Git workflow (create tests, run tests, fix errors, commit)

   - **Compliance Checklist**: `/Users/moosemarketer/Code/shared-docs/python/COMPLIANCE_CHECKLIST.md`
     - Verify ALL files exist (entry points, requirements files, tests/, etc.)
     - Check .gitignore excludes correct patterns
     - Ensure documentation is complete and current

   - **GUI Design**: `/Users/moosemarketer/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md`
     - ttkbootstrap framework with darkly theme
     - Thread-safe queue-based communication
     - Auto-save configuration
     - Tooltips with ⓘ icons
     - Processing modes (skip/overwrite)
     - Record range selection

   - **GraphQL Output**: `/Users/moosemarketer/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md`
     - Shopify GraphQL API 2025-10 format
     - Use `descriptionHtml` (NOT `body_html`)
     - Use `status: "ACTIVE"` (NOT `published: true`)
     - Proper metafield structure

   - **Git Workflow**: `/Users/moosemarketer/Code/shared-docs/python/GIT_WORKFLOW.md`
     - Commit message format with Co-Authored-By
     - Never skip hooks or force push
     - Check authorship before amending

   - **Technical Docs**: `/Users/moosemarketer/Code/shared-docs/python/TECHNICAL_DOCS.md`
     - Shopify product uploader patterns
     - API integration standards

3. **Review Collector-Specific Requirements**
   - **Input Structure**: `/Users/moosemarketer/Code/garoppos/shared-docs/INPUT_FILE_STRUCTURE.md`
     - Required fields (item_#, description_1, size, upc_updated, etc.)
     - Variant support fields (parent, option_1-4, color)
     - Data type specifications

   - **UPCItemDB Fallback**: `/Users/moosemarketer/Code/garoppos/shared-docs/UPCITEMDB_FALLBACK_REQUIREMENTS.md`
     - Image quality assessment (Laplacian variance)
     - Placeholder detection (perceptual hashing)
     - Fallback decision flow
     - Field mapping for fallback data

#### After Writing Code

**MANDATORY WORKFLOW:** Follow the sequence documented in PROJECT_STRUCTURE_REQUIREMENTS.md:

```
Code → Tests → Run Tests → Fix Errors → Re-run → Update README → Commit
```

4. **Create Comprehensive Automated Tests**
   - Write tests in `tests/` directory
   - Cover all major functionality (parsers, search, index builders, workflow)
   - Use sample/mock data where possible
   - Include `tests/__init__.py`, `tests/README.md`, `tests/.gitignore`

5. **Run Tests Yourself and Fix Errors**
   - Execute: `./run_tests.sh` (fast tests)
   - Execute: `./run_tests.sh --all` (full test suite)
   - Read and analyze ALL test output completely
   - Fix any failures in source code
   - Re-run until 100% tests pass
   - **NEVER commit with failing tests**

6. **Update README.md**
   - Document new/changed functionality
   - Update Features section
   - Update Architecture if needed
   - Same commit as code changes

7. **Commit to GitHub**
   - Stage changes: `git add .`
   - Commit with descriptive message
   - Include `🤖 Generated with [Claude Code]` footer
   - Include `Co-Authored-By: Claude <noreply@anthropic.com>`
   - Push to remote: `git push`

**Key Standards:**
- Python 3.12.9 with pyenv virtual environment named "cambridge"
- Three requirements files: requirements.txt, requirements-gui.txt, requirements-dev.txt
- Dual entry points: main.py (CLI), gui.py (GUI)
- Comprehensive tests with `tests/__init__.py`, `tests/README.md`, `tests/.gitignore`
- Thread-safe GUI with queue-based communication
- Shopify GraphQL 2025-10 output format
- Always update README.md when adding features (in same commit)

---

## Common Maintenance Tasks

### Update Product Index Crawler

**When:** Cambridge adds new product categories to public site

**How:**
1. Edit `src/index_builder.py`
2. Add new category URLs to `CATEGORY_URLS` list
3. Test with `python3 scripts/build_index.py`

```python
CATEGORY_URLS = [
    "/pavers",
    "/walls",
    "/new-category",  # ← Add here
]
```

### Update Public Parser

**When:** Cambridge changes website structure

**How:**
1. Fetch sample HTML: `curl https://www.cambridgepavers.com/pavers-details?prodid=64 > sample.html`
2. Inspect HTML structure
3. Update `src/public_parser.py` extraction methods
4. Test with sample HTML

**Key methods:**
- `_extract_hero_image()` - Main product image
- `_extract_gallery_images()` - Carousel images (HTML fallback)
- `extract_gallery_images_with_playwright()` - Lightbox images (full gallery)
- `_extract_description()` - Text after "Description:"
- `_extract_specifications()` - Text after "Specifications:"

### Update Portal Parser

**When:** Dealer portal structure changes

**How:**
1. Login manually and inspect page
2. Update `src/portal_parser.py` extraction methods
3. Test with real credentials

**Key methods:**
- `login()` - Authentication flow
- `_extract_gallery_images()` - Product images from carousel
- `_extract_weight()` - Item weight from custom PDP fields
- `_extract_cost()` - Product price from price element (uses data-rate attribute)
- `_extract_model_number()` - Vendor SKU from product line

**Recent improvements (2025-11-18):**
- All extractors now use Playwright (cost was previously using BeautifulSoup)
- Increased timeouts from 5s to 10s for more reliable extraction
- Added 0.5s sleep after selectors load to ensure JavaScript rendering completes
- Improved error handling with specific PlaywrightTimeoutError catches
- Cost extraction now tries data-rate attribute first (most reliable)
- Better logging to indicate extraction success/failure reasons
- Gallery images uses longer timeout and explicit carousel detection

### Update Portal Index Builder

**When:** Portal API endpoints change or new categories are added

**How:**
1. Inspect network traffic in portal manually
2. Update `src/portal_index_builder.py` API endpoints or query logic
3. Test with `python3 scripts/build_portal_index.py`

**Two-stage process:**
- Stage 1: Fetch category list from navigation API
- Stage 2: For each category, query search API with authentication

### Add New Metafields

**When:** Need to capture additional data

**How:**
1. Extract data in parser (`public_parser.py` or `portal_parser.py`)
2. Pass data to `product_generator.py`
3. Add to `_generate_metafields()` or variant metafields

```python
# In product_generator.py
def _generate_metafields(self, public_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    metafields = []

    # Add new metafield
    new_field = public_data.get("new_field", "")
    if new_field:
        metafields.append({
            "namespace": "custom",
            "key": "new_field",
            "value": new_field,
            "type": "single_line_text_field"  # or "rich_text_field", "json"
        })

    return metafields
```

---

## Testing

### Test Workflow

```bash
# 1. Build both product indexes
python3 scripts/build_index.py        # Public index
python3 scripts/build_portal_index.py # Portal index (requires credentials)

# 2. Test with small sample
# Edit config.json:
{
  "start_record": "1",
  "end_record": "2"
}

# 3. Run collector
python3 main.py

# 4. Verify output
cat output/cambridge.json | jq '.products[0]'
```

### Test Index Builder

```python
from src.index_builder import CambridgeIndexBuilder, save_index_to_cache
from src.collector import CambridgeCollector

collector = CambridgeCollector()
index = collector.index_builder.build_index(
    http_get=collector.session.get,
    timeout=30,
    log=print
)
save_index_to_cache(index, "tests/output/test_index.json", print)
```

### Test Portal Index Builder

```python
from src.portal_index_builder import CambridgePortalIndexBuilder
from src.index_builder import save_index_to_cache

config = {
    "portal_username": "your-email@example.com",
    "portal_password": "your-password"
}

builder = CambridgePortalIndexBuilder(config)
index = builder.build_index(log=print)
save_index_to_cache(index, "tests/output/test_portal_index.json", print)
```

### Test Public Parser

```python
from src.public_parser import CambridgePublicParser

parser = CambridgePublicParser({"public_origin": "https://www.cambridgepavers.com"})

with open("sample_files/Public - Cambridge Pavingstones.html", "r") as f:
    html = f.read()

data = parser.parse_page(html)
print(data)
```

### Test Portal Parser

```python
from src.portal_parser import CambridgePortalParser

config = {
    "portal_origin": "https://shop.cambridgepavers.com",
    "portal_username": "your-username",
    "portal_password": "your-password"
}

with CambridgePortalParser(config) as parser:
    if parser.login(print):
        html = parser.fetch_product_page("/some-product-url", print)
        if html:
            data = parser.parse_product_page(html, print)
            print(data)
```

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Product Indexes

```bash
# Public index
cat cache/product_index.json | jq '.products[] | select(.title | contains("Sherwood"))'

# Portal index
cat cache/portal_product_index.json | jq '.products[] | select(.title | contains("Sherwood"))'

# Check index stats
cat cache/product_index.json | jq '{total: .total_products, updated: .last_updated}'
cat cache/portal_product_index.json | jq '{total: .total_products, updated: .last_updated}'
```

### Test Fuzzy Matching (Public Index)

```python
from src.search import CambridgeSearcher
from src.index_builder import load_index_from_cache

searcher = CambridgeSearcher({"fuzzy_match_threshold": 60.0})
index = load_index_from_cache("cache/product_index.json", print)
searcher.load_index(index, print)

url = searcher.find_product_url("Sherwood Ledgestone 3-Pc", "Onyx", print)
print(f"Found URL: {url}")
```

### Test Exact Matching (Portal Index)

```python
from src.portal_search import CambridgePortalSearcher
from src.index_builder import load_index_from_cache

searcher = CambridgePortalSearcher({})
index = load_index_from_cache("cache/portal_product_index.json", print)
searcher.load_index(index, print)

product = searcher.find_product_by_title_and_color(
    "Sherwood Ledgestone 3-Pc. Design Kit",
    "Onyx/Natural",
    print
)
print(f"Found product: {product}")
```

### Debug Playwright

```python
# In portal_parser.py, change:
self._browser = playwright.chromium.launch(headless=False)  # Show browser
```

---

## Performance

### Bottlenecks

1. **Portal data collection** (Playwright): ~5-10 seconds per product page
2. **Portal index building** (API queries): ~3-5 minutes for 362 categories
3. **Public index building** (HTTP scraping): ~2-3 minutes for 60 products
4. **Public gallery extraction** (Playwright lightbox): ~3-5 seconds per product
5. **Network requests**: Depends on connection speed

### Optimization Strategies

**Reduce portal calls:**
- Cache portal data by color
- Skip portal if data already collected for that color
- Portal index eliminates need to search portal on each run

**Parallel processing:**
- Consider `concurrent.futures` for independent products
- Be careful with rate limiting
- Playwright sessions are not thread-safe (use separate instances)

**Index caching:**
- Already implemented for both indexes
- Auto-rebuild only when stale (>7 days)
- Manual rebuild available via scripts

**Share Playwright instances:**
- Public parser reuses portal parser's browser to avoid asyncio conflicts
- Reduces browser startup overhead

---

## Security

### Credentials Storage

**Current:** Stored in `config.json` (plaintext)

**Risk:** Credentials visible to anyone with file access

**Mitigation:**
- Add `config.json` to `.gitignore` (✓ already done)
- Document that credentials are not encrypted
- Consider environment variables for production

### Portal Access

**Current:** Automated login with Playwright

**Risk:** Portal may implement bot detection

**Mitigation:**
- Use realistic user agent
- Add jitter between requests
- Respect rate limits
- Portal index uses official search API (less likely to trigger detection)

---

## Known Limitations

1. **Color availability:** Public index doesn't include color-specific data
   - **Impact:** Can't pre-filter products by color in public search
   - **Workaround:** Portal index includes color-specific products

2. **Barcode generation:** Cambridge products don't have barcodes in source data
   - **Impact:** Shopify variant `barcode` field uses item_# + unit iterator
   - **Note:** Not critical for this use case

3. **Portal parsing reliability:** Selectors may break if portal updates
   - **Impact:** Data extraction fails
   - **Mitigation:** Monitor logs, update selectors as needed

4. **Gallery extraction timing:** Playwright lightbox requires page interaction
   - **Impact:** Adds 3-5 seconds per product
   - **Benefit:** Gets 20+ images instead of 10 from HTML

---

## Future Enhancements

### Nice to Have

1. **Direct portal API for product pages:** Eliminate Playwright for individual product parsing
2. **Concurrent processing:** Process multiple products in parallel (need thread-safe Playwright)
3. **Progress persistence:** Save progress to resume from exact point
4. **Dry-run mode:** Validate without writing output
5. **Image quality filtering:** Apply Laplacian threshold to portal images
6. **Incremental portal index updates:** Only query changed categories

### Breaking Changes to Avoid

- Don't change input file format (would break existing workflows)
- Don't change output format (would break uploader integration)
- Don't remove config fields (would break existing config.json files)
- Don't change index cache structure (would invalidate existing caches)

---

## Questions & Answers

### Q: Why not use Cambridge's search API?

**A:** No public API found on main site. Portal has search API (now used for index building), but requires authentication.

### Q: Why cache both product indexes?

**A:** Crawling/querying takes 5-7 minutes total. Caching makes subsequent runs near-instant. Public index provides URLs, portal index provides exact SKU/price/color data.

### Q: Why use Playwright instead of requests for portal?

**A:** Portal is a SuiteCommerce JavaScript app. No HTML content without JavaScript execution. Portal index now uses API where possible, but product pages still need Playwright.

### Q: Can we scrape faster?

**A:** Yes, but risk rate limiting or IP ban. Current speed (~10sec/product) is conservative. Portal index API is already much faster than scraping.

### Q: What if a product has no match?

**A:** Log warning, skip product, continue processing. Output will be missing that product.

### Q: Why two separate indexes?

**A:** Public site has limited catalog (60 products) but provides detail URLs. Portal has full catalog (362 products) with individual color variants and pricing. Using both provides best coverage and accuracy.

---

## Contributing

When modifying this collector:

1. **Read shared docs first** - Always reference requirements
2. **Test incrementally** - Test each module before integration
3. **Update documentation** - Keep README.md and CLAUDE.md in sync
4. **Log everything** - Add status messages for debugging
5. **Handle errors gracefully** - Don't crash on single product failure
6. **Test both indexes** - Changes may affect public or portal index building

---

## Contact

For questions or issues, contact the development team.

---

**Last Updated:** 2025-11-17
**Version:** 1.1.0

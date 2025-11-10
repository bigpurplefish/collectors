# Cambridge Product Collector - Development Guide

## Overview

The Cambridge collector scrapes product data from two sources:
1. **Public website** (`www.cambridgepavers.com`) - lifestyle images, descriptions, specifications
2. **Dealer portal** (`shop.cambridgepavers.com`) - product images, pricing, SKUs (requires auth)

Products are matched by **title + color** from the input Excel file, grouped into variant families, and output in Shopify GraphQL 2025-10 format.

---

## Architecture

### Data Flow

```
1. Load Excel Input
   ↓
2. Build/Load Product Index (cached)
   ↓
3. Group Records by Title (variant families)
   ↓
4. For each product family:
   a. Search for product URL (fuzzy match on title)
   b. Collect public website data
   c. For each color variant:
      - Collect dealer portal data
   d. Generate Shopify product
   ↓
5. Save JSON Output
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `collector.py` | Main orchestration, HTTP session management |
| `index_builder.py` | Crawls public site, builds searchable index |
| `search.py` | Fuzzy matching against cached index |
| `public_parser.py` | Parses public website HTML (BeautifulSoup) |
| `portal_parser.py` | Parses dealer portal (Playwright + BeautifulSoup) |
| `product_generator.py` | Groups variants, generates Shopify products |
| `processor.py` | Main workflow, file I/O, error handling |
| `config.py` | Configuration management, auto-save |

---

## Key Design Decisions

### 1. Cached Product Index

**Why:** Cambridge's search is unreliable, fuzzy matching requires full catalog

**Implementation:**
- Crawls all category pages on public site
- Extracts `prodid` values and product titles
- Caches to `cache/product_index.json`
- Auto-rebuilds if older than `index_max_age_days`

**Trade-offs:**
- ✅ Reliable fuzzy matching
- ✅ Fast subsequent runs
- ❌ Slow first run (2-3 minutes to crawl all products)

### 2. Title-Based Variant Grouping

**Why:** Input records with same title are color variants of one product

**Implementation:**
- `product_generator.group_by_title()` groups records
- Each group becomes one Shopify product
- Colors become `option1` values

**Example:**
```
Input Records:
  - title="Sherwood Ledgestone", color="Onyx"
  - title="Sherwood Ledgestone", color="Driftwood"

Output Product:
  - title="Sherwood Ledgestone"
  - options=[{name: "Color", values: ["Onyx", "Driftwood"]}]
  - variants=[{option1: "Onyx"}, {option1: "Driftwood"}]
```

### 3. Playwright for Dealer Portal

**Why:** Dealer portal is a SuiteCommerce JavaScript app (no static HTML)

**Implementation:**
- Headless Chromium browser
- Login with credentials
- Wait for JavaScript to render
- Extract data from rendered DOM

**Trade-offs:**
- ✅ Works with JavaScript apps
- ❌ Slower than requests library
- ❌ Requires browser install

**Alternative Considered:** Direct API calls (not found during investigation)

### 4. Image Ordering

**Requirement:** Product images first, then lifestyle images

**Implementation:**
```python
images = []
# Phase 1: Product images from portal (all colors)
for color, portal_data in portal_data_by_color.items():
    images.extend(portal_data["gallery_images"])

# Phase 2: Lifestyle images from public site
images.append(public_data["hero_image"])
images.extend(public_data["gallery_images"])
```

---

## Important Requirements

### Always Follow Shared Guidelines

**CRITICAL:** This project MUST comply with ALL shared-docs requirements.

#### Before Writing Any Code

1. **Use Context7 for Current Library Documentation**
   - ALWAYS fetch latest docs using Context7 MCP tools
   - Use `mcp__context7__resolve-library-id` to find library
   - Use `mcp__context7__get-library-docs` to get documentation
   - Common libraries:
     - Requests: `/psf/requests`
     - BeautifulSoup: `/wention/beautifulsoup4`
     - Playwright: `/microsoft/playwright-python`
     - Pandas: `/pandas-dev/pandas`

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
   - **Input Structure**: `/Users/moosemarketer/Code/garoppos/collectors/shared-docs/INPUT_FILE_STRUCTURE.md`
     - Required fields (item_#, description_1, size, upc_updated, etc.)
     - Variant support fields (parent, option_1-4, color)
     - Data type specifications

   - **UPCItemDB Fallback**: `/Users/moosemarketer/Code/garoppos/collectors/shared-docs/UPCITEMDB_FALLBACK_REQUIREMENTS.md`
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

**When:** Cambridge adds new product categories

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
- `_extract_gallery_images()` - Carousel images
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
- `_extract_gallery_images()` - Product images
- `_extract_weight()` - Item weight
- `_extract_cost()` - Product price
- `_extract_model_number()` - Vendor SKU

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
# 1. Build product index
python3 scripts/build_index.py

# 2. Test with small sample
# Edit config.json:
{
  "start_record": "1",
  "end_record": "2"
}

# 3. Run collector
python3 main.py

# 4. Verify output
cat output/cambridge_products.json | jq '.products[0]'
```

### Test Index Builder

```python
from src.index_builder import CambridgeIndexBuilder, save_index_to_cache
from src.collector import CambridgeCollector

collector = CambridgeCollector()
index = collector.index_builder.build_index(
    http_get=collector.session.get,
    log=print
)
save_index_to_cache(index, "tests/output/test_index.json", print)
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

### Inspect Product Index

```bash
cat cache/product_index.json | jq '.products[] | select(.title | contains("Sherwood"))'
```

### Test Fuzzy Matching

```python
from src.search import CambridgeSearcher
from src.index_builder import load_index_from_cache

searcher = CambridgeSearcher({"fuzzy_match_threshold": 60.0})
index = load_index_from_cache("cache/product_index.json", print)
searcher.load_index(index, print)

url = searcher.find_product_url("Sherwood Ledgestone 3-Pc", "Onyx", print)
print(f"Found URL: {url}")
```

### Debug Playwright

```python
# In portal_parser.py, change:
self._browser = playwright.chromium.launch(headless=False)  # Show browser
```

---

## Performance

### Bottlenecks

1. **Portal data collection** (Playwright): ~5-10 seconds per product
2. **Index building**: ~2-3 minutes for full catalog
3. **Network requests**: Depends on connection speed

### Optimization Strategies

**Reduce portal calls:**
- Cache portal data by color
- Skip portal if data already collected for that color

**Parallel processing:**
- Consider `concurrent.futures` for independent products
- Be careful with rate limiting

**Index caching:**
- Already implemented
- Rebuild only when needed

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

---

## Known Limitations

1. **Portal URL mapping:** Currently uses public site URL for portal (may not work)
   - **TODO:** Investigate portal URL structure, map public prodid to portal URL

2. **Color availability:** Index doesn't include color-specific data
   - **Impact:** Can't pre-filter products by color
   - **Workaround:** Parse colors from public page after finding product

3. **Barcode data:** Cambridge products may not have barcodes
   - **Impact:** Shopify variant `barcode` field is empty
   - **Workaround:** Not critical for this use case

4. **Portal parsing reliability:** Selectors may break if portal updates
   - **Impact:** Data extraction fails
   - **Mitigation:** Monitor logs, update selectors as needed

---

## Future Enhancements

### Nice to Have

1. **API endpoint discovery:** Find portal REST/GraphQL APIs (faster than Playwright)
2. **Concurrent processing:** Process multiple products in parallel
3. **Progress persistence:** Save progress to resume from exact point
4. **Dry-run mode:** Validate without writing output
5. **Image quality filtering:** Apply Laplacian threshold to portal images

### Breaking Changes to Avoid

- Don't change input file format (would break existing workflows)
- Don't change output format (would break uploader integration)
- Don't remove config fields (would break existing config.json files)

---

## Questions & Answers

### Q: Why not use Cambridge's search API?

**A:** No public API found. Site search is JavaScript-based (React/Vue), unreliable for programmatic use.

### Q: Why cache the product index?

**A:** Crawling 150+ products takes 2-3 minutes. Caching makes subsequent runs instant.

### Q: Why use Playwright instead of requests for portal?

**A:** Portal is a SuiteCommerce JavaScript app. No HTML content without JavaScript execution.

### Q: Can we scrape faster?

**A:** Yes, but risk rate limiting or IP ban. Current speed (~10sec/product) is conservative.

### Q: What if a product has no match?

**A:** Log warning, skip product, continue processing. Output will be missing that product.

---

## Contributing

When modifying this collector:

1. **Read shared docs first** - Always reference requirements
2. **Test incrementally** - Test each module before integration
3. **Update documentation** - Keep README.md and CLAUDE.md in sync
4. **Log everything** - Add status messages for debugging
5. **Handle errors gracefully** - Don't crash on single product failure

---

## Contact

For questions or issues, contact the development team.

---

**Last Updated:** 2025-11-10
**Version:** 1.0.0

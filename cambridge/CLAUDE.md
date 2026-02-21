# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Cambridge collector scrapes product data from two sources and outputs Shopify GraphQL 2025-10 format:

1. **Public website** (`www.cambridgepavers.com`) — lifestyle images, descriptions, specifications (~60 products)
2. **Dealer portal** (`shop.cambridgepavers.com`) — product images, pricing, SKUs, per-color variants (~1046 products, requires auth)

Products are matched by **title + color** from an input Excel file, grouped into variant families by title.

## Commands

```bash
# Run collector
python3 main.py          # CLI (requires config.json)
python3 gui.py           # GUI (recommended)

# Tests
./run_tests.sh           # Fast tests only (~5-10s): parsers, portal search, variant skip
./run_tests.sh --all     # Full suite including slow network tests (~5min)
python3 tests/test_parsers.py              # Single test file

# Rebuild indexes
python3 scripts/build_index.py             # Public product index
python3 scripts/build_portal_index.py      # Portal product index (needs credentials)

# Inspect cached indexes
cat cache/product_index.json | jq '.total_products'
cat cache/portal_product_index.json | jq '.total_products'
```

**Environment:** Python 3.12.9 via pyenv virtualenv named `cambridge` (see `.python-version`).

## Architecture

### Data Flow

```
Excel Input → Group by Title → For each product family:
  1. Fuzzy-match title against PUBLIC index → get product URL
  2. If found: scrape public page (Playwright for gallery lightbox, 20+ images)
  3. For each color variant: exact-match title+color against PORTAL index
     - If title fails, retry with title_alt field
  4. Generate Shopify product with variants (one per color)
→ Save JSON output + report (failures/warnings)
```

### Dual Index System

Both indexes are cached in `cache/` and auto-rebuild when >7 days old.

**Public Index** (`product_index.json`): Crawls category pages via HTTP. Provides product detail URLs for scraping. ~60 products.

**Portal Index** (`portal_product_index.json`): Navigation API + PLP scraping:
1. Fetch categories from navigation API (unauthenticated)
2. Authenticate with Playwright, navigate to each category page, scrape product cards from rendered DOM

Provides individual product variants with title, URL, SKU, price, stock, thumbnail. ~1000+ products.

**Resilience:** Probe mode tests first 5 categories with 15s timeouts. If all fail, early bail-out triggers cache fallback. Rate limiting: 2.5s between page navigations.

### Module Map

| Module | Role |
|--------|------|
| `processor.py` (850 lines) | Main workflow: load Excel, orchestrate collection, save output |
| `collector.py` | HTTP session management, coordinates both indexes |
| `product_generator.py` | Groups variants by title, generates Shopify products, image ordering with alt tags |
| `index_builder.py` | Crawls public site, builds searchable index |
| `portal_index_builder.py` | Nav API + Playwright PLP scraping: categories → page navigation per category |
| `search.py` | Fuzzy matching against public index (theshold configurable) |
| `portal_search.py` | Exact matching against portal index (title + color) |
| `public_parser.py` | Parses public website HTML (BS4 + Playwright for gallery lightbox) |
| `portal_parser.py` | Parses dealer portal pages (Playwright for JS-rendered SuiteCommerce app) |
| `config.py` | Config management, cache paths, defaults |

### Shared Dependencies

Modules use `sys.path.insert` to reach shared utilities at `../../shared/utils/`:
- `logging_utils.py` — dual logging (GUI status + file/console)
- `image_utils.py` — dedup, alt tags, URL cleaning
- `sku_generator.py` — SKU generation for products without SKUs
- `text_utils.py` — title normalization

### Variant Generation Logic

Each input record with the same title becomes a color variant. Each color gets exactly ONE variant:
- **Priority:** Piece (if `cost_per_piece` and `price_per_piece` exist)
- **Fallback:** Sq Ft (if `sq_ft_cost` and `sq_ft_price` exist)

Options: `Color` (per variant) + `Unit of Sale` (Piece or Sq Ft).

### Image Ordering

Per variant: portal images for that color → hero image (shared) → lifestyle gallery (shared). Alt tags include variant filter text (`"Color [Onyx] Unit [Sq Ft]"`) for Shopify filtering.

## Configuration

`config.json` (gitignored) — key fields:

| Field | Purpose |
|-------|---------|
| `portal_username` / `portal_password` | Dealer portal credentials |
| `input_file` | Path to Excel input |
| `output_file` | Path to JSON output |
| `processing_mode` | `skip` (resume) or `overwrite` |
| `start_product` / `end_product` | Product family range (1-based, after grouping by title) |
| `rebuild_index` | Force index rebuild |
| `skip_accessories_category` | Skip /accessories in portal index |
| `fuzzy_match_threshold` | Public search match score (0-100, default 60) |

## Shared Docs Requirements

Before writing code, review these shared requirements:

- **Project Structure**: `/Users/moosemarketer/Code/shared-docs/python/PROJECT_STRUCTURE_REQUIREMENTS.md`
- **GraphQL Output**: `/Users/moosemarketer/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md` — Shopify GraphQL 2025-10 format, `descriptionHtml` not `body_html`, `status: "ACTIVE"` not `published: true`
- **GUI Design**: `/Users/moosemarketer/Code/shared-docs/python/GUI_DESIGN_REQUIREMENTS.md` — ttkbootstrap darkly theme, thread-safe queue
- **Input Structure**: `/Users/moosemarketer/Code/garoppos/shared-docs/INPUT_FILE_STRUCTURE.md`
- **Compliance**: `/Users/moosemarketer/Code/shared-docs/python/COMPLIANCE_CHECKLIST.md`

Use Context7 (`mcp__context7__resolve-library-id` → `mcp__context7__query-docs`) for current library docs before writing integration code.

## After Writing Code

Follow: Code → Tests → Run `./run_tests.sh` → Fix failures → Re-run → Update README.md → Commit.

## Portal Scraping Notes

- Portal is a **SuiteCommerce JavaScript app** — requires Playwright (no static HTML)
- Public gallery lightbox also requires Playwright for full 20+ image extraction
- Portal parser shares browser instance with public parser to avoid asyncio conflicts
- Cost extraction uses `data-rate` attribute first (most reliable), with BS4 fallback
- All portal extractors use 10s timeouts with 0.5s post-load sleep for JS rendering

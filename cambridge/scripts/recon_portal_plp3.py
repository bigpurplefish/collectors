#!/usr/bin/env python3
"""
Recon 3: Navigate to a LEAF category (level 3) to find actual product cards.
Also test a parent category with products and check items-per-page.
"""

import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import load_config
from playwright.sync_api import sync_playwright

PORTAL_ORIGIN = "https://shop.cambridgepavers.com"
# Level 3 leaf categories from nav API
TEST_URLS = [
    "/pavers/sherwood/sherwood-belgium-5-pc-design-kit",
    "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit",
    "/pavers/crusader",   # Level 2 - might have direct products
]


def main():
    config = load_config()
    username = config.get("portal_username", "")
    password = config.get("portal_password", "")

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        # Login
        print("Logging in...")
        page.goto(PORTAL_ORIGIN, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        page.locator('input[type="email"], input[name="email"], input#login-email').fill(username)
        page.locator('input[type="password"], input[name="password"], input#login-password').fill(password)
        page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")').click()
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        print("Logged in.\n")

        for cat_url in TEST_URLS:
            print("=" * 80)
            print(f"TESTING: {cat_url}")
            print("=" * 80)

            page.goto(f"{PORTAL_ORIGIN}{cat_url}", wait_until="networkidle", timeout=30000)
            time.sleep(5)
            print(f"  Title: {page.title()}")

            # Check if it's a category page (subcategories) or product listing
            has_categories = page.locator(".facets-category-cell").count()
            has_items = page.locator(".facets-items-collection-view-row, .facets-item-cell-grid, .facets-item-cell-list").count()
            no_items = page.locator(".no-items").count()

            print(f"  Subcategory cells: {has_categories}")
            print(f"  Product items: {has_items}")
            print(f"  no-items class: {no_items}")

            # Find ALL anchor elements with product-like URLs in #content
            product_data = page.evaluate("""() => {
                const content = document.querySelector('#content') || document.body;

                // Find product cells - SuiteCommerce uses different views
                const results = {
                    categoryCells: [],
                    itemCells: [],
                    allContentLinks: []
                };

                // Category cells (subcategories)
                content.querySelectorAll('.facets-category-cell').forEach(cell => {
                    const a = cell.querySelector('a');
                    results.categoryCells.push({
                        href: a ? a.getAttribute('href') : null,
                        title: cell.querySelector('.facets-category-cell-title')?.textContent?.trim(),
                    });
                });

                // Item cells (actual products)
                content.querySelectorAll('.facets-item-cell-grid, .facets-item-cell-list, .facets-item-cell-table').forEach(cell => {
                    const a = cell.querySelector('a[href]');
                    results.itemCells.push({
                        href: a ? a.getAttribute('href') : null,
                        title: cell.querySelector('.facets-item-cell-grid-title a, .facets-item-cell-list-title a')?.textContent?.trim(),
                        price: cell.querySelector('.item-views-price-lead')?.textContent?.trim(),
                        img: cell.querySelector('img')?.getAttribute('src'),
                        outerHTML: cell.outerHTML.substring(0, 500)
                    });
                });

                // All links in main content
                const mainContent = content.querySelector('.facets-facet-browse') || content;
                mainContent.querySelectorAll('a[href]').forEach(a => {
                    const href = a.getAttribute('href');
                    if (href && !href.startsWith('#') && !href.startsWith('javascript')) {
                        results.allContentLinks.push({
                            href: href,
                            text: a.textContent.trim().substring(0, 80),
                            classes: a.className
                        });
                    }
                });

                return results;
            }""")

            print(f"\n  Category cells: {len(product_data['categoryCells'])}")
            for c in product_data['categoryCells'][:5]:
                print(f"    {c['title']} → {c['href']}")

            print(f"\n  Item cells: {len(product_data['itemCells'])}")
            for item in product_data['itemCells'][:5]:
                print(f"    title={item['title']}")
                print(f"    href={item['href']}")
                print(f"    price={item['price']}")
                print(f"    html={item['outerHTML'][:200]}")

            print(f"\n  All content links: {len(product_data['allContentLinks'])}")
            # Show unique links that look like product URLs
            seen = set()
            for link in product_data['allContentLinks']:
                href = link['href']
                if href not in seen and not href.startswith('/pavers/') and not href.startswith('/walls/') and not href.startswith('http'):
                    seen.add(href)
                    print(f"    {link['text'][:50]:50s} → {href}")
                    if len(seen) >= 10:
                        break

            # Check page content classes
            print("\n  Content area main children:")
            children_info = page.evaluate("""() => {
                const content = document.querySelector('.facets-facet-browse-content') || document.querySelector('#content');
                if (!content) return ['No content element found'];
                return Array.from(content.children).map(c => {
                    const cls = c.className;
                    const childCount = c.children.length;
                    const hasNoItems = c.classList.contains('no-items');
                    return `<${c.tagName.toLowerCase()} class="${cls}"> children=${childCount} no-items=${hasNoItems}`;
                });
            }""")
            for info in children_info:
                print(f"    {info}")

            # Pagination / items count
            items_count = page.evaluate("""() => {
                const el = document.querySelector('.facets-facet-browse-results-heading');
                return el ? el.textContent.trim() : 'not found';
            }""")
            print(f"\n  Results heading: {items_count}")

            # Screenshot this category
            safe_name = cat_url.strip("/").replace("/", "_")
            page.screenshot(path=str(Path(__file__).parent / f"recon_{safe_name}.png"), full_page=True)
            print(f"  Screenshot saved")
            print()

    finally:
        browser.close()
        pw.stop()

    print("DONE")


if __name__ == "__main__":
    main()

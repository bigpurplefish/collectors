#!/usr/bin/env python3
"""
Recon follow-up: Find actual PLP product card selectors in the main content area.
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
TEST_CATEGORIES = ["/pavers/sherwood", "/walls/edgestone-plus"]


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
        print("Logged in.")

        for cat_url in TEST_CATEGORIES:
            print()
            print("=" * 80)
            print(f"CATEGORY: {cat_url}")
            print("=" * 80)

            plp_url = f"{PORTAL_ORIGIN}{cat_url}"
            page.goto(plp_url, wait_until="networkidle", timeout=30000)
            time.sleep(5)

            # Find all links in main content area (exclude header/footer)
            print("\n--- All links with product-like hrefs ---")
            links = page.evaluate("""() => {
                // Exclude header and footer
                const main = document.querySelector('#content, .facets-faceted-navigation, main, [role="main"]')
                    || document.body;
                const allLinks = main.querySelectorAll('a[href]');
                const productLinks = [];
                for (const a of allLinks) {
                    const href = a.getAttribute('href');
                    // Product URLs have format /Product-Name_N
                    if (href && href.match(/^\/[A-Z].*_\d+$/)) {
                        productLinks.push({
                            href: href,
                            text: a.textContent.trim().substring(0, 80),
                            parentClass: a.parentElement?.className || '',
                            grandparentClass: a.parentElement?.parentElement?.className || '',
                            greatGPClass: a.parentElement?.parentElement?.parentElement?.className || ''
                        });
                    }
                }
                return productLinks;
            }""")
            print(f"  Found {len(links)} product links")
            for i, link in enumerate(links[:8]):
                print(f"  {i+1}. href={link['href']}")
                print(f"     text='{link['text']}'")
                print(f"     parent={link['parentClass']}")
                print(f"     grandparent={link['grandparentClass']}")
                print(f"     great-gp={link['greatGPClass']}")

            # Find the content wrapper and its children
            print("\n--- Content area structure ---")
            structure = page.evaluate("""() => {
                const content = document.querySelector('#content');
                if (!content) return 'No #content found';

                function describeElement(el, depth) {
                    if (depth > 4) return [];
                    const results = [];
                    for (const child of el.children) {
                        const tag = child.tagName.toLowerCase();
                        const cls = child.className ? `.${child.className.split(' ').join('.')}` : '';
                        const dataView = child.getAttribute('data-view') || '';
                        const childCount = child.children.length;
                        const text = child.textContent.trim().substring(0, 60);
                        results.push({
                            indent: '  '.repeat(depth),
                            desc: `<${tag}${cls}> data-view="${dataView}" children=${childCount}`,
                            text: text.substring(0, 40)
                        });
                        if (depth < 3 && childCount < 20) {
                            results.push(...describeElement(child, depth + 1));
                        }
                    }
                    return results;
                }
                return describeElement(content, 0);
            }""")
            if isinstance(structure, str):
                print(f"  {structure}")
            else:
                for item in structure[:50]:
                    print(f"  {item['indent']}{item['desc']}")

            # Try broader selectors for actual product grid
            print("\n--- Broad selector search ---")
            broad_selectors = [
                "#content a[href*='_']",
                ".facets-facet-browse-items a",
                ".facets-items-collection a",
                "[data-view*='Item'] a",
                "[data-view*='Facet'] a",
                ".category-list a",
                ".subcategory a",
                "[data-cms-area] a[href]",
                "#content .row a[href]",
                "[data-view='Facets.Browse'] a",
                "[data-view='CMS.Content']",
            ]
            for sel in broad_selectors:
                try:
                    count = page.locator(sel).count()
                    if count > 0:
                        first_text = page.locator(sel).first.text_content()
                        first_href = page.locator(sel).first.get_attribute("href") or ""
                        print(f"  {sel} → {count} elements")
                        print(f"    first: text='{first_text[:60]}' href='{first_href}'")
                except Exception as e:
                    print(f"  {sel} → ERROR: {e}")

            # Check if products are loaded via CMS content blocks
            print("\n--- CMS content blocks ---")
            cms = page.evaluate("""() => {
                const blocks = document.querySelectorAll('[data-cms-area]');
                return Array.from(blocks).map(b => ({
                    area: b.getAttribute('data-cms-area'),
                    childCount: b.children.length,
                    innerHTML: b.innerHTML.substring(0, 300)
                }));
            }""")
            for block in cms:
                print(f"  data-cms-area='{block['area']}' children={block['childCount']}")
                print(f"    html: {block['innerHTML'][:200]}")

            # Last resort: dump all unique class names that contain 'item' or 'product' or 'cell'
            print("\n--- Classes containing 'item', 'product', 'cell', 'facet' ---")
            classes = page.evaluate("""() => {
                const allElements = document.querySelectorAll('*');
                const classes = new Set();
                for (const el of allElements) {
                    for (const cls of el.classList) {
                        if (cls.match(/item|product|cell|facet/i)) {
                            classes.add(cls);
                        }
                    }
                }
                return Array.from(classes).sort();
            }""")
            for cls in classes:
                print(f"  .{cls}")

    finally:
        browser.close()
        pw.stop()

    print("\nDONE")


if __name__ == "__main__":
    main()

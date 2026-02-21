#!/usr/bin/env python3
"""
Recon script: Discover PLP DOM selectors on Cambridge dealer portal.

Logs in, navigates to a known category page, and dumps:
- Product card selectors
- Product name/title, URL, price, image elements
- Pagination mechanism
- Commerce API response (quick win test)
- SC.ENVIRONMENT JS globals

This is a throwaway script — not part of the collector pipeline.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import load_config

from playwright.sync_api import sync_playwright


PORTAL_ORIGIN = "https://shop.cambridgepavers.com"
# Known category with products
TEST_CATEGORY = "/pavers/sherwood"


def main():
    config = load_config()
    username = config.get("portal_username", "")
    password = config.get("portal_password", "")

    if not username or not password:
        print("ERROR: Portal credentials not configured in config.json")
        sys.exit(1)

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)  # headless=False for visual debugging
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    try:
        # --- LOGIN ---
        print("=" * 80)
        print("STEP 1: Login")
        print("=" * 80)
        page.goto(PORTAL_ORIGIN, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        email_input = page.locator('input[type="email"], input[name="email"], input#login-email')
        if email_input.count() > 0:
            email_input.fill(username)
            print(f"  Filled username: {username}")

        password_input = page.locator('input[type="password"], input[name="password"], input#login-password')
        if password_input.count() > 0:
            password_input.fill(password)
            print("  Filled password")

        login_button = page.locator('button[type="submit"], button:has-text("Log In"), button:has-text("Sign In")')
        if login_button.count() > 0:
            login_button.click()
            print("  Clicked login button")
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(3)
            print("  Login complete")

        # --- TEST COMMERCE API (quick win) ---
        print()
        print("=" * 80)
        print("STEP 2: Test Commerce API")
        print("=" * 80)
        commerce_url = f"{PORTAL_ORIGIN}/api/items?commercecategoryurl={TEST_CATEGORY}&fieldset=search&limit=100"
        print(f"  Testing: {commerce_url}")
        try:
            resp = page.request.get(commerce_url, timeout=15000)
            print(f"  Status: {resp.status}")
            if resp.ok:
                data = resp.json()
                print(f"  Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                if isinstance(data, dict) and "items" in data:
                    print(f"  Items count: {len(data['items'])}")
                    if data["items"]:
                        first = data["items"][0]
                        print(f"  First item keys: {list(first.keys())}")
                        print(f"  First item: {json.dumps(first, indent=2)[:500]}")
                print("  >>> COMMERCE API WORKS — could be a quick swap <<<")
            else:
                body = resp.text()[:300]
                print(f"  Response body: {body}")
                print("  Commerce API blocked/unavailable")
        except Exception as e:
            print(f"  Commerce API error: {e}")

        # --- NAVIGATE TO CATEGORY PLP ---
        print()
        print("=" * 80)
        print("STEP 3: Navigate to PLP")
        print("=" * 80)
        plp_url = f"{PORTAL_ORIGIN}{TEST_CATEGORY}"
        print(f"  Navigating to: {plp_url}")
        page.goto(plp_url, wait_until="networkidle", timeout=30000)
        time.sleep(5)  # Extra wait for SuiteCommerce SPA rendering
        print(f"  Page title: {page.title()}")
        print(f"  URL: {page.url}")

        # --- CHECK SC.ENVIRONMENT ---
        print()
        print("=" * 80)
        print("STEP 4: Check JS globals (SC.ENVIRONMENT)")
        print("=" * 80)
        try:
            sc_env = page.evaluate("JSON.stringify(SC?.ENVIRONMENT, null, 2)")
            if sc_env and sc_env != "undefined":
                env_data = json.loads(sc_env)
                print(f"  SC.ENVIRONMENT keys: {list(env_data.keys())[:20]}")
                print(f"  Full dump saved to recon_sc_environment.json")
                with open(Path(__file__).parent / "recon_sc_environment.json", "w") as f:
                    json.dump(env_data, f, indent=2)
            else:
                print("  SC.ENVIRONMENT not found")
        except Exception as e:
            print(f"  Error reading SC.ENVIRONMENT: {e}")

        # --- DISCOVER PRODUCT CARD SELECTORS ---
        print()
        print("=" * 80)
        print("STEP 5: Discover product card selectors")
        print("=" * 80)

        # Try common SuiteCommerce selectors
        selectors_to_try = [
            ".facets-item-cell-grid",
            ".facets-item-cell-list",
            ".item-cell",
            "[data-type='item']",
            ".facets-items-collection-view .cell",
            ".facets-facet-browse-items .cell",
            ".item-relations-cell",
            "[data-item-id]",
            ".facets-items-collection-view-row .cell",
            # Generic fallbacks
            ".product-card",
            ".product-tile",
            ".product-item",
        ]

        for selector in selectors_to_try:
            count = page.locator(selector).count()
            if count > 0:
                print(f"  FOUND: {selector} → {count} elements")

        # Dump the first product card HTML for analysis
        print()
        print("  --- First product card HTML ---")
        card_selectors = [".facets-item-cell-grid", ".item-cell", "[data-type='item']", "[data-item-id]"]
        for sel in card_selectors:
            if page.locator(sel).count() > 0:
                first_card_html = page.locator(sel).first.inner_html()
                print(f"  Selector: {sel}")
                print(f"  HTML ({len(first_card_html)} chars):")
                print(f"  {first_card_html[:1000]}")
                break

        # --- EXTRACT DATA FROM CARDS ---
        print()
        print("=" * 80)
        print("STEP 6: Extract product data from cards")
        print("=" * 80)

        # Try to extract from whichever selector worked
        products_found = page.evaluate("""() => {
            const cards = document.querySelectorAll(
                '.facets-item-cell-grid, .item-cell, [data-type="item"], [data-item-id]'
            );
            return Array.from(cards).slice(0, 5).map(card => {
                const link = card.querySelector('a[href]');
                const title = card.querySelector(
                    '.facets-item-cell-grid-title, .item-title, [data-type="item-title"], .facets-item-cell-grid-title a, a .facets-item-cell-grid-title'
                );
                const price = card.querySelector(
                    '.item-views-price, .product-views-price, [data-view="ItemViews.Price"]'
                );
                const img = card.querySelector('img');
                return {
                    href: link ? link.getAttribute('href') : null,
                    title: title ? title.textContent.trim() : null,
                    price: price ? price.textContent.trim() : null,
                    imgSrc: img ? img.getAttribute('src') : null,
                    cardClasses: card.className,
                    cardDataAttrs: Array.from(card.attributes)
                        .filter(a => a.name.startsWith('data-'))
                        .map(a => `${a.name}=${a.value}`)
                };
            });
        }""")
        for i, p in enumerate(products_found):
            print(f"  Product {i+1}: {json.dumps(p, indent=4)}")

        # --- PAGINATION ---
        print()
        print("=" * 80)
        print("STEP 7: Discover pagination")
        print("=" * 80)

        pagination_selectors = [
            "button:has-text('Show More')",
            "button:has-text('Show All')",
            "a:has-text('Show More')",
            "a:has-text('Show All')",
            ".global-views-pagination",
            ".facets-faceted-navigation-item-show-more",
            ".show-more",
            "[data-action='show-more']",
            ".pagination",
            "nav.pagination",
        ]

        for sel in pagination_selectors:
            try:
                count = page.locator(sel).count()
                if count > 0:
                    text = page.locator(sel).first.text_content()
                    print(f"  FOUND: {sel} → {count} elements, text: '{text[:80]}'")
            except Exception:
                pass

        # Check total product count displayed on page
        count_selectors = [
            ".facets-browse-view-items-count",
            ".facets-faceted-navigation-item-facets-count",
            "[data-view='ItemsCount']",
            ".items-count",
        ]
        for sel in count_selectors:
            try:
                el = page.locator(sel)
                if el.count() > 0:
                    print(f"  Items count element ({sel}): '{el.first.text_content().strip()}'")
            except Exception:
                pass

        # --- SAVE FULL PAGE SNAPSHOT ---
        print()
        print("=" * 80)
        print("STEP 8: Save page snapshot")
        print("=" * 80)
        snapshot_path = Path(__file__).parent / "recon_plp_snapshot.html"
        content = page.content()
        with open(snapshot_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Saved {len(content)} chars to {snapshot_path}")

        # Screenshot
        screenshot_path = Path(__file__).parent / "recon_plp_screenshot.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Saved screenshot to {screenshot_path}")

    finally:
        browser.close()
        pw.stop()

    print()
    print("=" * 80)
    print("RECON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

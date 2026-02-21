#!/usr/bin/env python3
"""
Recon 4: Dump full HTML of product cards and test pagination.
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
# Leaf category with products
TEST_URL = "/pavers/sherwood/sherwood-ledgestone-3-pc-design-kit"


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

        page.goto(f"{PORTAL_ORIGIN}{TEST_URL}", wait_until="networkidle", timeout=30000)
        time.sleep(5)
        print(f"Page: {page.title()}")

        # DUMP FULL OUTER HTML OF FIRST 3 PRODUCT CARDS
        print("=" * 80)
        print("FULL HTML OF FIRST 3 PRODUCT CARDS")
        print("=" * 80)
        cards = page.locator(".facets-item-cell-grid")
        count = cards.count()
        print(f"Total cards: {count}\n")

        for i in range(min(3, count)):
            html = cards.nth(i).evaluate("el => el.outerHTML")
            print(f"--- Card {i+1} ---")
            print(html)
            print()

        # EXTRACT ALL DATA ATTRIBUTES FROM CARDS
        print("=" * 80)
        print("ALL CARD DATA FROM JS")
        print("=" * 80)
        card_data = page.evaluate("""() => {
            const cards = document.querySelectorAll('.facets-item-cell-grid');
            return Array.from(cards).map(card => {
                const link = card.querySelector('a[href]');
                // Try every possible text element
                const allText = card.textContent.trim();
                const innerLinks = card.querySelectorAll('a');
                const linkTexts = Array.from(innerLinks).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.textContent.trim(),
                    class: a.className
                }));
                const img = card.querySelector('img');
                return {
                    href: link ? link.getAttribute('href') : null,
                    dataItemId: card.getAttribute('data-item-id'),
                    allText: allText.substring(0, 200),
                    linkTexts: linkTexts,
                    imgSrc: img ? img.getAttribute('src') : null,
                    imgAlt: img ? img.getAttribute('alt') : null,
                };
            });
        }""")
        for i, data in enumerate(card_data):
            print(f"\nCard {i+1}:")
            print(f"  data-item-id: {data['dataItemId']}")
            print(f"  href: {data['href']}")
            print(f"  allText: '{data['allText']}'")
            print(f"  imgSrc: {data['imgSrc']}")
            print(f"  imgAlt: {data['imgAlt']}")
            print(f"  linkTexts:")
            for lt in data['linkTexts']:
                print(f"    href={lt['href']} class={lt['class']} text='{lt['text']}'")

        # PAGINATION CHECK
        print()
        print("=" * 80)
        print("PAGINATION")
        print("=" * 80)
        pagination = page.evaluate("""() => {
            const pag = document.querySelector('.facets-facet-browse-pagination');
            if (!pag) return 'No pagination element';
            return {
                html: pag.innerHTML.substring(0, 500),
                links: Array.from(pag.querySelectorAll('a')).map(a => ({
                    href: a.getAttribute('href'),
                    text: a.textContent.trim()
                })),
                buttons: Array.from(pag.querySelectorAll('button')).map(b => ({
                    text: b.textContent.trim(),
                    disabled: b.disabled
                }))
            };
        }""")
        print(json.dumps(pagination, indent=2))

        # RESULTS COUNT
        print()
        print("=" * 80)
        print("RESULTS/ITEMS COUNT")
        print("=" * 80)
        results_info = page.evaluate("""() => {
            // Check various possible count elements
            const selectors = [
                '.facets-browse-view-items-count',
                '.facets-facet-browse-results-heading',
                '.facets-facet-browse-results .showing',
                '.facets-facet-browse-results > div:first-child',
            ];
            const results = {};
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                results[sel] = el ? el.textContent.trim().substring(0, 100) : 'NOT FOUND';
            }

            // Also check the results container children
            const rc = document.querySelector('.facets-facet-browse-results');
            if (rc) {
                results['results-children'] = Array.from(rc.children).map(c => ({
                    tag: c.tagName,
                    class: c.className,
                    text: c.textContent.trim().substring(0, 100)
                }));
            }
            return results;
        }""")
        print(json.dumps(results_info, indent=2))

        # CHECK show=N or limit params
        print()
        print("=" * 80)
        print("URL WITH SHOW PARAM")
        print("=" * 80)
        show_url = f"{PORTAL_ORIGIN}{TEST_URL}?show=200"
        print(f"Testing: {show_url}")
        page.goto(show_url, wait_until="networkidle", timeout=30000)
        time.sleep(5)
        new_count = page.locator(".facets-item-cell-grid").count()
        print(f"Cards with ?show=200: {new_count}")

    finally:
        browser.close()
        pw.stop()

    print("\nDONE")


if __name__ == "__main__":
    main()

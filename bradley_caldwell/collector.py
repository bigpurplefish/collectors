#!/usr/bin/env python3
"""
Bradley Caldwell Product Collector

This collector uses a pre-built JSON catalog to enrich product data.
No web scraping is performed - all data comes from the catalog file.
"""

import os
import re
import json
import html
from typing import Dict, Any, List, Optional

# Bradley Caldwell Site Configuration (embedded from profile)
SITE_CONFIG = {
    "key": "bradley_caldwell",
    "display_name": "Bradley Caldwell",
    "origin": "https://www.bradleycaldwell.com",
    "referer": "https://www.bradleycaldwell.com/",
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 Safari/605.1.15",
    "search": {
        "upc_overrides": {}
    }
}


class BradleyCaldwellCollector:
    """
    Zero-scrape collector that requires a product-catalog JSON file.
    Reads product URLs, titles, brands, UPCs, descriptions, and images from the catalog.
    """

    def __init__(self, catalog_path: Optional[str] = None):
        self.catalog_path = (catalog_path or "").strip()
        self.catalog_loaded = False
        self.by_upc: Dict[str, Dict[str, Any]] = {}
        self.by_url: Dict[str, Dict[str, Any]] = {}

    def set_catalog_path(self, path: str) -> None:
        """Set or update the catalog path."""
        self.catalog_path = (path or "").strip()
        self.catalog_loaded = False

    @staticmethod
    def _text_only(s: str) -> str:
        """Strip HTML tags and unescape entities."""
        if s is None:
            return ""
        s = re.sub(r"<\s*br\s*/?>", "\n", s, flags=re.I)
        s = re.sub(r"<[^>]+>", "", s)
        return html.unescape(s).strip()

    @staticmethod
    def _deproxy_image_url(src: Optional[str]) -> str:
        """Normalize image URL to HTTPS."""
        if not src or not isinstance(src, str):
            return ""
        u = src.strip()
        if u.startswith("http://"):
            u = "https://" + u[len("http://"):]
        return u

    def _ensure_catalog(self) -> None:
        """Load the product catalog from JSON file."""
        if self.catalog_loaded:
            return

        if not self.catalog_path:
            raise RuntimeError(
                "No Bradley Caldwell product catalog specified. "
                "Please provide a catalog JSON file path."
            )

        if not os.path.isfile(self.catalog_path):
            raise RuntimeError(
                f"Product catalog not found: {self.catalog_path}. "
                "Please select a valid JSON file."
            )

        try:
            with open(self.catalog_path, "r") as f:
                items = json.load(f) or []
        except Exception as e:
            raise RuntimeError(f"Failed to read product catalog JSON: {self.catalog_path} — {e}")

        by_upc: Dict[str, Dict[str, Any]] = {}
        by_url: Dict[str, Dict[str, Any]] = {}

        for rec in items:
            upc = re.sub(r"\D", "", str(rec.get("upc", "") or ""))
            url = (rec.get("product_url") or "").strip()
            if upc:
                by_upc[upc] = rec
            if url:
                by_url[url] = rec

        self.by_upc = by_upc
        self.by_url = by_url
        self.catalog_loaded = True

    @staticmethod
    def _benefits_from_description(desc: str) -> List[str]:
        """Extract bullet points from description if it looks like a list."""
        if not desc:
            return []

        norm = desc.strip().replace("\r\n", "\n").replace("\r", "\n")
        norm = norm.replace("..", "\n").replace(";", "\n")
        norm = norm.replace("•", "\n").replace("·", "\n").replace("●", "\n")
        norm = re.sub(r"\n?\s*[–—-]\s+", "\n", norm)
        parts = [p.strip(" .•\t") for p in norm.split("\n")]
        parts = [p for p in parts if p]

        looks_like_list = (
            len(parts) >= 2 and
            sum(1 for p in parts if len(p) <= 140) >= max(2, int(0.6 * len(parts)))
        )

        if not looks_like_list:
            return []

        def tidy(x: str) -> str:
            x = x.strip()
            if x.endswith("."):
                x = x[:-1].strip()
            if len(x) > 2 and x.isupper():
                x = x[:1].upper() + x[1:].lower()
            return x

        seen, out = set(), []
        for b in (tidy(p) for p in parts):
            k = b.lower()
            if b and k not in seen:
                out.append(b)
                seen.add(k)
        return out

    def find_product_by_upc(self, upc: str) -> str:
        """Locate product page URL for the given UPC from catalog."""
        self._ensure_catalog()
        clean = re.sub(r"\D", "", str(upc or ""))
        rec = self.by_upc.get(clean)
        return (rec or {}).get("product_url", "") or ""

    def enrich_product(self, input_row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a product record with data from the catalog.

        Args:
            input_row: Input product record (must contain UPC field)

        Returns:
            Enriched product record with manufacturer data
        """
        self._ensure_catalog()

        upc_digits = re.sub(r"\D", "", str(
            input_row.get("upc")
            or input_row.get("upc_updated")
            or input_row.get("upc_staged")
            or ""
        ))

        rec = self.by_upc.get(upc_digits, {})

        if rec:
            title = self._text_only(rec.get("product_name", ""))
            brand = self._text_only(rec.get("brand", ""))
            description_raw = self._text_only(rec.get("description", ""))

            description = re.sub(r"\s*\.\.\s*", ". ", description_raw).strip()
            if description and not description.endswith(".") and len(description.split()) > 8:
                description += "."

            benefits = self._benefits_from_description(description_raw)
            ingredients = self._text_only(rec.get("ingredients", ""))

            gallery: List[str] = []
            for url in rec.get("image_urls", []) or []:
                u = self._deproxy_image_url(url)
                if u and u not in gallery:
                    gallery.append(u)

            manufacturer = {
                "product_url": (rec.get("product_url") or "").strip(),
                "homepage": "https://www.bradleycaldwell.com",
                "name": title,
                "brand": brand,
                "product_name": title,
                "description": description,
                "benefits_text": benefits,
                "ingredients_text": ingredients,
                "nutrition_text": {},
                "directions_for_use": "",
                "media": gallery,
                "source_urls": [],
                "platform_guess": "",
                "ui_cues": []
            }
        else:
            manufacturer = {
                "product_url": "",
                "homepage": "https://www.bradleycaldwell.com",
                "name": "",
                "brand": "",
                "product_name": "",
                "description": "",
                "benefits_text": [],
                "ingredients_text": "",
                "nutrition_text": {},
                "directions_for_use": "",
                "media": [],
                "source_urls": [],
                "platform_guess": "",
                "ui_cues": []
            }

        shopify_media = [f"{upc_digits}_{i}.jpg" for i, _ in enumerate(manufacturer.get("media", []))]

        out = dict(input_row)
        out["manufacturer"] = manufacturer
        out["distributors_or_retailers"] = []
        out["shopify"] = {"media": shopify_media}

        return out

    def process_file(self, input_path: str, output_path: str) -> None:
        """
        Process an input JSON file and write enriched output.

        Args:
            input_path: Path to input JSON file (array of products)
            output_path: Path to output JSON file
        """
        with open(input_path, "r") as f:
            products = json.load(f)

        if not isinstance(products, list):
            raise ValueError("Input JSON must be an array of products")

        enriched = []
        for product in products:
            try:
                enriched_product = self.enrich_product(product)
                enriched.append(enriched_product)
            except Exception as e:
                print(f"Error processing product {product.get('upc', 'unknown')}: {e}")
                # Keep original product on error
                enriched.append(product)

        with open(output_path, "w") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)

        print(f"Processed {len(enriched)} products")
        print(f"Output written to: {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Bradley Caldwell Product Collector")
    parser.add_argument("--catalog", required=True, help="Path to product catalog JSON file")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    collector = BradleyCaldwellCollector(catalog_path=args.catalog)
    collector.process_file(args.input, args.output)


if __name__ == "__main__":
    main()

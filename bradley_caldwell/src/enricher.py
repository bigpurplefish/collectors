"""
Product enrichment logic for Bradley Caldwell Product Collector.

Handles enriching product records with catalog data.
"""

import re
from typing import Dict, Any, List
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from shared.src import (
    text_only,
    normalize_to_https,
    extract_bullet_points,
    deduplicate_urls,
)


class ProductEnricher:
    """Enriches product records with Bradley Caldwell catalog data."""

    HOMEPAGE = "https://www.bradleycaldwell.com"

    @staticmethod
    def _normalize_description(description: str) -> str:
        """
        Normalize description text.

        Cleans up double periods and adds ending period if needed.

        Args:
            description: Raw description text

        Returns:
            Normalized description
        """
        if not description:
            return ""

        # Clean up double periods
        desc = re.sub(r"\s*\.\.\s*", ". ", description).strip()

        # Add ending period if it looks like a sentence
        if desc and not desc.endswith(".") and len(desc.split()) > 8:
            desc += "."

        return desc

    @staticmethod
    def _build_empty_manufacturer() -> Dict[str, Any]:
        """
        Build empty manufacturer record.

        Returns:
            Empty manufacturer data structure
        """
        return {
            "product_url": "",
            "homepage": ProductEnricher.HOMEPAGE,
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

    @staticmethod
    def _extract_gallery(catalog_record: Dict[str, Any]) -> List[str]:
        """
        Extract and normalize gallery images from catalog record.

        Args:
            catalog_record: Catalog record containing image_urls

        Returns:
            List of normalized, deduplicated image URLs
        """
        gallery = []
        for url in catalog_record.get("image_urls", []) or []:
            normalized = normalize_to_https(url)
            if normalized:
                gallery.append(normalized)

        return deduplicate_urls(gallery)

    @classmethod
    def enrich(cls, input_row: Dict[str, Any], catalog_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a product record with catalog data.

        Args:
            input_row: Input product record
            catalog_record: Catalog data for this product (may be empty dict)

        Returns:
            Enriched product record with manufacturer data
        """
        from shared.src import normalize_upc

        # Extract UPC from input
        upc_digits = normalize_upc(
            input_row.get("upc")
            or input_row.get("upc_updated")
            or input_row.get("upc_staged")
            or ""
        )

        # Build manufacturer data
        if catalog_record:
            title = text_only(catalog_record.get("product_name", ""))
            brand = text_only(catalog_record.get("brand", ""))
            description_raw = text_only(catalog_record.get("description", ""))

            description = cls._normalize_description(description_raw)
            benefits = extract_bullet_points(description_raw)
            ingredients = text_only(catalog_record.get("ingredients", ""))
            gallery = cls._extract_gallery(catalog_record)

            manufacturer = {
                "product_url": (catalog_record.get("product_url") or "").strip(),
                "homepage": cls.HOMEPAGE,
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
            manufacturer = cls._build_empty_manufacturer()

        # Generate Shopify media filenames
        shopify_media = [
            f"{upc_digits}_{i}.jpg"
            for i, _ in enumerate(manufacturer.get("media", []))
        ]

        # Build output record
        out = dict(input_row)
        out["manufacturer"] = manufacturer
        out["distributors_or_retailers"] = []
        out["shopify"] = {"media": shopify_media}

        return out

"""
Catalog management for Ivyclassic collector.

Handles loading and looking up products from JSON catalog file.
"""

import json
import re
from typing import Dict, List, Optional, Callable


class CatalogManager:
    """Manages UPC to URL catalog for Ivyclassic."""

    def __init__(self, catalog_path: str = ""):
        """
        Initialize catalog manager.

        Args:
            catalog_path: Path to catalog JSON file
        """
        self.catalog_path = catalog_path
        self._catalog: Optional[Dict[str, str]] = None

    def set_catalog_path(self, path: Optional[str]) -> None:
        """
        Set or update the catalog path.

        Args:
            path: Path to catalog JSON file
        """
        self.catalog_path = (path or "").strip()
        self._catalog = None  # Force reload

    def _normalize_upc_variants(self, upc: str) -> List[str]:
        """
        Return a list of plausible UPC key forms to try against the catalog.
        Keeps only digits and tries 12/13/14-digit padded/sliced + stripped.

        Args:
            upc: UPC to normalize

        Returns:
            List of UPC variants to try
        """
        try:
            upc_num = re.sub(r"[^0-9]", "", upc or "")
        except Exception:
            upc_num = str(upc or "")

        variants: List[str] = []
        if not upc_num:
            return variants

        length = len(upc_num)
        for target in (12, 13, 14):
            if length == target:
                variants.append(upc_num)
            elif length < target:
                variants.append(upc_num.zfill(target))
            else:
                variants.append(upc_num[-target:])

        stripped = upc_num.lstrip("0")
        if stripped:
            if stripped not in variants:
                variants.append(stripped)
            for target in (12, 13, 14):
                cand = stripped.zfill(target) if len(stripped) <= target else stripped[-target:]
                if cand not in variants:
                    variants.append(cand)

        if upc_num not in variants:
            variants.append(upc_num)

        # Deduplicate while preserving order
        seen = set()
        out: List[str] = []
        for v in variants:
            if v and v not in seen:
                out.append(v)
                seen.add(v)
        return out

    def _ensure_catalog_loaded(self, log: Callable[[str], None]) -> None:
        """
        Load the JSON catalog one time (if a path is present).

        Args:
            log: Logging function
        """
        if self._catalog is not None:
            return

        self._catalog = {}
        if not self.catalog_path:
            log("[Ivy] No catalog_json_file path set.")
            return

        log(f"[Ivy] Loading catalog from: {self.catalog_path}")
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Accept either a mapping {upc: url, ...} or an array of {upc, url}
            if isinstance(data, dict):
                for k, v in data.items():
                    if v and isinstance(v, str):
                        self._catalog[str(k).strip()] = v.strip()
            elif isinstance(data, list):
                for row in data:
                    if not isinstance(row, dict):
                        continue
                    k = str(row.get("upc") or "").strip()
                    v = str(row.get("url") or "").strip()
                    if k and v:
                        self._catalog[k] = v
            else:
                log(f"[Ivy] Catalog is neither object nor array; ignoring contents.")

            log(f"[Ivy] Catalog loaded with {len(self._catalog)} entries.")
        except FileNotFoundError:
            log(f"[Ivy] Catalog file not found: {self.catalog_path}")
        except Exception as e:
            log(f"[Ivy] Catalog load error ({self.catalog_path}): {e}")

    def lookup(self, upc: str, log: Callable[[str], None]) -> Optional[str]:
        """
        Try to resolve UPC via the loaded catalog.

        Args:
            upc: UPC to lookup
            log: Logging function

        Returns:
            URL or None if not found
        """
        self._ensure_catalog_loaded(log)
        if not self._catalog:
            return None

        variants = self._normalize_upc_variants(upc)
        for key in [upc] + variants:
            url = self._catalog.get(key)
            if url:
                return url
        return None

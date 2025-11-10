"""
Product Index Builder for Cambridge Pavers

Crawls Cambridge public website to build a searchable product index.
Index is cached to avoid repeated crawling.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Callable
from bs4 import BeautifulSoup


# Category pages to crawl
CATEGORY_URLS = [
    "/pavers",
    "/walls",
    "/wallstones-stone-veneer",
    "/pavingstones-naturalstone",
    # Outdoor Living subcategories
    "/fireplaces",
    "/pizza-ovens",
    "/kitchens",
    "/waterfalls",
    "/fire-water",
    "/fountains",
    "/fire-tables-pits",
    "/grill-modules",
    "/patio-bistro-tables",
    "/bar-modules",
    "/caps-columns",
    "/steps-stairs",
    "/pergolas",
    "/umbrellas",
    "/garden-gate",
    "/outdoor-appliances",
    "/finishing-touches",
]


class CambridgeIndexBuilder:
    """Builds and manages product index for Cambridge Pavers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize index builder.

        Args:
            config: Site configuration dictionary
        """
        self.config = config
        self.origin = config.get("public_origin", "https://www.cambridgepavers.com")

    def build_index(
        self,
        http_get: Callable,
        timeout: float = 30,
        log: Callable = print
    ) -> Dict[str, Any]:
        """
        Build product index by crawling all category pages.

        Args:
            http_get: HTTP GET function
            timeout: Request timeout in seconds
            log: Logging function

        Returns:
            Index dictionary with products array and metadata
        """
        log("=" * 80)
        log("BUILDING CAMBRIDGE PRODUCT INDEX")
        log("=" * 80)

        products = []
        seen_prodids = set()

        # Crawl each category page
        for category_url in CATEGORY_URLS:
            log(f"\nCrawling category: {category_url}")
            full_url = f"{self.origin}{category_url}"

            try:
                response = http_get(full_url, timeout=timeout)
                if response.status_code != 200:
                    log(f"  ⚠ Failed to fetch {category_url}: HTTP {response.status_code}")
                    continue

                # Parse category page for product links
                soup = BeautifulSoup(response.text, "lxml")
                category_products = self._extract_products_from_page(soup, log)

                # Add new products to index
                for product in category_products:
                    prodid = product["prodid"]
                    if prodid not in seen_prodids:
                        products.append(product)
                        seen_prodids.add(prodid)
                        log(f"  ✓ Found: {product['title']} (prodid={prodid})")

            except Exception as e:
                log(f"  ❌ Error crawling {category_url}: {e}")
                continue

        # Build index structure
        index = {
            "last_updated": datetime.now().isoformat(),
            "total_products": len(products),
            "products": products
        }

        log("")
        log("=" * 80)
        log(f"INDEX BUILD COMPLETE: {len(products)} products found")
        log("=" * 80)

        return index

    def _extract_products_from_page(
        self,
        soup: BeautifulSoup,
        log: Callable = print
    ) -> List[Dict[str, Any]]:
        """
        Extract product information from category page.

        Args:
            soup: BeautifulSoup object of category page
            log: Logging function

        Returns:
            List of product dictionaries
        """
        products = []

        # Find all links with prodid parameter
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "pavers-details?prodid=" in href or "prodid=" in href:
                # Extract prodid
                try:
                    prodid_str = href.split("prodid=")[1].split("&")[0]
                    prodid = int(prodid_str)
                except (IndexError, ValueError):
                    continue

                # Extract product title from the link's parent structure
                # The title is typically in a specific pattern on Cambridge pages
                title = ""

                # Try to find the title in the overlay-info div
                parent = link.find_parent()
                if parent:
                    # Look for product title in specific elements
                    # Pattern: <h5>Product Title</h5> inside overlay-info
                    h5 = parent.find("h5")
                    if h5:
                        title = h5.get_text(strip=True)
                    else:
                        # Fallback: try to extract from structured text
                        full_text = parent.get_text(strip=True)
                        # The pattern is often: "Color Shown Title Collection Description"
                        # We want to extract just the "Title" part
                        # Split and look for "Collection" to find boundaries
                        if "Collection" in full_text:
                            # Extract text before "Collection"
                            before_collection = full_text.split("Collection")[0]
                            # Remove color info (typically ends with "Shown")
                            if "Shown" in before_collection:
                                parts = before_collection.split("Shown")
                                if len(parts) > 1:
                                    # Get the part between "Shown" and collection name
                                    # Collection names: Sherwood, RoundTable, KingsCourt, etc.
                                    middle = parts[1].strip()
                                    # Remove collection name at the end
                                    for coll in ["Sherwood", "RoundTable", "KingsCourt", "Excalibur",
                                                 "Crusader", "MaytRx", "Olde English Wall", "Omega",
                                                 "Pyzique", "Sigma", "Curbstone", "Edgestone"]:
                                        if middle.endswith(coll):
                                            title = middle[:-len(coll)].strip()
                                            break
                                    if not title:
                                        title = middle
                                else:
                                    title = before_collection.strip()
                            else:
                                title = before_collection.strip()

                if title and prodid not in [p["prodid"] for p in products]:
                    products.append({
                        "prodid": prodid,
                        "title": title,
                        "url": f"/pavers-details?prodid={prodid}",
                        "category": self._extract_category_from_page(soup)
                    })

        return products

    def _extract_category_from_page(self, soup: BeautifulSoup) -> str:
        """
        Extract category/collection name from page.

        Args:
            soup: BeautifulSoup object

        Returns:
            Category name or empty string
        """
        # Try to find category in page title or h1
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)

        return ""


def save_index_to_cache(index: Dict[str, Any], cache_file: str, log: Callable = print):
    """
    Save index to cache file.

    Args:
        index: Index dictionary
        cache_file: Path to cache file
        log: Logging function
    """
    try:
        # Ensure cache directory exists
        cache_dir = os.path.dirname(cache_file)
        os.makedirs(cache_dir, exist_ok=True)

        # Save index
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        log(f"\n✓ Index saved to cache: {cache_file}")
    except Exception as e:
        log(f"\n❌ Failed to save index to cache: {e}")
        raise


def load_index_from_cache(cache_file: str, log: Callable = print) -> Dict[str, Any]:
    """
    Load index from cache file.

    Args:
        cache_file: Path to cache file
        log: Logging function

    Returns:
        Index dictionary or None if cache doesn't exist
    """
    if not os.path.exists(cache_file):
        log(f"Cache file not found: {cache_file}")
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            index = json.load(f)

        log(f"✓ Loaded index from cache: {cache_file}")
        log(f"  Last updated: {index.get('last_updated', 'Unknown')}")
        log(f"  Total products: {index.get('total_products', 0)}")

        return index
    except Exception as e:
        log(f"❌ Failed to load index from cache: {e}")
        return None


def is_index_stale(index: Dict[str, Any], max_age_days: int = 7) -> bool:
    """
    Check if index is older than max_age_days.

    Args:
        index: Index dictionary
        max_age_days: Maximum age in days

    Returns:
        True if index is stale, False otherwise
    """
    if not index or "last_updated" not in index:
        return True

    try:
        last_updated = datetime.fromisoformat(index["last_updated"])

        # Handle both timezone-aware and timezone-naive timestamps
        if last_updated.tzinfo is not None:
            # Timestamp is timezone-aware (has Z suffix), compare with UTC now
            from datetime import timezone
            now = datetime.now(timezone.utc)
        else:
            # Timestamp is timezone-naive, compare with local now
            now = datetime.now()

        age_days = (now - last_updated).days
        return age_days > max_age_days
    except Exception:
        return True

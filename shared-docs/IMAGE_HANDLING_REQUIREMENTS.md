# Image Handling Requirements

## Overview

This document defines the requirements for handling product images in collectors, including URL normalization, deduplication, alt tag generation, and Shopify-specific formatting.

**Last Updated**: November 11, 2025

---

## Image URL Handling

### Querystring Stripping

**Requirement**: All image URLs must have querystrings stripped before being added to the product gallery.

**Why**:
- Querystrings often contain session tokens, tracking parameters, or cache-busting values
- Same image may appear with different querystrings causing false duplicates
- Shopify image hosting works better with clean URLs

**Implementation**:
```python
from urllib.parse import urlparse, urlunparse

def strip_querystring(url: str) -> str:
    """
    Strip querystring from URL.

    Examples:
        "https://example.com/image.jpg?v=123&cache=456" -> "https://example.com/image.jpg"
        "https://example.com/image.jpg" -> "https://example.com/image.jpg"
    """
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))
```

---

## Image Validation

### URL Resolution Check

**Requirement**: After stripping querystrings, verify that the cleaned URL resolves correctly (returns 200 OK).

**Why**:
- Some images may require querystring parameters to work
- Broken images should be filtered out
- Only valid URLs should be added to gallery

**Implementation**:
```python
import requests

def verify_image_url(url: str, timeout: int = 10) -> bool:
    """
    Verify image URL resolves correctly.

    Args:
        url: Image URL to verify
        timeout: Request timeout in seconds

    Returns:
        True if URL returns 200 OK, False otherwise
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except:
        return False
```

**Fallback Behavior**:
- If cleaned URL fails verification, try the original URL with querystring
- If both fail, log warning and skip the image
- Don't block the entire product due to one bad image

---

## Image Deduplication

### Per-Variant Deduplication

**Requirement**: Remove duplicate images from the gallery, checking by variant.

**Why**:
- Same image may appear multiple times from different sources
- Portal and public site may have overlapping images
- Different color variants may share images

**Deduplication Rules**:
1. **By URL**: Two images with identical cleaned URLs are duplicates
2. **By Variant**: Deduplication is done per product family, not globally
3. **Priority**: When duplicates exist, keep whichever version works (verified URL)
4. **Position**: Maintain the order of first occurrence

**Implementation**:
```python
def deduplicate_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate images from gallery while preserving order.

    Args:
        images: List of image dictionaries with 'src' and 'alt' keys

    Returns:
        Deduplicated list with original order preserved
    """
    seen_urls = set()
    deduplicated = []

    for img in images:
        url = strip_querystring(img['src'])

        if url not in seen_urls:
            seen_urls.add(url)
            # Update image to use cleaned URL
            img['src'] = url
            deduplicated.append(img)

    return deduplicated
```

---

## Alt Tag Generation

### Shopify Image Filtering Format

**Requirement**: Image alt tags must be formatted for Shopify's image filtering feature.

**Format**: `#[option1]#[option2]#[option3]`
- Each variant option value is wrapped in `#` symbols
- Options are appended in order (option1, option2, option3, option4)
- Used by Shopify to filter product images by selected variant

**Why**:
- Shopify uses alt tags to determine which images to show for each variant
- When customer selects "Red" color, only images with `#Red#` in alt tag are shown
- Essential for proper variant image display in Shopify storefronts

**Examples**:

| Variant Options | Alt Tag Format | Example |
|----------------|----------------|---------|
| Color: "Onyx Natural" | `#Onyx Natural#` | `#Onyx Natural#` |
| Color: "Red", Size: "Large" | `#Red#Large#` | `#Red#Large#` |
| Color: "Blue", Material: "Wood", Finish: "Matte" | `#Blue#Wood#Matte#` | `#Blue#Wood#Matte#` |

**Special Cases**:
- **Lifestyle images (no variant association)**: Use product title as alt text (no `#` symbols)
- **Hero images**: Use product title + "Hero" as alt text
- **Gallery images**: Use product title + "Lifestyle" or "Gallery" as alt text

**Implementation**:
```python
def generate_variant_alt_tag(options: Dict[str, Any]) -> str:
    """
    Generate Shopify-compatible alt tag for variant images.

    Args:
        options: Dictionary with option1, option2, option3, option4 values

    Returns:
        Formatted alt tag string

    Examples:
        {"option1": "Red"} -> "#Red#"
        {"option1": "Red", "option2": "Large"} -> "#Red#Large#"
    """
    alt_parts = []

    for i in range(1, 5):
        option_value = options.get(f"option{i}", "")
        if option_value:
            alt_parts.append(f"#{option_value}#")

    return "".join(alt_parts) if alt_parts else ""


def generate_lifestyle_alt_tag(product_title: str, image_type: str = "Lifestyle") -> str:
    """
    Generate alt tag for lifestyle/hero images.

    Args:
        product_title: Product title
        image_type: Type of image (Hero, Lifestyle, Gallery, etc.)

    Returns:
        Alt tag string

    Examples:
        ("Sherwood Ledgestone", "Hero") -> "Sherwood Ledgestone - Hero"
        ("Sherwood Ledgestone", "Lifestyle") -> "Sherwood Ledgestone - Lifestyle"
    """
    return f"{product_title} - {image_type}"
```

---

## Image Source Priority

### Portal Images (Product Images)

**Requirement**: Portal images are product-specific and should be captured ONLY from the image gallery on the product page.

**Why**:
- Portal has the most accurate product images
- Gallery images are the official product photos
- Other images on page may be UI elements, thumbnails, or unrelated

**Capture Method**: Use Playwright to render the page and extract gallery images in order

**Example Selectors** (adjust per site):
```python
# Wait for gallery to load
page.wait_for_selector(".product-gallery")

# Get gallery images in order
gallery_images = page.query_selector_all(".product-gallery img[src]")
image_urls = [img.get_attribute("src") for img in gallery_images]
```

**Image Order**: Maintain the exact order images appear in the gallery

---

### Public Images (Lifestyle Images)

**Requirement**: Public website images should be captured ONLY from:
1. **Hero image** (main product image)
2. **Gallery carousel** (additional lifestyle images)

**Why**:
- Hero image is the primary lifestyle/marketing image
- Gallery carousel contains additional lifestyle shots
- Other images on page are UI chrome, thumbnails, or unrelated content

**Capture Method**: Use BeautifulSoup or Playwright to extract hero + gallery images

**Example Implementation**:
```python
def extract_public_images(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract hero and gallery images from public website."""
    images = {
        "hero_image": "",
        "gallery_images": []
    }

    # Extract hero image
    hero_container = soup.find("div", class_="image-box")
    if hero_container:
        img = hero_container.find("img", src=True)
        if img:
            images["hero_image"] = strip_querystring(img["src"])

    # Extract gallery images (in order)
    carousel = soup.find("div", class_="owl-carousel")
    if carousel:
        for img in carousel.find_all("img", src=True):
            url = strip_querystring(img["src"])
            if url and url not in images["gallery_images"]:
                images["gallery_images"].append(url)

    return images
```

**Image Order**:
1. Hero image first
2. Gallery images in the order they appear in carousel

---

## Complete Image Processing Pipeline

### Step-by-Step Process

1. **Extract Images**
   - Portal: Extract gallery images only (Playwright)
   - Public: Extract hero + gallery carousel only (BeautifulSoup/Playwright)

2. **Strip Querystrings**
   - Remove all querystring parameters from URLs
   - Keep fragment identifiers if present

3. **Verify URLs**
   - Check that cleaned URLs resolve (200 OK)
   - Fallback to original URL if cleaned version fails
   - Skip images that fail both checks

4. **Deduplicate**
   - Remove duplicate URLs per product family
   - Keep first occurrence
   - Maintain original order

5. **Generate Alt Tags**
   - Variant images: Use `#[option1]#[option2]#...` format
   - Lifestyle images: Use `{title} - {type}` format

6. **Build Gallery**
   - Phase 1: Add portal images (all variants) with variant alt tags
   - Phase 2: Add public hero image with lifestyle alt tag
   - Phase 3: Add public gallery images with lifestyle alt tags

**Example Implementation**:
```python
def build_product_gallery(
    portal_images_by_variant: Dict[str, List[str]],
    public_hero_image: str,
    public_gallery_images: List[str],
    product_title: str,
    variants: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Build complete product image gallery.

    Args:
        portal_images_by_variant: Portal images indexed by variant option values
        public_hero_image: Hero image URL from public site
        public_gallery_images: Gallery image URLs from public site
        product_title: Product title
        variants: List of variant dictionaries with option1, option2, etc.

    Returns:
        List of image dictionaries with src, alt, position
    """
    images = []
    position = 1

    # Phase 1: Portal images (variant-specific)
    for variant in variants:
        variant_key = variant.get("option1", "")
        variant_images = portal_images_by_variant.get(variant_key, [])

        # Generate variant alt tag
        alt_tag = generate_variant_alt_tag({
            "option1": variant.get("option1"),
            "option2": variant.get("option2"),
            "option3": variant.get("option3"),
            "option4": variant.get("option4"),
        })

        for img_url in variant_images:
            clean_url = strip_querystring(img_url)
            if verify_image_url(clean_url):
                images.append({
                    "position": position,
                    "src": clean_url,
                    "alt": alt_tag
                })
                position += 1

    # Phase 2: Public hero image
    if public_hero_image:
        clean_url = strip_querystring(public_hero_image)
        if verify_image_url(clean_url):
            images.append({
                "position": position,
                "src": clean_url,
                "alt": generate_lifestyle_alt_tag(product_title, "Hero")
            })
            position += 1

    # Phase 3: Public gallery images
    for img_url in public_gallery_images:
        clean_url = strip_querystring(img_url)
        if verify_image_url(clean_url):
            images.append({
                "position": position,
                "src": clean_url,
                "alt": generate_lifestyle_alt_tag(product_title, "Lifestyle")
            })
            position += 1

    # Deduplicate while preserving order
    return deduplicate_images(images)
```

---

## Testing Requirements

### Unit Tests

Collectors should include tests for:

1. **Querystring stripping**
   - URLs with querystrings
   - URLs without querystrings
   - URLs with fragments
   - Edge cases (empty URL, malformed URL)

2. **URL verification**
   - Valid URLs (200 OK)
   - Invalid URLs (404, 500, timeout)
   - Network errors

3. **Deduplication**
   - Duplicate URLs
   - Different querystrings, same base URL
   - Empty lists
   - Single image

4. **Alt tag generation**
   - Single option variant
   - Multi-option variant (2, 3, 4 options)
   - Lifestyle images
   - Edge cases (empty options, null values)

### Integration Tests

Test complete image pipeline:
- Extract images from real product pages
- Verify correct image count
- Verify correct alt tags
- Verify no duplicates
- Verify proper ordering

---

## Common Pitfalls

1. **Don't strip fragments**: URL fragments (#section) are different from querystrings (?param=value)
   - ❌ Wrong: Strip both `?` and `#`
   - ✅ Correct: Only strip `?` and its parameters

2. **Don't verify synchronously in loop**: Verifying 50 images one-by-one is slow
   - ❌ Wrong: `for url in urls: verify(url)`
   - ✅ Better: Use concurrent requests or batch verification

3. **Don't forget option order**: Shopify expects options in order
   - ❌ Wrong: `#Large#Red#` (when option1=Red, option2=Large)
   - ✅ Correct: `#Red#Large#`

4. **Don't add empty alt tags**: Missing values should be skipped
   - ❌ Wrong: `#Red###` (empty option2 and option3)
   - ✅ Correct: `#Red#` (only include populated options)

---

## See Also

- [GraphQL Output Requirements](/Users/moosemarketer/Code/shared-docs/python/GRAPHQL_OUTPUT_REQUIREMENTS.md) - Shopify product format
- [Input File Structure](INPUT_FILE_STRUCTURE.md) - Variant option configuration
- [Technical Docs](/Users/moosemarketer/Code/shared-docs/python/TECHNICAL_DOCS.md) - Implementation patterns

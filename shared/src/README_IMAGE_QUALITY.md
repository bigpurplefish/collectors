# Image Quality Assessment Module

**Location:** `/collectors/shared/src/image_quality.py`
**Purpose:** Select the highest quality product image from multiple candidates
**Used By:** All collectors with UPCItemDB fallback functionality

---

## Overview

This module provides functions to evaluate and select the best product image from a list of URLs based on multiple quality metrics. It ensures consistent image quality standards across all product collectors.

## Features

- ✅ **Sharpness Detection**: Laplacian variance to measure image focus
- ✅ **Placeholder Detection**: Perceptual hashing to identify generic/placeholder images
- ✅ **Whitespace Cropping**: Remove borders for accurate size measurement
- ✅ **Querystring Stripping**: Automatic removal of URL parameters with fallback to original
- ✅ **Smart Selection**: Prioritize larger, sharper images
- ✅ **Error Handling**: Graceful handling of download failures and invalid images
- ✅ **Logging**: Detailed output for debugging selection process

---

## Quick Start

```python
from shared.src.image_quality import load_placeholder_images, select_best_image

# 1. Load placeholder images for comparison
placeholders = load_placeholder_images("/path/to/placeholder_images/")

# 2. Define image URLs to evaluate
image_urls = [
    "https://example.com/product1.jpg",
    "https://example.com/product2.jpg",
    "https://example.com/product3.jpg"
]

# 3. Select best image
best_image, best_url = select_best_image(
    image_urls=image_urls,
    placeholders=placeholders,
    laplacian_threshold=100,  # Minimum sharpness score
    hamming_threshold=10,     # Maximum placeholder similarity
    log=print                 # Logging function
)

# 4. Use the selected image
if best_image:
    best_image.save("output/best_product_image.jpg", "JPEG", quality=95)
    print(f"Selected: {best_url}")
else:
    print("No suitable images found")
```

---

## Functions

### `calculate_laplacian_score(image: Image.Image) -> float`

Calculate the Laplacian variance (sharpness metric) for an image.

**Parameters:**
- `image`: PIL Image object

**Returns:**
- `float`: Laplacian variance score (higher = sharper)

**Example:**
```python
from PIL import Image
from shared.src.image_quality import calculate_laplacian_score

img = Image.open("product.jpg")
sharpness = calculate_laplacian_score(img)
print(f"Sharpness score: {sharpness:.2f}")
# Output: Sharpness score: 235.67
```

---

### `crop_whitespace(image: Image.Image) -> Image.Image`

Crop whitespace borders from an image.

**Parameters:**
- `image`: PIL Image object

**Returns:**
- PIL Image object with whitespace removed

**Example:**
```python
from PIL import Image
from shared.src.image_quality import crop_whitespace

img = Image.open("product_with_borders.jpg")
cropped = crop_whitespace(img)
cropped.save("product_cropped.jpg")
```

---

### `load_placeholder_images(placeholder_dir: str) -> List[Image.Image]`

Load placeholder images from directory for comparison.

**Parameters:**
- `placeholder_dir`: Path to directory containing placeholder images

**Returns:**
- List of PIL Image objects

**Example:**
```python
from shared.src.image_quality import load_placeholder_images

placeholders = load_placeholder_images("/collectors/placeholder_images/")
print(f"Loaded {len(placeholders)} placeholder images")
```

**Directory Structure:**
```
placeholder_images/
├── placeholder1.jpg
├── placeholder2.jpg
└── placeholder3.png
```

---

### `strip_querystring(url: str) -> str`

Strip querystring parameters and fragments from URL.

**Parameters:**
- `url`: URL potentially with querystring parameters

**Returns:**
- URL without querystring or fragment

**Example:**
```python
from shared.src.image_quality import strip_querystring

original = "https://cdn.example.com/image.jpg?width=500&height=500#anchor"
clean = strip_querystring(original)
print(clean)  # "https://cdn.example.com/image.jpg"
```

**Usage in select_best_image:**
The function automatically:
1. Strips querystring from each URL
2. Tests stripped version first (preferred)
3. Falls back to original URL if stripped version fails
4. Returns the working URL (stripped or original) in output

---

### `is_placeholder(image: Image.Image, placeholders: List[Image.Image], threshold: int = 10) -> bool`

Check if an image matches known placeholder images using perceptual hashing.

**Parameters:**
- `image`: PIL Image object to check
- `placeholders`: List of known placeholder images
- `threshold`: Hamming distance threshold (default: 10)

**Returns:**
- `bool`: True if image matches a placeholder

**Example:**
```python
from shared.src.image_quality import load_placeholder_images, is_placeholder
from PIL import Image

placeholders = load_placeholder_images("placeholder_images/")
img = Image.open("candidate.jpg")

if is_placeholder(img, placeholders):
    print("Image is a placeholder - rejecting")
else:
    print("Image is unique - accepting")
```

**How It Works:**
- Uses perceptual hashing (pHash) to create image fingerprint
- Compares Hamming distance between hashes
- Distance ≤ threshold = placeholder match

---

### `download_image(url: str, retries: int = 1, delay: int = 2) -> Optional[Image.Image]`

Download image from URL with retry logic and validation.

**Parameters:**
- `url`: Image URL to download
- `retries`: Number of retry attempts (default: 1)
- `delay`: Delay between retries in seconds (default: 2)

**Returns:**
- PIL Image object or None if download fails

**Example:**
```python
from shared.src.image_quality import download_image

img = download_image("https://example.com/product.jpg", retries=3)
if img:
    print(f"Downloaded: {img.width}x{img.height}")
else:
    print("Download failed")
```

**Features:**
- Validates Content-Type header
- Handles HTTP errors (403, 404)
- Retry logic for transient failures
- Converts to RGB format

---

### `select_best_image(...) -> Tuple[Optional[Image.Image], Optional[str]]`

Select the best image from a list of URLs based on quality metrics.

**Full Signature:**
```python
def select_best_image(
    image_urls: List[str],
    placeholders: List[Image.Image],
    laplacian_threshold: int = 100,
    hamming_threshold: int = 10,
    log: callable = print
) -> Tuple[Optional[Image.Image], Optional[str]]
```

**Parameters:**
- `image_urls`: List of image URLs to evaluate
- `placeholders`: List of placeholder images to filter out
- `laplacian_threshold`: Minimum Laplacian score (default: 100)
- `hamming_threshold`: Maximum Hamming distance for placeholders (default: 10)
- `log`: Logging function (default: print)

**Returns:**
- Tuple of (best_image, source_url) or (None, None)

**Selection Criteria (in order):**
1. Strip querystring from URL and test (prefer clean URLs)
2. Download & validate (try stripped first, fallback to original)
3. Detect and skip placeholder images
4. Crop whitespace
5. Check sharpness (Laplacian score)
6. Prefer larger dimensions
7. Use sharpness as tiebreaker
8. Return working URL (stripped or original)

**Example:**
```python
from shared.src.image_quality import load_placeholder_images, select_best_image

placeholders = load_placeholder_images("placeholder_images/")

urls = [
    "https://example.com/small.jpg",      # 300x300, sharp
    "https://example.com/large_blurry.jpg",  # 800x800, blurry (score 50)
    "https://example.com/large_sharp.jpg"    # 800x800, sharp (score 250)
]

best, url = select_best_image(
    image_urls=urls,
    placeholders=placeholders,
    laplacian_threshold=100,
    log=print
)

# Output:
#   Evaluating 3 candidate image(s)...
#     ✗ Low quality (score=50.0): https://example.com/large_blurry.jpg
#     ✓ New best: 300x300, score=180.5
#     ✓ New best: 800x800, score=250.3
#   Selected best image: https://example.com/large_sharp.jpg
#     Dimensions: 800x800
#     Sharpness score: 250.3
```

---

## Quality Metrics

### Laplacian Variance (Sharpness)

Measures edge definition and focus quality.

- **Score < 100**: Blurry, reject
- **Score 100-200**: Acceptable quality
- **Score > 200**: Sharp, high quality

**Technical Details:**
- Converts image to grayscale
- Applies Laplacian operator (edge detection)
- Calculates variance of result
- Higher variance = sharper edges

### Perceptual Hashing (Placeholder Detection)

Creates a compact fingerprint of visual content.

- **Hamming Distance ≤ 10**: Placeholder match, reject
- **Hamming Distance > 10**: Unique image, accept

**Technical Details:**
- Uses pHash algorithm (imagehash library)
- Compares 64-bit hash values
- Hamming distance = number of differing bits
- Robust to minor variations (cropping, compression)

### Dimensions (Size Priority)

Larger images provide better quality potential.

- **Priority**: width × height
- **Example**: 800×800 (640,000) > 600×600 (360,000)

---

## Integration Example

### Basic UPCItemDB Fallback

```python
import sys
import os

# Add parent path for shared imports
parent_path = os.path.dirname(os.path.dirname(__file__))
if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

from shared.src.image_quality import load_placeholder_images, select_best_image
import ast

# Load placeholders once at startup
placeholder_dir = os.path.join(parent_path, "placeholder_images")
placeholders = load_placeholder_images(placeholder_dir)

# During product processing
def process_upcitemdb_fallback(product, laplacian_threshold=100):
    # Get image URLs (handle Excel string format)
    image_urls_raw = product.get('upcitemdb_images', [])

    if isinstance(image_urls_raw, str):
        try:
            image_urls = ast.literal_eval(image_urls_raw)
        except (ValueError, SyntaxError):
            return None, None
    else:
        image_urls = image_urls_raw

    if not image_urls:
        return None, None

    # Select best image
    best_image, best_url = select_best_image(
        image_urls=image_urls,
        placeholders=placeholders,
        laplacian_threshold=laplacian_threshold,
        hamming_threshold=10,
        log=print
    )

    return best_image, best_url
```

---

## Dependencies

Install required packages:

```bash
pip install Pillow>=10.0.0 opencv-python>=4.8.0 numpy>=1.24.0 imagehash>=4.3.0
```

**Package Purposes:**
- **Pillow**: Image loading and manipulation
- **opencv-python**: Laplacian variance calculation
- **numpy**: Required by OpenCV
- **imagehash**: Perceptual hashing (pHash)

---

## Configuration

### Recommended Settings

| Parameter | Default | Range | Purpose |
|-----------|---------|-------|---------|
| `laplacian_threshold` | 100 | 0-500 | Minimum sharpness score |
| `hamming_threshold` | 10 | 0-64 | Maximum placeholder similarity |

### Tuning Guidelines

**Laplacian Threshold:**
- **Lower (50-80)**: Accept more images, including slightly blurry
- **Default (100)**: Balanced - rejects obvious blur
- **Higher (150-200)**: Very strict - only sharp images

**Hamming Threshold:**
- **Lower (5-8)**: Strict placeholder detection
- **Default (10)**: Balanced - catches most placeholders
- **Higher (12-15)**: Lenient - only exact matches

---

## Testing

### Test Image Quality

```python
from shared.src.image_quality import calculate_laplacian_score, is_placeholder, load_placeholder_images
from PIL import Image

# Test sharpness
img = Image.open("test_image.jpg")
score = calculate_laplacian_score(img)
print(f"Sharpness: {score:.2f} - {'Sharp' if score >= 100 else 'Blurry'}")

# Test placeholder detection
placeholders = load_placeholder_images("placeholder_images/")
is_ph = is_placeholder(img, placeholders)
print(f"Placeholder: {'Yes' if is_ph else 'No'}")
```

### Test Selection Algorithm

```python
from shared.src.image_quality import load_placeholder_images, select_best_image

placeholders = load_placeholder_images("placeholder_images/")

test_urls = [
    "https://i5.walmartimages.com/asr/abc123.jpeg",
    "https://images.example.com/product.jpg",
    "https://cdn.shopify.com/s/files/1/0123/4567/products/item.jpg"
]

best, url = select_best_image(
    image_urls=test_urls,
    placeholders=placeholders,
    laplacian_threshold=100,
    log=print
)

if best:
    print(f"\nWinner: {url}")
    print(f"Size: {best.width}x{best.height}")
```

---

## Troubleshooting

### No Images Pass Quality Check

**Problem:** All images rejected for low sharpness

**Solution:**
- Lower `laplacian_threshold` (try 50-80)
- Check if images are genuinely blurry
- Verify image URLs are valid

### All Images Detected as Placeholders

**Problem:** Legitimate images rejected as placeholders

**Solution:**
- Increase `hamming_threshold` (try 15-20)
- Review placeholder images directory
- Ensure placeholder images are truly generic

### Download Failures

**Problem:** Cannot download images from URLs

**Solution:**
- Check network connectivity
- Verify URLs are accessible
- Increase `retries` parameter
- Check for rate limiting

---

## Best Practices

✅ **Do:**
- Load placeholders once at application startup
- Use descriptive log messages
- Save best image immediately after selection
- Handle None return values gracefully
- Test with various image qualities

❌ **Don't:**
- Reload placeholders for every image check
- Skip whitespace cropping before dimension comparison
- Ignore log output (contains valuable debugging info)
- Use extremely high thresholds (may reject all images)
- Forget to handle Excel string array format

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-05 | Initial release - Extracted from Purinamills collector |

---

## See Also

- [UPCITEMDB_FALLBACK_REQUIREMENTS.md](../../shared-docs/UPCITEMDB_FALLBACK_REQUIREMENTS.md)
- [OpenCV Laplacian Documentation](https://docs.opencv.org/4.x/d5/db5/tutorial_laplace_operator.html)
- [imagehash Library](https://github.com/JohannesBuchner/imagehash)

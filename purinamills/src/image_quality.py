"""
Image quality assessment utilities for UPCItemDB image selection.

Provides functions to evaluate and select the best image from multiple candidates
based on quality metrics like sharpness, dimensions, and placeholder detection.
"""

import os
import cv2
import numpy as np
import imagehash
import requests
from io import BytesIO
from PIL import Image
from typing import List, Optional, Tuple
import logging


def calculate_laplacian_score(image: Image.Image) -> float:
    """
    Calculate Laplacian variance (sharpness metric) for an image.

    Higher scores indicate sharper images with more detail.

    Args:
        image: PIL Image object

    Returns:
        float: Laplacian variance score
    """
    gray = np.array(image.convert("L"))
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def crop_whitespace(image: Image.Image) -> Image.Image:
    """
    Crop whitespace borders from an image.

    Args:
        image: PIL Image object

    Returns:
        Cropped PIL Image object
    """
    bg = image.convert("L")
    bbox = bg.point(lambda x: 0 if x < 255 else 255).getbbox()
    return image.crop(bbox) if bbox else image


def load_placeholder_images(placeholder_dir: str) -> List[Image.Image]:
    """
    Load placeholder images from directory for comparison.

    Args:
        placeholder_dir: Path to directory containing placeholder images

    Returns:
        List of PIL Image objects
    """
    placeholders = []
    if not os.path.exists(placeholder_dir):
        logging.warning(f"Placeholder directory not found: {placeholder_dir}")
        return placeholders

    for filename in os.listdir(placeholder_dir):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                img_path = os.path.join(placeholder_dir, filename)
                img = Image.open(img_path).convert("RGB")
                placeholders.append(img)
            except Exception as e:
                logging.warning(f"Failed to load placeholder image {filename}: {e}")

    return placeholders


def is_placeholder(image: Image.Image, placeholders: List[Image.Image], threshold: int = 10) -> bool:
    """
    Check if image is a placeholder using perceptual hashing.

    Args:
        image: PIL Image object to check
        placeholders: List of known placeholder images
        threshold: Hamming distance threshold for match

    Returns:
        bool: True if image matches a placeholder
    """
    if not placeholders:
        return False

    image_hash = imagehash.phash(image)
    return any(image_hash - imagehash.phash(ph) <= threshold for ph in placeholders)


def download_image(url: str, retries: int = 1, delay: int = 2) -> Optional[Image.Image]:
    """
    Download image from URL with retry logic.

    Args:
        url: Image URL to download
        retries: Number of retry attempts
        delay: Delay between retries in seconds

    Returns:
        PIL Image object or None if download fails
    """
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            # Validate content type
            if not r.headers.get("Content-Type", "").startswith("image/"):
                logging.info(f"Skipping non-image URL: {url}")
                return None

            return Image.open(BytesIO(r.content)).convert("RGB")

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code in (403, 404):
                logging.info(f"Image not accessible ({status_code}): {url}")
                return None  # No point retrying
            else:
                logging.warning(f"HTTP error for {url}: {e}")

        except requests.exceptions.RequestException as e:
            logging.info(f"Network error for {url}: {e}")

        except Exception as e:
            logging.warning(f"Unexpected error for {url}: {e}")

    return None


def select_best_image(
    image_urls: List[str],
    placeholders: List[Image.Image],
    laplacian_threshold: int = 100,
    hamming_threshold: int = 10,
    log: callable = print
) -> Tuple[Optional[Image.Image], Optional[str]]:
    """
    Select the best image from a list of URLs based on quality metrics.

    Selection criteria (in order):
    1. Download & validate
    2. Detect and skip placeholder images
    3. Crop whitespace
    4. Check sharpness (Laplacian score)
    5. Prefer larger dimensions
    6. Use sharpness as tiebreaker

    Args:
        image_urls: List of image URLs to evaluate
        placeholders: List of placeholder images to filter out
        laplacian_threshold: Minimum Laplacian score (sharpness). Default: 100
        hamming_threshold: Maximum Hamming distance for placeholder detection
        log: Logging function

    Returns:
        Tuple of (best_image, source_url) or (None, None) if no suitable image found
    """
    best_image = None
    best_score = 0
    best_dim = 0
    best_source_url = None

    log(f"  Evaluating {len(image_urls)} candidate image(s)...")

    for url in image_urls:
        # Download image
        img = download_image(url)
        if img is None:
            log(f"    ✗ Failed to download: {url[:60]}...")
            continue

        # Check if placeholder
        if is_placeholder(img, placeholders, hamming_threshold):
            log(f"    ✗ Placeholder detected: {url[:60]}...")
            continue

        # Crop whitespace
        cropped = crop_whitespace(img)

        # Calculate sharpness
        lap_score = calculate_laplacian_score(cropped)
        if lap_score < laplacian_threshold:
            log(f"    ✗ Low quality (score={lap_score:.1f}): {url[:60]}...")
            continue

        # Calculate dimensions
        dim = cropped.width * cropped.height

        # Select based on dimensions first, then sharpness
        if dim > best_dim or (dim == best_dim and lap_score > best_score):
            best_image = cropped
            best_score = lap_score
            best_dim = dim
            best_source_url = url
            log(f"    ✓ New best: {cropped.width}x{cropped.height}, score={lap_score:.1f}")

    if best_image:
        log(f"  Selected best image: {best_source_url[:60]}...")
        log(f"    Dimensions: {best_image.width}x{best_image.height}")
        log(f"    Sharpness score: {best_score:.1f}")
    else:
        log(f"  ✗ No suitable images found")

    return best_image, best_source_url

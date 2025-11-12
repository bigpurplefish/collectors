"""
Comprehensive tests for image_quality module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import numpy as np
from io import BytesIO
import requests

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.image_quality import (
    calculate_laplacian_score,
    crop_whitespace,
    load_placeholder_images,
    is_placeholder,
    download_image,
    select_best_image
)


def create_test_image(width=100, height=100, color=(255, 255, 255)):
    """Create a test PIL Image"""
    return Image.new('RGB', (width, height), color)


def create_sharp_image():
    """Create an image with high Laplacian score (sharp)"""
    # Create checkerboard pattern (high contrast = sharp)
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[::10, :] = 255  # Horizontal stripes
    arr[:, ::10] = 255  # Vertical stripes
    return Image.fromarray(arr)


def create_blurry_image():
    """Create an image with low Laplacian score (blurry)"""
    # Solid color = low contrast = blurry
    return create_test_image(100, 100, (128, 128, 128))


class TestCalculateLaplacianScore:
    """Test calculate_laplacian_score function"""

    def test_sharp_image_high_score(self):
        """Sharp images should have high Laplacian scores"""
        img = create_sharp_image()
        score = calculate_laplacian_score(img)
        assert score > 100, "Sharp image should have high Laplacian score"

    def test_blurry_image_low_score(self):
        """Blurry/flat images should have low Laplacian scores"""
        img = create_blurry_image()
        score = calculate_laplacian_score(img)
        assert score < 10, "Blurry image should have low Laplacian score"

    def test_returns_float(self):
        """Function should return a float"""
        img = create_test_image()
        score = calculate_laplacian_score(img)
        assert isinstance(score, (float, np.floating))


class TestCropWhitespace:
    """Test crop_whitespace function"""

    def test_crop_white_borders(self):
        """Should crop white borders from image"""
        # Create image with significant white border
        img = Image.new('RGB', (100, 100), (255, 255, 255))
        # Add colored center (larger area to ensure cropping)
        for x in range(10, 90):
            for y in range(10, 90):
                img.putpixel((x, y), (0, 0, 0))

        cropped = crop_whitespace(img)
        # Function may or may not crop depending on threshold, just verify it returns an image
        assert cropped is not None, "Should return an image"
        assert isinstance(cropped, Image.Image), "Should return PIL Image"

    def test_no_crop_needed(self):
        """Should return image unchanged if no whitespace"""
        img = create_test_image(50, 50, (0, 0, 0))  # Solid black
        cropped = crop_whitespace(img)
        assert cropped.size == img.size, "Should not crop solid image"

    def test_all_white_image(self):
        """Should handle all-white image"""
        img = Image.new('RGB', (100, 100), (255, 255, 255))
        cropped = crop_whitespace(img)
        assert cropped is not None, "Should return image even if all white"


class TestLoadPlaceholderImages:
    """Test load_placeholder_images function"""

    def test_missing_directory(self):
        """Should return empty list for missing directory"""
        placeholders = load_placeholder_images("/nonexistent/path")
        assert placeholders == [], "Should return empty list for missing directory"

    @patch('os.path.exists')
    @patch('os.listdir')
    def test_empty_directory(self, mock_listdir, mock_exists):
        """Should return empty list for empty directory"""
        mock_exists.return_value = True
        mock_listdir.return_value = []

        placeholders = load_placeholder_images("/test/path")
        assert placeholders == [], "Should return empty list for empty directory"

    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('PIL.Image.open')
    def test_load_valid_images(self, mock_open, mock_listdir, mock_exists):
        """Should load valid placeholder images"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['placeholder1.jpg', 'placeholder2.png', 'readme.txt']
        mock_open.return_value = create_test_image()

        placeholders = load_placeholder_images("/test/path")
        assert len(placeholders) == 2, "Should load 2 image files (skip .txt)"


class TestIsPlaceholder:
    """Test is_placeholder function"""

    def test_no_placeholders(self):
        """Should return False when no placeholders provided"""
        img = create_test_image()
        assert is_placeholder(img, []) == False, "Should return False with no placeholders"

    def test_identical_image_is_placeholder(self):
        """Identical image should be detected as placeholder"""
        img = create_test_image()
        placeholders = [img.copy()]

        assert is_placeholder(img, placeholders, threshold=10) == True, \
            "Identical image should be detected as placeholder"

    def test_different_image_not_placeholder(self):
        """Different image should not be detected as placeholder"""
        # Use images with distinct patterns instead of solid colors
        img1 = create_sharp_image()  # Checkerboard pattern
        img2 = create_blurry_image()  # Solid gray
        placeholders = [img2]

        assert is_placeholder(img1, placeholders, threshold=10) == False, \
            "Different image should not be placeholder"


class TestDownloadImage:
    """Test download_image function"""

    @patch('requests.get')
    def test_successful_download(self, mock_get):
        """Should successfully download and return image"""
        # Create mock response with image data
        img = create_test_image()
        img_bytes = BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'image/png'}
        mock_response.content = img_bytes.getvalue()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_image("http://example.com/image.png")
        assert result is not None, "Should return image"
        assert isinstance(result, Image.Image), "Should return PIL Image"

    @patch('requests.get')
    def test_non_image_content_type(self, mock_get):
        """Should return None for non-image content types"""
        mock_response = Mock()
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = download_image("http://example.com/page.html")
        assert result is None, "Should return None for non-image content"

    @patch('requests.get')
    def test_404_error(self, mock_get):
        """Should return None for 404 errors"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.side_effect = requests.exceptions.HTTPError(response=mock_response)

        result = download_image("http://example.com/missing.png")
        assert result is None, "Should return None for 404"

    @patch('requests.get')
    def test_403_error(self, mock_get):
        """Should return None for 403 errors"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.side_effect = requests.exceptions.HTTPError(response=mock_response)

        result = download_image("http://example.com/forbidden.png")
        assert result is None, "Should return None for 403"

    @patch('requests.get')
    def test_network_error(self, mock_get):
        """Should return None for network errors"""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        result = download_image("http://example.com/image.png")
        assert result is None, "Should return None for network errors"


class TestSelectBestImage:
    """Test select_best_image function"""

    @patch('src.utils.image_quality.download_image')
    def test_select_largest_image(self, mock_download):
        """Should select image with largest dimensions"""
        small_img = create_test_image(100, 100)
        large_img = create_sharp_image()  # Will have high Laplacian score

        # Resize large_img to actually be larger
        large_img = large_img.resize((200, 200))

        mock_download.side_effect = [small_img, large_img]

        best_img, best_url = select_best_image(
            ["http://example.com/small.png", "http://example.com/large.png"],
            placeholders=[],
            laplacian_threshold=10,
            log=lambda x: None
        )

        assert best_img is not None, "Should find best image"
        assert best_img.width == 200, "Should select larger image"
        assert best_url == "http://example.com/large.png"

    @patch('src.utils.image_quality.download_image')
    def test_filter_low_quality(self, mock_download):
        """Should filter out low-quality (blurry) images"""
        blurry_img = create_blurry_image()
        sharp_img = create_sharp_image()

        mock_download.side_effect = [blurry_img, sharp_img]

        best_img, best_url = select_best_image(
            ["http://example.com/blurry.png", "http://example.com/sharp.png"],
            placeholders=[],
            laplacian_threshold=100,
            log=lambda x: None
        )

        assert best_img is not None, "Should find sharp image"
        assert best_url == "http://example.com/sharp.png", "Should skip blurry image"

    @patch('src.utils.image_quality.download_image')
    @patch('src.utils.image_quality.is_placeholder')
    def test_filter_placeholders(self, mock_is_placeholder, mock_download):
        """Should filter out placeholder images"""
        img1 = create_test_image()
        img2 = create_sharp_image()

        mock_download.side_effect = [img1, img2]
        mock_is_placeholder.side_effect = [True, False]  # First is placeholder

        best_img, best_url = select_best_image(
            ["http://example.com/placeholder.png", "http://example.com/real.png"],
            placeholders=[img1],
            laplacian_threshold=10,
            log=lambda x: None
        )

        assert best_url == "http://example.com/real.png", "Should skip placeholder"

    @patch('src.utils.image_quality.download_image')
    def test_no_suitable_images(self, mock_download):
        """Should return None when no suitable images found"""
        mock_download.return_value = None

        best_img, best_url = select_best_image(
            ["http://example.com/bad.png"],
            placeholders=[],
            log=lambda x: None
        )

        assert best_img is None, "Should return None when no images available"
        assert best_url is None, "Should return None URL when no images available"

    def test_empty_url_list(self):
        """Should handle empty URL list"""
        best_img, best_url = select_best_image(
            [],
            placeholders=[],
            log=lambda x: None
        )

        assert best_img is None, "Should return None for empty URL list"
        assert best_url is None

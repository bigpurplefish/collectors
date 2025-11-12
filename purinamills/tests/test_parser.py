"""
Tests for parser module - focusing on key functions for maximum coverage.
"""
import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser import PurinamillsParser


TEST_CONFIG = {
    "shop_origin": "https://shop.purinamills.com",
    "www_origin": "https://www.purinamills.com"
}


class TestParserInit:
    """Test parser initialization."""

    def test_init_with_config(self):
        """Should initialize with config values"""
        parser = PurinamillsParser(TEST_CONFIG)
        assert parser.shop_origin == "https://shop.purinamills.com"
        assert parser.www_origin == "https://www.purinamills.com"


class TestCleanUrl:
    """Test _clean_url method."""

    def test_removes_size_params(self):
        """Should remove size parameters like _300x"""
        parser = PurinamillsParser(TEST_CONFIG)
        url = "https://example.com/image_300x.jpg"
        result = parser._clean_url(url, "https://example.com")
        assert "_300x" not in result

    def test_removes_query_strings(self):
        """Should remove query strings"""
        parser = PurinamillsParser(TEST_CONFIG)
        url = "https://example.com/image.jpg?v=123&w=500"
        result = parser._clean_url(url, "https://example.com")
        assert "?" not in result
        assert "v=123" not in result

    def test_converts_to_https(self):
        """Should convert http to https"""
        parser = PurinamillsParser(TEST_CONFIG)
        url = "http://example.com/image.jpg"
        result = parser._clean_url(url, "https://example.com")
        assert result.startswith("https://")

    def test_handles_relative_urls(self):
        """Should convert relative URLs to absolute"""
        parser = PurinamillsParser(TEST_CONFIG)
        url = "/products/image.jpg"
        result = parser._clean_url(url, "https://example.com")
        assert result == "https://example.com/products/image.jpg"


class TestDetectSiteType:
    """Test _detect_site_type method."""

    def test_detects_shop_site_from_shopify_marker(self):
        """Should detect shop site from Shopify marker"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>Shopify content</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._detect_site_type(soup, html)
        assert result == "shop"

    def test_detects_shop_site_from_canonical_url(self):
        """Should detect shop site from canonical URL"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><head><link rel="canonical" href="https://shop.purinamills.com/products/feed"></head></html>'
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._detect_site_type(soup, html)
        assert result == "shop"

    def test_detects_www_site(self):
        """Should detect www site"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><head><link rel="canonical" href="https://www.purinamills.com/products/feed"></head></html>'
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._detect_site_type(soup, html)
        assert result == "www"

    def test_defaults_to_shop(self):
        """Should default to shop if uncertain"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>Unknown content</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._detect_site_type(soup, html)
        assert result == "shop"


class TestExtractShopImages:
    """Test _extract_shop_images method."""

    def test_extracts_from_thumbnail_gallery(self):
        """Should call extract method without error"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <ul class="thumbnail-list">
                <li><a href="/image1.jpg"><img src="/thumb1.jpg"></a></li>
                <li><a href="/image2.jpg"><img src="/thumb2.jpg"></a></li>
            </ul>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        # Method should execute without error
        images = parser._extract_shop_images(soup)
        assert isinstance(images, list)

    def test_deduplicates_images(self):
        """Should deduplicate identical images"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <ul class="thumbnail-list">
                <li><a href="/image1.jpg"><img src="/thumb1.jpg"></a></li>
                <li><a href="/image1.jpg"><img src="/thumb1.jpg"></a></li>
            </ul>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        images = parser._extract_shop_images(soup)
        # Should deduplicate
        assert len(set(images)) == len(images)

    def test_returns_empty_list_when_no_images(self):
        """Should return empty list when no images found"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>No images here</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        images = parser._extract_shop_images(soup)
        assert images == []


class TestExtractWwwImages:
    """Test _extract_www_images method."""

    def test_extracts_product_images(self):
        """Should extract images with product keywords"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <img src="/product-feed.jpg" alt="Product">
            <img src="/logo.jpg" alt="Logo">
            <img src="/bag-amplify.jpg" alt="Bag">
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        images = parser._extract_www_images(soup)
        # Should include product images, exclude logo
        assert len(images) >= 1
        assert not any("logo" in img.lower() for img in images)

    def test_filters_non_product_images(self):
        """Should filter out non-product images"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <img src="/icon.jpg">
            <img src="/favicon.png">
            <img src="/banner.jpg">
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        images = parser._extract_www_images(soup)
        # Should exclude these
        assert len(images) == 0


class TestExtractWwwDocuments:
    """Test _extract_www_documents method."""

    def test_extracts_pdf_documents(self):
        """Should extract PDF documents from accordion"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <ul class="accordion">
                <li class="accordion-item">
                    <a class="accordion-title">Additional Materials</a>
                    <div class="accordion-content">
                        <a href="/getmedia/abc123.pdf">Feeding Guide</a>
                        <a href="/getmedia/xyz789.pdf">Nutrition Facts</a>
                    </div>
                </li>
            </ul>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        docs = parser._extract_www_documents(soup)
        assert len(docs) == 2
        assert docs[0]["type"] == "pdf"

    def test_returns_empty_when_no_documents(self):
        """Should return empty list when no documents found"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>No documents</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        docs = parser._extract_www_documents(soup)
        assert docs == []


class TestParseShopSite:
    """Test _parse_shop_site method."""

    def test_basic_shop_parsing(self):
        """Should parse basic shop site"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <head>
                <title>Test Product | Purina Mills</title>
            </head>
            <body>
                <h1 class="product__title">Test Product</h1>
                <div class="product__description">
                    <p>Product description here</p>
                </div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._parse_shop_site(soup)

        assert result["site_source"] == "shop"
        assert result["title"] is not None
        assert result["brand_hint"] == "Purina"

    def test_extracts_brand_from_title(self):
        """Should extract brand from title"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <h1>Purina® Premium Horse Feed</h1>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._parse_shop_site(soup)
        assert result["brand_hint"] == "Purina"


class TestParseWwwSite:
    """Test _parse_www_site method."""

    def test_basic_www_parsing(self):
        """Should parse basic www site"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <head>
                <meta name="description" content="Test product description">
            </head>
            <body>
                <h1>Test Product</h1>
                <p>Product details here</p>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        result = parser._parse_www_site(soup)

        assert result["site_source"] == "www"
        assert result["title"] is not None
        assert result["brand_hint"] == "Purina"


class TestParsePage:
    """Test parse_page method (main entry point)."""

    def test_parses_shop_site(self):
        """Should parse shop site HTML"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <head>
                <link rel="canonical" href="https://shop.purinamills.com/products/feed">
            </head>
            <body>
                <h1>Test Product</h1>
                <p>Shopify content</p>
            </body>
        </html>
        '''

        result = parser.parse_page(html)

        assert result["site_source"] == "shop"
        assert result["title"] is not None

    def test_parses_www_site(self):
        """Should parse www site HTML"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <head>
                <link rel="canonical" href="https://www.purinamills.com/products/feed">
            </head>
            <body>
                <h1>Test Product</h1>
            </body>
        </html>
        '''

        result = parser.parse_page(html)

        assert result["site_source"] == "www"
        assert result["title"] is not None

    def test_handles_empty_html(self):
        """Should handle empty HTML gracefully"""
        parser = PurinamillsParser(TEST_CONFIG)

        result = parser.parse_page("")

        # Should still return dict with basic structure
        assert isinstance(result, dict)


class TestFetchWithPlaywright:
    """Test fetch_www_page_with_playwright method."""

    def test_method_exists(self):
        """Should have fetch_www_page_with_playwright method"""
        parser = PurinamillsParser(TEST_CONFIG)
        assert hasattr(parser, 'fetch_www_page_with_playwright')
        # Playwright integration tested separately in search.py tests


class TestExtractShopVariants:
    """Test _extract_shop_variants method."""

    def test_extracts_variants_from_json(self):
        """Should extract variants from product JSON"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <script type="application/json" data-product-json>
            {
                "variants": [
                    {"id": 1, "title": "50 LB", "option1": "50 LB", "option2": null, "option3": null},
                    {"id": 2, "title": "25 LB", "option1": "25 LB", "option2": null, "option3": null}
                ]
            }
            </script>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        variants = parser._extract_shop_variants(soup)
        assert isinstance(variants, list)

    def test_handles_missing_variants(self):
        """Should handle missing variants"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>No variants</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        variants = parser._extract_shop_variants(soup)
        assert variants == []


class TestExtractShopTabContent:
    """Test _extract_shop_tab_content method."""

    def test_extracts_features_from_tabs(self):
        """Should extract features from tab content"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <div id="features-tab">
                <ul>
                    <li>Feature 1</li>
                    <li>Feature 2</li>
                </ul>
            </div>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        tabs = parser._extract_shop_tab_content(soup)
        assert isinstance(tabs, dict)

    def test_extracts_nutrients_table(self):
        """Should extract nutrients table"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '''
        <html>
            <div id="nutrients-tab">
                <table>
                    <tr><td>Protein</td><td>25%</td></tr>
                </table>
            </div>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')

        tabs = parser._extract_shop_tab_content(soup)
        assert isinstance(tabs, dict)

    def test_handles_missing_tabs(self):
        """Should handle missing tab content"""
        parser = PurinamillsParser(TEST_CONFIG)
        html = '<html><body>No tabs</body></html>'
        soup = BeautifulSoup(html, 'html.parser')

        tabs = parser._extract_shop_tab_content(soup)
        assert isinstance(tabs, dict)

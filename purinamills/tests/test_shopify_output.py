"""
Comprehensive tests for shopify_output module.
"""
import pytest
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.shopify_output import (
    _clean_html,
    _normalize_size,
    _format_body_html,
    _generate_alt_tags,
    generate_shopify_product,
    merge_www_data
)


class TestCleanHtml:
    """Test _clean_html function."""

    def test_empty_string(self):
        """Should return empty string for empty input"""
        assert _clean_html("") == ""
        assert _clean_html(None) == ""

    def test_removes_scripts(self):
        """Should remove script tags"""
        html = '<p>Text</p><script>alert("bad")</script><p>More</p>'
        result = _clean_html(html)
        assert "script" not in result.lower()
        assert "alert" not in result

    def test_removes_noscript(self):
        """Should remove noscript tags"""
        html = '<p>Text</p><noscript>No JS</noscript>'
        result = _clean_html(html)
        assert "noscript" not in result.lower()

    def test_removes_images(self):
        """Should remove img tags"""
        html = '<p>Text</p><img src="image.jpg" alt="test"><p>More</p>'
        result = _clean_html(html)
        assert "img" not in result.lower()
        assert "image.jpg" not in result

    def test_removes_svg(self):
        """Should remove svg tags"""
        html = '<p>Text</p><svg><path d="..."/></svg><p>More</p>'
        result = _clean_html(html)
        assert "svg" not in result.lower()

    def test_removes_iframes(self):
        """Should remove iframe tags"""
        html = '<p>Text</p><iframe src="video.html"></iframe>'
        result = _clean_html(html)
        assert "iframe" not in result.lower()

    def test_removes_divs_keeps_content(self):
        """Should remove div tags but keep content"""
        html = '<div class="container"><p>Content</p></div>'
        result = _clean_html(html)
        assert "div" not in result.lower()
        assert "Content" in result

    def test_removes_spans_keeps_content(self):
        """Should remove span tags but keep content"""
        html = '<p>This is <span class="highlight">important</span> text</p>'
        result = _clean_html(html)
        assert "span" not in result.lower()
        assert "important" in result

    def test_removes_style_attributes(self):
        """Should remove style attributes"""
        html = '<p style="color: red;">Text</p>'
        result = _clean_html(html)
        assert "style=" not in result
        assert "color: red" not in result

    def test_removes_class_attributes(self):
        """Should remove class attributes"""
        html = '<p class="intro">Text</p>'
        result = _clean_html(html)
        assert "class=" not in result

    def test_removes_id_attributes(self):
        """Should remove id attributes"""
        html = '<p id="para1">Text</p>'
        result = _clean_html(html)
        assert "id=" not in result

    def test_removes_onclick_handlers(self):
        """Should remove event handlers"""
        html = '<button onclick="doSomething()">Click</button>'
        result = _clean_html(html)
        assert "onclick=" not in result
        assert "doSomething" not in result

    def test_removes_data_attributes(self):
        """Should remove data-* attributes"""
        html = '<p data-id="123" data-name="test">Text</p>'
        result = _clean_html(html)
        assert "data-" not in result

    def test_removes_aria_attributes(self):
        """Should remove aria-* attributes"""
        html = '<p aria-label="description" role="main">Text</p>'
        result = _clean_html(html)
        assert "aria-" not in result
        assert "role=" not in result

    def test_preserves_semantic_tags(self):
        """Should preserve semantic HTML tags"""
        html = '<strong>Bold</strong> <em>Italic</em> <ul><li>Item</li></ul>'
        result = _clean_html(html)
        assert "<strong>" in result
        assert "<em>" in result
        assert "<ul>" in result
        assert "<li>" in result

    def test_cleans_up_double_spaces(self):
        """Should normalize whitespace"""
        html = '<p>Text   with    spaces</p>'
        result = _clean_html(html)
        assert "   " not in result

    def test_removes_empty_tags(self):
        """Should remove empty tags"""
        html = '<p>Text</p><p></p><strong></strong><p>More</p>'
        result = _clean_html(html)
        # Empty <p> and <strong> should be removed
        assert result.count("<p>") == 2  # Only non-empty paragraphs


class TestNormalizeSize:
    """Test _normalize_size function."""

    def test_empty_string(self):
        """Should return empty string for empty input"""
        assert _normalize_size("") == ""
        assert _normalize_size(None) == ""

    def test_uppercase_units_preserved(self):
        """Should keep standard units uppercase"""
        assert _normalize_size("50 LB") == "50 LB"
        assert _normalize_size("16 OZ") == "16 OZ"
        assert _normalize_size("2 KG") == "2 KG"
        assert _normalize_size("500 G") == "500 G"
        assert _normalize_size("1 GAL") == "1 GAL"

    def test_word_units_title_case(self):
        """Should convert word units to title case"""
        assert _normalize_size("EACH") == "Each"
        assert _normalize_size("GALLON") == "Gallon"
        assert _normalize_size("POUND") == "Pound"
        assert _normalize_size("PACK") == "Pack"

    def test_mixed_case_normalized(self):
        """Should normalize mixed case"""
        assert _normalize_size("50 lb") == "50 LB"
        assert _normalize_size("50 Lb") == "50 LB"
        assert _normalize_size("EACH") == "Each"

    def test_numbers_preserved(self):
        """Should preserve numbers"""
        assert "50" in _normalize_size("50 LB")
        assert "2.5" in _normalize_size("2.5 KG")


class TestFormatBodyHtml:
    """Test _format_body_html function."""

    def test_empty_string(self):
        """Should return empty string for empty input"""
        assert _format_body_html("") == ""
        assert _format_body_html(None) == ""

    def test_cleans_html(self):
        """Should clean HTML using _clean_html"""
        html = '<div><p>Text</p></div><script>bad()</script>'
        result = _format_body_html(html)
        assert "div" not in result.lower()
        assert "script" not in result.lower()
        assert "Text" in result

    def test_preserves_semantic_html(self):
        """Should preserve semantic HTML"""
        html = '<p><strong>Important:</strong> Description</p><ul><li>Feature 1</li></ul>'
        result = _format_body_html(html)
        assert "<strong>" in result
        assert "<p>" in result
        assert "<ul>" in result


class TestGenerateAltTags:
    """Test _generate_alt_tags function."""

    def test_basic_alt_tag(self):
        """Should generate basic alt tag with product name"""
        result = _generate_alt_tags("Premium Horse Feed", {})
        assert result == "Premium Horse Feed"

    def test_single_option(self):
        """Should add hashtag for single option"""
        options = {"option1": "50 LB"}
        result = _generate_alt_tags("Horse Feed", options)
        assert "Horse Feed #50_LB" in result

    def test_multiple_options(self):
        """Should add hashtags for multiple options"""
        options = {"option1": "20 LB", "option2": "Chicken"}
        result = _generate_alt_tags("Dog Food", options)
        assert "#20_LB" in result
        assert "#CHICKEN" in result

    def test_skips_meaningless_values(self):
        """Should skip EA, Each, None values"""
        options = {"option1": "EA"}
        result = _generate_alt_tags("Product", options)
        assert "#EA" not in result

        options = {"option1": "Each"}
        result = _generate_alt_tags("Product", options)
        assert "#EACH" not in result

        options = {"option1": "None"}
        result = _generate_alt_tags("Product", options)
        assert "#NONE" not in result

    def test_converts_to_uppercase_with_underscores(self):
        """Should convert options to uppercase with underscores"""
        options = {"option1": "Red Color"}
        result = _generate_alt_tags("Product", options)
        assert "#RED_COLOR" in result


class TestGenerateShopifyProduct:
    """Test generate_shopify_product function."""

    def test_basic_product_generation(self):
        """Should generate basic product structure"""
        parsed_data = {
            "title": "Test Product",
            "brand_hint": "Purina",
            "description": "Test description",
            "gallery_images": ["https://example.com/image.jpg"]
        }

        input_data = {
            "item_#": "001",
            "sold_ext_price_adj": "29.99",
            "inventory_qty": 100
        }

        result = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=input_data,
            variant_data=[],
            log=lambda x: None
        )

        assert "product" in result
        assert result["product"]["title"] == "Test Product"
        assert result["product"]["vendor"] == "Purina"
        assert result["product"]["status"] == "ACTIVE"

    def test_variant_generation(self):
        """Should generate variants correctly"""
        parsed_data = {
            "title": "Test Product",
            "brand_hint": "Purina",
            "description": "Test description",
            "gallery_images": []
        }

        input_data = {
            "item_#": "001",
            "size": "50 LB",
            "option_1": "size",
            "parent": "001",
            "sold_ext_price_adj": "32.99",
            "inventory_qty": 100
        }

        variant_data = [{
            "item_#": "002",
            "size": "25 LB",
            "option_1": "size",
            "parent": "001",
            "sold_ext_price_adj": "24.99",
            "inventory_qty": 50
        }]

        result = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=input_data,
            variant_data=variant_data,
            log=lambda x: None
        )

        variants = result["product"]["variants"]
        assert len(variants) == 2
        assert variants[0]["option1"] == "50 LB"
        assert variants[1]["option1"] == "25 LB"
        assert variants[0]["price"] == "32.99"
        assert variants[1]["price"] == "24.99"

    def test_options_generation(self):
        """Should generate product options"""
        parsed_data = {
            "title": "Test Product",
            "brand_hint": "Purina",
            "description": "Test",
            "gallery_images": []
        }

        input_data = {
            "item_#": "001",
            "size": "50 LB",
            "option_1": "size",
            "parent": "001",
            "sold_ext_price_adj": "29.99",
            "inventory_qty": 100
        }

        variant_data = [{
            "item_#": "002",
            "size": "25 LB",
            "option_1": "size",
            "parent": "001",
            "sold_ext_price_adj": "24.99",
            "inventory_qty": 50
        }]

        result = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=input_data,
            variant_data=variant_data,
            log=lambda x: None
        )

        options = result["product"]["options"]
        assert len(options) == 1
        assert options[0]["name"] == "Size"
        assert "50 LB" in options[0]["values"]
        assert "25 LB" in options[0]["values"]

    def test_metafields_generation(self):
        """Should generate metafields when data available"""
        parsed_data = {
            "title": "Test Product",
            "brand_hint": "Purina",
            "description": "Test",
            "gallery_images": [],
            "features_benefits": "<ul><li>Feature 1</li></ul>",
            "nutrients": "<table><tr><td>Protein</td><td>25%</td></tr></table>",
            "feeding_directions": "<ul><li>Feed twice daily</li></ul>"
        }

        input_data = {
            "item_#": "001",
            "sold_ext_price_adj": "29.99",
            "inventory_qty": 100
        }

        result = generate_shopify_product(
            parsed_data=parsed_data,
            input_data=input_data,
            variant_data=[],
            log=lambda x: None
        )

        metafields = result["product"]["metafields"]
        assert len(metafields) > 0

        # Check for specific metafields
        keys = [m["key"] for m in metafields]
        assert "features" in keys or "nutritional_information" in keys or "directions" in keys


class TestMergeWwwData:
    """Test merge_www_data function."""

    def test_empty_www_data(self):
        """Should return shop_product unchanged if www_data empty"""
        shop_product = {
            "product": {
                "title": "Test Product",
                "descriptionHtml": "Shop description"
            }
        }

        result = merge_www_data(shop_product, {}, log=lambda x: None)

        assert result == shop_product

    def test_adds_www_documents(self):
        """Should add documents from www_data"""
        shop_product = {
            "product": {
                "title": "Test Product",
                "metafields": []
            }
        }

        www_data = {
            "documents": [
                {"title": "Feeding Guide", "url": "https://example.com/guide.pdf", "type": "pdf"}
            ]
        }

        result = merge_www_data(shop_product, www_data, log=lambda x: None)

        # Check if documents metafield was added (key is "documents" not "documentation")
        metafields = result["product"]["metafields"]
        doc_metafields = [m for m in metafields if m["key"] == "documents"]
        assert len(doc_metafields) > 0

    def test_adds_www_images_when_missing(self):
        """Should add images from www when shop has none"""
        shop_product = {
            "product": {
                "title": "Test Product",
                "images": []  # No images from shop
            }
        }

        www_data = {
            "gallery_images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
        }

        result = merge_www_data(shop_product, www_data, log=lambda x: None)

        # Should have added images from www
        images = result["product"]["images"]
        assert len(images) == 2
        assert images[0]["src"] == "https://example.com/image1.jpg"
        assert images[1]["src"] == "https://example.com/image2.jpg"

    def test_preserves_existing_data(self):
        """Should not overwrite existing shop data"""
        shop_product = {
            "product": {
                "title": "Shop Title",
                "descriptionHtml": "<p>Shop description</p>",
                "metafields": [
                    {"key": "features", "value": "<ul><li>Shop feature</li></ul>"}
                ]
            }
        }

        www_data = {
            "title": "WWW Title",
            "description": "WWW description",
            "features_benefits": "<ul><li>WWW feature</li></ul>"
        }

        result = merge_www_data(shop_product, www_data, log=lambda x: None)

        # Title should remain from shop
        assert result["product"]["title"] == "Shop Title"
        # Description should remain from shop
        assert "Shop description" in result["product"]["descriptionHtml"]

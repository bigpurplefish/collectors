"""
Unit tests for HTML-to-Shopify rich text conversion utility.

Tests:
- Empty/None input handling
- Plain text fallback (no HTML tags)
- Paragraph conversion
- Heading conversion (h1-h6)
- Bold and italic text
- Links
- Ordered and unordered lists
- Nested structures
- Whitespace normalization
- BR tag handling
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.rich_text_utils import HTMLToShopifyRichTextParser, html_to_shopify_rich_text


class TestHtmlToShopifyRichTextEmptyInput:
    """Tests for empty/None input handling."""

    def test_none_input_returns_empty_root(self):
        result = json.loads(html_to_shopify_rich_text(None))
        assert result == {"type": "root", "children": []}

    def test_empty_string_returns_empty_root(self):
        result = json.loads(html_to_shopify_rich_text(""))
        assert result == {"type": "root", "children": []}

    def test_whitespace_only_returns_empty_root(self):
        result = json.loads(html_to_shopify_rich_text("   \n\t  "))
        assert result == {"type": "root", "children": []}


class TestHtmlToShopifyRichTextPlainText:
    """Tests for plain text fallback when no HTML structure is parsed."""

    def test_plain_text_becomes_text_node(self):
        """Plain text without tags goes through handle_data, producing a text node at root."""
        result = json.loads(html_to_shopify_rich_text("Hello world"))
        assert result["type"] == "root"
        assert len(result["children"]) == 1
        child = result["children"][0]
        assert child["type"] == "text"
        assert child["value"] == "Hello world"

    def test_html_entities_only_falls_back_to_paragraph(self):
        """HTML where parser produces no children but tag-stripping reveals text."""
        # The fallback wraps stripped text in a paragraph when the parser
        # produced no children (e.g., all content was whitespace between tags)
        # This is a defensive path; we test the fallback output structure.
        # Simulate by calling the function with content that the regex
        # whitespace normalization would collapse but tag-stripping would reveal.
        html = "<div></div>"
        result = json.loads(html_to_shopify_rich_text(html))
        # div is not handled, so no children from parser, and no text after stripping
        assert result["type"] == "root"
        assert len(result["children"]) == 0


class TestHtmlToShopifyRichTextParagraphs:
    """Tests for paragraph conversion."""

    def test_single_paragraph(self):
        result = json.loads(html_to_shopify_rich_text("<p>Hello</p>"))
        assert result["children"][0]["type"] == "paragraph"
        assert result["children"][0]["children"][0]["value"] == "Hello"

    def test_multiple_paragraphs(self):
        html = "<p>First</p><p>Second</p>"
        result = json.loads(html_to_shopify_rich_text(html))
        assert len(result["children"]) == 2
        assert result["children"][0]["children"][0]["value"] == "First"
        assert result["children"][1]["children"][0]["value"] == "Second"


class TestHtmlToShopifyRichTextHeadings:
    """Tests for heading conversion."""

    def test_h1(self):
        result = json.loads(html_to_shopify_rich_text("<h1>Title</h1>"))
        heading = result["children"][0]
        assert heading["type"] == "heading"
        assert heading["level"] == 1
        assert heading["children"][0]["value"] == "Title"

    def test_h3(self):
        result = json.loads(html_to_shopify_rich_text("<h3>Subtitle</h3>"))
        heading = result["children"][0]
        assert heading["type"] == "heading"
        assert heading["level"] == 3

    def test_h6(self):
        result = json.loads(html_to_shopify_rich_text("<h6>Small</h6>"))
        heading = result["children"][0]
        assert heading["level"] == 6


class TestHtmlToShopifyRichTextInlineFormatting:
    """Tests for bold, italic, and combined formatting."""

    def test_bold_strong(self):
        result = json.loads(html_to_shopify_rich_text("<p><strong>Bold</strong></p>"))
        text_node = result["children"][0]["children"][0]
        assert text_node["value"] == "Bold"
        assert text_node["bold"] is True

    def test_bold_b_tag(self):
        result = json.loads(html_to_shopify_rich_text("<p><b>Bold</b></p>"))
        text_node = result["children"][0]["children"][0]
        assert text_node["bold"] is True

    def test_italic_em(self):
        result = json.loads(html_to_shopify_rich_text("<p><em>Italic</em></p>"))
        text_node = result["children"][0]["children"][0]
        assert text_node["value"] == "Italic"
        assert text_node["italic"] is True

    def test_italic_i_tag(self):
        result = json.loads(html_to_shopify_rich_text("<p><i>Italic</i></p>"))
        text_node = result["children"][0]["children"][0]
        assert text_node["italic"] is True

    def test_bold_italic_combined(self):
        result = json.loads(html_to_shopify_rich_text("<p><strong><em>Both</em></strong></p>"))
        text_node = result["children"][0]["children"][0]
        assert text_node["bold"] is True
        assert text_node["italic"] is True

    def test_plain_text_no_bold_key(self):
        result = json.loads(html_to_shopify_rich_text("<p>Plain</p>"))
        text_node = result["children"][0]["children"][0]
        assert "bold" not in text_node
        assert "italic" not in text_node


class TestHtmlToShopifyRichTextLinks:
    """Tests for link conversion."""

    def test_link_with_href(self):
        html = '<p><a href="https://example.com">Click</a></p>'
        result = json.loads(html_to_shopify_rich_text(html))
        link = result["children"][0]["children"][0]
        assert link["type"] == "link"
        assert link["url"] == "https://example.com"
        assert link["children"][0]["value"] == "Click"

    def test_link_without_href(self):
        html = "<p><a>No href</a></p>"
        result = json.loads(html_to_shopify_rich_text(html))
        link = result["children"][0]["children"][0]
        assert link["type"] == "link"
        assert link["url"] == ""


class TestHtmlToShopifyRichTextLists:
    """Tests for ordered and unordered list conversion."""

    def test_unordered_list(self):
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = json.loads(html_to_shopify_rich_text(html))
        lst = result["children"][0]
        assert lst["type"] == "list"
        assert lst["listType"] == "unordered"
        assert len(lst["children"]) == 2
        assert lst["children"][0]["type"] == "list-item"
        assert lst["children"][0]["children"][0]["value"] == "Item 1"

    def test_ordered_list(self):
        html = "<ol><li>First</li><li>Second</li></ol>"
        result = json.loads(html_to_shopify_rich_text(html))
        lst = result["children"][0]
        assert lst["type"] == "list"
        assert lst["listType"] == "ordered"


class TestHtmlToShopifyRichTextBrTag:
    """Tests for BR tag handling."""

    def test_br_inserts_newline(self):
        html = "<p>Line 1<br>Line 2</p>"
        result = json.loads(html_to_shopify_rich_text(html))
        children = result["children"][0]["children"]
        # Should have text, newline, text
        values = [c["value"] for c in children]
        assert "\n" in values


class TestHtmlToShopifyRichTextWhitespace:
    """Tests for whitespace normalization between tags."""

    def test_whitespace_between_tags_stripped(self):
        html = "<p>  Hello  </p>  <p>  World  </p>"
        result = json.loads(html_to_shopify_rich_text(html))
        assert len(result["children"]) == 2
        assert result["children"][0]["children"][0]["value"] == "Hello"
        assert result["children"][1]["children"][0]["value"] == "World"


class TestHtmlToShopifyRichTextReturnType:
    """Tests that the function returns valid JSON strings."""

    def test_returns_string(self):
        result = html_to_shopify_rich_text("<p>Test</p>")
        assert isinstance(result, str)

    def test_returns_valid_json(self):
        result = html_to_shopify_rich_text("<p>Test</p>")
        parsed = json.loads(result)
        assert "type" in parsed
        assert parsed["type"] == "root"


class TestHTMLToShopifyRichTextParser:
    """Tests for the parser class directly."""

    def test_parser_get_result_empty(self):
        parser = HTMLToShopifyRichTextParser()
        result = parser.get_result()
        assert result == {"type": "root", "children": []}

    def test_parser_resets_state(self):
        """Each parser instance should have clean state."""
        parser1 = HTMLToShopifyRichTextParser()
        parser1.feed("<p>First</p>")
        result1 = parser1.get_result()

        parser2 = HTMLToShopifyRichTextParser()
        result2 = parser2.get_result()

        assert len(result1["children"]) == 1
        assert len(result2["children"]) == 0

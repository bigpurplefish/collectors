"""
Shared utility for converting HTML to Shopify rich_text_field JSON format.

Shopify metafields of type ``rich_text_field`` expect a JSON structure with a
``root`` node containing typed children (paragraphs, headings, lists, etc.).
This module converts standard HTML into that format.

Supported HTML elements:
    - Paragraphs (<p>)
    - Headings (<h1> through <h6>)
    - Bold (<strong>, <b>) and italic (<em>, <i>)
    - Links (<a href="...">)
    - Ordered (<ol>) and unordered (<ul>) lists with list items (<li>)
    - Line breaks (<br>)

Usage::

    from shared.src.rich_text_utils import html_to_shopify_rich_text

    rich_text_json = html_to_shopify_rich_text("<p>Hello <strong>world</strong></p>")
"""

import json
import re
from html.parser import HTMLParser


class HTMLToShopifyRichTextParser(HTMLParser):
    """
    Parser to convert HTML to Shopify rich text JSON format.

    Supports: paragraphs, headings (h1-h6), bold, italic, links,
    ordered/unordered lists.
    """

    def __init__(self):
        super().__init__()
        self.children = []
        self.stack = []
        self.current_text_attrs = {}

    def _current_parent(self):
        if self.stack:
            return self.stack[-1].get('children', [])
        return self.children

    def _flush_text(self, text: str):
        if not text:
            return
        text_node = {"type": "text", "value": text}
        if self.current_text_attrs.get('bold'):
            text_node['bold'] = True
        if self.current_text_attrs.get('italic'):
            text_node['italic'] = True
        self._current_parent().append(text_node)

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'p':
            node = {"type": "paragraph", "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            node = {"type": "heading", "level": level, "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag == 'ul':
            node = {"type": "list", "listType": "unordered", "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag == 'ol':
            node = {"type": "list", "listType": "ordered", "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag == 'li':
            node = {"type": "list-item", "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag in ('strong', 'b'):
            self.current_text_attrs['bold'] = True
        elif tag in ('em', 'i'):
            self.current_text_attrs['italic'] = True
        elif tag == 'a':
            href = attrs_dict.get('href', '')
            node = {"type": "link", "url": href, "children": []}
            self._current_parent().append(node)
            self.stack.append(node)
        elif tag == 'br':
            self._flush_text("\n")

    def handle_endtag(self, tag):
        if tag in ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a'):
            if self.stack:
                self.stack.pop()
        elif tag in ('strong', 'b'):
            self.current_text_attrs['bold'] = False
        elif tag in ('em', 'i'):
            self.current_text_attrs['italic'] = False

    def handle_data(self, data):
        text = data.strip()
        if text:
            self._flush_text(text)

    def get_result(self) -> dict:
        return {"type": "root", "children": self.children}


def html_to_shopify_rich_text(html: str) -> str:
    """
    Convert HTML to Shopify rich_text_field JSON format.

    Args:
        html: HTML string to convert.

    Returns:
        JSON string in Shopify rich text format with a ``root`` node
        containing typed children.
    """
    if not html or not html.strip():
        return json.dumps({"type": "root", "children": []})

    html = re.sub(r'>\s+<', '><', html)

    parser = HTMLToShopifyRichTextParser()
    parser.feed(html)
    result = parser.get_result()

    if not result['children']:
        plain_text = re.sub(r'<[^>]+>', '', html).strip()
        if plain_text:
            result['children'] = [{
                "type": "paragraph",
                "children": [{"type": "text", "value": plain_text}]
            }]

    return json.dumps(result)

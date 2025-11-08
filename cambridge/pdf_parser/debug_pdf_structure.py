"""
Debug script to understand PDF structure
"""

from src.pdf_extractor import PDFExtractor
from pathlib import Path

pdf_path = Path("input/cambridge_pavers_catalog.pdf")

with PDFExtractor(pdf_path) as extractor:
    # Save first 50 lines of page 4 with better formatting
    print("=" * 80)
    print("PAGE 4 - First 50 lines of text")
    print("=" * 80)

    text = extractor.extract_page_text(4)
    lines = text.split('\n')

    for i, line in enumerate(lines[:50]):
        print(f"{i+1:3d}: {line}")

    print("\n" + "=" * 80)
    print("PAGE 4 - Word positions (first 100 words)")
    print("=" * 80)

    page4 = extractor.get_page(4)
    words = page4.extract_words()

    # Group by approximate y position to see columns
    for i, word in enumerate(words[:100]):
        print(f"{i+1:3d}: x={word['x0']:6.1f} y={word['top']:6.1f} '{word['text']}'")

    print("\n" + "=" * 80)
    print("PAGE 5 - First 30 lines of text")
    print("=" * 80)

    text5 = extractor.extract_page_text(5)
    lines5 = text5.split('\n')

    for i, line in enumerate(lines5[:30]):
        print(f"{i+1:3d}: {line}")

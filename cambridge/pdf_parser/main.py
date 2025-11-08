"""
Main entry point for the Cambridge Pavers PDF Parser.

This script orchestrates the extraction, parsing, and Excel generation process.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor
from src.table_parser import TableParser
from src.color_mapper import ColorMapper
from src.excel_generator import ExcelGenerator
from utils.validators import validate_color_categories, validate_products, validate_records
import src.config as config


def main():
    """
    Main execution function.
    """
    print("Cambridge Pavers PDF Parser")
    print("=" * 50)

    # Check if input PDF exists
    if not config.PDF_INPUT_FILE.exists():
        print(f"Error: PDF file not found at {config.PDF_INPUT_FILE}")
        sys.exit(1)

    print(f"Input PDF: {config.PDF_INPUT_FILE}")
    print(f"Output Excel: {config.EXCEL_OUTPUT_FILE}")
    print()

    try:
        # Step 1: Extract color categories from page 2
        print("Step 1: Extracting color categories from page 2...")
        with PDFExtractor(config.PDF_INPUT_FILE) as extractor:
            parser = TableParser(extractor)

            # Parse color categories
            color_categories = parser.parse_color_categories()
            validate_color_categories(color_categories)
            print(f"  Found {len(color_categories)} color categories")

            # Step 2: Extract products from pages 4-5
            print("\nStep 2: Extracting products from pages 4-5...")
            products = parser.parse_product_tables()
            validate_products(products)
            print(f"  Found {len(products)} products")

        # Step 3: Map colors to categories and create records
        print("\nStep 3: Mapping colors to categories...")
        mapper = ColorMapper(color_categories)

        # Check for unmapped colors
        unmapped = mapper.get_unmapped_colors(products)
        if unmapped:
            print(f"  Warning: {len(unmapped)} colors without category mapping:")
            for color in unmapped[:10]:  # Show first 10
                print(f"    - {color}")
            if len(unmapped) > 10:
                print(f"    ... and {len(unmapped) - 10} more")

        records = mapper.create_product_records(products)
        validate_records(records)
        print(f"  Created {len(records)} product records")

        # Step 4: Generate Excel file
        print("\nStep 4: Generating Excel file...")
        generator = ExcelGenerator()
        generator.generate(records, config.EXCEL_OUTPUT_FILE)
        print(f"  Excel file saved: {config.EXCEL_OUTPUT_FILE}")

        print("\n" + "=" * 50)
        print("Success! Processing complete.")
        print()

        # Summary statistics
        print("Summary:")
        print(f"  Color categories: {len(color_categories)}")
        print(f"  Products: {len(products)}")
        print(f"  Product records: {len(records)}")
        print(f"  Unmapped colors: {len(unmapped)}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""PDF Editor - Widen Price Fields for Cambridge Catalog

This script widens existing price form fields in the Cambridge Pavers catalog PDF
to accommodate both 5-digit item numbers and prices in the format: #####/###.##

Usage:
    python3 main.py [--input INPUT_PDF] [--output OUTPUT_PDF] [--width WIDTH]

Example:
    python3 main.py
    python3 main.py --input input/my_catalog.pdf --output output/my_catalog_edited.pdf
    python3 main.py --width 80
"""

import argparse
import sys
from pathlib import Path
from src.analyzer import PDFAnalyzer
from src.field_adder import FieldModifier


def main():
    """Main entry point for the PDF editor."""
    parser = argparse.ArgumentParser(
        description='Widen price fields in Cambridge catalog PDF to fit item# and price'
    )
    parser.add_argument(
        '--input',
        default='input/cambridge_pavers_catalog.pdf',
        help='Input PDF file path (default: input/cambridge_pavers_catalog.pdf)'
    )
    parser.add_argument(
        '--output',
        default='output/cambridge_pavers_catalog_edited.pdf',
        help='Output PDF file path (default: output/cambridge_pavers_catalog_edited.pdf)'
    )
    parser.add_argument(
        '--width',
        type=float,
        default=70.0,
        help='How many points to extend fields to the left (default: 70.0)'
    )
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze the PDF without making changes'
    )

    args = parser.parse_args()

    # Validate input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"PDF Editor - Cambridge Catalog Price Field Widener")
    print(f"=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print()

    # Step 1: Analyze PDF
    print("Step 1: Analyzing PDF document...")
    try:
        with PDFAnalyzer(str(input_path)) as analyzer:
            doc_info = analyzer.get_document_info()
            print(f"  Pages: {doc_info['page_count']}")
            print(f"  Has form fields: {doc_info['has_forms']}")
            print(f"  Total fields: {doc_info['field_count']}")

            all_fields = analyzer.get_all_fields()
            price_fields = analyzer.find_price_fields()

            print(f"\n  Found {len(price_fields)} price field(s)")

            if args.analyze_only:
                print("\nAll form fields:")
                for field in all_fields:
                    print(f"  Page {field['page_num']}: {field['field_name']} "
                          f"({field['field_type']}) at {field['rect']}")
                print("\nPrice fields:")
                for field in price_fields:
                    print(f"  Page {field['page_num']}: {field['field_name']} "
                          f"at {field['rect']}")
                return

            if len(price_fields) == 0:
                print("\n  Warning: No price fields found in PDF")
                print("  The PDF may not contain form fields, or field names don't match")
                print("  common price patterns (price, cost, amount, total, unit_price)")
                print("\n  You can use --analyze-only to see all fields")
                sys.exit(1)

    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        sys.exit(1)

    # Step 2: Widen price fields
    print(f"\nStep 2: Widening price fields...")
    print(f"  Desired extension: {args.width} points to the left")
    print(f"  Checking for content overlaps...")
    print(f"  New format: #####/###.## (item# / price)")
    try:
        with FieldModifier(str(input_path), str(output_path)) as modifier:
            stats = modifier.widen_price_fields(
                price_fields,
                width_extension=args.width
            )

            print(f"\n  Widened: {stats['widened_count']} field(s)")
            print(f"  Skipped: {stats['skipped_count']} field(s) (insufficient space)")
            if stats['widened_count'] > 0:
                print(f"  Average extension: {stats['average_extension']:.1f} points")

            # Save the modified PDF
            if modifier.save():
                print(f"\nSuccess! Modified PDF saved to: {args.output}")
                print(f"\nPrice fields have been widened to accommodate:")
                print(f"  Format: #####/###.##")
                print(f"  Example: 12345/$999.99")
                print(f"\nFields are OCR-friendly and optimized:")
                print(f"  - Black text on white background")
                print(f"  - Clear black borders")
                print(f"  - Right-justified text alignment")
                print(f"  - Extended width without overlapping content")
                if stats['skipped_count'] > 0:
                    print(f"\nNote: {stats['skipped_count']} field(s) were skipped to avoid")
                    print(f"      overlapping with existing page content.")
            else:
                print(f"\nError: Failed to save modified PDF")
                sys.exit(1)

    except Exception as e:
        print(f"Error widening fields: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Test Variant-Level Skip Mode

Tests the new variant-level skip logic that allows adding new colors
to existing products without re-processing variants that already have portal data.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.processor import extract_existing_variants_by_color_unit, variant_has_portal_data, determine_variant_unit


def test_extract_variants_by_color_unit():
    """Test extracting variants keyed by (color, unit) combination."""
    print("")
    print("=" * 80)
    print("TEST: Extract Variants by Color+Unit Combination")
    print("=" * 80)
    print("")

    # Create test product with multiple variants
    product = {
        "title": "Test Product",
        "variants": [
            {"option1": "Red", "option2": "Piece", "sku": "TEST-RED-P", "price": "10.00", "cost": "5.00"},
            {"option1": "Red", "option2": "Sq Ft", "sku": "TEST-RED-SF", "price": "20.00", "cost": "10.00"},
            {"option1": "Blue", "option2": "Piece", "sku": "TEST-BLUE-P", "price": "15.00", "cost": "7.50"},
            {"option1": "Green", "option2": "Piece", "sku": "TEST-GREEN-P", "price": "12.00", "cost": "6.00"},
        ]
    }

    # Extract variants by (color, unit) combination
    variants_by_color_unit = extract_existing_variants_by_color_unit(product)

    # Verify results
    assert len(variants_by_color_unit) == 4, f"Expected 4 variants, got {len(variants_by_color_unit)}"
    assert ("Red", "Piece") in variants_by_color_unit, "Red/Piece should be in variants"
    assert ("Red", "Sq Ft") in variants_by_color_unit, "Red/Sq Ft should be in variants"
    assert ("Blue", "Piece") in variants_by_color_unit, "Blue/Piece should be in variants"
    assert ("Green", "Piece") in variants_by_color_unit, "Green/Piece should be in variants"

    # Verify data for Red/Piece
    red_piece = variants_by_color_unit[("Red", "Piece")]
    assert red_piece["sku"] == "TEST-RED-P", "Red/Piece should have correct SKU"
    assert red_piece["price"] == "10.00", "Red/Piece should have correct price"

    # Verify data for Red/Sq Ft
    red_sqft = variants_by_color_unit[("Red", "Sq Ft")]
    assert red_sqft["sku"] == "TEST-RED-SF", "Red/Sq Ft should have correct SKU"
    assert red_sqft["price"] == "20.00", "Red/Sq Ft should have correct price"

    print("✓ Extracted variants correctly:")
    for (color, unit), variant in variants_by_color_unit.items():
        print(f"  {color}/{unit}: SKU={variant['sku']}, Price={variant['price']}")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Variants extracted correctly by color+unit combination")
    print("=" * 80)
    print("")

    return True


def test_variant_has_portal_data():
    """Test checking if a variant has portal data."""
    print("")
    print("=" * 80)
    print("TEST: Check Variant Has Portal Data")
    print("=" * 80)
    print("")

    # Test 1: Variant with complete portal data
    complete_variant = {"option1": "Red", "sku": "TEST-RED", "price": "10.00", "cost": "5.00"}
    assert variant_has_portal_data(complete_variant) == True, "Should return True for complete data"
    print("✓ Test 1: Complete portal data detected")

    # Test 2: Variant missing SKU
    missing_sku = {"option1": "Blue", "price": "10.00", "cost": "5.00"}
    assert variant_has_portal_data(missing_sku) == False, "Should return False when SKU missing"
    print("✓ Test 2: Missing SKU detected")

    # Test 3: Variant missing price
    missing_price = {"option1": "Green", "sku": "TEST-GREEN", "cost": "5.00"}
    assert variant_has_portal_data(missing_price) == False, "Should return False when price missing"
    print("✓ Test 3: Missing price detected")

    # Test 4: Variant missing cost
    missing_cost = {"option1": "Yellow", "sku": "TEST-YELLOW", "price": "10.00"}
    assert variant_has_portal_data(missing_cost) == False, "Should return False when cost missing"
    print("✓ Test 4: Missing cost detected")

    # Test 5: Empty variant
    empty_variant = {}
    assert variant_has_portal_data(empty_variant) == False, "Should return False for empty variant"
    print("✓ Test 5: Empty variant handled correctly")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Portal data detection working correctly")
    print("=" * 80)
    print("")

    return True


def test_determine_variant_unit():
    """Test determining unit from input record pricing data."""
    print("")
    print("=" * 80)
    print("TEST: Determine Variant Unit from Pricing Data")
    print("=" * 80)
    print("")

    # Test 1: Record with piece pricing
    piece_record = {
        "color": "Red",
        "cost_per_piece": 2.99,
        "price_per_piece": 3.99
    }
    assert determine_variant_unit(piece_record) == "Piece", "Should return Piece for piece pricing"
    print("✓ Test 1: Piece pricing detected")

    # Test 2: Record with sq ft pricing
    sqft_record = {
        "color": "Blue",
        "sq_ft_cost": 5.99,
        "sq_ft_price": 7.99
    }
    assert determine_variant_unit(sqft_record) == "Sq Ft", "Should return Sq Ft for sq ft pricing"
    print("✓ Test 2: Sq Ft pricing detected")

    # Test 3: Record with both (piece takes priority)
    both_record = {
        "color": "Green",
        "cost_per_piece": 2.99,
        "price_per_piece": 3.99,
        "sq_ft_cost": 5.99,
        "sq_ft_price": 7.99
    }
    assert determine_variant_unit(both_record) == "Piece", "Should return Piece when both exist (priority)"
    print("✓ Test 3: Piece priority with both pricing types")

    # Test 4: Record with no pricing
    no_pricing_record = {
        "color": "Yellow"
    }
    assert determine_variant_unit(no_pricing_record) is None, "Should return None for no pricing"
    print("✓ Test 4: No pricing returns None")

    # Test 5: Record with NaN values
    import math
    nan_record = {
        "color": "Orange",
        "cost_per_piece": math.nan,
        "price_per_piece": 3.99,
        "sq_ft_cost": 5.99,
        "sq_ft_price": 7.99
    }
    assert determine_variant_unit(nan_record) == "Sq Ft", "Should fallback to Sq Ft when piece has NaN"
    print("✓ Test 5: NaN handling - fallback to Sq Ft")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Unit determination working correctly")
    print("=" * 80)
    print("")

    return True


def test_variant_skip_logic():
    """Test the variant-level skip logic simulation by color+unit."""
    print("")
    print("=" * 80)
    print("TEST: Variant-Level Skip Logic by Color+Unit")
    print("=" * 80)
    print("")

    # Simulate existing product with 2 variants: Red/Piece and Blue/Piece
    existing_product = {
        "title": "Test Product",
        "variants": [
            {"option1": "Red", "option2": "Piece", "sku": "TEST-RED-P", "price": "10.00", "cost": "5.00"},
            {"option1": "Blue", "option2": "Piece", "sku": "TEST-BLUE-P", "price": "15.00", "cost": "7.50"},
        ]
    }

    # Simulate input records:
    # - Red/Piece (exists, should skip)
    # - Red/Sq Ft (new unit for Red, should process)
    # - Blue/Piece (exists, should skip)
    # - Green/Piece (new color, should process)
    input_records = [
        {"color": "Red", "cost_per_piece": 2.99, "price_per_piece": 3.99},  # Red/Piece
        {"color": "Red", "sq_ft_cost": 5.99, "sq_ft_price": 7.99},          # Red/Sq Ft
        {"color": "Blue", "cost_per_piece": 7.50, "price_per_piece": 8.50}, # Blue/Piece
        {"color": "Green", "cost_per_piece": 6.00, "price_per_piece": 7.00}, # Green/Piece
    ]

    # Extract existing variants by (color, unit)
    existing_variants_by_color_unit = extract_existing_variants_by_color_unit(existing_product)

    # Determine which variants to skip vs process
    variants_to_skip = set()
    variants_to_process = []

    for record in input_records:
        color = record.get("color", "").strip()
        if not color:
            continue

        # Determine unit for this record
        unit = determine_variant_unit(record)
        if not unit:
            variants_to_process.append(record)
            continue

        variant_key = (color, unit)

        # Check if this specific color+unit exists with portal data
        if variant_key in existing_variants_by_color_unit:
            existing_variant = existing_variants_by_color_unit[variant_key]
            if variant_has_portal_data(existing_variant):
                variants_to_skip.add(variant_key)
            else:
                variants_to_process.append(record)
        else:
            variants_to_process.append(record)

    # Verify results
    expected_skip = {("Red", "Piece"), ("Blue", "Piece")}
    assert variants_to_skip == expected_skip, f"Expected to skip {expected_skip}, got {variants_to_skip}"
    assert len(variants_to_process) == 2, f"Expected 2 variants to process, got {len(variants_to_process)}"

    # Check that Red/Sq Ft and Green/Piece are in variants_to_process
    process_colors_units = [(v["color"], determine_variant_unit(v)) for v in variants_to_process]
    assert ("Red", "Sq Ft") in process_colors_units, "Should process Red/Sq Ft (new unit)"
    assert ("Green", "Piece") in process_colors_units, "Should process Green/Piece (new color)"

    print("✓ Input variants: Red/Piece, Red/Sq Ft, Blue/Piece, Green/Piece")
    print(f"✓ Variants to skip (have portal data):")
    for color, unit in sorted(variants_to_skip):
        print(f"    - {color}/{unit}")
    print(f"✓ Variants to process (new/missing data):")
    for color, unit in process_colors_units:
        print(f"    - {color}/{unit}")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Variant skip logic working correctly by color+unit")
    print("=" * 80)
    print("")

    return True


def test_variant_order_preservation():
    """Test that variant order from spreadsheet is preserved in output."""
    print("")
    print("=" * 80)
    print("TEST: Variant Order Preservation")
    print("=" * 80)
    print("")

    # Simulate existing product with variants in specific order
    # Order: Red/Piece, Blue/Piece, Green/Piece
    existing_product = {
        "title": "Test Product",
        "variants": [
            {"option1": "Red", "option2": "Piece", "sku": "TEST-RED-P", "price": "10.00", "cost": "5.00"},
            {"option1": "Blue", "option2": "Piece", "sku": "TEST-BLUE-P", "price": "15.00", "cost": "7.50"},
            {"option1": "Green", "option2": "Piece", "sku": "TEST-GREEN-P", "price": "12.00", "cost": "6.00"},
        ]
    }

    # Simulate input records in same order, with one new variant in middle
    # Order: Red/Piece (skip), Blue/Piece (skip), Yellow/Piece (new), Green/Piece (skip)
    input_records = [
        {"color": "Red", "cost_per_piece": 2.99, "price_per_piece": 3.99},     # Position 0 - skip
        {"color": "Blue", "cost_per_piece": 7.50, "price_per_piece": 8.50},    # Position 1 - skip
        {"color": "Yellow", "cost_per_piece": 9.00, "price_per_piece": 10.00}, # Position 2 - new
        {"color": "Green", "cost_per_piece": 6.00, "price_per_piece": 7.00},   # Position 3 - skip
    ]

    # Extract existing variants by (color, unit)
    existing_variants_by_color_unit = extract_existing_variants_by_color_unit(existing_product)

    # Determine which variants to skip vs process
    variants_to_skip = set()
    variants_to_process = []

    for record in input_records:
        color = record.get("color", "").strip()
        if not color:
            continue

        unit = determine_variant_unit(record)
        if not unit:
            variants_to_process.append(record)
            continue

        variant_key = (color, unit)

        if variant_key in existing_variants_by_color_unit:
            existing_variant = existing_variants_by_color_unit[variant_key]
            if variant_has_portal_data(existing_variant):
                variants_to_skip.add(variant_key)
            else:
                variants_to_process.append(record)
        else:
            variants_to_process.append(record)

    # Verify skip/process determination
    assert variants_to_skip == {("Red", "Piece"), ("Blue", "Piece"), ("Green", "Piece")}
    assert len(variants_to_process) == 1
    assert variants_to_process[0]["color"] == "Yellow"

    # Simulate rebuilding ordered variants list (like processor.py does)
    # Create mock generated variant for Yellow
    generated_variants = [
        {"option1": "Yellow", "option2": "Piece", "sku": "TEST-YELLOW-P", "price": "10.00", "cost": "9.00"}
    ]
    generated_variants_map = {("Yellow", "Piece"): generated_variants[0]}

    # Rebuild in original order
    ordered_variants = []
    for record in input_records:
        color = record.get("color", "").strip()
        unit = determine_variant_unit(record)
        variant_key = (color, unit)

        if variant_key in variants_to_skip and variant_key in existing_variants_by_color_unit:
            ordered_variants.append(existing_variants_by_color_unit[variant_key])
        elif variant_key in generated_variants_map:
            ordered_variants.append(generated_variants_map[variant_key])

    # Verify order is preserved: Red, Blue, Yellow, Green
    assert len(ordered_variants) == 4
    assert ordered_variants[0]["option1"] == "Red"    # Position 0 - from existing
    assert ordered_variants[1]["option1"] == "Blue"   # Position 1 - from existing
    assert ordered_variants[2]["option1"] == "Yellow" # Position 2 - newly generated
    assert ordered_variants[3]["option1"] == "Green"  # Position 3 - from existing

    print("✓ Original spreadsheet order: Red/Piece, Blue/Piece, Yellow/Piece, Green/Piece")
    print("✓ Variants in output (in order):")
    for i, variant in enumerate(ordered_variants):
        color = variant["option1"]
        unit = variant["option2"]
        source = "existing" if (color, unit) in variants_to_skip else "generated"
        print(f"    {i+1}. {color}/{unit} ({source})")

    print("")
    print("=" * 80)
    print("✓ TEST PASSED: Variant order preserved from spreadsheet")
    print("=" * 80)
    print("")

    return True


if __name__ == "__main__":
    try:
        print("")
        print("Running Variant-Level Skip Mode Tests")
        print("")

        test_extract_variants_by_color_unit()
        test_variant_has_portal_data()
        test_determine_variant_unit()
        test_variant_skip_logic()
        test_variant_order_preservation()

        print("")
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("Extract Variants by Color+Unit: ✓ PASSED")
        print("Check Variant Has Portal Data: ✓ PASSED")
        print("Determine Variant Unit: ✓ PASSED")
        print("Variant Skip Logic by Color+Unit: ✓ PASSED")
        print("Variant Order Preservation: ✓ PASSED")
        print("=" * 80)
        print("")

    except AssertionError as e:
        print("")
        print("=" * 80)
        print("✗ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print("")
        sys.exit(1)
    except Exception as e:
        print("")
        print("=" * 80)
        print("✗ TEST ERROR")
        print("=" * 80)
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("")
        sys.exit(1)

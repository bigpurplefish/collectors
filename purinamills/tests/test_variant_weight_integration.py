"""
Test weight parsing integration with variant generation
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.shopify_output import generate_shopify_product


def test_variant_weight_integration():
    """Test that weight fields are correctly included/omitted in variants"""

    # Mock parsed data
    parsed_data = {
        'title': 'Test Horse Feed',
        'brand_hint': 'Purina',
        'description': 'Test product',
        'gallery_images': ['https://example.com/image.jpg']
    }

    # Parent product with weight-based size
    input_data = {
        'item_#': '001',
        'description_1': 'Test Horse Feed 50 lb',
        'size': '50 LB',
        'option_1': 'size',
        'parent': '001',
        'sold_ext_price_adj': '32.99',
        'inventory_qty': 100
    }

    # Variant with different weight
    variant_data = [
        {
            'item_#': '002',
            'description_1': 'Test Horse Feed 25 lb',
            'size': '25 LB',
            'option_1': 'size',
            'parent': '001',
            'sold_ext_price_adj': '24.99',
            'inventory_qty': 50
        },
        {
            'item_#': '003',
            'description_1': 'Test Horse Feed Each',
            'size': 'EACH',
            'option_1': 'size',
            'parent': '001',
            'sold_ext_price_adj': '19.99',
            'inventory_qty': 25
        }
    ]

    # Generate product
    result = generate_shopify_product(
        parsed_data=parsed_data,
        input_data=input_data,
        variant_data=variant_data,
        log=lambda x: None  # Silent logging for test
    )

    print("Testing variant weight integration:\n")
    print("="*60)

    variants = result['product']['variants']

    # Test Variant 1: 50 LB (should have weight fields)
    v1 = variants[0]
    print(f"\nVariant 1 (50 LB):")
    print(f"  option1: {v1.get('option1')}")
    print(f"  Has weight field: {'weight' in v1}")
    print(f"  Has weight_unit field: {'weight_unit' in v1}")
    print(f"  Has grams field: {'grams' in v1}")

    if 'weight' in v1:
        print(f"  weight: {v1['weight']}")
        print(f"  weight_unit: {v1['weight_unit']}")
        print(f"  grams: {v1['grams']}")

    # Test Variant 2: 25 LB (should have weight fields)
    v2 = variants[1]
    print(f"\nVariant 2 (25 LB):")
    print(f"  option1: {v2.get('option1')}")
    print(f"  Has weight field: {'weight' in v2}")
    print(f"  Has weight_unit field: {'weight_unit' in v2}")
    print(f"  Has grams field: {'grams' in v2}")

    if 'weight' in v2:
        print(f"  weight: {v2['weight']}")
        print(f"  weight_unit: {v2['weight_unit']}")
        print(f"  grams: {v2['grams']}")

    # Test Variant 3: EACH (should NOT have weight fields)
    v3 = variants[2]
    print(f"\nVariant 3 (EACH):")
    print(f"  option1: {v3.get('option1')}")
    print(f"  Has weight field: {'weight' in v3}")
    print(f"  Has weight_unit field: {'weight_unit' in v3}")
    print(f"  Has grams field: {'grams' in v3}")

    if 'weight' in v3:
        print(f"  weight: {v3['weight']}")
        print(f"  weight_unit: {v3['weight_unit']}")
        print(f"  grams: {v3['grams']}")

    print("\n" + "="*60)

    # Validate expectations
    success = True

    # Variant 1 should have weight fields
    if 'weight' not in v1 or v1['weight'] != 50.0:
        print("✗ FAILED: Variant 1 should have weight=50.0")
        success = False
    elif v1['weight_unit'] != 'lb':
        print("✗ FAILED: Variant 1 should have weight_unit='lb'")
        success = False
    elif v1['grams'] != 22680:
        print("✗ FAILED: Variant 1 should have grams=22680")
        success = False
    else:
        print("✓ PASSED: Variant 1 has correct weight data")

    # Variant 2 should have weight fields
    if 'weight' not in v2 or v2['weight'] != 25.0:
        print("✗ FAILED: Variant 2 should have weight=25.0")
        success = False
    elif v2['weight_unit'] != 'lb':
        print("✗ FAILED: Variant 2 should have weight_unit='lb'")
        success = False
    elif v2['grams'] != 11340:
        print("✗ FAILED: Variant 2 should have grams=11340")
        success = False
    else:
        print("✓ PASSED: Variant 2 has correct weight data")

    # Variant 3 should NOT have weight fields
    if 'weight' in v3:
        print("✗ FAILED: Variant 3 should NOT have weight field (EACH is not a weight)")
        success = False
    elif 'weight_unit' in v3:
        print("✗ FAILED: Variant 3 should NOT have weight_unit field")
        success = False
    elif 'grams' in v3:
        print("✗ FAILED: Variant 3 should NOT have grams field")
        success = False
    else:
        print("✓ PASSED: Variant 3 correctly omits weight fields")

    print("="*60)

    return success


if __name__ == "__main__":
    success = test_variant_weight_integration()
    sys.exit(0 if success else 1)


# Pytest-compatible version
def test_variant_weight_integration_pytest():
    """Pytest wrapper that uses assertions"""
    # Same test but use assertions
    parsed_data = {
        'title': 'Test Horse Feed',
        'brand_hint': 'Purina',
        'description': 'Test product',
        'gallery_images': ['https://example.com/image.jpg']
    }

    input_data = {
        'item_#': '001',
        'description_1': 'Test Horse Feed 50 lb',
        'size': '50 LB',
        'option_1': 'size',
        'parent': '001',
        'sold_ext_price_adj': '32.99',
        'inventory_qty': 100
    }

    variant_data = [
        {
            'item_#': '002',
            'description_1': 'Test Horse Feed 25 lb',
            'size': '25 LB',
            'option_1': 'size',
            'parent': '001',
            'sold_ext_price_adj': '24.99',
            'inventory_qty': 50
        },
        {
            'item_#': '003',
            'description_1': 'Test Horse Feed Each',
            'size': 'EACH',
            'option_1': 'size',
            'parent': '001',
            'sold_ext_price_adj': '19.99',
            'inventory_qty': 25
        }
    ]

    result = generate_shopify_product(
        parsed_data=parsed_data,
        input_data=input_data,
        variant_data=variant_data,
        log=lambda x: None
    )

    variants = result['product']['variants']

    # Test Variant 1: 50 LB (should have weight fields)
    v1 = variants[0]
    assert 'weight' in v1, "Variant 1 should have weight field"
    assert v1['weight'] == 50.0, "Variant 1 weight should be 50.0"
    assert v1['weight_unit'] == 'lb', "Variant 1 weight_unit should be 'lb'"
    assert v1['grams'] == 22680, "Variant 1 grams should be 22680"

    # Test Variant 2: 25 LB (should have weight fields)
    v2 = variants[1]
    assert 'weight' in v2, "Variant 2 should have weight field"
    assert v2['weight'] == 25.0, "Variant 2 weight should be 25.0"
    assert v2['weight_unit'] == 'lb', "Variant 2 weight_unit should be 'lb'"
    assert v2['grams'] == 11340, "Variant 2 grams should be 11340"

    # Test Variant 3: EACH (should NOT have weight fields)
    v3 = variants[2]
    assert 'weight' not in v3, "Variant 3 should NOT have weight field"
    assert 'weight_unit' not in v3, "Variant 3 should NOT have weight_unit field"
    assert 'grams' not in v3, "Variant 3 should NOT have grams field"

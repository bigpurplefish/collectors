# Input File Structure Requirements

## Overview

This document defines the structure and requirements for input files used by product collectors. Input files can be provided in either Excel (.xlsx) or JSON format and contain product information to be enriched with manufacturer data.

**Last Updated**: November 4, 2025

## File Formats

### Supported Formats

1. **Excel (.xlsx)**: Multi-column spreadsheet format
2. **JSON (.json)**: Array of objects with matching field names

Both formats must contain the same core fields and follow the same data structure requirements.

## Core Field Structure

### Required Fields

These fields must be present in every input file:

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `item_#` | Integer | Unique identifier for each product/variant | `7676` |
| `department` | String | Product category/department | `"FEED"`, `"HORSE"`, `"CAT FOOD"` |
| `description_1` | String | Primary product description | `"PURINA® AMPLIFY® HIGH-FAT HORSE SUPPLEMENT"` |
| `size` | String | Product size/weight | `"50 LB"`, `"32 OZ"`, `"1 GALLON"` |
| `upc_updated` | String | UPC code (12-13 digits) | `"804273058207"` |
| `manufacturer_found` | String | Manufacturer name | `"PURINA MILLS"` |
| `manufacturer_homepage_found` | String | Manufacturer website URL | `"https://www.purinamills.com"` |

### Variant Support Fields

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `parent` | Integer/Float | Reference to parent product's `item_#` for product families | `36962.0` |
| `option_1` | String | First Shopify option dimension (e.g., "size", "weight", "flavor") | `"size"` |
| `option_2` | String | Second Shopify option dimension | `"color"` |
| `option_3` | String | Third Shopify option dimension | `"style"` |
| `option_4` | String | Fourth Shopify option dimension (rarely used) | `null` |
| `color` | String | Color value when color selection is required in Shopify | `"Red"`, `"Blue"` |
| `cost` | Float | Variant cost (wholesale/cost price) | `12.50` |
| `price` | Float | Variant price (retail/selling price) | `24.99` |

**Important - Parent Field**:
- If `parent` equals `item_#`: This is a **parent product** with variants
- If `parent` equals a different `item_#`: This is a **child/variant** product
- If `parent` is **null/empty**: Standalone product with no variants
- The `parent` value must match an existing `item_#` in the same file

**Important - Option Fields**:
- Option fields define which product attributes drive Shopify variant options
- Common values: `"size"`, `"weight"`, `"color"`, `"flavor"`, `"scent"`, `"style"`
- The actual option values come from the corresponding data columns (e.g., if `option_1="size"`, values come from `size` column)
- All products in a family (same `parent` value) should have the same option configuration
- Most products use only `option_1` (typically "size")
- `color` field is separate and used for Shopify color pickers/swatches

### Optional Enrichment Fields

These fields may be populated by upstream processes (e.g., UPCItemDB lookups):

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `upcitemdb_match` | Integer | Match status (0=failed, 1=found) |
| `upcitemdb_status` | String | Match result text |
| `upcitemdb_title` | String | Product title from UPCItemDB |
| `upcitemdb_brand` | String | Brand name from UPCItemDB |
| `upcitemdb_model` | String | Model number |
| `upcitemdb_description` | String | Product description |
| `upcitemdb_category` | String | Product category hierarchy |
| `upcitemdb_size` | String | Size information |
| `upcitemdb_weight` | String | Weight information |
| `upcitemdb_images` | String/Array | Product image URLs |
| `upcitemdb_currency` | String | Currency code |
| `upcitemdb_lowest_recorded_price` | Float | Lowest price found |
| `upcitemdb_highest_recorded_price` | Float | Highest price found |

### Additional Optional Fields

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `search_string` | String | Full-text search query used for discovery |
| `description_2` | String | Secondary description |
| `attribute` | String | Product attribute (e.g., "CRUMBLE") |
| `alternate_lookup` | String | Alternate identifier code |
| `dept_code` | String | Department code |
| `vendor_code` | String | Vendor identifier |
| `pid` | String | Product ID |
| `quick_pick_group` | String | Quick pick grouping |
| `notes` | String | Free-form notes |

### Inventory & Sales Fields (Optional)

These fields contain business metrics and are preserved in output but not used by collectors:

| Field Group | Fields |
|-------------|--------|
| **Inventory** | `inventory_qty`, `inventory_ext_price`, `inventory_ext_cost` |
| **Sales** | `sold_qty`, `sold_ext_price`, `sold_ext_cost`, `sold_qty_adjusted` |
| **Analytics** | `avg_cost_/_unit`, `avg_price_/_unit`, `gross_profit`, `margin` |
| **Adjusted** | `sold_ext_cost_adj`, `sold_ext_price_adj` |

### UPC Fields

| Field Name | Data Type | Description |
|------------|-----------|-------------|
| `upc_updated` | String | Primary UPC field (used by collectors) |
| `upc_staged` | String | Staging UPC field |
| `upc` | Float/String | Alternate UPC field |

**Note**: Collectors typically use `upc_updated` as the primary UPC source.

## Product Variants Structure

### Parent-Child Relationship

The `parent` field enables support for product variants (e.g., different sizes of the same product):

#### Example: Omega Match Oil Supplement (Size Variants)

**Parent Product:**
```json
{
  "item_#": 36962,
  "parent": 36962,
  "description_1": "PURINA® OMEGA MATCH® AHIFLOWER® OIL SUPPLEMENT",
  "size": "1 GALLON",
  "upc_updated": "804273058214",
  "option_1": "size",
  "option_2": null,
  "option_3": null,
  "option_4": null,
  "color": null
}
```

**Variant Product:**
```json
{
  "item_#": 33673,
  "parent": 36962,
  "description_1": "PURINA® OMEGA MATCH® AHIFLOWER® OIL SUPPLEMENT",
  "size": "32 OZ",
  "upc_updated": "804273058221",
  "option_1": "size",
  "option_2": null,
  "option_3": null,
  "option_4": null,
  "color": null
}
```

**Key Points:**
- Parent product has `parent` = `item_#` (36962 = 36962) indicating it's the family parent
- Child product has `parent` = 36962 (references the parent)
- Both have `option_1` = "size" indicating size drives variant selection
- Variant values come from the `size` field: "1 GALLON" vs "32 OZ"

#### How to Identify Product Families

To find all members of a product family:

1. **Find the parent**: Look for rows where `parent` = `item_#`
2. **Find all children**: Look for all rows where `parent` = that parent's `item_#`
3. **Include the parent**: The parent is also a member of its own family

**SQL-style query:**
```sql
-- Find all products in item_# 36962's family
SELECT * FROM products
WHERE parent = 36962
ORDER BY item_#
```

**Python example:**
```python
parent_id = 36962
family = df[df['parent'] == parent_id]  # Includes parent and all children
parent_product = family[family['item_#'] == parent_id].iloc[0]
children = family[family['item_#'] != parent_id]
```

### Variant Rules

1. **Unique Identifiers**: Each variant must have its own unique `item_#` and `upc_updated`
2. **Parent Identification**:
   - Parent products have `parent` = `item_#` (self-referencing)
   - Child products have `parent` = parent's `item_#` (reference to parent)
3. **Same Base Product**: All products in a family share the same `description_1` and `manufacturer_found`
4. **Option Configuration**: All family members must have identical `option_1` through `option_4` values
5. **Differentiating Fields**: Variants differ in the fields specified by option columns (e.g., `size`, `color`)
6. **Self-Standing**: Each variant can be processed independently by collectors with its own UPC

### Common Variant Types

| Variant Type | Option Field | Data Field | Example Values |
|--------------|--------------|------------|----------------|
| **Size variants** | `option_1="size"` | `size` | "15 LB" vs "3.5 LB" vs "50 LB" |
| **Weight variants** | `option_1="weight"` | `size` | "25 LB" vs "50 LB" |
| **Volume variants** | `option_1="size"` | `size` | "32 OZ" vs "1 GALLON" |
| **Color variants** | `option_2="color"` | `color` | "Red" vs "Blue" vs "Green" |
| **Flavor variants** | `option_1="flavor"` | `attribute` or `description_2` | "Apple" vs "Carrot" |
| **Form variants** | `option_1="form"` | `attribute` | "CRUMBLE" vs "PELLET" |
| **Multi-option** | `option_1="size"`, `option_2="color"` | `size`, `color` | "Small/Red" vs "Large/Blue" |

**Note**: Most products (>90%) use only `option_1="size"` for size-based variants.

## Data Type Specifications

### Excel Format

When providing input as Excel (.xlsx):

- **Integer fields** (`item_#`, inventory/sales quantities): Excel Number format, no decimals
- **Float fields** (`parent`, prices, costs): Excel Number format, 2 decimals
- **String fields**: Excel Text or General format
- **UPC fields**: Excel Text format (to preserve leading zeros)

### JSON Format

When providing input as JSON:

```json
[
  {
    "item_#": 7676,
    "parent": null,
    "department": "FEED",
    "description_1": "PURINA® AMPLIFY® HIGH-FAT HORSE SUPPLEMENT",
    "size": "50 LB",
    "upc_updated": "804273058207",
    "manufacturer_found": "PURINA MILLS",
    "manufacturer_homepage_found": "https://www.purinamills.com",
    "upcitemdb_match": 1,
    "upcitemdb_status": "Match found"
  },
  {
    "item_#": 33673,
    "parent": 36962,
    "description_1": "PURINA® OMEGA MATCH® AHIFLOWER® OIL SUPPLEMENT",
    "size": "32 OZ",
    "upc_updated": "804273058221"
  }
]
```

**Type Mapping:**
- `null` for missing values (not empty strings)
- `number` for integers and floats
- `string` for text fields
- `boolean` where applicable

## File Location Conventions

### Directory Structure

```
/Users/moosemarketer/Code/Python/collectors/<collector_name>/
├── input/
│   └── <manufacturer>-<date>.xlsx     # Input file
├── output/
│   └── <manufacturer>-enriched.json   # Output file
├── collector.py
└── requirements.txt
```

### Naming Conventions

- **Input files**: `<manufacturer>-<description>.xlsx` or `.json`
  - Example: `purina-mills.xlsx`
- **Output files**: `<manufacturer>-enriched.json`
  - Example: `purina-mills-enriched.json`

## Validation Requirements

### Pre-Processing Validation

Before running collectors, input files should validate:

1. **Required fields present**: All required fields exist
2. **UPC format**: `upc_updated` contains 12-13 digit numeric strings
3. **Parent references valid**: All `parent` values reference existing `item_#` values
4. **Parent self-reference**: Parent products have `parent` = `item_#`
5. **No circular references**: Variants don't reference each other in a loop
6. **Unique item numbers**: No duplicate `item_#` values
7. **Option consistency**: All products with same `parent` have identical option_1-4 values
8. **Option-data alignment**: If `option_1="color"`, then `color` field must be populated

### Validation Errors

| Error Type | Description | Resolution |
|------------|-------------|------------|
| Missing required field | Required column not found | Add missing column to input file |
| Invalid parent reference | `parent` value doesn't match any `item_#` | Fix parent reference or remove it |
| Parent not self-referencing | Parent product has `parent` ≠ `item_#` | Set parent's `parent` = `item_#` |
| Duplicate item_# | Multiple rows with same `item_#` | Ensure unique identifiers |
| Invalid UPC format | Non-numeric or wrong length UPC | Correct UPC in source data |
| Inconsistent options | Family members have different option values | Ensure all family members have same option_1-4 |
| Missing option data | `option_1="color"` but `color` field empty | Populate the referenced data field |

## Processing Behavior

### Collector Processing Rules

1. **Field Preservation**: Collectors preserve ALL input fields in output
2. **Enrichment Addition**: Collectors add `manufacturer` and `shopify` objects
3. **Variant Independence**: Each variant is processed independently with its own UPC
4. **Parent Awareness**: Collectors MAY use parent relationships for optimization (future)

### Current Variant Handling

**As of November 2025:**
- Variants are processed as independent products
- Each variant gets its own enrichment based on its UPC
- Parent-child relationships are preserved but not actively used during collection
- Future enhancement: Collectors may reuse parent product data for variants

## Example Input Files

### Minimal Required Fields (Excel)

| item_# | department | description_1 | size | upc_updated | manufacturer_found | manufacturer_homepage_found | parent | option_1 | option_2 | option_3 | option_4 | color |
|--------|------------|---------------|------|-------------|-------------------|---------------------------|--------|----------|----------|----------|----------|-------|
| 7676 | FEED | PURINA® AMPLIFY® | 50 LB | 804273058207 | PURINA MILLS | https://www.purinamills.com | | | | | | |
| 36962 | FEED | PURINA® OMEGA MATCH® | 1 GALLON | 804273058214 | PURINA MILLS | https://www.purinamills.com | 36962 | size | | | | |
| 33673 | FEED | PURINA® OMEGA MATCH® | 32 OZ | 804273058221 | PURINA MILLS | https://www.purinamills.com | 36962 | size | | | | |

**Notes:**
- Row 1: Standalone product (no parent, no options)
- Row 2: Parent product (parent=item_#, has option_1="size")
- Row 3: Child variant (parent=36962, same option_1="size")

### Full Example (JSON)

```json
[
  {
    "item_#": 36962,
    "parent": 36962,
    "department": "FEED",
    "description_1": "PURINA® OMEGA MATCH® AHIFLOWER® OIL SUPPLEMENT",
    "size": "1 GALLON",
    "upc_updated": "804273058214",
    "manufacturer_found": "PURINA MILLS",
    "manufacturer_homepage_found": "https://www.purinamills.com",
    "option_1": "size",
    "option_2": null,
    "option_3": null,
    "option_4": null,
    "color": null,
    "search_string": "DOES THE COMPANY THAT MAKES PURINA® OMEGA MATCH® 804273058214 HAVE A WEBSITE",
    "inventory_qty": 5,
    "inventory_ext_price": 199.95,
    "inventory_ext_cost": 149.96,
    "sold_qty": 42,
    "sold_ext_price": 1679.58,
    "sold_ext_cost": 1259.64,
    "upcitemdb_match": 1,
    "upcitemdb_status": "Match found",
    "upcitemdb_title": "Purina Omega Match Ahiflower Oil Supplement 1 Gallon",
    "upcitemdb_brand": "Purina",
    "upcitemdb_category": "Animals & Pet Supplies > Pet Supplies"
  },
  {
    "item_#": 33673,
    "parent": 36962,
    "department": "FEED",
    "description_1": "PURINA® OMEGA MATCH® AHIFLOWER® OIL SUPPLEMENT",
    "size": "32 OZ",
    "upc_updated": "804273058221",
    "manufacturer_found": "PURINA MILLS",
    "manufacturer_homepage_found": "https://www.purinamills.com",
    "option_1": "size",
    "option_2": null,
    "option_3": null,
    "option_4": null,
    "color": null,
    "search_string": "DOES THE COMPANY THAT MAKES PURINA® OMEGA MATCH® 804273058221 HAVE A WEBSITE",
    "inventory_qty": 12,
    "inventory_ext_price": 287.88,
    "inventory_ext_cost": 215.91,
    "sold_qty": 86,
    "sold_ext_price": 2065.14,
    "sold_ext_cost": 1548.86,
    "upcitemdb_match": 1,
    "upcitemdb_status": "Match found",
    "upcitemdb_title": "Purina Omega Match Ahiflower Oil Supplement 32 oz",
    "upcitemdb_brand": "Purina",
    "upcitemdb_category": "Animals & Pet Supplies > Pet Supplies"
  }
]
```

## Migration Notes

### Changes from Previous Format

**What's New (November 2025):**
- Added `parent` field for variant/family support
- Added `option_1` through `option_4` fields to define Shopify variant dimensions
- Added `color` field for color-specific variant handling
- Parent products now self-reference: `parent` = `item_#`
- Option fields specify which data columns drive Shopify variant selection

**What Stayed the Same:**
- All existing required fields remain unchanged
- Field names and data types are backwards compatible
- Collectors still process each row independently by UPC

**Backwards Compatibility:**
- Files without `parent` field still work (treated as all standalone products)
- Files without `option_*` fields still work (no Shopify variant configuration)
- Empty/null `parent` values indicate standalone products (no variants)
- Empty/null option fields indicate no variant configuration
- No code changes required for collectors unless implementing Shopify variant optimization

**Key Behavior Change:**
- **Old**: `parent` field was either null or referenced another `item_#`
- **New**: Parent products have `parent` = `item_#` (self-referencing) for easier family identification

## See Also

- [Output Structure Requirements](OUTPUT_STRUCTURE_REQUIREMENTS.md) - Enriched output format
- [Product Taxonomy](PRODUCT_TAXONOMY.md) - Category classification
- [Technical Docs](TECHNICAL_DOCS.md) - Implementation details

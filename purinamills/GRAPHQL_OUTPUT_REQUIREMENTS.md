# Purinamills Collector - GraphQL API 2025-10 Output Requirements

## Overview

The Purinamills collector outputs product data in a format compatible with **Shopify GraphQL Admin API 2025-10**. This document specifies the expected output structure for integration with the uploader.

---

## Output Format

### Product Structure

The collector outputs products in the following structure:

```json
{
  "product": {
    "title": "Product Name",
    "descriptionHtml": "<p>HTML description</p>",
    "vendor": "Purina",
    "status": "ACTIVE",
    "options": [...],
    "variants": [...],
    "images": [...],
    "metafields": [...],
    "media": [...]  // Optional - only if product has videos or 3D models
  }
}
```

### Field Mappings (REST vs GraphQL)

| REST API (deprecated) | GraphQL API 2025-10 | Notes |
|----------------------|---------------------|-------|
| `body_html` | `descriptionHtml` | HTML product description |
| `published: true/false` | `status: "ACTIVE"/"DRAFT"/"ARCHIVED"` | Product visibility |
| `options` | `options` | Same structure (uploader converts to `productOptions`) |
| N/A | `media` | New field for videos and 3D models |

---

## Product-Level Fields

### Required Fields

#### title (String)
Product title extracted from shop site.

**Example:**
```json
"title": "Purina® Amplify® High-Fat Horse Supplement"
```

#### descriptionHtml (String)
HTML-formatted product description.

**GraphQL Note:** Uses `descriptionHtml` instead of deprecated `body_html`.

**Example:**
```json
"descriptionHtml": "<p>Purina® Amplify® High-Fat Horse Supplement helps hardworking horses...</p>"
```

#### vendor (String)
Product vendor/brand name.

**Example:**
```json
"vendor": "Purina"
```

#### status (String)
Product status for GraphQL API.

**Valid Values:**
- `"ACTIVE"` - Product is published and visible
- `"DRAFT"` - Product is hidden (not used in collector)
- `"ARCHIVED"` - Product is archived (not used in collector)

**GraphQL Note:** Replaces REST API's `published: true/false` boolean.

**Example:**
```json
"status": "ACTIVE"
```

---

### Optional Fields

#### options (Array)
Product options (Size, Color, etc.) extracted from shop site variants.

**Structure:**
```json
"options": [
  {
    "name": "Size",
    "position": 1,
    "values": ["10 LB", "40 LB"]
  }
]
```

**GraphQL Note:** The uploader converts this to `productOptions` format for GraphQL.

#### images (Array)
Product images with variant-specific alt tags for gallery filtering.

**Structure:**
```json
"images": [
  {
    "position": 1,
    "src": "https://shop.purinamills.com/cdn/shop/files/image.jpg",
    "alt": "Product Name #10_LB"
  }
]
```

**Alt Tag Format:**
- Product title + variant option filters
- Example: `"Purina® Amplify® #10_LB #BAG"`
- Filters use `#OPTION_VALUE` format (spaces replaced with underscores)

**GraphQL Note:** Images go in the `images` array. The uploader converts to `media` input with `mediaContentType: "IMAGE"`.

#### media (Array)
Product videos and 3D models (not included in images array).

**Structure:**
```json
"media": [
  {
    "alt": "Video title or description",
    "media_content_type": "EXTERNAL_VIDEO",
    "original_source": "https://www.youtube.com/watch?v=VIDEO_ID",
    "host": "YOUTUBE",
    "external_id": "VIDEO_ID",
    "variant_options": [
      {
        "option1": "10 LB",
        "option2": "",
        "option3": ""
      }
    ]
  }
]
```

**Media Types:**
- `EXTERNAL_VIDEO` - YouTube, Vimeo embedded videos
- `VIDEO` - Hosted videos
- `MODEL_3D` - 3D models (GLB, USDZ)

**Important:** Videos are uploaded using `productCreateMedia` GraphQL mutation after product creation.

#### metafields (Array)
Product-level metafields for additional data.

**Structure:**
```json
"metafields": [
  {
    "namespace": "custom",
    "key": "features",
    "value": "<ul><li>Feature 1</li></ul>",
    "type": "rich_text_field"
  }
]
```

**Purinamills Metafield Keys:**
- `features` - Features & benefits (rich_text_field)
- `nutritional_information` - Nutritional analysis table (rich_text_field)
- `directions` - Feeding directions (rich_text_field)
- `documentation` - PDF documents from www site (json)

---

## Variants

### Structure

```json
"variants": [
  {
    "sku": "7676",
    "price": "54.99",
    "cost": "45.25",
    "barcode": "804273058207",
    "inventory_quantity": 10,
    "position": 1,
    "option1": "10 LB",
    "inventory_policy": "deny",
    "compare_at_price": null,
    "fulfillment_service": "manual",
    "inventory_management": "shopify",
    "taxable": true,
    "grams": 0,
    "weight": 0,
    "weight_unit": "lb",
    "requires_shipping": true,
    "image_id": 1,
    "metafields": []
  }
]
```

### Field Mappings

| Field | Source | Notes |
|-------|--------|-------|
| `sku` | `item_#` from input file | Primary product identifier |
| `barcode` | `sku` or `upc` from input file | UPC/barcode for scanning |
| `price` | `sold_ext_price_adj` from input | Selling price |
| `cost` | `sold_ext_cost_adj` from input | Cost price (for margin calculation) |
| `inventory_quantity` | `inventory_qty` from input | Stock level |
| `option1`, `option2`, etc. | Mapped from shop site variants | Variant selectors |
| `image_id` | Determined from variant-image mapping | Position of associated image |

### Variant Metafields

#### size_info (JSON)
Size information extracted from variant options.

**Example:**
```json
{
  "namespace": "custom",
  "key": "size_info",
  "value": "{\"label\": \"10 LB\", \"weight\": \"10 LB\"}",
  "type": "json"
}
```

---

## Video Support

### How Videos Are Extracted

1. **Source**: Videos are extracted from the shop site's product JSON `media` array
2. **Media Types Supported**:
   - `external_video` - YouTube, Vimeo, etc.
   - `video` - Hosted video files
3. **Variant Association**: Videos inherit variant filters from alt tags (same as images)

### Video Output Format

```json
{
  "alt": "Video description",
  "media_content_type": "EXTERNAL_VIDEO",
  "original_source": "https://www.youtube.com/watch?v=5LBT4o5TcCc",
  "host": "YOUTUBE",
  "external_id": "5LBT4o5TcCc",
  "variant_options": [
    {
      "option1": "32 OZ",
      "option2": "",
      "option3": ""
    },
    {
      "option1": "1 GALLON",
      "option2": "",
      "option3": ""
    }
  ]
}
```

### Uploader Requirements for Videos

Videos **cannot** be uploaded during product creation. The uploader must:

1. Create the product first using `productCreate` mutation
2. Upload videos separately using `productCreateMedia` mutation:

```graphql
mutation {
  productCreateMedia(
    productId: "gid://shopify/Product/123",
    media: [{
      alt: "Video alt text",
      mediaContentType: EXTERNAL_VIDEO,
      originalSource: "https://www.youtube.com/watch?v=VIDEO_ID"
    }]
  ) {
    media { id }
    mediaUserErrors { message }
  }
}
```

3. Associate videos with specific variants using `productVariantAppendMedia` if `variant_options` is present.

---

## GraphQL Compatibility

### API Version
- **Target**: Shopify GraphQL Admin API **2025-10**
- **Supported Until**: October 2026

### Key Differences from REST API

| Feature | REST API (deprecated) | GraphQL API 2025-10 |
|---------|----------------------|---------------------|
| Endpoint | `/admin/api/2025-10/products.json` | `/admin/api/2025-10/graphql.json` |
| Product Creation | Single REST call | `productCreate` mutation |
| Variant Creation | Included in product | `productVariantsBulkCreate` after product |
| Images | Included in product JSON | Converted to `media` input |
| Videos | Not supported via JSON | `productCreateMedia` mutation required |
| Description Field | `body_html` | `descriptionHtml` |
| Published Status | `published: true/false` | `status: ACTIVE/DRAFT/ARCHIVED` |

### Uploader Conversion

The uploader handles the conversion from collector output to GraphQL format:

1. **Field Name Mapping**: Converts `descriptionHtml`, `status`, etc.
2. **Media Processing**: Converts images array to GraphQL `media` input
3. **Video Upload**: Processes `media` array videos via `productCreateMedia`
4. **Variant Association**: Links images/videos to variants based on `variant_options`

---

## Testing Output

### Validation Checklist

✅ Product has `descriptionHtml` (not `body_html`)
✅ Product has `status: "ACTIVE"` (not `published: true`)
✅ Images array contains proper alt tags with variant filters
✅ Videos are in `media` array (not `images` array)
✅ Video entries have `media_content_type: "EXTERNAL_VIDEO"` or `"VIDEO"`
✅ Video entries have `original_source` URL
✅ Video entries have `host` and `external_id` for external videos
✅ Video entries have `variant_options` for association

### Example Test Command

```bash
python3 test_workflow.py
```

This will:
1. Load first product from input file
2. Search for product on shop site
3. Parse product page
4. Fetch additional materials from www site
5. Generate GraphQL-compatible output
6. Save to `output/test_output.json`

---

## Integration with Uploader

### Expected Flow

1. **Collector** generates products in GraphQL-compatible format
2. **Uploader** reads product JSON and:
   - Creates product using `productCreate` mutation
   - Uploads images as media during product creation
   - Uploads videos using `productCreateMedia` after product creation
   - Associates media with variants using `productVariantAppendMedia`
   - Creates variants using `productVariantsBulkCreate`

### Uploader Location

```
/Users/moosemarketer/Code/Python/uploader
```

### Uploader Requirements

See `/Users/moosemarketer/Code/Python/uploader/requirements/SHOPIFY_API_2025-10_REQUIREMENTS.md` for detailed uploader specifications.

---

## Document Version

- **Version**: 1.0
- **Date**: November 4, 2025
- **API Version**: Shopify GraphQL Admin API 2025-10
- **Collector Version**: Compatible with main branch (post-GraphQL update)

---

## Related Documentation

- Shopify GraphQL Admin API: https://shopify.dev/docs/api/admin-graphql
- Uploader Requirements: `/Users/moosemarketer/Code/Python/uploader/requirements/SHOPIFY_API_2025-10_REQUIREMENTS.md`
- Collector Architecture: `CLAUDE.md`

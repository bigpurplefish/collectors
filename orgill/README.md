# Orgill Product Collector

Collects and enriches product data from Orgill website (requires authentication) for Shopify import.

## Overview

This collector retrieves product information from:
- **www.orgill.com** - B2B distributor website with authentication required

Uses sophisticated authentication system with multiple login strategies.

## Features

### Authentication
- **Multi-strategy login** - Multiple authentication approaches
- **Session management** - Persistent authenticated sessions
- **Cookie handling** - Automatic session cookie management
- **Login error handling** - Raises StrategyLoginError on failure

### Search & Collection
- **Authenticated search** - Requires valid credentials
- **UPC override support** - Hardcoded mappings for problematic products
- **Post-authentication search** - Uses authenticated session

### Data Processing
- **B2B HTML parsing** - Extracts product data from B2B structure
- **Description extraction** - Parses product descriptions
- **Image extraction** - Collects product images
- **Distributor data** - Captures distributor-specific information

### Image Processing
- **Gallery extraction** - Multi-source image collection
- **URL normalization** - Converts to HTTPS, removes query params
- **Deduplication** - Removes duplicate images

### User Interfaces
- **Thread-safe GUI** with credential configuration
- **CLI interface** for automation
- **Real-time progress tracking**
- **Auto-save configuration** (excluding credentials)

## Installation

```bash
cd /Users/moosemarketer/Code/garoppos/collectors/orgill
pyenv local orgill
pip install -r requirements.txt

# For GUI/development
pip install -r requirements-gui.txt
pip install -r requirements-dev.txt
```

### Dependencies

**Core:** `requests>=2.31.0`, `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`, `openpyxl>=3.1.0`
**GUI:** `ttkbootstrap>=1.10.1`
**Dev:** `pytest>=7.4.0`, `black>=23.7.0`, `flake8>=6.1.0`

## Usage

### GUI Mode

```bash
python gui.py
```

The GUI provides credential input fields for authentication.

### Command Line

```bash
python main.py --input input/products.json --output output/products.json
```

Note: CLI requires credentials to be configured via GUI or API.

### Python API

```python
from src.collector import OrgillCollector

collector = OrgillCollector()

# Set credentials
collector.set_auth(username="user@example.com", password="password")

# Find product URL (will authenticate automatically)
try:
    product_url = collector.find_product_url("012345678901", None, 30, print)
except StrategyLoginError as e:
    print(f"Authentication failed: {e}")
```

## Project Structure

```
orgill/
├── main.py                 # CLI entry point
├── gui.py                  # GUI entry point
├── src/                    # Application code
│   ├── collector.py        # Main orchestration
│   ├── auth.py             # Authentication system
│   ├── search.py           # Authenticated search
│   └── parser.py           # HTML parsing
├── tests/                  # Test scripts
└── README.md               # This file
```

## Configuration

```python
SITE_CONFIG = {
    "key": "orgill",
    "display_name": "Orgill",
    "origin": "https://www.orgill.com",
    "robots": "respect",
    "search": {"upc_overrides": {}}
}
```

## Architecture

### Core Components

**collector.py** - Main orchestration with authentication integration

**auth.py** - Authentication system:
- `OrgillAuthenticator` class with multi-strategy login
- Session management and cookie persistence
- `login()` method with retry logic
- Raises `StrategyLoginError` on authentication failure

**search.py** - Authenticated search:
- Uses authenticated session for searches
- UPC-based product lookup
- B2B-specific search logic

**parser.py** - B2B HTML parsing:
- Extracts product data from B2B structure
- Handles distributor-specific fields
- Parses pricing and availability (if needed)

### Data Flow

1. **Authentication**: Login with credentials → Establish session → Store cookies
2. **Search**: Use authenticated session → Search by UPC → Extract product URL
3. **Parse**: Fetch product page with session → Parse HTML → Extract data
4. **Output**: Combine input + manufacturer data

## Security Notes

- **Credentials storage**: GUI does not persist credentials in config
- **Session handling**: Sessions are short-lived and not persisted
- **Authentication errors**: Raises explicit errors for debugging
- **Respect robots.txt**: Config includes `"robots": "respect"`

## Notes

- **Authentication required** - Cannot function without valid credentials
- **B2B site** - Different structure from consumer sites
- **Multi-strategy login** - Sophisticated authentication handling
- **Session management** - Persistent sessions during collection
- **StrategyLoginError** - Explicit authentication error handling

## License

Internal tool - Not for public distribution

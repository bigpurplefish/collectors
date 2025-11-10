"""
Configuration management for Cambridge collector.

Handles loading and saving configuration with auto-save support.
"""

import json
import os
import logging
from typing import Dict, Any


# Project root directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
CACHE_DIR = os.path.join(APP_DIR, "cache")
INDEX_CACHE_FILE = os.path.join(CACHE_DIR, "product_index.json")


# Default configuration
DEFAULT_CONFIG = {
    "_SYSTEM_SETTINGS": "# Cambridge Dealer Portal Credentials",
    "portal_username": "",
    "portal_password": "",

    "_USER_SETTINGS": "# Application Settings",
    "input_file": "",
    "output_file": "",
    "log_file": "",
    "window_geometry": "900x900",

    "_PROCESSING_SETTINGS": "# Processing Options",
    "processing_mode": "skip",  # skip or overwrite
    "start_record": "",  # blank = start from beginning
    "end_record": "",    # blank = process to end
    "rebuild_index": False,  # Force rebuild product index
    "index_max_age_days": 7,  # Auto-rebuild if older than 7 days

    "_IMAGE_SETTINGS": "# Image Quality (for UPCItemDB fallback if needed)",
    "laplacian_threshold": 100,

    "_SITE_CONFIG": "# Cambridge Site Configuration (embedded)",
    "public_origin": "https://www.cambridgepavers.com",
    "portal_origin": "https://shop.cambridgepavers.com",
    "fuzzy_match_threshold": 60.0,  # Minimum fuzzy match score (0-100)
    "timeout": 30,
}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file or create with defaults.

    Returns:
        Configuration dictionary
    """
    if not os.path.exists(CONFIG_FILE):
        logging.info(f"Config file not found, creating default: {CONFIG_FILE}")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Merge with defaults (add any new keys from DEFAULT_CONFIG)
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)

        return merged

    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Failed to save config: {e}")

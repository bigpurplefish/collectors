"""
Configuration management for Aggregates collector.

Handles loading and saving configuration with auto-save support.
"""

import json
import os
import logging
from typing import Dict, Any


# Project root directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")


# Default configuration
DEFAULT_CONFIG = {
    "_USER_SETTINGS": "# Application Settings",
    "input_file": "",
    "output_file": "",
    "log_file": "",
    "window_geometry": "900x800",

    "_AWS_SETTINGS": "# AWS S3 Settings",
    "AWS_ACCESS_KEY_ID": "",
    "AWS_SECRET_ACCESS_KEY": "",
    "AWS_REGION_NAME": "",
    "S3_BUCKET": "",
    "S3_FOLDER": "aggregates/images",

    "_PROCESSING_SETTINGS": "# Processing Options",
    "processing_mode": "skip",  # skip or overwrite
    "start_record": "",  # blank = start from first product
    "end_record": "",    # blank = process to last product
}


def load_config() -> Dict[str, Any]:
    """Load configuration from file or create with defaults."""
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
    """Save configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Failed to save config: {e}")

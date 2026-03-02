#!/usr/bin/env python3
"""
Aggregates Excel-to-Categorizer Converter - CLI Entry Point

Converts product data from Excel spreadsheet into categorizer-compatible JSON.
"""

import sys
import os
import logging

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config
from src.processor import process_products


def setup_logging(log_file: str):
    """Setup logging with dual output (console + file)."""
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True,
    )

    if log_file:
        for handler in logging.root.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.stream.reconfigure(line_buffering=True)


def main():
    """Main entry point for CLI."""
    print("=" * 80)
    print("Aggregates Excel-to-Categorizer Converter - CLI Mode")
    print("=" * 80)
    print()

    cfg = load_config()

    log_file = cfg.get("log_file", "")
    if log_file:
        setup_logging(log_file)
        print(f"Logging to: {log_file}")

    input_file = cfg.get("input_file", "")
    output_file = cfg.get("output_file", "")

    if not input_file:
        print("Error: Input file not configured")
        print("Please edit config.json or use the GUI to configure settings")
        return 1

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return 1

    if not output_file:
        print("Error: Output file not configured")
        print("Please edit config.json or use the GUI to configure settings")
        return 1

    print("Configuration:")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Processing Mode: {cfg.get('processing_mode', 'skip')}")
    print()

    try:
        process_products(cfg, status_fn=print)
        print()
        print("Processing completed successfully")
        return 0

    except KeyboardInterrupt:
        print()
        print("Processing interrupted by user")
        return 130

    except Exception as e:
        print()
        print(f"Fatal error: {e}")
        logging.exception("Fatal error in main()")
        return 1


if __name__ == "__main__":
    sys.exit(main())

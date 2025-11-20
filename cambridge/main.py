#!/usr/bin/env python3
"""
Cambridge Product Collector - CLI Entry Point

Command-line interface for running the Cambridge collector.
"""

import sys
import os
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config
from src.processor import process_products


def setup_logging(log_file: str):
    """
    Setup logging configuration with dual output (console + file).

    Args:
        log_file: Path to log file
    """
    # Ensure log directory exists
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # Create handlers for both console and file
    handlers = [
        logging.StreamHandler(sys.stdout)  # Console output
    ]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        # Force immediate flush after each log message
        file_handler.setLevel(logging.INFO)
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        force=True  # Force reconfiguration if already configured
    )

    # Force unbuffered output for file handler
    if log_file:
        for handler in logging.root.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.stream.reconfigure(line_buffering=True)


def main():
    """Main entry point for CLI."""
    print("=" * 80)
    print("Cambridge Product Collector - CLI Mode")
    print("=" * 80)
    print()

    # Load configuration
    cfg = load_config()

    # Setup logging
    log_file = cfg.get("log_file", "")
    if log_file:
        setup_logging(log_file)
        print(f"Logging to: {log_file}")
    else:
        print("Warning: No log file configured")

    # Validate configuration
    input_file = cfg.get("input_file", "")
    output_file = cfg.get("output_file", "")
    portal_username = cfg.get("portal_username", "")
    portal_password = cfg.get("portal_password", "")

    if not input_file:
        print("❌ Error: Input file not configured")
        print("Please edit config.json or use the GUI to configure settings")
        return 1

    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found: {input_file}")
        return 1

    if not output_file:
        print("❌ Error: Output file not configured")
        print("Please edit config.json or use the GUI to configure settings")
        return 1

    if not portal_username or not portal_password:
        print("❌ Error: Dealer portal credentials not configured")
        print("Please edit config.json or use the GUI to configure credentials")
        return 1

    print()
    print("Configuration:")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Portal Username: {portal_username}")
    print(f"  Processing Mode: {cfg.get('processing_mode', 'skip')}")
    print()

    # Run processing
    try:
        process_products(cfg, status_fn=print)
        print()
        print("✓ Processing completed successfully")
        return 0

    except KeyboardInterrupt:
        print()
        print("⚠ Processing interrupted by user")
        return 130

    except Exception as e:
        print()
        print(f"❌ Fatal error: {e}")
        logging.exception("Fatal error in main()")
        return 1


if __name__ == "__main__":
    sys.exit(main())

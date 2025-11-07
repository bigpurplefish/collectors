#!/usr/bin/env python3
"""
Coastal Pet Product Collector - Main Entry Point

Collects product data from https://www.coastalpet.com.
"""

import argparse
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.collector import CoastalCollector


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Coastal Pet Product Collector")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to output JSON file")

    args = parser.parse_args()

    # Implementation here
    print(f"Processing {args.input} -> {args.output}")

    # TODO: Implement actual collection logic
    collector = CoastalCollector()
    print(f"Collector initialized with config: {collector.config['origin']}")


if __name__ == "__main__":
    main()

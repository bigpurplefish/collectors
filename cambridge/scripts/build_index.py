#!/usr/bin/env python3
"""
Standalone Product Index Builder

Builds and caches the Cambridge product index.
Can be run independently of the main collector.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.collector import CambridgeCollector
from src.config import load_config


def main():
    """Main entry point for index builder."""
    print("=" * 80)
    print("Cambridge Product Index Builder")
    print("=" * 80)
    print()

    # Load configuration
    cfg = load_config()

    # Initialize collector
    print("Initializing collector...")
    collector = CambridgeCollector(cfg)

    # Build index (force rebuild)
    try:
        print()
        if collector.ensure_index_loaded(force_rebuild=True, log=print):
            print()
            print("=" * 80)
            print("✓ Product index built and cached successfully")
            print("=" * 80)
            return 0
        else:
            print()
            print("=" * 80)
            print("❌ Failed to build product index")
            print("=" * 80)
            return 1

    except KeyboardInterrupt:
        print()
        print("⚠ Index building interrupted by user")
        return 130

    except Exception as e:
        print()
        print(f"❌ Fatal error: {e}")
        return 1

    finally:
        collector.close()


if __name__ == "__main__":
    sys.exit(main())

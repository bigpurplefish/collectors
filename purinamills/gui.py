#!/usr/bin/env python3
"""
Purinamills Product Collector - GUI

Thread-safe GUI for running the Purinamills collector with queue-based communication.
Follows GUI_DESIGN_REQUIREMENTS.md patterns.
"""

import os
import sys
import json
import logging
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToolTip
import threading
import queue
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.collector import PurinamillsCollector, SITE_CONFIG

# Configuration file path
APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "_COMMENT_USER_SETTINGS": "User-configurable settings",
    "INPUT_FILE": "",
    "OUTPUT_FILE": "",
    "LOG_FILE": "logs/purinamills.log",
    "WINDOW_GEOMETRY": "900x900",
    "PROCESSING_MODE": "skip",  # "skip" or "overwrite"
    "START_RECORD": "",
    "END_RECORD": "",

    "_COMMENT_SYSTEM_INFO": "System information (do not edit)",
    "COLLECTOR_NAME": "Purinamills",
    "COLLECTOR_ORIGIN": SITE_CONFIG["origin"]
}


def load_config():
    """Load configuration or create with defaults."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Merge with defaults in case new fields were added
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        logging.error(f"Config load error: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logging.error(f"Config save error: {e}")


def build_gui():
    """Build and launch the GUI."""
    # Load configuration
    cfg = load_config()

    # Create main window
    app = tb.Window(themename="darkly")
    app.title(f"{cfg['COLLECTOR_NAME']} Product Collector")
    app.geometry(cfg.get("WINDOW_GEOMETRY", "900x900"))

    # Queues for thread-safe communication
    status_queue = queue.Queue()
    button_control_queue = queue.Queue()
    messagebox_queue = queue.Queue()  # For thread-safe messagebox calls

    # Toolbar
    toolbar = tb.Frame(app)
    toolbar.pack(side="top", fill="x", padx=5, pady=5)

    # Main container
    container = tb.Frame(app, padding=20)
    container.pack(fill="both", expand=True)
    container.columnconfigure(1, weight=1)  # Make input fields expandable

    # Title
    title = tb.Label(
        container,
        text=f"{cfg['COLLECTOR_NAME']} Product Collector",
        font=("Arial", 16, "bold")
    )
    title.grid(row=0, column=0, columnspan=3, pady=(0, 10))

    # Site info
    site_label = tb.Label(
        container,
        text=f"Site: {cfg['COLLECTOR_ORIGIN']}",
        font=("Arial", 10)
    )
    site_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))

    # Row counter
    current_row = 2

    # ========== Input File ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Input File", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Select the input file containing your product data.\n\nSupports both JSON (.json) and Excel (.xlsx, .xlsm) formats.\nFile should include product information with UPCs and names.\n\nTip: Use the Browse button to easily find your file.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    input_var = tb.StringVar(value=cfg.get("INPUT_FILE", ""))
    tb.Entry(container, textvariable=input_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    def browse_input():
        try:
            filename = filedialog.askopenfilename(
                title="Select Input File",
                filetypes=[
                    ("JSON files", "*.json"),
                    ("Excel files", "*.xlsx *.xlsm"),
                    ("All files", "*.*")
                ]
            )
            if filename:
                input_var.set(filename)
        except Exception as e:
            messagebox.showerror("Browse Failed", f"Failed to open file dialog:\n\n{str(e)}")

    tb.Button(
        container,
        text="Browse",
        command=browse_input,
        bootstyle="info-outline"
    ).grid(row=current_row, column=2, padx=5, pady=5)

    # Auto-save
    def on_input_change(*args):
        try:
            cfg["INPUT_FILE"] = input_var.get()
            save_config(cfg)
        except Exception:
            pass

    input_var.trace_add("write", on_input_change)
    current_row += 1

    # ========== Output File ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Output File", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Select where to save the enriched product data.\n\nThe output will be a JSON file with manufacturer data added.\n\nTip: Choose a different name than your input file to avoid overwriting.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    output_var = tb.StringVar(value=cfg.get("OUTPUT_FILE", ""))
    tb.Entry(container, textvariable=output_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    def browse_output():
        try:
            filename = filedialog.asksaveasfilename(
                title="Select Output File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                defaultextension=".json"
            )
            if filename:
                output_var.set(filename)
        except Exception as e:
            messagebox.showerror("Browse Failed", f"Failed to open file dialog:\n\n{str(e)}")

    tb.Button(
        container,
        text="Browse",
        command=browse_output,
        bootstyle="info-outline"
    ).grid(row=current_row, column=2, padx=5, pady=5)

    # Auto-save
    def on_output_change(*args):
        try:
            cfg["OUTPUT_FILE"] = output_var.get()
            save_config(cfg)
        except Exception:
            pass

    output_var.trace_add("write", on_output_change)
    current_row += 1

    # ========== Log File ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Log File", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Select where to save the processing log.\n\nThis log file will contain detailed information about each product processed.\n\nTip: Logs are useful for debugging and tracking progress.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    log_var = tb.StringVar(value=cfg.get("LOG_FILE", "logs/purinamills.log"))
    tb.Entry(container, textvariable=log_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    def browse_log():
        try:
            filename = filedialog.asksaveasfilename(
                title="Select Log File",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                defaultextension=".log"
            )
            if filename:
                log_var.set(filename)
        except Exception as e:
            messagebox.showerror("Browse Failed", f"Failed to open file dialog:\n\n{str(e)}")

    tb.Button(
        container,
        text="Browse",
        command=browse_log,
        bootstyle="info-outline"
    ).grid(row=current_row, column=2, padx=5, pady=5)

    # Auto-save
    def on_log_change(*args):
        try:
            cfg["LOG_FILE"] = log_var.get()
            save_config(cfg)
        except Exception:
            pass

    log_var.trace_add("write", on_log_change)
    current_row += 1

    # ========== Processing Mode ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Processing Mode", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Choose how to handle products that have already been processed.\n\nSkip: Skip products that already have manufacturer data in the output file.\nOverwrite: Re-process all products, overwriting existing data.\n\nTip: Use 'Skip' to resume interrupted processing.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    mode_frame = tb.Frame(container)
    mode_frame.grid(row=current_row, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    mode_var = tb.StringVar(value=cfg.get("PROCESSING_MODE", "skip"))

    skip_radio = tb.Radiobutton(
        mode_frame,
        text="Skip Processed Records",
        variable=mode_var,
        value="skip",
        bootstyle="primary"
    )
    skip_radio.pack(side="left", padx=(0, 20))

    overwrite_radio = tb.Radiobutton(
        mode_frame,
        text="Overwrite All Records",
        variable=mode_var,
        value="overwrite",
        bootstyle="warning"
    )
    overwrite_radio.pack(side="left")

    # Auto-save
    def on_mode_change(*args):
        try:
            cfg["PROCESSING_MODE"] = mode_var.get()
            save_config(cfg)
        except Exception:
            pass

    mode_var.trace_add("write", on_mode_change)
    current_row += 1

    # ========== Start Record ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Start Record", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Specify the first record to process (1-based index).\n\nLeave empty to start from the beginning.\nExample: Enter '10' to start processing from the 10th record.\n\nTip: Useful for processing specific ranges of products.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    # Use StringVar to allow blank values in spinbox
    start_val = cfg.get("START_RECORD", "")
    start_var = tb.StringVar(value=start_val)
    start_spinbox = tb.Spinbox(
        container,
        textvariable=start_var,
        from_=0,
        to=999999,
        increment=1,
        width=10
    )
    start_spinbox.grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    # Auto-save
    def on_start_change(*args):
        try:
            val = start_var.get().strip()
            # Validate it's a number or blank
            if val:
                int(val)  # Validate it's a valid integer
            cfg["START_RECORD"] = val
            save_config(cfg)
        except (ValueError, tk.TclError, Exception):
            # Handle invalid spinbox values gracefully
            cfg["START_RECORD"] = ""
            save_config(cfg)

    start_var.trace_add("write", on_start_change)
    current_row += 1

    # ========== End Record ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="End Record", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Specify the last record to process (1-based index).\n\nLeave empty to process until the end.\nExample: Enter '50' to stop processing after the 50th record.\n\nTip: Combine with Start Record to process specific ranges.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    # Use StringVar to allow blank values in spinbox
    end_val = cfg.get("END_RECORD", "")
    end_var = tb.StringVar(value=end_val)
    end_spinbox = tb.Spinbox(
        container,
        textvariable=end_var,
        from_=0,
        to=999999,
        increment=1,
        width=10
    )
    end_spinbox.grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    # Auto-save
    def on_end_change(*args):
        try:
            val = end_var.get().strip()
            # Validate it's a number or blank
            if val:
                int(val)  # Validate it's a valid integer
            cfg["END_RECORD"] = val
            save_config(cfg)
        except (ValueError, tk.TclError, Exception):
            # Handle invalid spinbox values gracefully
            cfg["END_RECORD"] = ""
            save_config(cfg)

    end_var.trace_add("write", on_end_change)
    current_row += 1

    # ========== Laplacian Threshold ==========
    label_frame = tb.Frame(container)
    label_frame.grid(row=current_row, column=0, sticky="w", padx=5, pady=5)

    tb.Label(label_frame, text="Laplacian Threshold", anchor="w").pack(side="left")
    help_icon = tb.Label(
        label_frame,
        text=" ⓘ ",
        font=("Arial", 9),
        foreground="#5BC0DE",
        cursor="hand2"
    )
    help_icon.pack(side="left")
    ToolTip(
        help_icon,
        text="Minimum image sharpness score for UPCItemDB fallback images.\n\nImages below this threshold will be rejected as low quality.\nDefault: 100\n\nHigher values = stricter quality requirements.\nLower values = accept more images (including slightly blurry ones).",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    laplacian_var = tb.IntVar(value=cfg.get("LAPLACIAN_THRESHOLD", 100))
    tb.Spinbox(
        container,
        textvariable=laplacian_var,
        from_=0,
        to=500,
        increment=10,
        width=10
    ).grid(
        row=current_row, column=1, sticky="w", padx=5, pady=5
    )

    # Auto-save
    def on_laplacian_change(*args):
        try:
            cfg["LAPLACIAN_THRESHOLD"] = laplacian_var.get()
            save_config(cfg)
        except Exception:
            pass

    laplacian_var.trace_add("write", on_laplacian_change)
    current_row += 1

    # ========== Buttons ==========
    button_frame = tb.Frame(app)
    button_frame.pack(pady=10)

    def validate_inputs():
        """Validate all required inputs."""
        try:
            if not input_var.get().strip():
                messagebox.showerror("Validation Error", "Input File is required.")
                return False

            if not os.path.exists(input_var.get()):
                messagebox.showerror("Validation Error", "Input File does not exist.")
                return False

            if not output_var.get().strip():
                messagebox.showerror("Validation Error", "Output File is required.")
                return False

            if not log_var.get().strip():
                messagebox.showerror("Validation Error", "Log File is required.")
                return False

            return True
        except Exception as e:
            messagebox.showerror("Validation Error", f"Unexpected error during validation:\n\n{str(e)}")
            return False

    def clear_status():
        """Clear status log."""
        try:
            status_log.config(state="normal")
            status_log.delete("1.0", "end")
            status_log.config(state="disabled")
        except Exception as e:
            logging.warning(f"Failed to clear status: {e}")

    def status(msg):
        """Thread-safe status update (also prints to console)."""
        try:
            # Print to console for VS Code terminal visibility
            print(msg)
            # Queue for GUI status window
            status_queue.put(msg)
        except Exception as e:
            logging.error(f"Failed to queue status message: {e}")

    def start_processing():
        """Start processing in worker thread."""
        if not validate_inputs():
            return

        # Clear status
        clear_status()

        # Disable buttons
        start_btn.config(state="disabled")

        def worker():
            """Background worker thread."""
            try:
                input_file = input_var.get()
                output_file = output_var.get()
                log_file = log_var.get()
                processing_mode = mode_var.get()

                # Safely get integer values, handling blank/invalid inputs
                try:
                    start_val = start_var.get().strip()
                    start_record_int = int(start_val) if start_val else 0
                except (ValueError, tk.TclError, AttributeError):
                    start_record_int = 0

                try:
                    end_val = end_var.get().strip()
                    end_record_int = int(end_val) if end_val else 0
                except (ValueError, tk.TclError, AttributeError):
                    end_record_int = 0

                try:
                    laplacian_threshold = laplacian_var.get()
                except (ValueError, tk.TclError):
                    laplacian_threshold = 100  # Default value

                # Setup logging
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                logging.basicConfig(
                    filename=log_file,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s'
                )

                status("=" * 80)
                status(f"{cfg['COLLECTOR_NAME']} Product Collector")
                status("=" * 80)
                status(f"Input: {input_file}")
                status(f"Output: {output_file}")
                status(f"Log: {log_file}")
                status(f"Processing Mode: {processing_mode.upper()}")
                status(f"Laplacian Threshold: {laplacian_threshold}")

                # Parse start/end record
                start_idx = 0
                end_idx = None

                if start_record_int > 0:
                    start_idx = start_record_int - 1  # Convert to 0-based
                    status(f"Start Record: {start_record_int}")

                if end_record_int > 0:
                    end_idx = end_record_int  # Keep as 1-based for slicing
                    status(f"End Record: {end_record_int}")

                status("")

                # Load input (supports JSON and Excel)
                status("Loading input file...")

                # Add parent directory to path for shared imports
                import sys
                parent_path = os.path.dirname(os.path.dirname(__file__))
                if parent_path not in sys.path:
                    sys.path.insert(0, parent_path)

                from shared.src.excel_utils import load_products
                all_products = load_products(input_file)

                if not isinstance(all_products, list):
                    raise ValueError("Input must be an array of products")

                status(f"Loaded {len(all_products)} total products")

                # Apply range filtering
                products = all_products[start_idx:end_idx]
                status(f"Processing range: records {start_idx + 1} to {(end_idx if end_idx else len(all_products))}")
                status(f"Products to process: {len(products)}")
                status("")

                # Load existing output if it exists and we're in skip mode
                existing_products = {}
                if processing_mode == "skip" and os.path.exists(output_file):
                    status("Loading existing output file for skip mode...")
                    try:
                        existing_products = load_products(output_file)
                        # Index by UPC or item_# for faster lookup
                        existing_dict = {}
                        for p in existing_products:
                            upc = p.get('upc_updated') or p.get('upc', '')
                            item_num = p.get('item_#', '')
                            if upc:
                                existing_dict[upc] = p
                            elif item_num:
                                existing_dict[f"item_{item_num}"] = p
                        existing_products = existing_dict
                        status(f"✅ Loaded {len(existing_products)} existing records")
                    except Exception as e:
                        status(f"⚠ Could not load existing output: {str(e)}")
                        existing_products = {}
                    status("")

                # Initialize collector
                status("Initializing collector...")
                collector = PurinamillsCollector()
                status("✅ Collector initialized")
                status("")

                # Import HTTP library for requests
                import requests
                from time import sleep
                from random import uniform

                # Group products by parent field
                # - If parent is blank: single product
                # - If parent == item_#: parent product (first variant)
                # - If parent != item_#: child variant
                status("Grouping products by parent field...")
                product_groups = []
                processed_items = set()

                for product in products:
                    item_num = str(product.get('item_#', ''))
                    parent = str(product.get('parent', '')).strip()

                    # Skip if already processed as part of a group
                    if item_num in processed_items:
                        continue

                    if not parent:
                        # Single product (no variants)
                        product_groups.append({
                            'parent': product,
                            'variants': []
                        })
                        processed_items.add(item_num)
                    elif parent == item_num:
                        # Parent product - find all its variants
                        variants = [p for p in products if str(p.get('parent', '')).strip() == parent and str(p.get('item_#', '')) != parent]
                        product_groups.append({
                            'parent': product,
                            'variants': variants
                        })
                        processed_items.add(item_num)
                        for v in variants:
                            processed_items.add(str(v.get('item_#', '')))

                status(f"  ✓ Grouped {len(products)} products into {len(product_groups)} product(s)")
                status("")

                # Process products
                enriched = []
                failed_records = []  # Track failed records for summary and error log
                unmatched_products = []  # Track unmatched products (no manufacturer match AND no UPCItemDB match)
                success_count = 0
                skip_count = 0
                fail_count = 0
                unmatched_count = 0

                for i, group in enumerate(product_groups):
                    product = group['parent']
                    variants = group['variants']
                    upc = product.get('upc_updated') or product.get('upc', '')
                    item_num = product.get('item_#', '')
                    name = product.get('description_1', '')

                    # Calculate actual record number in original file
                    actual_record_num = start_idx + i + 1

                    variant_info = f" ({len(variants) + 1} variants)" if variants else ""
                    status(f"[{i+1}/{len(product_groups)}] Record #{actual_record_num}: {name}{variant_info}")
                    status(f"  UPC: {upc}")

                    # Check if already processed (skip mode)
                    if processing_mode == "skip":
                        lookup_key = upc if upc else f"item_{item_num}"
                        existing = existing_products.get(lookup_key)
                        if existing and existing.get('product'):  # Check for Shopify format
                            status(f"  ⏭ Skipping (already processed)")
                            enriched.append(existing)
                            skip_count += 1
                            status("")
                            continue

                    try:
                        # Step 1: Find product URL
                        status(f"  🔍 Searching for product...")
                        product_url = collector.find_product_url(
                            upc=upc,
                            http_get=requests.get,
                            timeout=30,
                            log=status,
                            product_data=product
                        )

                        if not product_url:
                            status(f"  ⚠ Product not found on either site")

                            # Check for UPCItemDB fallback
                            upcitemdb_status = product.get('upcitemdb_status', '')

                            if upcitemdb_status == "Lookup failed":
                                error_msg = "No manufacturer match and no UPCItemDB data"
                                status(f"  ⚠ Unmatched: No manufacturer match and no UPCItemDB data")
                                # This is an unmatched product - add to both lists
                                unmatched_record = {
                                    **product,  # Include all original fields
                                    'error_reason': error_msg
                                }
                                unmatched_products.append(unmatched_record)
                                failed_records.append(unmatched_record)
                                unmatched_count += 1
                                fail_count += 1
                                status("")
                                continue

                            elif upcitemdb_status == "Match found":
                                status(f"  🔄 Falling back to UPCItemDB data...")

                                # Load placeholder images for detection
                                # Import from shared library
                                parent_path = os.path.dirname(os.path.dirname(__file__))
                                if parent_path not in sys.path:
                                    sys.path.insert(0, parent_path)

                                from shared.src.image_quality import load_placeholder_images, select_best_image
                                placeholder_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "placeholder_images")
                                placeholders = load_placeholder_images(placeholder_dir)

                                # Get UPCItemDB image URLs
                                import ast
                                image_urls_raw = product.get('upcitemdb_images', [])

                                # Parse if it's a string representation of a list
                                if isinstance(image_urls_raw, str) and image_urls_raw:
                                    try:
                                        image_urls = ast.literal_eval(image_urls_raw)
                                    except (ValueError, SyntaxError):
                                        status(f"  ⚠ Could not parse UPCItemDB images: {image_urls_raw}")
                                        image_urls = []
                                elif isinstance(image_urls_raw, list):
                                    image_urls = image_urls_raw
                                else:
                                    image_urls = []

                                if not image_urls:
                                    error_msg = "No UPCItemDB images available"
                                    status(f"  ⚠ {error_msg}")
                                    # Don't add to enriched - only add to failed_records
                                    failed_records.append({
                                        **product,
                                        'error_reason': error_msg
                                    })
                                    fail_count += 1
                                    status("")
                                    continue

                                # Select best image
                                best_image, best_url = select_best_image(
                                    image_urls=image_urls,
                                    placeholders=placeholders,
                                    laplacian_threshold=laplacian_threshold,
                                    hamming_threshold=10,
                                    log=status
                                )

                                if not best_image:
                                    error_msg = "No suitable UPCItemDB images (failed quality check)"
                                    status(f"  ⚠ No suitable UPCItemDB images found")
                                    # Don't add to enriched - only add to failed_records
                                    failed_records.append({
                                        **product,
                                        'error_reason': error_msg
                                    })
                                    fail_count += 1
                                    status("")
                                    continue

                                # Store the URL (don't save image at this stage)
                                status(f"  ✓ Selected best image: {best_url[:80]}...")

                                # Create fallback parsed_data structure
                                parsed_data = {
                                    'title': product.get('description_1', ''),
                                    'description': product.get('upcitemdb_description', ''),
                                    'vendor': 'Purina',
                                    'gallery_images': [best_url],  # Store URL instead of filename
                                    'site_source': 'upcitemdb',
                                    'variants': [],  # Will be generated from input data
                                    'features_benefits': None,
                                    'nutrients': None,
                                    'feeding_directions': None,
                                    'documents': []
                                }

                                status(f"  ✓ Created fallback product data from UPCItemDB")

                                # Continue to Shopify output generation (skip steps 2-4)
                                status(f"  🏗️  Generating Shopify product structure...")

                                # Import the output generator
                                sys.path.insert(0, os.path.dirname(__file__))
                                from src.utils.shopify_output import generate_shopify_product

                                shopify_product = generate_shopify_product(
                                    parsed_data=parsed_data,
                                    input_data=product,
                                    variant_data=variants,
                                    log=status
                                )

                                status(f"  ✓ Generated product with {len(shopify_product.get('product', {}).get('variants', []))} variant(s)")

                                enriched.append(shopify_product)
                                success_count += 1
                                status(f"  ✅ Successfully processed with UPCItemDB fallback")

                                # Rate limiting
                                sleep(uniform(0.2, 0.7))
                                status("")
                                continue

                            else:
                                # No fallback available (upcitemdb_status is blank or invalid)
                                error_msg = "No manufacturer match and no UPCItemDB data"
                                status(f"  ⚠ Unmatched: No manufacturer match and no UPCItemDB data")
                                # This is an unmatched product - add to both lists
                                unmatched_record = {
                                    **product,
                                    'error_reason': error_msg
                                }
                                unmatched_products.append(unmatched_record)
                                failed_records.append(unmatched_record)
                                unmatched_count += 1
                                fail_count += 1
                                status("")
                                continue

                        status(f"  ✓ Found: {product_url}")

                        # Step 2: Fetch product page
                        status(f"  📥 Fetching product page...")
                        response = requests.get(product_url, timeout=30)
                        response.raise_for_status()
                        status(f"  ✓ Page fetched ({len(response.text)} bytes)")

                        # Step 3: Parse product data
                        status(f"  📋 Parsing product data...")
                        parsed_data = collector.parse_page(response.text)
                        status(f"  ✓ Parsed from {parsed_data.get('site_source', 'unknown')} site")

                        if parsed_data.get('variants'):
                            status(f"    - Found {len(parsed_data['variants'])} variant(s)")
                        if parsed_data.get('gallery_images'):
                            status(f"    - Found {len(parsed_data['gallery_images'])} image(s)")
                        if parsed_data.get('features_benefits'):
                            status(f"    - Extracted Features & Benefits")
                        if parsed_data.get('nutrients'):
                            status(f"    - Extracted Nutrients")
                        if parsed_data.get('feeding_directions'):
                            status(f"    - Extracted Feeding Directions")

                        # Step 4: If from shop site, also fetch www site for documents
                        www_data = None
                        if parsed_data.get('site_source') == 'shop':
                            status(f"  🌐 Fetching additional materials from www site...")
                            # Try to construct www URL
                            www_url = product_url.replace('shop.purinamills.com/products/', 'www.purinamills.com/horse-feed/products/detail/')
                            try:
                                www_response = requests.get(www_url, timeout=30)
                                if www_response.status_code == 200:
                                    www_data = collector.parse_page(www_response.text)
                                    if www_data.get('documents'):
                                        status(f"  ✓ Found {len(www_data['documents'])} document(s)")
                                        parsed_data['documents'] = www_data['documents']
                                else:
                                    status(f"  ⚠ WWW site returned {www_response.status_code}")
                            except Exception as e:
                                status(f"  ⚠ Could not fetch www site: {str(e)}")

                        # Step 5: Generate Shopify output structure
                        status(f"  🏗️  Generating Shopify product structure...")

                        # Import the output generator
                        sys.path.insert(0, os.path.dirname(__file__))
                        from src.utils.shopify_output import generate_shopify_product

                        shopify_product = generate_shopify_product(
                            parsed_data=parsed_data,
                            input_data=product,
                            variant_data=variants,  # Pass variant products from input file
                            log=status
                        )

                        status(f"  ✓ Generated product with {len(shopify_product.get('product', {}).get('variants', []))} variant(s)")

                        enriched.append(shopify_product)
                        success_count += 1
                        status(f"  ✅ Successfully processed")

                        # Rate limiting
                        sleep(uniform(0.2, 0.7))

                    except Exception as e:
                        fail_count += 1
                        error_msg = str(e)
                        status(f"  ❌ Error: {error_msg}")
                        logging.exception(f"Error processing product {upc}:")
                        # Don't add to enriched - only add to failed_records
                        failed_records.append({
                            **product,
                            'error_reason': error_msg
                        })

                    status("")

                # Save output
                status(f"Saving results to {output_file}...")
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                # Wrap products in "products" array for GraphQL 2025-10 compliance
                # Each item in enriched is {"product": {...}}, but upscaler expects [{...}, ...]
                # So we unwrap the "product" key from each item
                output_data = {
                    "products": [item["product"] for item in enriched]
                }

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

                status(f"  ✓ Saved {len(enriched)} product(s)")

                # Save unmatched products to separate file
                if unmatched_products:
                    from pathlib import Path
                    output_path = Path(output_file)
                    unmatched_file = output_path.parent / f"{output_path.stem}_unmatched.json"

                    status(f"Saving unmatched products to {unmatched_file}...")
                    unmatched_data = {
                        "unmatched_products": unmatched_products
                    }

                    with open(unmatched_file, 'w', encoding='utf-8') as f:
                        json.dump(unmatched_data, f, indent=2, ensure_ascii=False)

                    status(f"  ✓ Saved {len(unmatched_products)} unmatched product(s)")
                    status(f"  These products could not be found on manufacturer site and have no UPCItemDB data.")

                # Save error log if there are failed records
                if failed_records:
                    error_log_file = output_file.replace('.json', '_errors.xlsx')
                    status(f"Saving error log to {error_log_file}...")

                    try:
                        import openpyxl
                        wb = openpyxl.Workbook()
                        ws = wb.active
                        ws.title = "Failed Records"

                        # Write headers (all fields from first record)
                        if failed_records:
                            headers = list(failed_records[0].keys())
                            ws.append(headers)

                            # Write data rows
                            for record in failed_records:
                                row = [record.get(header, '') for header in headers]
                                ws.append(row)

                        wb.save(error_log_file)
                        status(f"  ✓ Error log saved: {len(failed_records)} failed record(s)")
                    except Exception as e:
                        status(f"  ⚠ Could not save error log: {str(e)}")

                status("")
                status("=" * 80)
                status("PROCESSING COMPLETE")
                status("=" * 80)
                status(f"✅ Successful: {success_count}")
                status(f"⚠ Skipped: {skip_count}")
                status(f"🔍 Unmatched: {unmatched_count}")
                status(f"❌ Failed: {fail_count}")
                status(f"Total: {len(product_groups)} product(s) from {len(products)} record(s)")

                # Print failed records summary
                if failed_records:
                    status("")
                    status("=" * 80)
                    status("FAILED RECORDS SUMMARY")
                    status("=" * 80)
                    for record in failed_records:
                        item_num = record.get('item_#', 'N/A')
                        desc = record.get('description_1', 'N/A')
                        error = record.get('error_reason', 'Unknown error')
                        status(f"  Item #{item_num}: {desc}")
                        status(f"    Error: {error}")
                        status("")
                    status(f"Error log saved to: {error_log_file}")

                status("=" * 80)

                # Queue messagebox to main thread
                messagebox_queue.put(("info", "Success", f"Processing complete!\n\n✅ Successful: {success_count}\n⚠ Skipped: {skip_count}\n🔍 Unmatched: {unmatched_count}\n❌ Failed: {fail_count}\n\nProcessed {len(product_groups)} product(s) from {len(products)} record(s)"))

            except Exception as e:
                status(f"\n❌ FATAL ERROR: {str(e)}")
                logging.exception("Fatal error:")
                # Queue error messagebox to main thread
                messagebox_queue.put(("error", "Error", f"Fatal error occurred:\n\n{str(e)}"))
            finally:
                # ALWAYS re-enable buttons
                button_control_queue.put("enable_buttons")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    start_btn = tb.Button(
        button_frame,
        text="Start Processing",
        command=start_processing,
        bootstyle="success"
    )
    start_btn.pack(side="left", padx=5)

    exit_btn = tb.Button(
        button_frame,
        text="Exit",
        command=app.quit,
        bootstyle="secondary"
    )
    exit_btn.pack(side="left", padx=5)

    # ========== Status Log ==========
    status_label = tb.Label(app, text="Status Log:", anchor="w")
    status_label.pack(anchor="w", padx=10, pady=(10, 0))

    status_log = tb.Text(app, height=100, state="normal")
    status_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ========== Queue Processor ==========
    def process_queues():
        """Process all pending messages from queues (runs in main thread)."""
        try:
            # Process status messages
            messages = []
            while True:
                try:
                    msg = status_queue.get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break

            if messages:
                status_log.config(state="normal")
                for msg in messages:
                    status_log.insert("end", msg + "\n")
                status_log.see("end")
                status_log.config(state="disabled")
                status_log.update_idletasks()

            # Process button control signals
            while True:
                try:
                    signal = button_control_queue.get_nowait()
                    if signal == "enable_buttons":
                        start_btn.config(state="normal")
                except queue.Empty:
                    break

            # Process messagebox requests (MUST run in main thread)
            while True:
                try:
                    msg_type, title, message = messagebox_queue.get_nowait()
                    if msg_type == "info":
                        messagebox.showinfo(title, message)
                    elif msg_type == "error":
                        messagebox.showerror(title, message)
                    elif msg_type == "warning":
                        messagebox.showwarning(title, message)
                except queue.Empty:
                    break

        except Exception as e:
            logging.error(f"Error processing queues: {e}", exc_info=True)

        # Schedule next check (50ms = 20 times per second)
        app.after(50, process_queues)

    # Start queue processor
    app.after(50, process_queues)

    # Initial welcome messages
    status("=" * 80)
    status(f"{cfg['COLLECTOR_NAME']} Product Collector v1.0.0")
    status("GUI loaded successfully")
    status("=" * 80)
    status("")

    # ========== Window Close Handler ==========
    def on_closing():
        """Handle window close event."""
        try:
            cfg["WINDOW_GEOMETRY"] = app.geometry()
            save_config(cfg)
        except Exception as e:
            logging.warning(f"Failed to save window geometry: {e}")
        app.quit()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Start main loop
    app.mainloop()


if __name__ == "__main__":
    build_gui()

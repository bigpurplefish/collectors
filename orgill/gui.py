#!/usr/bin/env python3
"""
Orgill Product Collector - GUI

Thread-safe GUI for running the Orgill collector with queue-based communication.
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
from ttkbootstrap.tooltip import ToolTip
import threading
import queue
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.collector import OrgillCollector, SITE_CONFIG

# Configuration file path
APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "_COMMENT_USER_SETTINGS": "User-configurable settings",
    "INPUT_FILE": "",
    "OUTPUT_FILE": "",
    "LOG_FILE": "logs/orgill.log",
    "WINDOW_GEOMETRY": "900x900",
    "PROCESSING_MODE": "skip",  # "skip" or "overwrite"
    "START_RECORD": "",
    "END_RECORD": "",

    "_COMMENT_SYSTEM_INFO": "System information (do not edit)",
    "COLLECTOR_NAME": "Orgill",
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

    log_var = tb.StringVar(value=cfg.get("LOG_FILE", "logs/orgill.log"))
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

    start_var = tb.StringVar(value=cfg.get("START_RECORD", ""))
    tb.Entry(container, textvariable=start_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    # Auto-save
    def on_start_change(*args):
        try:
            cfg["START_RECORD"] = start_var.get()
            save_config(cfg)
        except Exception:
            pass

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

    end_var = tb.StringVar(value=cfg.get("END_RECORD", ""))
    tb.Entry(container, textvariable=end_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    # Auto-save
    def on_end_change(*args):
        try:
            cfg["END_RECORD"] = end_var.get()
            save_config(cfg)
        except Exception:
            pass

    end_var.trace_add("write", on_end_change)
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
        """Thread-safe status update."""
        try:
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
                start_record_str = start_var.get().strip()
                end_record_str = end_var.get().strip()

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

                # Parse start/end record
                start_idx = 0
                end_idx = None
                if start_record_str:
                    try:
                        start_idx = int(start_record_str) - 1  # Convert to 0-based
                        if start_idx < 0:
                            start_idx = 0
                        status(f"Start Record: {start_idx + 1}")
                    except ValueError:
                        status(f"⚠ Invalid start record '{start_record_str}', using 1")

                if end_record_str:
                    try:
                        end_idx = int(end_record_str)  # Keep as 1-based for slicing
                        status(f"End Record: {end_idx}")
                    except ValueError:
                        status(f"⚠ Invalid end record '{end_record_str}', processing to end")
                        end_idx = None

                status("")

                # Load input (supports JSON and Excel)
                status("Loading input file...")

                # Add shared utilities to path
                import sys
                shared_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared')
                if shared_path not in sys.path:
                    sys.path.insert(0, shared_path)

                from src.excel_utils import load_products
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
                collector = OrgillCollector()
                status("✅ Collector initialized")
                status("")

                # Process products
                enriched = []
                success_count = 0
                skip_count = 0
                fail_count = 0

                for i, product in enumerate(products):
                    upc = product.get('upc_updated') or product.get('upc', '')
                    item_num = product.get('item_#', '')
                    name = product.get('description_1', '')

                    # Calculate actual record number in original file
                    actual_record_num = start_idx + i + 1

                    status(f"[{i+1}/{len(products)}] Record #{actual_record_num}: {name}")

                    # Check if already processed (skip mode)
                    if processing_mode == "skip":
                        lookup_key = upc if upc else f"item_{item_num}"
                        existing = existing_products.get(lookup_key)
                        if existing and existing.get('manufacturer'):
                            status(f"  ⏭ Skipping (already processed)")
                            enriched.append(existing)
                            skip_count += 1
                            status("")
                            continue

                    try:
                        # TODO: Implement actual collection logic here
                        # enriched_product = collector.enrich(product)
                        enriched.append(product)
                        success_count += 1
                        status(f"  ✅ Processed successfully")
                    except Exception as e:
                        fail_count += 1
                        status(f"  ❌ Error: {str(e)}")
                        logging.exception(f"Error processing product {upc}:")
                        enriched.append(product)  # Keep original on error

                    status("")

                # Save output
                status(f"Saving results to {output_file}...")
                output_dir = os.path.dirname(output_file)
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(enriched, f, indent=2, ensure_ascii=False)

                status("")
                status("=" * 80)
                status("PROCESSING COMPLETE")
                status("=" * 80)
                status(f"✅ Successful: {success_count}")
                status(f"⚠ Skipped: {skip_count}")
                status(f"❌ Failed: {fail_count}")
                status(f"Total: {len(products)}")
                status("=" * 80)

                messagebox.showinfo("Success", f"Processing complete!\n\n✅ Successful: {success_count}\n❌ Failed: {fail_count}")

            except Exception as e:
                status(f"\n❌ FATAL ERROR: {str(e)}")
                logging.exception("Fatal error:")
                messagebox.showerror("Error", f"Fatal error occurred:\n\n{str(e)}")
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

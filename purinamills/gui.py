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
from ttkbootstrap.tooltip import ToolTip
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
        text="Select the JSON file containing your product data.\n\nThis file should include product information with UPCs and names.\n\nTip: Use the Browse button to easily find your file.",
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
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
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
                status("")

                # Load input
                status("Loading input file...")
                with open(input_file, 'r', encoding='utf-8') as f:
                    products = json.load(f)

                if not isinstance(products, list):
                    raise ValueError("Input must be a JSON array of products")

                status(f"Loaded {len(products)} products")
                status("")

                # Initialize collector
                status("Initializing collector...")
                collector = PurinamillsCollector()
                status("✅ Collector initialized")
                status("")

                # Process products
                enriched = []
                success_count = 0
                skip_count = 0
                fail_count = 0

                for i, product in enumerate(products):
                    upc = product.get('upc_updated') or product.get('upc', '')
                    name = product.get('description_1', '')

                    status(f"[{i+1}/{len(products)}] Processing: {name} (UPC: {upc})")

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

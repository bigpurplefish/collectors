#!/usr/bin/env python3
"""
Cambridge Product Collector - GUI

Thread-safe GUI for running the Cambridge collector with queue-based communication.
Follows GUI_DESIGN_REQUIREMENTS.md patterns.
"""

import os
import sys
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToolTip
import threading
import queue

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config, save_config, INDEX_CACHE_FILE, PORTAL_INDEX_CACHE_FILE
from src.processor import process_products
from src.index_builder import load_index_from_cache, is_index_stale
from src.settings_dialog import open_settings_dialog


def build_gui():
    """Build and launch the GUI."""
    # Load configuration
    cfg = load_config()

    # Create main window
    app = tb.Window(themename="darkly")
    app.title("Cambridge Product Collector")
    app.geometry(cfg.get("window_geometry", "900x1000"))

    # Queues for thread-safe communication
    status_queue = queue.Queue()
    button_control_queue = queue.Queue()

    # Menu Bar
    menu_bar = tb.Menu(app)
    app.config(menu=menu_bar)

    settings_menu = tb.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Settings", menu=settings_menu)
    settings_menu.add_command(
        label="Portal Credentials",
        command=lambda: open_settings_dialog(cfg, app)
    )

    # Toolbar
    toolbar = tb.Frame(app)
    toolbar.pack(side="top", fill="x", padx=5, pady=5)

    settings_btn = tb.Button(
        toolbar,
        text="⚙️ Settings",
        command=lambda: open_settings_dialog(cfg, app),
        bootstyle="secondary-outline"
    )
    settings_btn.pack(side="left", padx=5)

    # Main container
    container = tb.Frame(app, padding=20)
    container.pack(fill="both", expand=True)
    container.columnconfigure(1, weight=1)  # Make input fields expandable

    # Title
    title = tb.Label(
        container,
        text="Cambridge Product Collector",
        font=("Arial", 16, "bold")
    )
    title.grid(row=0, column=0, columnspan=3, pady=(0, 10))

    # Site info
    site_label = tb.Label(
        container,
        text="Public Site: https://www.cambridgepavers.com | Portal: https://shop.cambridgepavers.com",
        font=("Arial", 9)
    )
    site_label.grid(row=1, column=0, columnspan=3, pady=(0, 20))

    # Row counter
    current_row = 2

    # ========== File Paths Section ==========
    section_label = tb.Label(
        container,
        text="File Paths",
        font=("Arial", 12, "bold"),
        foreground="#5BC0DE"
    )
    section_label.grid(row=current_row, column=0, columnspan=3, sticky="w", pady=(20, 5))
    current_row += 1

    # Input File
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
        text="Select the Excel file containing Cambridge product data.\n\nExpected columns: vendor_type, title, color_category, color, item_#, price\n\nTip: Use the Browse button to easily find your file.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    input_var = tb.StringVar(value=cfg.get("input_file", ""))
    tb.Entry(container, textvariable=input_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5
    )

    def browse_input():
        try:
            filename = filedialog.askopenfilename(
                title="Select Input File",
                filetypes=[
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

    def on_input_change(*args):
        try:
            cfg["input_file"] = input_var.get()
            save_config(cfg)
        except Exception:
            pass

    input_var.trace_add("write", on_input_change)
    current_row += 1

    # Output File
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
        text="Select where to save the Shopify product data (JSON).\n\nThe output will be in Shopify GraphQL 2025-10 format.\n\nTip: Choose a different name than your input file.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    output_var = tb.StringVar(value=cfg.get("output_file", ""))
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

    def on_output_change(*args):
        try:
            cfg["output_file"] = output_var.get()
            save_config(cfg)
        except Exception:
            pass

    output_var.trace_add("write", on_output_change)
    current_row += 1

    # Log File
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

    log_var = tb.StringVar(value=cfg.get("log_file", ""))
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

    def on_log_change(*args):
        try:
            cfg["log_file"] = log_var.get()
            save_config(cfg)
        except Exception:
            pass

    log_var.trace_add("write", on_log_change)
    current_row += 1

    # ========== Processing Options Section ==========
    section_label = tb.Label(
        container,
        text="Processing Options",
        font=("Arial", 12, "bold"),
        foreground="#5BC0DE"
    )
    section_label.grid(row=current_row, column=0, columnspan=3, sticky="w", pady=(20, 5))
    current_row += 1

    # Processing Mode
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
        text="Choose how to handle products that have already been processed.\n\nSkip: Skip products that already have processed data.\nOverwrite: Re-process all products, overwriting existing data.\n\nTip: Use 'Skip' to resume interrupted processing.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    mode_frame = tb.Frame(container)
    mode_frame.grid(row=current_row, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    mode_var = tb.StringVar(value=cfg.get("processing_mode", "skip"))

    skip_radio = tb.Radiobutton(
        mode_frame,
        text="Skip Processed Products",
        variable=mode_var,
        value="skip",
        bootstyle="primary"
    )
    skip_radio.pack(side="left", padx=(0, 20))

    overwrite_radio = tb.Radiobutton(
        mode_frame,
        text="Overwrite All Products",
        variable=mode_var,
        value="overwrite",
        bootstyle="warning"
    )
    overwrite_radio.pack(side="left")

    def on_mode_change(*args):
        try:
            cfg["processing_mode"] = mode_var.get()
            save_config(cfg)
        except Exception:
            pass

    mode_var.trace_add("write", on_mode_change)
    current_row += 1

    # Start Record
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
        text="Specify the first record to process (1-based index).\n\nLeave blank to start from the beginning.\nExample: Enter '10' to start from the 10th record.\n\nTip: Blank = process from start.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    start_var = tb.StringVar(value=cfg.get("start_record", ""))
    tb.Spinbox(
        container,
        textvariable=start_var,
        from_=0,
        to=999999,
        increment=1,
        width=10
    ).grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    def on_start_change(*args):
        try:
            val = start_var.get().strip()
            if val:
                int(val)
            cfg["start_record"] = val
            save_config(cfg)
        except (ValueError, tk.TclError, Exception):
            cfg["start_record"] = ""
            save_config(cfg)

    start_var.trace_add("write", on_start_change)
    current_row += 1

    # End Record
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
        text="Specify the last record to process (1-based index).\n\nLeave blank to process until the end.\nExample: Enter '50' to stop processing after the 50th record.\n\nTip: Blank = process to end.",
        bootstyle="info"
    )
    tb.Label(label_frame, text=":", anchor="w").pack(side="left")

    end_var = tb.StringVar(value=cfg.get("end_record", ""))
    tb.Spinbox(
        container,
        textvariable=end_var,
        from_=0,
        to=999999,
        increment=1,
        width=10
    ).grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    def on_end_change(*args):
        try:
            val = end_var.get().strip()
            if val:
                int(val)
            cfg["end_record"] = val
            save_config(cfg)
        except (ValueError, tk.TclError, Exception):
            cfg["end_record"] = ""
            save_config(cfg)

    end_var.trace_add("write", on_end_change)
    current_row += 1

    # ========== Product Indexes Section ==========
    section_label = tb.Label(
        container,
        text="Product Indexes",
        font=("Arial", 12, "bold"),
        foreground="#5BC0DE"
    )
    section_label.grid(row=current_row, column=0, columnspan=3, sticky="w", pady=(20, 5))
    current_row += 1

    # Public Site Index Status Label
    public_index_status_label = tb.Label(
        container,
        text="Checking public site index status...",
        font=("Arial", 10),
        foreground="#888"
    )
    public_index_status_label.grid(row=current_row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
    current_row += 1

    # Portal Index Status Label
    portal_index_status_label = tb.Label(
        container,
        text="Checking portal index status...",
        font=("Arial", 10),
        foreground="#888"
    )
    portal_index_status_label.grid(row=current_row, column=0, columnspan=3, sticky="w", padx=5, pady=2)
    current_row += 1

    def update_index_status():
        """Update both index status labels."""
        max_age_days = cfg.get("index_max_age_days", 7)

        # Public Site Index
        try:
            cached_index = load_index_from_cache(INDEX_CACHE_FILE, lambda x: None)
            if cached_index:
                last_updated = cached_index.get("last_updated", "Unknown")
                total_products = cached_index.get("total_products", 0)
                is_stale = is_index_stale(cached_index, max_age_days)

                if is_stale:
                    public_index_status_label.config(
                        text=f"⚠ Public Site Index: STALE ({total_products} products, last updated: {last_updated})",
                        foreground="#FFA500"
                    )
                else:
                    public_index_status_label.config(
                        text=f"✓ Public Site Index: Fresh ({total_products} products, last updated: {last_updated})",
                        foreground="#5BC0DE"
                    )
            else:
                public_index_status_label.config(
                    text="Public Site Index: Not cached - will build on first run",
                    foreground="#888"
                )
        except Exception:
            public_index_status_label.config(
                text="Public Site Index: Unable to check status",
                foreground="#888"
            )

        # Portal Index
        try:
            cached_portal_index = load_index_from_cache(PORTAL_INDEX_CACHE_FILE, lambda x: None)
            if cached_portal_index:
                last_updated = cached_portal_index.get("last_updated", "Unknown")
                total_products = cached_portal_index.get("total_products", 0)
                is_stale = is_index_stale(cached_portal_index, max_age_days)

                if is_stale:
                    portal_index_status_label.config(
                        text=f"⚠ Portal Index: STALE ({total_products} products, last updated: {last_updated})",
                        foreground="#FFA500"
                    )
                else:
                    portal_index_status_label.config(
                        text=f"✓ Portal Index: Fresh ({total_products} products, last updated: {last_updated})",
                        foreground="#5BC0DE"
                    )
            else:
                portal_index_status_label.config(
                    text="Portal Index: Not cached - will build on first run",
                    foreground="#888"
                )
        except Exception:
            portal_index_status_label.config(
                text="Portal Index: Unable to check status",
                foreground="#888"
            )

    update_index_status()

    # Rebuild Index Checkbox
    rebuild_index_var = tb.BooleanVar(value=cfg.get("rebuild_index", False))

    rebuild_checkbox = tb.Checkbutton(
        container,
        text="Force Rebuild Both Product Indexes",
        variable=rebuild_index_var,
        bootstyle="primary-round-toggle"
    )
    rebuild_checkbox.grid(row=current_row, column=0, columnspan=3, sticky="w", padx=5, pady=5)

    def on_rebuild_change(*args):
        try:
            cfg["rebuild_index"] = rebuild_index_var.get()
            save_config(cfg)
        except Exception:
            pass

    rebuild_index_var.trace_add("write", on_rebuild_change)
    current_row += 1

    # Skip Accessories Category Checkbox
    skip_accessories_var = tb.BooleanVar(value=cfg.get("skip_accessories_category", True))

    skip_accessories_checkbox = tb.Checkbutton(
        container,
        text="Skip /accessories Category When Building Portal Index",
        variable=skip_accessories_var,
        bootstyle="primary-round-toggle"
    )
    skip_accessories_checkbox.grid(row=current_row, column=0, columnspan=3, sticky="w", padx=5, pady=5)

    def on_skip_accessories_change(*args):
        try:
            cfg["skip_accessories_category"] = skip_accessories_var.get()
            save_config(cfg)
        except Exception:
            pass

    skip_accessories_var.trace_add("write", on_skip_accessories_change)
    current_row += 1

    # Tooltip for skip accessories
    ToolTip(
        skip_accessories_checkbox,
        text="When enabled, /accessories category will be excluded from the portal product index.\n"
             "This reduces index size and build time. Disable if you need accessories products.",
        bootstyle="info"
    )

    # ========== Action Buttons ==========
    button_frame = tb.Frame(app)
    button_frame.pack(pady=10)

    # Thread-safe status function
    def status(msg):
        """Update status log. Thread-safe - can be called from any thread."""
        try:
            status_queue.put(msg)
        except Exception as e:
            logging.error(f"Failed to queue status message: {e}")

    # Validation function
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

            if not cfg.get("portal_username", "").strip():
                messagebox.showerror(
                    "Validation Error",
                    "Portal Username is required.\n\nPlease configure credentials in Settings (⚙️ button or Settings menu)."
                )
                return False

            if not cfg.get("portal_password", "").strip():
                messagebox.showerror(
                    "Validation Error",
                    "Portal Password is required.\n\nPlease configure credentials in Settings (⚙️ button or Settings menu)."
                )
                return False

            return True

        except Exception as e:
            messagebox.showerror("Validation Error", f"Unexpected error during validation:\n\n{str(e)}")
            return False

    # Start Processing button
    def start_processing():
        """Start processing in background thread."""
        if not validate_inputs():
            return

        # Clear status log
        status_log.config(state="normal")
        status_log.delete("1.0", "end")
        status_log.config(state="disabled")

        # Disable buttons
        start_btn.config(state="disabled")
        validate_btn.config(state="disabled")

        def worker():
            """Background worker thread."""
            try:
                # Setup logging
                log_file = log_var.get().strip()
                if log_file:
                    os.makedirs(os.path.dirname(log_file), exist_ok=True)
                    logging.basicConfig(
                        filename=log_file,
                        level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s"
                    )

                # Run processing
                process_products(cfg, status)

            except Exception as e:
                status(f"❌ Fatal error: {e}")
                logging.exception("Worker error:")
            finally:
                # Re-enable buttons
                button_control_queue.put("enable_buttons")
                # Update index status
                app.after(0, update_index_status)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    start_btn = tb.Button(
        button_frame,
        text="Start Processing",
        command=start_processing,
        bootstyle="success",
        width=20
    )
    start_btn.pack(side="left", padx=5)

    # Validate button
    validate_btn = tb.Button(
        button_frame,
        text="Validate Settings",
        command=validate_inputs,
        bootstyle="info",
        width=20
    )
    validate_btn.pack(side="left", padx=5)

    # Exit button
    def exit_app():
        """Exit the application."""
        app.quit()

    tb.Button(
        button_frame,
        text="Exit",
        command=exit_app,
        bootstyle="secondary",
        width=20
    ).pack(side="left", padx=5)

    # ========== Status Log ==========
    status_label = tb.Label(app, text="Status Log:", anchor="w")
    status_label.pack(anchor="w", padx=10, pady=(10, 0))

    status_log = tb.Text(app, height=15, state="normal")
    status_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Queue processor
    def process_queues():
        """Process all pending messages from queues. Runs in main thread."""
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
                        validate_btn.config(state="normal")
                except queue.Empty:
                    break

        except Exception as e:
            logging.error(f"Error processing queues: {e}", exc_info=True)

        # Schedule next check
        app.after(50, process_queues)

    # Start queue processor
    app.after(50, process_queues)

    # Initial status messages
    status("=" * 80)
    status("Cambridge Product Collector v1.0.0")
    status("GUI loaded successfully")
    status("=" * 80)
    status("")

    # Window close handler
    def on_closing():
        """Handle window close event."""
        try:
            cfg["window_geometry"] = app.geometry()
            save_config(cfg)
        except Exception as e:
            logging.warning(f"Failed to save window geometry: {e}")
        app.quit()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Start main loop
    app.mainloop()


if __name__ == "__main__":
    build_gui()

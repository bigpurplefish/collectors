#!/usr/bin/env python3
"""
Aggregates Excel-to-Categorizer Converter - GUI

Thread-safe GUI with queue-based communication.
Follows GUI_DESIGN_REQUIREMENTS.md patterns.
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToolTip
import threading
import queue

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.config import load_config, save_config
from src.processor import process_products
from src.settings_dialog import open_settings_dialog


def build_gui():
    """Build and launch the GUI."""
    cfg = load_config()

    app = tb.Window(themename="darkly")
    app.title("Aggregates Excel-to-Categorizer Converter")
    app.geometry(cfg.get("window_geometry", "900x800"))

    # Queues for thread-safe communication
    status_queue = queue.Queue()
    button_control_queue = queue.Queue()

    # Main container
    container = tb.Frame(app, padding=20)
    container.pack(fill="both", expand=True)
    container.columnconfigure(1, weight=1)

    # Title
    title = tb.Label(
        container,
        text="Aggregates Excel-to-Categorizer Converter",
        font=("Arial", 16, "bold"),
    )
    title.grid(row=0, column=0, columnspan=3, pady=(0, 5))

    subtitle = tb.Label(
        container,
        text="Converts Excel product data into categorizer-compatible JSON",
        font=("Arial", 9),
    )
    subtitle.grid(row=1, column=0, columnspan=3, pady=(0, 20))

    current_row = 2

    # Helper to create labeled field with tooltip
    def make_label(row, text, tooltip_text):
        frame = tb.Frame(container)
        frame.grid(row=row, column=0, sticky="w", padx=5, pady=5)
        tb.Label(frame, text=text, anchor="w").pack(side="left")
        icon = tb.Label(
            frame, text=" \u24d8 ", font=("Arial", 9),
            foreground="#5BC0DE", cursor="hand2",
        )
        icon.pack(side="left")
        ToolTip(icon, text=tooltip_text, bootstyle="info")
        tb.Label(frame, text=":", anchor="w").pack(side="left")

    # ========== File Paths Section ==========
    section = tb.Label(
        container, text="File Paths",
        font=("Arial", 12, "bold"), foreground="#5BC0DE",
    )
    section.grid(row=current_row, column=0, columnspan=3, sticky="w", pady=(20, 5))
    current_row += 1

    # Input File
    make_label(current_row, "Input File",
               "Select the Excel file containing aggregates product data.\n\n"
               "Expected columns: sku, parent_sku, vendor, title, price, cost,\n"
               "color, size, unit_of_sale, approximate_product_coverage, image_file_name")

    input_var = tb.StringVar(value=cfg.get("input_file", ""))
    tb.Entry(container, textvariable=input_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5)

    def browse_input():
        filename = filedialog.askopenfilename(
            title="Select Input File",
            filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if filename:
            input_var.set(filename)

    tb.Button(container, text="Browse", command=browse_input,
              bootstyle="info-outline").grid(row=current_row, column=2, padx=5, pady=5)

    def on_input_change(*args):
        try:
            cfg["input_file"] = input_var.get()
            save_config(cfg)
        except Exception:
            pass

    input_var.trace_add("write", on_input_change)
    current_row += 1

    # Output File
    make_label(current_row, "Output File",
               "Select where to save the categorizer-compatible JSON output.\n\n"
               "The output will contain products grouped by parent_sku\n"
               "with variants, options, images, and descriptions.")

    output_var = tb.StringVar(value=cfg.get("output_file", ""))
    tb.Entry(container, textvariable=output_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5)

    def browse_output():
        filename = filedialog.asksaveasfilename(
            title="Select Output File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            defaultextension=".json",
        )
        if filename:
            output_var.set(filename)

    tb.Button(container, text="Browse", command=browse_output,
              bootstyle="info-outline").grid(row=current_row, column=2, padx=5, pady=5)

    def on_output_change(*args):
        try:
            cfg["output_file"] = output_var.get()
            save_config(cfg)
        except Exception:
            pass

    output_var.trace_add("write", on_output_change)
    current_row += 1

    # Log File
    make_label(current_row, "Log File",
               "Select where to save the processing log.\n\n"
               "Contains detailed information about each product processed.\n"
               "Useful for debugging and tracking progress.")

    log_var = tb.StringVar(value=cfg.get("log_file", ""))
    tb.Entry(container, textvariable=log_var, width=50).grid(
        row=current_row, column=1, sticky="ew", padx=5, pady=5)

    def browse_log():
        filename = filedialog.asksaveasfilename(
            title="Select Log File",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".log",
        )
        if filename:
            log_var.set(filename)

    tb.Button(container, text="Browse", command=browse_log,
              bootstyle="info-outline").grid(row=current_row, column=2, padx=5, pady=5)

    def on_log_change(*args):
        try:
            cfg["log_file"] = log_var.get()
            save_config(cfg)
        except Exception:
            pass

    log_var.trace_add("write", on_log_change)
    current_row += 1

    # ========== Processing Options Section ==========
    section = tb.Label(
        container, text="Processing Options",
        font=("Arial", 12, "bold"), foreground="#5BC0DE",
    )
    section.grid(row=current_row, column=0, columnspan=3, sticky="w", pady=(20, 5))
    current_row += 1

    # Processing Mode
    make_label(current_row, "Processing Mode",
               "Choose how to handle existing output files.\n\n"
               "Skip: Do not overwrite if output file already exists.\n"
               "Overwrite: Regenerate output even if file exists.\n\n"
               "Tip: Use 'Overwrite' to regenerate after editing the Excel file.")

    mode_frame = tb.Frame(container)
    mode_frame.grid(row=current_row, column=1, columnspan=2, sticky="w", padx=5, pady=5)

    mode_var = tb.StringVar(value=cfg.get("processing_mode", "skip"))

    tb.Radiobutton(
        mode_frame, text="Skip Existing", variable=mode_var,
        value="skip", bootstyle="primary",
    ).pack(side="left", padx=(0, 20))

    tb.Radiobutton(
        mode_frame, text="Overwrite", variable=mode_var,
        value="overwrite", bootstyle="warning",
    ).pack(side="left")

    def on_mode_change(*args):
        try:
            cfg["processing_mode"] = mode_var.get()
            save_config(cfg)
        except Exception:
            pass

    mode_var.trace_add("write", on_mode_change)
    current_row += 1

    # Start Record
    make_label(current_row, "Start Record",
               "Specify the first product to process (1-based index).\n\n"
               "Products are numbered after grouping by parent_sku.\n"
               "Leave blank to start from the first product.")

    start_var = tb.StringVar(value=cfg.get("start_record", ""))
    tb.Spinbox(
        container, textvariable=start_var,
        from_=0, to=999999, increment=1, width=10,
    ).grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    def on_start_change(*args):
        try:
            val = start_var.get().strip()
            if val:
                int(val)
            cfg["start_record"] = val
            save_config(cfg)
        except (ValueError, tk.TclError):
            cfg["start_record"] = ""
            save_config(cfg)

    start_var.trace_add("write", on_start_change)
    current_row += 1

    # End Record
    make_label(current_row, "End Record",
               "Specify the last product to process (1-based index).\n\n"
               "Products are numbered after grouping by parent_sku.\n"
               "Leave blank to process all remaining products.")

    end_var = tb.StringVar(value=cfg.get("end_record", ""))
    tb.Spinbox(
        container, textvariable=end_var,
        from_=0, to=999999, increment=1, width=10,
    ).grid(row=current_row, column=1, sticky="w", padx=5, pady=5)

    def on_end_change(*args):
        try:
            val = end_var.get().strip()
            if val:
                int(val)
            cfg["end_record"] = val
            save_config(cfg)
        except (ValueError, tk.TclError):
            cfg["end_record"] = ""
            save_config(cfg)

    end_var.trace_add("write", on_end_change)
    current_row += 1

    # ========== Action Buttons ==========
    button_frame = tb.Frame(app)
    button_frame.pack(pady=10)

    def status(msg):
        """Thread-safe status update."""
        try:
            status_queue.put(msg)
        except Exception:
            pass

    def validate_inputs():
        """Validate all required inputs including S3 configuration."""
        if not input_var.get().strip():
            messagebox.showerror("Validation Error", "Input File is required.")
            return False
        if not os.path.exists(input_var.get()):
            messagebox.showerror("Validation Error", "Input File does not exist.")
            return False
        if not output_var.get().strip():
            messagebox.showerror("Validation Error", "Output File is required.")
            return False
        if not cfg.get("AWS_ACCESS_KEY_ID") or not cfg.get("AWS_SECRET_ACCESS_KEY"):
            messagebox.showerror(
                "Validation Error",
                "AWS credentials not configured.\n\nClick Settings to configure.",
            )
            return False
        if not cfg.get("S3_BUCKET"):
            messagebox.showerror(
                "Validation Error",
                "S3 Bucket not configured.\n\nClick Settings to configure.",
            )
            return False
        return True

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
            try:
                log_file = log_var.get().strip()
                if log_file:
                    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
                    file_handler = logging.FileHandler(log_file)
                    file_handler.setLevel(logging.INFO)
                    logging.basicConfig(
                        level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[file_handler],
                        force=True,
                    )
                    for handler in logging.root.handlers:
                        if isinstance(handler, logging.FileHandler):
                            handler.stream.reconfigure(line_buffering=True)

                process_products(cfg, status)
            except Exception as e:
                status(f"Fatal error: {e}")
                logging.exception("Worker error:")
            finally:
                button_control_queue.put("enable_buttons")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    start_btn = tb.Button(
        button_frame, text="Start Processing",
        command=start_processing, bootstyle="success", width=20,
    )
    start_btn.pack(side="left", padx=5)

    validate_btn = tb.Button(
        button_frame, text="Validate Settings",
        command=validate_inputs, bootstyle="info", width=20,
    )
    validate_btn.pack(side="left", padx=5)

    tb.Button(
        button_frame, text="Settings",
        command=lambda: open_settings_dialog(cfg, app),
        bootstyle="warning-outline", width=20,
    ).pack(side="left", padx=5)

    tb.Button(
        button_frame, text="Exit",
        command=app.quit, bootstyle="secondary", width=20,
    ).pack(side="left", padx=5)

    # ========== Status Log ==========
    tb.Label(app, text="Status Log:", anchor="w").pack(anchor="w", padx=10, pady=(10, 0))

    status_log = tb.Text(app, height=15, state="normal")
    status_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Queue processor (50ms poll)
    def process_queues():
        try:
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

        app.after(50, process_queues)

    app.after(50, process_queues)

    # Initial status
    status("=" * 80)
    status("Aggregates Excel-to-Categorizer Converter v1.0.0")
    status("GUI loaded successfully")
    status("=" * 80)
    status("")

    # Window close handler
    def on_closing():
        try:
            cfg["window_geometry"] = app.geometry()
            save_config(cfg)
        except Exception:
            pass
        app.quit()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    app.mainloop()


if __name__ == "__main__":
    build_gui()

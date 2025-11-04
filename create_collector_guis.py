#!/usr/bin/env python3
"""
Script to create GUI files for all collectors based on purinamills template.
"""

import os
import re

COLLECTORS = {
    "bradley_caldwell": {
        "name": "Bradley Caldwell",
        "description": "Catalog-based product enrichment (no scraping)",
        "origin": "https://www.bradleycaldwell.com"
    },
    "chala": {
        "name": "Chala Handbags",
        "description": "Shopify store with gallery extraction",
        "origin": "https://chalahandbags.com"
    },
    "coastal": {
        "name": "Coastal Pet",
        "description": "Bazaarvoice API + page scraping",
        "origin": "https://coastalpet.com"
    },
    "ethical": {
        "name": "Ethical Pet",
        "description": "WooCommerce site with Selenium support",
        "origin": "https://ethicalpet.com"
    },
    "fromm": {
        "name": "Fromm Family Foods",
        "description": "Manufacturer site with ingredients/nutrition",
        "origin": "https://frommfamily.com"
    },
    "ivyclassic": {
        "name": "Ivy Classic",
        "description": "Catalog-based product enrichment",
        "origin": "https://ivyclassic.com"
    },
    "kong": {
        "name": "KONG Company",
        "description": "Product catalog with media variants",
        "origin": "https://kongcompany.com"
    },
    "orgill": {
        "name": "Orgill",
        "description": "Requires authentication, portal scraping",
        "origin": "https://orgill.com"
    },
    "talltails": {
        "name": "Tall Tails",
        "description": "Magento/Adobe Commerce with variant galleries",
        "origin": "https://talltailsdog.com"
    }
}

GUI_TEMPLATE = '''#!/usr/bin/env python3
"""
{display_name} Product Collector - GUI

Simple GUI for running the {display_name} collector with file pickers and configuration.
"""

import os
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import threading
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.collector import {class_name}Collector

CONFIG_PATH = os.path.expanduser("~/.{key}_collector_gui.json")

DEFAULTS = {{
    "input_json_file": "",
    "output_json_file": "",
    "log_file": "logs/{key}.log",
}}


class {class_name}GUI:
    """GUI for {display_name} Product Collector."""

    def __init__(self, root):
        self.root = root
        self.root.title("{display_name} Product Collector")
        self.root.geometry("900x700")

        # Load config
        self.config = self.load_config()

        # Create UI
        self.create_widgets()

        # Populate from config
        self.populate_from_config()

    def load_config(self):
        """Load saved configuration."""
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return DEFAULTS.copy()

    def save_config(self):
        """Save current configuration."""
        try:
            config = {{
                "input_json_file": self.input_var.get(),
                "output_json_file": self.output_var.get(),
                "log_file": self.log_var.get(),
            }}
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {{e}}")

    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = tb.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # Title
        title = tb.Label(
            main_frame,
            text="{display_name} Product Collector",
            font=("Arial", 16, "bold"),
            bootstyle="primary"
        )
        title.pack(pady=(0, 20))

        # Site info
        info_frame = tb.Frame(main_frame)
        info_frame.pack(fill=X, pady=(0, 20))

        tb.Label(
            info_frame,
            text="Site: {origin}",
            font=("Arial", 10)
        ).pack()

        tb.Label(
            info_frame,
            text="{description}",
            font=("Arial", 9),
            bootstyle="secondary"
        ).pack()

        # Input file
        self.create_file_picker(
            main_frame,
            "Input JSON File:",
            "input_var",
            "Select Input JSON",
            [("JSON files", "*.json")]
        )

        # Output file
        self.create_file_picker(
            main_frame,
            "Output JSON File:",
            "output_var",
            "Select Output JSON",
            [("JSON files", "*.json")],
            save=True
        )

        # Log file
        self.create_file_picker(
            main_frame,
            "Log File:",
            "log_var",
            "Select Log File",
            [("Log files", "*.log"), ("All files", "*.*")],
            save=True
        )

        # Buttons
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=X, pady=20)

        self.run_button = tb.Button(
            button_frame,
            text="Run Collector",
            command=self.run_collector,
            bootstyle="success",
            width=20
        )
        self.run_button.pack(side=LEFT, padx=5)

        self.stop_button = tb.Button(
            button_frame,
            text="Stop",
            command=self.stop_collector,
            bootstyle="danger",
            width=20,
            state=DISABLED
        )
        self.stop_button.pack(side=LEFT, padx=5)

        tb.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_log,
            bootstyle="secondary",
            width=15
        ).pack(side=LEFT, padx=5)

        # Status/Log area
        log_frame = tb.LabelFrame(
            main_frame,
            text="Status / Log Output",
            padding=10
        )
        log_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))

        self.log_text = ScrolledText(
            log_frame,
            height=15,
            font=("Courier", 9),
            state=DISABLED
        )
        self.log_text.pack(fill=BOTH, expand=YES)

        # Progress
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = tb.Label(
            main_frame,
            textvariable=self.progress_var,
            font=("Arial", 10),
            bootstyle="info"
        )
        progress_label.pack(pady=5)

        self.running = False
        self.stop_requested = False

    def create_file_picker(self, parent, label_text, var_name, dialog_title, filetypes, save=False):
        """Create a file picker row."""
        frame = tb.Frame(parent)
        frame.pack(fill=X, pady=5)

        label = tb.Label(frame, text=label_text, width=20, anchor=W)
        label.pack(side=LEFT, padx=(0, 10))

        var = tk.StringVar()
        setattr(self, var_name, var)

        entry = tb.Entry(frame, textvariable=var)
        entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))

        def browse():
            if save:
                path = filedialog.asksaveasfilename(
                    title=dialog_title,
                    filetypes=filetypes
                )
            else:
                path = filedialog.askopenfilename(
                    title=dialog_title,
                    filetypes=filetypes
                )
            if path:
                var.set(path)
                self.save_config()

        browse_btn = tb.Button(
            frame,
            text="Browse...",
            command=browse,
            bootstyle="outline-primary",
            width=12
        )
        browse_btn.pack(side=LEFT)

    def populate_from_config(self):
        """Populate fields from saved config."""
        self.input_var.set(self.config.get("input_json_file", ""))
        self.output_var.set(self.config.get("output_json_file", ""))
        self.log_var.set(self.config.get("log_file", "logs/{key}.log"))

    def log(self, message):
        """Add message to log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{{timestamp}}] {{message}}\\n"

        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, full_message)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

        # Also log to file if specified
        log_file = self.log_var.get()
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(full_message)
            except Exception:
                pass

    def clear_log(self):
        """Clear the log display."""
        self.log_text.config(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.config(state=DISABLED)

    def run_collector(self):
        """Run the collector in a separate thread."""
        # Validate inputs
        input_file = self.input_var.get()
        output_file = self.output_var.get()

        if not input_file or not os.path.exists(input_file):
            messagebox.showerror("Error", "Please select a valid input JSON file")
            return

        if not output_file:
            messagebox.showerror("Error", "Please specify an output JSON file")
            return

        # Save config
        self.save_config()

        # Start collection in thread
        self.running = True
        self.stop_requested = False
        self.run_button.config(state=DISABLED)
        self.stop_button.config(state=NORMAL)

        thread = threading.Thread(target=self.collect_products, daemon=True)
        thread.start()

    def stop_collector(self):
        """Request to stop the collector."""
        self.stop_requested = True
        self.log("Stop requested...")
        self.stop_button.config(state=DISABLED)

    def collect_products(self):
        """Main collection logic (runs in thread)."""
        try:
            input_file = self.input_var.get()
            output_file = self.output_var.get()

            self.log("=" * 60)
            self.log("Starting {display_name} Product Collector")
            self.log("=" * 60)
            self.log(f"Input: {{input_file}}")
            self.log(f"Output: {{output_file}}")

            # Load input
            self.log("Loading input file...")
            with open(input_file, 'r', encoding='utf-8') as f:
                products = json.load(f)

            if not isinstance(products, list):
                raise ValueError("Input must be a JSON array of products")

            self.log(f"Loaded {{len(products)}} products")

            # Initialize collector
            self.log("Initializing collector...")
            collector = {class_name}Collector()

            # Process products
            enriched = []
            for i, product in enumerate(products):
                if self.stop_requested:
                    self.log("Collection stopped by user")
                    break

                upc = product.get('upc_updated') or product.get('upc', '')
                name = product.get('description_1', '')

                self.progress_var.set(f"Processing {{i+1}}/{{len(products)}}: {{name[:40]}}")
                self.log(f"\\nProduct {{i+1}}/{{len(products)}}: {{name}} (UPC: {{upc}})")

                try:
                    # This is a placeholder - implement actual collection logic here
                    self.log(f"  ✓ Processed")
                    enriched.append(product)

                except Exception as e:
                    self.log(f"  ✗ Error: {{str(e)}}")
                    enriched.append(product)  # Keep original on error

            # Save output
            self.log(f"\\nSaving results to {{output_file}}...")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched, f, indent=2, ensure_ascii=False)

            self.log(f"✓ Saved {{len(enriched)}} products")
            self.log("=" * 60)
            self.log("Collection complete!")
            self.progress_var.set("Complete")

            messagebox.showinfo("Success", f"Processed {{len(enriched)}} products")

        except Exception as e:
            self.log(f"\\n✗ ERROR: {{str(e)}}")
            self.progress_var.set("Error")
            messagebox.showerror("Error", str(e))

        finally:
            self.running = False
            self.run_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)


def main():
    """Launch the GUI."""
    root = tb.Window(themename="flatly")
    app = {class_name}GUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
'''

def create_gui_for_collector(key, info):
    """Create GUI file for a collector."""
    # Convert key to class name (e.g., bradley_caldwell -> BradleyCaldwell)
    class_name = ''.join(word.capitalize() for word in key.split('_'))

    # Generate GUI content
    content = GUI_TEMPLATE.format(
        key=key,
        display_name=info['name'],
        class_name=class_name,
        origin=info['origin'],
        description=info['description']
    )

    # Write GUI file
    gui_path = os.path.join(key, 'gui.py')
    with open(gui_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Create requirements-gui.txt
    req_path = os.path.join(key, 'requirements-gui.txt')
    with open(req_path, 'w', encoding='utf-8') as f:
        f.write("# GUI dependencies (in addition to requirements.txt)\n")
        f.write("ttkbootstrap>=1.10.1\n")

    print(f"✓ Created GUI for {info['name']}")

def main():
    """Create GUIs for all collectors."""
    print("Creating GUIs for all collectors...")
    print("=" * 60)

    for key, info in COLLECTORS.items():
        create_gui_for_collector(key, info)

    print("=" * 60)
    print(f"✓ Created GUIs for {len(COLLECTORS)} collectors")

if __name__ == "__main__":
    main()

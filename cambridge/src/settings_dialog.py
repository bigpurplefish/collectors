"""
Settings Dialog for Cambridge Product Collector

Modal dialog for managing dealer portal credentials and system settings.
"""

import ttkbootstrap as tb
from tkinter import messagebox
from src.config import save_config


def open_settings_dialog(cfg, parent):
    """
    Open modal settings dialog for portal credentials.

    Args:
        cfg: Configuration dictionary
        parent: Parent window (app)
    """
    dialog = tb.Toplevel(parent)
    dialog.title("Settings")
    dialog.geometry("600x300")
    dialog.transient(parent)  # Modal dialog
    dialog.grab_set()  # Block interaction with parent

    # Center dialog on parent
    dialog.update_idletasks()
    x = parent.winfo_x() + (parent.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = parent.winfo_y() + (parent.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")

    # Container
    container = tb.Frame(dialog)
    container.pack(fill="both", expand=True, padx=20, pady=20)
    container.columnconfigure(1, weight=1)

    # Title
    tb.Label(
        container,
        text="Cambridge Collector Settings",
        font=("Arial", 14, "bold")
    ).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    # Portal Username
    row = 1
    tb.Label(container, text="Portal Username:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=10
    )
    username_var = tb.StringVar(value=cfg.get("portal_username", ""))
    tb.Entry(container, textvariable=username_var).grid(
        row=row, column=1, sticky="ew", padx=5, pady=10
    )

    # Portal Password (masked)
    row += 1
    tb.Label(container, text="Portal Password:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=10
    )
    password_var = tb.StringVar(value=cfg.get("portal_password", ""))
    tb.Entry(container, textvariable=password_var, show="*").grid(
        row=row, column=1, sticky="ew", padx=5, pady=10
    )

    # Help text
    row += 1
    help_text = tb.Label(
        container,
        text="Credentials for https://shop.cambridgepavers.com\nExample: markjr@garoppos.com",
        font=("Arial", 9),
        foreground="#888"
    )
    help_text.grid(row=row, column=0, columnspan=2, pady=(10, 20))

    # Button frame
    button_frame = tb.Frame(container)
    button_frame.grid(row=row + 1, column=0, columnspan=2)

    def save_settings():
        """Validate and save settings."""
        # Validation
        username = username_var.get().strip()
        password = password_var.get().strip()

        if not username:
            messagebox.showerror("Validation Error", "Portal Username is required.")
            return

        if not password:
            messagebox.showerror("Validation Error", "Portal Password is required.")
            return

        # Save to config
        cfg["portal_username"] = username
        cfg["portal_password"] = password
        save_config(cfg)

        messagebox.showinfo("Success", "Settings saved successfully.")
        dialog.destroy()

    def cancel_settings():
        """Close without saving."""
        dialog.destroy()

    tb.Button(
        button_frame,
        text="Save",
        command=save_settings,
        bootstyle="success",
        width=15
    ).pack(side="left", padx=5)

    tb.Button(
        button_frame,
        text="Cancel",
        command=cancel_settings,
        bootstyle="secondary",
        width=15
    ).pack(side="left", padx=5)

    dialog.wait_window()  # Wait for dialog to close

"""
Settings Dialog for Aggregates Converter.

Modal dialog for managing AWS credentials and S3 configuration.
"""

import ttkbootstrap as tb
from tkinter import messagebox
from src.config import save_config


def open_settings_dialog(cfg, parent):
    """Open modal settings dialog for AWS/S3 configuration.

    Args:
        cfg: Configuration dictionary
        parent: Parent window (app)
    """
    dialog = tb.Toplevel(parent)
    dialog.title("Settings")
    dialog.geometry("600x450")
    dialog.transient(parent)
    dialog.grab_set()

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
        text="Aggregates Settings",
        font=("Arial", 14, "bold"),
    ).grid(row=0, column=0, columnspan=2, pady=(0, 20))

    row = 1

    # ========== AWS Credentials Section ==========
    tb.Label(
        container,
        text="AWS Credentials",
        font=("Arial", 11, "bold"),
        foreground="#5BC0DE",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))
    row += 1

    # Access Key ID
    tb.Label(container, text="Access Key ID:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=5,
    )
    access_key_var = tb.StringVar(value=cfg.get("AWS_ACCESS_KEY_ID", ""))
    tb.Entry(container, textvariable=access_key_var).grid(
        row=row, column=1, sticky="ew", padx=5, pady=5,
    )
    row += 1

    # Secret Access Key (masked)
    tb.Label(container, text="Secret Access Key:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=5,
    )
    secret_key_var = tb.StringVar(value=cfg.get("AWS_SECRET_ACCESS_KEY", ""))
    tb.Entry(container, textvariable=secret_key_var, show="*").grid(
        row=row, column=1, sticky="ew", padx=5, pady=5,
    )
    row += 1

    # Region
    tb.Label(container, text="Region:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=5,
    )
    region_var = tb.StringVar(value=cfg.get("AWS_REGION_NAME", ""))
    tb.Entry(container, textvariable=region_var).grid(
        row=row, column=1, sticky="ew", padx=5, pady=5,
    )
    row += 1

    # ========== S3 Settings Section ==========
    tb.Label(
        container,
        text="S3 Settings",
        font=("Arial", 11, "bold"),
        foreground="#5BC0DE",
    ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5))
    row += 1

    # Bucket
    tb.Label(container, text="S3 Bucket:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=5,
    )
    bucket_var = tb.StringVar(value=cfg.get("S3_BUCKET", ""))
    tb.Entry(container, textvariable=bucket_var).grid(
        row=row, column=1, sticky="ew", padx=5, pady=5,
    )
    row += 1

    # Folder prefix
    tb.Label(container, text="S3 Folder:", anchor="w").grid(
        row=row, column=0, sticky="w", padx=5, pady=5,
    )
    folder_var = tb.StringVar(value=cfg.get("S3_FOLDER", "aggregates/images"))
    tb.Entry(container, textvariable=folder_var).grid(
        row=row, column=1, sticky="ew", padx=5, pady=5,
    )
    row += 1

    # Help text
    help_text = tb.Label(
        container,
        text="Images will be uploaded to s3://{bucket}/{folder}/{filename}\n"
             "Bucket must have public read access for downstream systems.",
        font=("Arial", 9),
        foreground="#888",
    )
    help_text.grid(row=row, column=0, columnspan=2, pady=(10, 20))
    row += 1

    # Button frame
    button_frame = tb.Frame(container)
    button_frame.grid(row=row, column=0, columnspan=2)

    def save_settings():
        """Validate and save settings."""
        access_key = access_key_var.get().strip()
        secret_key = secret_key_var.get().strip()
        bucket = bucket_var.get().strip()

        if not access_key:
            messagebox.showerror("Validation Error", "Access Key ID is required.")
            return
        if not secret_key:
            messagebox.showerror("Validation Error", "Secret Access Key is required.")
            return
        if not bucket:
            messagebox.showerror("Validation Error", "S3 Bucket is required.")
            return

        cfg["AWS_ACCESS_KEY_ID"] = access_key
        cfg["AWS_SECRET_ACCESS_KEY"] = secret_key
        cfg["AWS_REGION_NAME"] = region_var.get().strip()
        cfg["S3_BUCKET"] = bucket
        cfg["S3_FOLDER"] = folder_var.get().strip()
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
        width=15,
    ).pack(side="left", padx=5)

    tb.Button(
        button_frame,
        text="Cancel",
        command=cancel_settings,
        bootstyle="secondary",
        width=15,
    ).pack(side="left", padx=5)

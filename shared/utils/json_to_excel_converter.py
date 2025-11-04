"""
JSON → Excel Converter (with GUI)

Features
--------
- Converts a JSON file into an Excel workbook (.xlsx) using pandas/openpyxl.
- Data typing rules:
  1) Integers → int
  2) Decimals → float
  3) Booleans → int (True→1, False→0)
  4) Date-like strings → datetime (Excel-friendly)
  5) Arrays → flattened to columns named: <key>_0, <key>_1, ... (width is the max length observed for that key across all records)
  6) Everything else → string
- Robust input normalization (supports array of objects, single object, or a dict containing one top-level list of objects).
- GUI built with tkbootstrap (theme: flatly) providing read-only file pickers and a Convert button.
- ID field selector (required). After choosing a JSON file, a dropdown is populated with available keys; default is the first key found.
- Last-used paths & ID field persist between runs (stored in a config file in your home folder).
- ID field values are coerced to integers where possible; blank or non-integer values remain unchanged.
- Purely numeric strings are never treated as dates, regardless of length.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union, Optional

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

import pandas as pd

try:
    from dateutil import parser as dateutil_parser  # type: ignore
    _HAS_DATEUTIL = True
except Exception:
    _HAS_DATEUTIL = False

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".json_to_excel_converter_config.json")


def load_config() -> Dict[str, str]:
    """Load persisted UI state (last used json path, excel path, id field)."""
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {k: str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_config(cfg: Dict[str, str]) -> None:
    """Persist UI state to the config file in the user's home directory."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

Primitive = Union[str, int, float, datetime, None]
JsonValue = Union[Primitive, Dict[str, Any], List[Any]]
Record = Dict[str, JsonValue]


def is_date_string(value: str) -> bool:
    """Return True if the string looks like a date/time.
    Purely numeric strings are never treated as dates to avoid ID misclassification.
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return False
    if s.isdigit():
        return False
    iso_candidates = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]
    for fmt in iso_candidates:
        try:
            datetime.strptime(s[:19], fmt)
            return True
        except Exception:
            pass
    common_formats = ["%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y/%m/%d", "%Y.%m.%d"]
    for fmt in common_formats:
        try:
            datetime.strptime(s, fmt)
            return True
        except Exception:
            pass
    if _HAS_DATEUTIL:
        try:
            dt = dateutil_parser.parse(s, dayfirst=False, yearfirst=True, fuzzy=False)
            if not (dt.hour != 0 or dt.minute != 0 or dt.second != 0) and "." in s:
                return False
            return True
        except Exception:
            return False
    return False


def coerce_value(key: str, value: JsonValue) -> Primitive:
    """Coerce a single value according to the project rules."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if is_date_string(value):
            try:
                if _HAS_DATEUTIL:
                    return dateutil_parser.parse(value, dayfirst=False, yearfirst=True, fuzzy=False)
                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y/%m/%d", "%Y.%m.%d"]:
                    try:
                        return datetime.strptime(value[:19], fmt)
                    except Exception:
                        pass
            except Exception:
                return value
            return value
        return value
    if isinstance(value, list):
        return None
    if isinstance(value, dict):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return None


def analyze_array_lengths(records: List[Record]) -> Dict[str, int]:
    """Compute maximum length for each array field across all records."""
    max_lengths: Dict[str, int] = {}
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, list):
                current = max_lengths.get(k, 0)
                length = len(v)
                if length > current:
                    max_lengths[k] = length
    return max_lengths


def flatten_record(rec: Record, array_lengths: Dict[str, int]) -> Dict[str, Primitive]:
    """Flatten arrays to multiple columns and coerce values."""
    out: Dict[str, Primitive] = {}
    for k, v in rec.items():
        if isinstance(v, list):
            continue
        out[k] = coerce_value(k, v)
    for k, max_len in array_lengths.items():
        values = rec.get(k, [])
        if not isinstance(values, list):
            values = []
        for idx in range(max_len):
            col_name = f"{k}_{idx}"
            if idx < len(values):
                elem = values[idx]
                if isinstance(elem, (str, int, float, bool)) or elem is None:
                    out[col_name] = coerce_value(k, elem)
                else:
                    try:
                        out[col_name] = json.dumps(elem, ensure_ascii=False)
                    except Exception:
                        out[col_name] = str(elem)
            else:
                out[col_name] = None
    return out


def normalize_input(json_obj: Any) -> List[Record]:
    """Normalize JSON data to a list of record dictionaries."""
    if isinstance(json_obj, list):
        if all(isinstance(item, dict) for item in json_obj):
            return json_obj  # type: ignore
        else:
            wrapped: List[Record] = []
            for idx, item in enumerate(json_obj):
                wrapped.append({"value": item, "index": idx})
            return wrapped
    if isinstance(json_obj, dict):
        list_keys = [k for k, v in json_obj.items() if isinstance(v, list) and all(isinstance(i, dict) for i in v)]
        if len(list_keys) == 1:
            return json_obj[list_keys[0]]  # type: ignore
        return [json_obj]
    raise ValueError("Unsupported JSON structure. Expecting an object or an array of objects.")


def convert_json_to_excel(json_path: str, excel_path: str, id_field: Optional[str] = None) -> Tuple[int, List[str]]:
    """Convert JSON file to Excel, with optional ID field ordering and coercion."""
    warnings: List[str] = []
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")
    records = normalize_input(data)
    if not records:
        raise ValueError("No records found in the JSON file.")
    array_lengths = analyze_array_lengths(records)
    flat_rows: List[Dict[str, Primitive]] = []
    for rec in records:
        flat = flatten_record(rec, array_lengths)
        if id_field and id_field in flat and flat[id_field] not in (None, ""):
            try:
                flat[id_field] = int(flat[id_field])
            except (ValueError, TypeError):
                pass
        flat_rows.append(flat)
    df = pd.DataFrame(flat_rows)
    array_cols = sorted([c for c in df.columns if any(c.startswith(f"{k}_") for k in array_lengths.keys())])
    ordered_cols = [c for c in df.columns if c not in array_cols] + array_cols
    if id_field and id_field in ordered_cols:
        ordered_cols = [id_field] + [c for c in ordered_cols if c != id_field]
    df = df.reindex(columns=ordered_cols)
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl", datetime_format="yyyy-mm-dd hh:mm:ss") as writer:
            df.to_excel(writer, index=False, sheet_name="Data")
    except Exception as e:
        raise IOError(f"Failed to write Excel file: {e}")
    return len(df), warnings


def collect_record_keys(records: List[Record], sample_limit: int = 200) -> List[str]:
    """Collect unique keys from up to `sample_limit` records."""
    seen: Dict[str, None] = {}
    for rec in records[: sample_limit]:
        for k in rec.keys():
            if k not in seen:
                seen[k] = None
    return list(seen.keys())


class JsonToExcelApp:
    """Tkinter GUI for selecting JSON, ID field, Excel output, and running conversion."""

    def __init__(self, master: tb.Window) -> None:
        self.master = master
        self.cfg: Dict[str, str] = load_config()
        master.title("JSON to Excel Converter")
        master.geometry("1200x400")
        master.option_add("*Font", ("Arial", 11))
        container = tb.Frame(master, padding=20)
        container.pack(fill=BOTH, expand=True)
        self.json_path_var = tk.StringVar(value=self.cfg.get("json_path", ""))
        json_row = tb.Frame(container)
        json_row.pack(fill=X, pady=10)
        tb.Label(json_row, text="Input JSON file:", width=20, anchor=W).pack(side=LEFT)
        self.json_entry = tb.Entry(json_row, textvariable=self.json_path_var, width=100, state="readonly")
        self.json_entry.pack(side=LEFT, padx=(0, 10))
        tb.Button(json_row, text="Browse", bootstyle=PRIMARY, command=self.browse_json).pack(side=LEFT)
        id_row = tb.Frame(container)
        id_row.pack(fill=X, pady=10)
        tb.Label(id_row, text="ID field (required):", width=20, anchor=W).pack(side=LEFT)
        self.id_key_var = tk.StringVar(value=self.cfg.get("id_field", ""))
        self.id_combo = tb.Combobox(id_row, textvariable=self.id_key_var, width=40, state="readonly")
        self.id_combo.pack(side=LEFT)
        self.excel_path_var = tk.StringVar(value=self.cfg.get("excel_path", ""))
        excel_row = tb.Frame(container)
        excel_row.pack(fill=X, pady=10)
        tb.Label(excel_row, text="Output Excel file:", width=20, anchor=W).pack(side=LEFT)
        self.excel_entry = tb.Entry(excel_row, textvariable=self.excel_path_var, width=100, state="readonly")
        self.excel_entry.pack(side=LEFT, padx=(0, 10))
        tb.Button(excel_row, text="Browse", bootstyle=PRIMARY, command=self.browse_excel).pack(side=LEFT)
        action_row = tb.Frame(container)
        action_row.pack(fill=X, pady=20)
        tb.Button(action_row, text="Convert", bootstyle=SUCCESS, command=self.convert).pack(side=LEFT)
        hint_text = (
            "Rules: integers->int, decimals->float, booleans->int, dates->datetime; "
            "arrays flattened to key_0, key_1, ...;\n"
            "Everything else becomes a string."
        )
        tb.Label(container, text=hint_text, anchor=W, justify=LEFT, wraplength=1100).pack(fill=X, pady=(10, 0))
        if self.json_path_var.get():
            self.refresh_id_keys(initial=True)

    def refresh_id_keys(self, initial: bool = False) -> None:
        """Populate ID field dropdown from keys in the selected JSON file."""
        path = self.json_path_var.get().strip()
        keys: List[str] = []
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = normalize_input(data)
                keys = collect_record_keys(records)
            except Exception:
                keys = []
        self.id_combo["values"] = keys
        persisted = self.cfg.get("id_field", "") if initial else self.id_key_var.get()
        if persisted and persisted in keys:
            self.id_key_var.set(persisted)
        elif keys:
            self.id_key_var.set(keys[0])
        else:
            self.id_key_var.set("")

    def browse_json(self) -> None:
        """Browse for input JSON file and refresh ID field list."""
        path = filedialog.askopenfilename(
            title="Select JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.json_path_var.set(path)
            self.cfg["json_path"] = path
            save_config(self.cfg)
            self.refresh_id_keys(initial=False)

    def browse_excel(self) -> None:
        """Browse for Excel output file."""
        path = filedialog.asksaveasfilename(
            title="Save Excel file",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")],
        )
        if path:
            self.excel_path_var.set(path)
            self.cfg["excel_path"] = path
            save_config(self.cfg)

    def convert(self) -> None:
        """Validate inputs and run the JSON-to-Excel conversion."""
        json_path = self.json_path_var.get().strip()
        excel_path = self.excel_path_var.get().strip()
        id_field = self.id_key_var.get().strip()
        if not json_path:
            messagebox.showerror("Missing input", "Please select an input JSON file.")
            return
        if not id_field:
            messagebox.showerror("Missing ID field", "Please select an ID field from the dropdown.")
            return
        if not excel_path:
            messagebox.showerror("Missing output", "Please choose a destination for the Excel file.")
            return
        try:
            rows, warnings = convert_json_to_excel(json_path, excel_path, id_field=id_field)
        except Exception as e:
            messagebox.showerror("Conversion failed", str(e))
            return
        self.cfg.update({
            "json_path": json_path,
            "excel_path": excel_path,
            "id_field": id_field,
        })
        save_config(self.cfg)
        msg = f"Success! Wrote {rows} row(s) to:\n{excel_path}"
        if warnings:
            msg += "\n\nWarnings:\n- " + "\n- ".join(warnings)
        messagebox.showinfo("Done", msg)


def main() -> None:
    """Launch the Tkinter bootstrap window."""
    app = tb.Window(themename="flatly")
    JsonToExcelApp(app)
    app.mainloop()


if __name__ == "__main__":
    main()

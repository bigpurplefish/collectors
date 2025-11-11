"""
Logging utilities for Cambridge collector.

Implements dual logging pattern from GUI_DESIGN_REQUIREMENTS.md:
- User-friendly messages to status callback (GUI)
- Detailed technical logs to console and file
"""

import logging
from typing import Callable, Optional


def log_and_status(
    status_fn: Optional[Callable],
    msg: str,
    level: str = "info",
    ui_msg: Optional[str] = None
):
    """
    Log to file/console and update UI status.

    Args:
        status_fn: Status callback function (for GUI)
        msg: Detailed technical message for logs
        level: Log level ("info", "warning", "error", "debug")
        ui_msg: User-friendly message for UI (defaults to msg if not provided)
    """
    if ui_msg is None:
        ui_msg = msg

    # Log detailed message to file/console
    if level == "error":
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)
    elif level == "debug":
        logging.debug(msg)
    else:
        logging.info(msg)

    # Update UI with user-friendly message
    if status_fn:
        try:
            status_fn(ui_msg)
        except Exception as e:
            logging.warning(f"Status update failed: {e}")


def log_section_header(status_fn: Optional[Callable], title: str):
    """
    Log a section header.

    Args:
        status_fn: Status callback function
        title: Section title
    """
    log_and_status(status_fn, f"\n{'=' * 80}\n{title}\n{'=' * 80}", ui_msg=f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def log_progress(
    status_fn: Optional[Callable],
    current: int,
    total: int,
    item_name: str,
    details: Optional[str] = None
):
    """
    Log progress update.

    Args:
        status_fn: Status callback function
        current: Current item number (1-based)
        total: Total items
        item_name: Name of item being processed
        details: Additional technical details for logs
    """
    ui_msg = f"[{current}/{total}] Processing: {item_name}"
    tech_msg = f"[{current}/{total}] Processing: {item_name}"
    if details:
        tech_msg += f" | {details}"

    log_and_status(status_fn, tech_msg, ui_msg=ui_msg)


def log_success(
    status_fn: Optional[Callable],
    msg: str,
    details: Optional[str] = None
):
    """
    Log success message.

    Args:
        status_fn: Status callback function
        msg: User-friendly success message
        details: Additional technical details for logs
    """
    ui_msg = f"✅ {msg}"
    tech_msg = f"SUCCESS: {msg}"
    if details:
        tech_msg += f" | {details}"

    log_and_status(status_fn, tech_msg, ui_msg=ui_msg)


def log_warning(
    status_fn: Optional[Callable],
    msg: str,
    details: Optional[str] = None
):
    """
    Log warning message.

    Args:
        status_fn: Status callback function
        msg: User-friendly warning message
        details: Additional technical details for logs
    """
    ui_msg = f"⚠ {msg}"
    tech_msg = f"WARNING: {msg}"
    if details:
        tech_msg += f" | {details}"

    log_and_status(status_fn, tech_msg, level="warning", ui_msg=ui_msg)


def log_error(
    status_fn: Optional[Callable],
    msg: str,
    details: Optional[str] = None,
    exc: Optional[Exception] = None
):
    """
    Log error message.

    Args:
        status_fn: Status callback function
        msg: User-friendly error message
        details: Additional technical details for logs
        exc: Exception object for stack trace logging
    """
    ui_msg = f"❌ {msg}"
    tech_msg = f"ERROR: {msg}"
    if details:
        tech_msg += f" | {details}"
    if exc:
        tech_msg += f" | Exception: {type(exc).__name__}: {str(exc)}"
        logging.error(tech_msg, exc_info=True)
    else:
        logging.error(tech_msg)

    # Update UI
    if status_fn:
        try:
            status_fn(ui_msg)
        except Exception as e:
            logging.warning(f"Status update failed: {e}")


def log_summary(
    status_fn: Optional[Callable],
    title: str,
    stats: dict
):
    """
    Log completion summary with statistics.

    Args:
        status_fn: Status callback function
        title: Summary title
        stats: Dictionary of statistics to display
    """
    lines = [
        "",
        "=" * 80,
        title,
        "=" * 80
    ]

    for key, value in stats.items():
        lines.append(f"{key}: {value}")

    lines.append("=" * 80)

    summary_text = "\n".join(lines)
    log_and_status(status_fn, summary_text, ui_msg=summary_text)

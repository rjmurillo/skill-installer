"""Shared utility functions for TUI components."""

from __future__ import annotations

import locale
import re
import sys


def sanitize_css_id(value: str) -> str:
    """Sanitize a string for use as a CSS ID.

    CSS IDs can only contain letters, numbers, underscores, or hyphens,
    and must not begin with a number.

    Args:
        value: The string to sanitize.

    Returns:
        A valid CSS ID string.
    """
    # Replace common separators with hyphens
    sanitized = value.replace("/", "--").replace(" ", "-")
    # Remove any remaining invalid characters
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", sanitized)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"id-{sanitized}"
    return sanitized or "item"


def sanitize_terminal_text(text: str, max_length: int = 100) -> str:
    """Sanitize text for safe terminal rendering.

    Removes:
    - ANSI escape sequences (\\x1b[...)
    - Control characters (except \\n, \\t)
    - Unicode directional overrides (RLO, LRO)
    - Non-printable characters

    Args:
        text: The text to sanitize.
        max_length: Maximum length for the output (default 100).

    Returns:
        Sanitized text safe for terminal display.
    """
    # Remove ANSI escape sequences (CSI, OSC, APC, DCS)
    # CSI: \x1b[...m (colors, cursor, etc.)
    # OSC: \x1b]...\x07 or \x1b]...\x1b\\ (titles, etc.)
    # APC/DCS: \x1b_...\x1b\\ and \x1bP...\x1b\\
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)  # CSI sequences
    text = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", text)  # OSC sequences
    text = re.sub(r"\x1b[P_][^\x1b]*\x1b\\", "", text)  # APC/DCS sequences

    # Remove control characters except newline/tab
    text = "".join(char for char in text if char.isprintable() or char in "\n\t")

    # Remove Unicode directional overrides (single pass)
    text = text.translate(str.maketrans("", "", "\u202e\u202d\u200f\u200e"))

    # Truncate to prevent DoS
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."

    return text


def get_terminal_indicators() -> dict[str, str]:
    """Detect terminal UTF-8 support and return appropriate indicators.

    Returns:
        Dict with keys: "checked", "installed", "unchecked"
    """
    try:
        encoding = getattr(sys.stdout, "encoding", None) or locale.getpreferredencoding()
    except (AttributeError, TypeError):
        encoding = "utf-8"  # Default to UTF-8 if detection fails

    supports_utf8 = encoding.lower() in ("utf-8", "utf8")

    if supports_utf8:
        return {
            "checked": "\u25c9",  # ◉
            "installed": "\u25cf",  # ●
            "unchecked": "\u25cb",  # ○
        }
    return {
        "checked": "[x]",
        "installed": "[*]",
        "unchecked": "[ ]",
    }

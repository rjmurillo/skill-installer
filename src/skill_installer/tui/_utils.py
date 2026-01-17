"""Shared utility functions for TUI components."""

from __future__ import annotations

import re


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

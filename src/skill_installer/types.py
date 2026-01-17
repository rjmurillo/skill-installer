"""Shared data types for skill installer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["InstallResult"]


@dataclass
class InstallResult:
    """Result of an installation operation.

    Attributes:
        success: True if installation succeeded.
        item_id: Item identifier in format source/type/key.
        platform: Target platform name.
        installed_path: Path where item was installed (None on failure).
        error: Error message (None on success).
    """

    success: bool
    item_id: str
    platform: str
    installed_path: Path | None
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate invariants."""
        if self.success and self.error is not None:
            raise ValueError("success=True but error is set")
        if not self.success and self.error is None:
            raise ValueError("success=False requires error message")
        if not self.item_id:
            raise ValueError("item_id cannot be empty")

"""Data types for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class DisplayItem:
    """Generic item for display in the TUI."""

    name: str
    item_type: str
    description: str
    source_name: str
    platforms: list[str]
    installed_platforms: list[str]
    raw_data: Any
    source_url: str = ""

    @property
    def unique_id(self) -> str:
        """Generate a unique ID for this item (source/type/name)."""
        return f"{self.source_name}/{self.item_type}/{self.name}"


@dataclass
class DisplaySource:
    """Source/marketplace for display in the TUI."""

    name: str
    display_name: str
    url: str
    available_count: int
    installed_count: int
    last_sync: str
    raw_data: Any

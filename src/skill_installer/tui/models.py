"""Data types for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from skill_installer.discovery import DiscoveredItem


@dataclass
class DisplayItem:
    """Generic item for display in the TUI."""

    name: str
    item_type: str
    description: str
    source_name: str
    platforms: list[str]
    installed_platforms: list[str]
    raw_data: Any  # DiscoveredItem
    source_url: str = ""
    relative_path: str = ""  # Path relative to repo root for disambiguation

    @property
    def unique_id(self) -> str:
        """Generate a unique ID for this item.

        Delegates to DiscoveredItem.make_item_id() as the single source of truth.
        """
        discovered: DiscoveredItem = self.raw_data
        return discovered.make_item_id(self.source_name)


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

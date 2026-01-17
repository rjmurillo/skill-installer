"""TUI screens package."""

from skill_installer.tui.screens.confirmation import ConfirmationScreen
from skill_installer.tui.screens.installed_item_detail import InstalledItemDetailScreen
from skill_installer.tui.screens.item_detail import ItemDetailScreen
from skill_installer.tui.screens.location_selection import LocationSelectionScreen
from skill_installer.tui.screens.source_detail import SourceDetailScreen

__all__ = [
    "ConfirmationScreen",
    "InstalledItemDetailScreen",
    "ItemDetailScreen",
    "LocationSelectionScreen",
    "SourceDetailScreen",
]

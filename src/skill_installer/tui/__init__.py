"""TUI package for skill-installer.

This package provides both interactive (Textual-based) and non-interactive
(Rich-based) terminal user interface components.
"""

from skill_installer.tui._utils import sanitize_css_id as _sanitize_css_id
from skill_installer.tui.app import SkillInstallerApp
from skill_installer.tui.console import TUI, console
from skill_installer.tui.models import DisplayItem, DisplaySource
from skill_installer.tui.panes import DiscoverPane, InstalledPane, MarketplacesPane
from skill_installer.tui.screens import (
    AddSourceScreen,
    ConfirmationScreen,
    ItemDetailScreen,
    LocationSelectionScreen,
    SourceDetailScreen,
)
from skill_installer.tui.widgets import (
    ItemDataTable,
    ItemDetailOption,
    ItemListView,
    LocationOption,
    ScrollIndicator,
    SearchInput,
    SourceDetailOption,
    SourceListView,
    SourceRow,
)

__all__ = [
    # Private (for backward compatibility)
    "_sanitize_css_id",
    # App
    "SkillInstallerApp",
    # Console (legacy)
    "TUI",
    "console",
    # Models
    "DisplayItem",
    "DisplaySource",
    # Panes
    "DiscoverPane",
    "InstalledPane",
    "MarketplacesPane",
    # Screens
    "AddSourceScreen",
    "ConfirmationScreen",
    "ItemDetailScreen",
    "LocationSelectionScreen",
    "SourceDetailScreen",
    # Widgets
    "ItemDataTable",
    "ItemDetailOption",
    "ItemListView",
    "LocationOption",
    "ScrollIndicator",
    "SearchInput",
    "SourceDetailOption",
    "SourceListView",
    "SourceRow",
]

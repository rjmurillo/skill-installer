"""Discover pane for browsing available items."""

from __future__ import annotations

from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Input, Select, Static

from skill_installer.tui.models import DisplayItem
from skill_installer.tui.widgets.item_list import ItemListView
from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator
from skill_installer.tui.widgets.search import SearchInput


class DiscoverPane(Container):
    """Discover tab - browse available skills/agents from all sources."""

    DEFAULT_CSS = """
    DiscoverPane {
        height: 1fr;
    }
    DiscoverPane #discover-filter-banner {
        height: 3;
        padding: 0 2;
        background: $primary-background;
        color: $warning;
        display: none;
    }
    DiscoverPane #discover-filter-banner.visible {
        display: block;
    }
    DiscoverPane #discover-filters {
        height: auto;
        padding: 1 2 0 2;
    }
    DiscoverPane #discover-search {
        width: 1fr;
    }
    DiscoverPane #platform-filter {
        width: 30;
        margin-left: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "clear_filter", "Clear Filter", show=False),
    ]

    def __init__(self, registry_manager: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._all_items: list[DisplayItem] = []
        self._search_query = ""
        self._source_filter: str | None = None
        self._platform_filter: str | None = None
        self.registry_manager = registry_manager

    def compose(self) -> ComposeResult:
        yield Static("", id="discover-filter-banner")
        with Horizontal(id="discover-filters"):
            yield SearchInput(id="discover-search")
            yield Select(
                [
                    ("All Platforms", None),
                    ("Claude", "claude"),
                    ("VS Code", "vscode"),
                    ("VS Code Insiders", "vscode-insiders"),
                    ("Copilot", "copilot"),
                ],
                value=None,
                id="platform-filter",
                allow_blank=False,
            )
        yield ItemListView(id="discover-list")
        yield ScrollIndicator(id="discover-scroll-indicator")

    def set_items(self, items: list[DisplayItem]) -> None:
        """Set the items to display."""
        self._all_items = items
        self._filter_items()

    def set_source_filter(self, source_name: str | None) -> None:
        """Filter items by source name."""
        self._source_filter = source_name
        self._update_filter_banner()
        self._filter_items()

    def set_platform_filter(self, platform: str | None) -> None:
        """Filter items by platform compatibility."""
        self._platform_filter = platform
        self._update_filter_banner()
        self._filter_items()

    def _update_filter_banner(self) -> None:
        """Update the filter banner based on active filters."""
        banner = self.query_one("#discover-filter-banner", Static)
        filters = []
        if self._source_filter:
            filters.append(f"marketplace: {self._source_filter}")
        if self._platform_filter:
            filters.append(f"platform: {self._platform_filter}")

        if filters:
            banner.update(f"Filtered by {', '.join(filters)} (Press Escape to clear)")
            banner.add_class("visible")
        else:
            banner.update("")
            banner.remove_class("visible")

    def _filter_items(self) -> None:
        """Filter items based on search query, source filter, and platform filter."""
        filtered = self._all_items

        # Apply source filter
        if self._source_filter:
            filtered = [item for item in filtered if item.source_name == self._source_filter]

        # Apply platform filter
        if self._platform_filter:
            # Normalize platform for comparison
            normalized = "vscode" if self._platform_filter == "vscode-insiders" else self._platform_filter
            filtered = [
                item for item in filtered
                if item.platforms and normalized in [
                    "vscode" if p == "vscode-insiders" else p for p in item.platforms
                ]
            ]

        # Apply search query
        query = self._search_query.lower()
        if query:
            filtered = [
                item for item in filtered
                if query in item.name.lower()
                or query in item.description.lower()
                or query in item.source_name.lower()
                or query in item.item_type.lower()
            ]

        list_view = self.query_one("#discover-list", ItemListView)
        list_view.set_items(filtered)

    def action_clear_filter(self) -> None:
        """Clear all filters."""
        if self._source_filter or self._platform_filter:
            self.set_source_filter(None)
            self.set_platform_filter(None)
            # Reset the platform filter select widget
            platform_select = self.query_one("#platform-filter", Select)
            platform_select.value = None

    @on(Input.Changed, "#discover-search Input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._search_query = event.value
        self._filter_items()

    @on(Select.Changed, "#platform-filter")
    def on_platform_filter_changed(self, event: Select.Changed) -> None:
        """Handle platform filter selection."""
        self.set_platform_filter(event.value)

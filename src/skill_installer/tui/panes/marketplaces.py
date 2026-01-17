"""Marketplaces pane for managing sources."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from skill_installer.tui.models import DisplaySource
from skill_installer.tui.widgets.source_list import SourceListView


class MarketplacesPane(Container):
    """Marketplaces tab - manage sources."""

    DEFAULT_CSS = """
    MarketplacesPane {
        height: 1fr;
    }
    MarketplacesPane #marketplaces-header {
        height: 3;
        padding: 1 2;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Configured source repositories:", id="marketplaces-header")
        yield SourceListView(id="marketplaces-list")

    def set_sources(self, sources: list[DisplaySource]) -> None:
        """Set the sources to display."""
        list_view = self.query_one("#marketplaces-list", SourceListView)
        list_view.set_sources(sources)

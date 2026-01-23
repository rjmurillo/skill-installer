"""Installed pane for viewing installed items."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input

from skill_installer.tui.models import DisplayItem
from skill_installer.tui.widgets.item_list import ItemListView
from skill_installer.tui.widgets.scroll_indicator import ScrollIndicator
from skill_installer.tui.widgets.search import SearchInput


class InstalledPane(Container):
    """Installed tab - view installed items."""

    DEFAULT_CSS = """
    InstalledPane {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._all_items: list[DisplayItem] = []
        self._search_query = ""

    def compose(self) -> ComposeResult:
        yield SearchInput(id="installed-search")
        yield ItemListView(id="installed-list")
        yield ScrollIndicator(id="installed-scroll-indicator")

    def set_items(self, items: list[DisplayItem]) -> None:
        """Set the items to display."""
        self._all_items = items
        self._filter_items()

    def _filter_items(self) -> None:
        """Filter items based on search query."""
        query = self._search_query.lower()
        if query:
            filtered = [
                item
                for item in self._all_items
                if query in item.name.lower()
                or query in item.description.lower()
                or query in item.source_name.lower()
            ]
        else:
            filtered = self._all_items

        list_view = self.query_one("#installed-list", ItemListView)
        list_view.set_items(filtered)

    @on(Input.Changed, "#installed-search Input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._search_query = event.value
        self._filter_items()

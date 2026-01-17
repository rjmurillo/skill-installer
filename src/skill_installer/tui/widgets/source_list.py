"""Source list widget for marketplace view."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from skill_installer.tui._utils import sanitize_css_id
from skill_installer.tui.models import DisplaySource


class SourceRow(Widget):
    """A source row for the Marketplaces tab."""

    DEFAULT_CSS = """
    SourceRow {
        height: 4;
        padding: 0 2;
    }
    SourceRow.selected {
        background: $accent;
    }
    SourceRow .source-name {
        color: $secondary;
        text-style: bold;
    }
    SourceRow .source-url {
        color: $text-muted;
    }
    SourceRow .source-stats {
        color: $text;
    }
    """

    selected = reactive(False)

    def __init__(self, source: DisplaySource, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = source

    def compose(self) -> ComposeResult:
        # Build stats line: "X available * Y installed * Updated date"
        stats_parts = [f"{self.source.available_count} available"]
        if self.source.installed_count > 0:
            stats_parts.append(f"{self.source.installed_count} installed")
        stats_parts.append(f"Updated {self.source.last_sync}")
        stats_line = " * ".join(stats_parts)

        with Vertical():
            yield Static(self.source.display_name, classes="source-name")
            yield Static(self.source.url, classes="source-url")
            yield Static(stats_line, classes="source-stats")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")


class SourceListView(VerticalScroll):
    """List view for sources (marketplaces)."""

    DEFAULT_CSS = """
    SourceListView {
        height: 1fr;
        border: solid $primary-background;
    }
    SourceListView:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("u", "update_source", "Update"),
        Binding("r", "remove_source", "Remove"),
    ]

    can_focus = True

    class SourceSelected(Message):
        """Posted when a source is selected."""

        def __init__(self, source: DisplaySource) -> None:
            super().__init__()
            self.source = source

    class SourceUpdate(Message):
        """Posted when a source should be updated."""

        def __init__(self, source: DisplaySource) -> None:
            super().__init__()
            self.source = source

    class SourceRemove(Message):
        """Posted when a source should be removed."""

        def __init__(self, source: DisplaySource) -> None:
            super().__init__()
            self.source = source

    selected_index = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sources: list[DisplaySource] = []
        self._rows: list[SourceRow] = []
        self._update_counter = 0  # Instance counter to ensure unique IDs on refresh

    @property
    def refresh_count(self) -> int:
        """Number of times the list has been refreshed."""
        return self._update_counter

    def _make_row_id(self, index: int, source: DisplaySource) -> str:
        """Create a unique row ID using list ID prefix and source name."""
        sanitized = sanitize_css_id(source.name)
        # Include update counter to ensure uniqueness across refreshes
        return f"{self.id}--{self._update_counter}--{index}--{sanitized}"

    def set_sources(self, sources: list[DisplaySource]) -> None:
        """Update the sources list."""
        # Increment update counter to ensure new unique IDs
        self._update_counter += 1

        # Remove all existing children first
        children = list(self.children)
        for child in children:
            child.remove()

        # Reset state
        self.sources = sources
        self.selected_index = 0
        self._rows = []

        # Mount new rows with new unique IDs
        for i, source in enumerate(sources):
            row = SourceRow(source, id=self._make_row_id(i, source))
            row.selected = i == 0
            self._rows.append(row)
            self.mount(row)

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if 0 <= old_index < len(self._rows):
            self._rows[old_index].selected = False
        if 0 <= new_index < len(self._rows):
            self._rows[new_index].selected = True
            self._rows[new_index].scroll_visible()

    def action_cursor_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_cursor_down(self) -> None:
        if self.selected_index < len(self.sources) - 1:
            self.selected_index += 1

    def action_select(self) -> None:
        if self.sources:
            self.post_message(self.SourceSelected(self.sources[self.selected_index]))

    def action_update_source(self) -> None:
        """Update the selected source."""
        if self.sources:
            self.post_message(self.SourceUpdate(self.sources[self.selected_index]))

    def action_remove_source(self) -> None:
        """Remove the selected source."""
        if self.sources:
            self.post_message(self.SourceRemove(self.sources[self.selected_index]))

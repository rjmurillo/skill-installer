"""Item list widget with keyboard navigation."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from skill_installer.tui._utils import sanitize_css_id
from skill_installer.tui.models import DisplayItem


class ItemRow(Widget):
    """A single item row in the list."""

    DEFAULT_CSS = """
    ItemRow {
        height: 3;
        padding: 0 2;
    }
    ItemRow.selected {
        background: $accent;
    }
    ItemRow.checked .item-indicator {
        color: $success;
    }
    ItemRow .item-header {
        color: $secondary;
    }
    ItemRow .item-description {
        color: $text-muted;
    }
    ItemRow .item-indicator {
        width: 3;
        color: $text-muted;
    }
    """

    selected = reactive(False)
    checked = reactive(False)

    def __init__(self, item: DisplayItem, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.item = item
        self._indicator: Static | None = None

    def compose(self) -> ComposeResult:
        installed = bool(self.item.installed_platforms)
        indicator = "\u25cf" if installed else "\u25cb"
        status = f"[{', '.join(self.item.installed_platforms)}]" if installed else ""

        # First line: name * source_name [status]
        first_line_parts = [self.item.name, " * ", self.item.source_name]
        if status:
            first_line_parts.append(f" {status}")
        first_line = "".join(first_line_parts)

        # Second line: description (truncated if needed)
        description = self.item.description or "No description"
        max_desc_length = 80
        if len(description) > max_desc_length:
            description = description[:max_desc_length - 3] + "..."

        with Horizontal():
            self._indicator = Static(indicator, classes="item-indicator")
            yield self._indicator
            with Vertical():
                yield Static(first_line, classes="item-header")
                yield Static(description, classes="item-description")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")

    def watch_checked(self, checked: bool) -> None:
        self.set_class(checked, "checked")
        if self._indicator:
            # Update indicator: ◉ for checked, ● for installed unchecked, ○ for not installed unchecked
            installed = bool(self.item.installed_platforms)
            if checked:
                self._indicator.update("\u25c9")  # ◉ (checked)
            elif installed:
                self._indicator.update("\u25cf")  # ● (installed)
            else:
                self._indicator.update("\u25cb")  # ○ (not installed)


class ItemListView(VerticalScroll):
    """Scrollable list of items with keyboard navigation."""

    DEFAULT_CSS = """
    ItemListView {
        height: 1fr;
        border: solid $primary-background;
    }
    ItemListView:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
        Binding("space", "toggle", "Toggle"),
    ]

    can_focus = True

    class ItemSelected(Message):
        """Posted when an item is selected (Enter key)."""

        def __init__(self, item: DisplayItem) -> None:
            super().__init__()
            self.item = item

    class ItemToggled(Message):
        """Posted when an item is toggled (Space key)."""

        def __init__(self, item: DisplayItem, checked: bool) -> None:
            super().__init__()
            self.item = item
            self.checked = checked

    selected_index = reactive(0)

    # Class variable to ensure unique IDs across all list updates
    _id_counter = 0

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.items: list[DisplayItem] = []
        self._rows: list[ItemRow] = []
        self._checked_items: set[str] = set()  # Track checked items by unique_id
        self._update_counter = 0  # Instance counter for this list

    def _make_row_id(self, index: int, item: DisplayItem) -> str:
        """Create a unique row ID using list ID prefix and item unique ID."""
        sanitized = sanitize_css_id(item.unique_id)
        # Include list ID prefix, update counter, and index to ensure uniqueness
        return f"{self.id}--{self._update_counter}--{index}--{sanitized}"

    def compose(self) -> ComposeResult:
        for i, item in enumerate(self.items):
            row = ItemRow(item, id=self._make_row_id(i, item))
            row.selected = i == self.selected_index
            self._rows.append(row)
            yield row

    def set_items(self, items: list[DisplayItem]) -> None:
        """Update the list items."""
        # Increment update counter to ensure new unique IDs
        self._update_counter += 1

        # Remove all existing children first
        children = list(self.children)
        for child in children:
            child.remove()

        # Reset state
        self.items = items
        self.selected_index = 0
        self._rows = []
        self._checked_items.clear()

        # Mount new rows with new unique IDs
        for i, item in enumerate(items):
            row = ItemRow(item, id=self._make_row_id(i, item))
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
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1

    def action_select(self) -> None:
        if self.items:
            self.post_message(self.ItemSelected(self.items[self.selected_index]))

    def action_toggle(self) -> None:
        """Toggle the checked state of the current item."""
        if not self.items or not self._rows:
            return
        row = self._rows[self.selected_index]
        item = self.items[self.selected_index]
        # Toggle the checked state
        new_checked = not row.checked
        row.checked = new_checked
        # Track in set
        if new_checked:
            self._checked_items.add(item.unique_id)
        else:
            self._checked_items.discard(item.unique_id)
        self.post_message(self.ItemToggled(item, new_checked))

    def get_checked_items(self) -> list[DisplayItem]:
        """Get all currently checked items."""
        return [item for item in self.items if item.unique_id in self._checked_items]

    def clear_checked(self) -> None:
        """Clear all checked items."""
        for row in self._rows:
            row.checked = False
        self._checked_items.clear()

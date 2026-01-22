"""Item list widget with keyboard navigation using DataTable virtualization."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from textual import on
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widgets import DataTable

from skill_installer.tui._utils import get_terminal_indicators, sanitize_terminal_text
from skill_installer.tui.models import DisplayItem


class ItemDataTable(DataTable):
    """Virtualized item list using DataTable.

    This replaces the old ItemListView/ItemRow implementation with a
    DataTable-based approach for dramatically improved performance through
    virtualization (rendering only visible rows instead of all items).
    """

    # Column width limits for terminal display
    MAX_NAME_LENGTH = 50
    MAX_SOURCE_LENGTH = 30
    MAX_PLATFORM_LENGTH = 20
    MAX_DESCRIPTION_LENGTH = 60
    MAX_PATH_PREFIX_LENGTH = 30

    DEFAULT_CSS = """
    ItemDataTable {
        height: 1fr;
        border: solid $primary-background;
    }
    ItemDataTable:focus {
        border: solid $accent;
    }
    ItemDataTable > .datatable--header {
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    ItemDataTable > .datatable--cursor {
        background: $accent;
        color: $text;
    }
    ItemDataTable > .datatable--even-row {
        background: $surface;
    }
    ItemDataTable > .datatable--odd-row {
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("enter", "select_cursor", "Select"),
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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.items: list[DisplayItem] = []
        self._checked: set[str] = set()
        self._is_filtering = False  # Mutex flag for race condition protection
        self.cursor_type = "row"
        self.zebra_stripes = True
        self._indicators = get_terminal_indicators()

    def on_mount(self) -> None:
        """Initialize table columns on mount."""
        self.add_columns("", "Name \u2022 Source", "Status", "Description")

    def set_items(self, items: list[DisplayItem]) -> None:
        """Replace all items (same API as old ItemListView).

        Preserves checked state across item updates.
        Sets _is_filtering to prevent toggle race conditions.
        """
        self._is_filtering = True
        try:
            # Preserve checked state before clearing
            checked_ids = self._checked.copy()

            self.clear()
            self.items = items

            # Bulk add rows for performance
            for item in items:
                indicator = self._get_indicator(item, checked_ids)

                # Sanitize external data (CRITICAL-001)
                name = sanitize_terminal_text(item.name, max_length=self.MAX_NAME_LENGTH)
                source = sanitize_terminal_text(item.source_name, max_length=self.MAX_SOURCE_LENGTH)
                name_source = f"{name} \u2022 {source}"

                # Sanitize platform names from external data
                status = (
                    f"[{', '.join(sanitize_terminal_text(p, max_length=self.MAX_PLATFORM_LENGTH) for p in item.installed_platforms)}]"
                    if item.installed_platforms
                    else ""
                )

                # Build description with path prefix (sanitize path from external data)
                description = sanitize_terminal_text(
                    item.description or "No description",
                    max_length=self.MAX_DESCRIPTION_LENGTH,
                )
                path_prefix = ""
                if item.relative_path:
                    parent = str(PurePosixPath(item.relative_path).parent)
                    if parent and parent != ".":
                        path_prefix = f"[{sanitize_terminal_text(parent, max_length=self.MAX_PATH_PREFIX_LENGTH)}] "
                desc = path_prefix + description
                if len(desc) > self.MAX_DESCRIPTION_LENGTH:
                    desc = desc[: self.MAX_DESCRIPTION_LENGTH - 3] + "..."

                self.add_row(indicator, name_source, status, desc, key=item.unique_id)

            # Restore checked state
            self._checked = checked_ids
            self._sync_checked_state_with_display()
        finally:
            self._is_filtering = False

    def _get_indicator(self, item: DisplayItem, checked_set: set[str] | None = None) -> str:
        """Get the indicator for an item."""
        check_set = checked_set if checked_set is not None else self._checked
        if item.unique_id in check_set:
            return self._indicators["checked"]
        if item.installed_platforms:
            return self._indicators["installed"]
        return self._indicators["unchecked"]

    def _sync_checked_state_with_display(self) -> None:
        """Synchronize checked indicators with _checked set."""
        for idx, item in enumerate(self.items):
            if item.unique_id in self._checked:
                coord = Coordinate(idx, 0)
                if coord.row < self.row_count:
                    self.update_cell_at(coord, self._indicators["checked"])

    def get_checked_items(self) -> list[DisplayItem]:
        """Get all currently checked items."""
        return [item for item in self.items if item.unique_id in self._checked]

    def clear_checked(self) -> None:
        """Clear all checked items."""
        self._checked.clear()
        for idx, item in enumerate(self.items):
            coord = Coordinate(idx, 0)
            if coord.row < self.row_count:
                indicator = self._get_indicator(item)
                self.update_cell_at(coord, indicator)

    def action_toggle(self) -> None:
        """Toggle the checked state of the current row."""
        # Race condition protection
        if self._is_filtering:
            return

        if not self.items or self.cursor_row is None:
            return

        row_idx = self.cursor_row
        if row_idx >= len(self.items):
            return

        item = self.items[row_idx]
        unique_id = item.unique_id

        # Toggle state
        if unique_id in self._checked:
            self._checked.discard(unique_id)
            new_checked = False
        else:
            self._checked.add(unique_id)
            new_checked = True

        # Update indicator
        coord = Coordinate(row_idx, 0)
        indicator = self._get_indicator(item)
        self.update_cell_at(coord, indicator)

        # Post message
        self.post_message(self.ItemToggled(item, new_checked))

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        row_key = event.row_key
        if row_key is None:
            return

        # Find item by row key (use row_key, not cursor_row per plan correction)
        item = next(
            (item for item in self.items if item.unique_id == str(row_key.value)),
            None,
        )
        if item:
            self.post_message(self.ItemSelected(item))


# Backwards compatibility alias
ItemListView = ItemDataTable

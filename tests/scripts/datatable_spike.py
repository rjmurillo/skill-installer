#!/usr/bin/env python3
"""DataTable validation spike - Phase 0 of migration plan.

This prototype validates:
1. Rich Text rendering in cells (colored indicators)
2. Row selection/cursor events work
3. Dynamic row add/remove performance
4. Render time vs. ItemListView baseline
5. Keyboard navigation (j/k/up/down/Enter/Space)
6. Multi-line cell content handling

Decision Gate: If >5s render time OR missing features, STOP migration.
Target: 500 rows render in <1s
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widgets import DataTable, Footer, Header, Static


@dataclass
class MockDisplayItem:
    """Mock item for validation testing."""

    name: str
    item_type: str
    description: str
    source_name: str
    platforms: list[str]
    installed_platforms: list[str]
    relative_path: str = ""

    @property
    def unique_id(self) -> str:
        return f"{self.source_name}/{self.item_type}/{self.name}"


class ItemDataTable(DataTable):
    """Prototype DataTable with ItemListView API compatibility."""

    BINDINGS = [
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("space", "toggle", "Toggle"),
        Binding("enter", "select", "Select"),
    ]

    class ItemSelected(Message):
        """Posted when an item is selected (Enter key)."""

        def __init__(self, item: MockDisplayItem) -> None:
            super().__init__()
            self.item = item

    class ItemToggled(Message):
        """Posted when an item is toggled (Space key)."""

        def __init__(self, item: MockDisplayItem, checked: bool) -> None:
            super().__init__()
            self.item = item
            self.checked = checked

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.items: list[MockDisplayItem] = []
        self._checked: set[str] = set()
        self.cursor_type = "row"
        self.zebra_stripes = True
        self._indicators = self._get_terminal_indicators()

    def _get_terminal_indicators(self) -> dict[str, str]:
        """Detect UTF-8 support and return appropriate indicators."""
        import locale
        import sys

        try:
            encoding = getattr(sys.stdout, "encoding", None) or locale.getpreferredencoding()
        except (AttributeError, TypeError):
            encoding = "utf-8"  # Default to UTF-8 if detection fails
        supports_utf8 = encoding.lower() in ("utf-8", "utf8")

        if supports_utf8:
            return {
                "checked": "\u25c9",  # ◉
                "installed": "\u25cf",  # ●
                "unchecked": "\u25cb",  # ○
            }
        return {
            "checked": "[x]",
            "installed": "[*]",
            "unchecked": "[ ]",
        }

    def on_mount(self) -> None:
        """Initialize table columns on mount."""
        self.add_columns("", "Name \u2022 Source", "Status", "Description")

    def set_items(self, items: list[MockDisplayItem]) -> None:
        """Replace all items (same API as ItemListView)."""
        # Preserve checked state before clearing
        checked_ids = self._checked.copy()

        self.clear()
        self.items = items

        # Bulk add rows for performance
        rows = []
        for item in items:
            indicator = self._get_indicator(item, checked_ids)
            name_source = f"{item.name} \u2022 {item.source_name}"
            status = f"[{', '.join(item.installed_platforms)}]" if item.installed_platforms else ""
            desc = (item.description or "No description")[:60]
            rows.append((indicator, name_source, status, desc))

        # Single bulk operation
        for idx, row in enumerate(rows):
            self.add_row(*row, key=items[idx].unique_id)

        # Restore checked state
        self._checked = checked_ids
        self._sync_checked_state_with_display()

    def _get_indicator(self, item: MockDisplayItem, checked_set: set[str] | None = None) -> str:
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

    def get_checked_items(self) -> list[MockDisplayItem]:
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

        # Find item by row key
        item = next(
            (item for item in self.items if item.unique_id == str(row_key.value)),
            None,
        )
        if item:
            self.post_message(self.ItemSelected(item))


class SpikeApp(App):
    """Validation spike app."""

    CSS = """
    ItemDataTable {
        height: 1fr;
        border: solid $primary-background;
    }
    ItemDataTable:focus {
        border: solid $accent;
    }
    #status {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $primary-background;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear_check", "Clear Checks"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.start_time = time.time()
        self.render_time: float | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ItemDataTable(id="items")
        yield Static("Loading...", id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Load test data on mount."""
        # Generate 501 mock items (matching real workload)
        items = []
        sources = ["awesome-prompts", "copilot-skills", "claude-agents", "local"]
        types = ["skill", "agent", "prompt"]

        for i in range(501):
            source = sources[i % len(sources)]
            item_type = types[i % len(types)]
            installed = i < 10  # First 10 are installed

            items.append(
                MockDisplayItem(
                    name=f"skill-{i:03d}",
                    item_type=item_type,
                    description=f"Description for skill {i}. This is a longer description to test truncation behavior in the table.",
                    source_name=source,
                    platforms=["claude", "copilot"],
                    installed_platforms=["claude"] if installed else [],
                    relative_path=f"skills/{item_type}/{source}/skill-{i:03d}",
                )
            )

        # Measure set_items time
        table = self.query_one("#items", ItemDataTable)
        set_start = time.time()
        table.set_items(items)
        set_time = time.time() - set_start

        # Record render time
        self.render_time = time.time() - self.start_time

        # Update status
        status = self.query_one("#status", Static)
        status.update(
            f"Loaded {len(items)} items in {set_time:.3f}s | "
            f"Total startup: {self.render_time:.3f}s | "
            f"Checked: {len(table.get_checked_items())}"
        )

    @on(ItemDataTable.ItemSelected)
    def on_item_selected(self, event: ItemDataTable.ItemSelected) -> None:
        status = self.query_one("#status", Static)
        status.update(f"Selected: {event.item.name} ({event.item.source_name})")

    @on(ItemDataTable.ItemToggled)
    def on_item_toggled(self, event: ItemDataTable.ItemToggled) -> None:
        table = self.query_one("#items", ItemDataTable)
        status = self.query_one("#status", Static)
        status.update(
            f"Toggled: {event.item.name} -> {'checked' if event.checked else 'unchecked'} | "
            f"Total checked: {len(table.get_checked_items())}"
        )

    def action_refresh(self) -> None:
        """Refresh the data to test re-rendering."""
        table = self.query_one("#items", ItemDataTable)
        items = table.items.copy()
        start = time.time()
        table.set_items(items)
        elapsed = time.time() - start

        status = self.query_one("#status", Static)
        status.update(f"Refreshed {len(items)} items in {elapsed:.3f}s")

    def action_clear_check(self) -> None:
        """Clear all checked items."""
        table = self.query_one("#items", ItemDataTable)
        table.clear_checked()
        status = self.query_one("#status", Static)
        status.update("Cleared all checked items")


def run_headless_benchmark() -> dict:
    """Run headless benchmark for CI validation."""
    import locale
    import sys

    print("DataTable Validation Spike - Headless Benchmark")
    print("=" * 60)

    # Generate test data
    items = []
    sources = ["awesome-prompts", "copilot-skills", "claude-agents", "local"]
    types = ["skill", "agent", "prompt"]

    for i in range(501):
        source = sources[i % len(sources)]
        item_type = types[i % len(types)]
        installed = i < 10

        items.append(
            MockDisplayItem(
                name=f"skill-{i:03d}",
                item_type=item_type,
                description=f"Description for skill {i}.",
                source_name=source,
                platforms=["claude", "copilot"],
                installed_platforms=["claude"] if installed else [],
            )
        )

    # Test indicator detection
    encoding = sys.stdout.encoding or locale.getpreferredencoding()
    print(f"Terminal encoding: {encoding}")

    # Instantiate table directly (not mounted)
    table = ItemDataTable()
    table._indicators = table._get_terminal_indicators()

    print(f"Indicators: {table._indicators}")

    # Measure bulk operations
    start = time.time()
    table.items = items
    rows = []
    for item in items:
        indicator = table._get_indicator(item)
        name_source = f"{item.name} * {item.source_name}"
        status = f"[{', '.join(item.installed_platforms)}]" if item.installed_platforms else ""
        desc = (item.description or "No description")[:60]
        rows.append((indicator, name_source, status, desc))
    row_prep_time = time.time() - start

    print(f"Row preparation (501 items): {row_prep_time:.4f}s")

    # Test checked state
    table._checked.add(items[0].unique_id)
    table._checked.add(items[5].unique_id)
    checked = [item for item in items if item.unique_id in table._checked]
    print(f"Checked items: {len(checked)}")

    # Test indicator logic
    assert table._get_indicator(items[0]) == table._indicators["checked"]
    assert table._get_indicator(items[10]) == table._indicators["unchecked"]
    assert table._get_indicator(items[5]) == table._indicators["checked"]
    print("Indicator logic: PASS")

    results = {
        "items": len(items),
        "row_prep_time": row_prep_time,
        "checked_count": len(checked),
        "encoding": encoding,
        "pass": row_prep_time < 1.0,
    }

    print("=" * 60)
    print(f"RESULT: {'PASS' if results['pass'] else 'FAIL'}")
    print(f"Row prep time: {row_prep_time:.4f}s (target: <1s)")

    return results


if __name__ == "__main__":
    import sys

    if "--headless" in sys.argv:
        results = run_headless_benchmark()
        sys.exit(0 if results["pass"] else 1)
    else:
        app = SpikeApp()
        app.run()

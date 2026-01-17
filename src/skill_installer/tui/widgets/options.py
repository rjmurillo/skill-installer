"""Option widgets for detail screens."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class ItemDetailOption(Widget):
    """A single option in the item detail view."""

    DEFAULT_CSS = """
    ItemDetailOption {
        height: 3;
        padding: 0 2;
    }
    ItemDetailOption.selected {
        background: $accent;
    }
    ItemDetailOption .option-indicator {
        width: 3;
        color: $text-muted;
    }
    ItemDetailOption .option-label {
        color: $text;
    }
    """

    selected = reactive(False)

    def __init__(self, label: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.label = label
        self._indicator: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            self._indicator = Static(" ", classes="option-indicator")
            yield self._indicator
            yield Static(self.label, classes="option-label")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")
        if self._indicator:
            self._indicator.update(">" if selected else " ")


class LocationOption(Widget):
    """A single platform location option with checkbox."""

    DEFAULT_CSS = """
    LocationOption {
        height: 3;
        padding: 0 2;
    }
    LocationOption.selected {
        background: $accent;
    }
    LocationOption.checked {
        text-style: bold;
    }
    LocationOption .option-indicator {
        width: 3;
        color: $text-muted;
    }
    LocationOption .option-checkbox {
        width: 5;
        color: $text-muted;
    }
    LocationOption .option-name {
        color: $text;
        width: 25;
    }
    LocationOption .option-path {
        color: $text-muted;
    }
    """

    selected = reactive(False)
    checked = reactive(False)

    def __init__(self, platform_id: str, name: str, path: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.platform_id = platform_id
        self.platform_name = name
        self.path = path
        self._indicator: Static | None = None
        self._checkbox: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            self._indicator = Static(" ", classes="option-indicator")
            yield self._indicator
            self._checkbox = Static("[ ]", classes="option-checkbox")
            yield self._checkbox
            yield Static(self.platform_name, classes="option-name")
            yield Static(self.path, classes="option-path")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")
        if self._indicator:
            self._indicator.update(">" if selected else " ")

    def watch_checked(self, checked: bool) -> None:
        self.set_class(checked, "checked")
        if self._checkbox:
            self._checkbox.update("[X]" if checked else "[ ]")

    def toggle_checked(self) -> None:
        self.checked = not self.checked


class SourceDetailOption(Widget):
    """A single option in the source detail view."""

    DEFAULT_CSS = """
    SourceDetailOption {
        height: 3;
        padding: 0 2;
    }
    SourceDetailOption.selected {
        background: $accent;
    }
    SourceDetailOption .option-indicator {
        width: 3;
        color: $text-muted;
    }
    SourceDetailOption .option-label {
        color: $text;
    }
    SourceDetailOption .option-meta {
        color: $text-muted;
    }
    """

    selected = reactive(False)

    def __init__(self, label: str, meta: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.label = label
        self.meta = meta
        self._indicator: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            self._indicator = Static(" ", classes="option-indicator")
            yield self._indicator
            yield Static(self.label, classes="option-label")
            if self.meta:
                yield Static(f" ({self.meta})", classes="option-meta")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")
        if self._indicator:
            self._indicator.update(">" if selected else " ")

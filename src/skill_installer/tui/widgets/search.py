"""Search input widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label


class SearchInput(Horizontal):
    """Search input with magnifying glass icon."""

    DEFAULT_CSS = """
    SearchInput {
        height: 3;
        padding: 0 1;
        background: $surface;
        border: solid $primary-background;
    }
    SearchInput Label {
        width: 3;
        padding: 0 1;
        color: $text-muted;
    }
    SearchInput Input {
        border: none;
        background: transparent;
        width: 1fr;
    }
    SearchInput Input:focus {
        border: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("\U0001f50d")
        yield Input(placeholder="Search...")

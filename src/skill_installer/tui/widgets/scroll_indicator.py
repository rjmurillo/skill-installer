"""Scroll indicator widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static


class ScrollIndicator(Static):
    """Scroll indicator showing position."""

    DEFAULT_CSS = """
    ScrollIndicator {
        height: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._total = 0
        self._visible = 0
        self._position = 0

    def update_position(self, position: int, visible: int, total: int) -> None:
        self._position = position
        self._visible = visible
        self._total = total
        self._update_text()

    def _update_text(self) -> None:
        if self._total <= self._visible:
            self.update("")
            return

        text_parts = []
        if self._position > 0:
            text_parts.append("\u2191 more above")
        if self._position + self._visible < self._total:
            text_parts.append("\u2193 more below")

        self.update(" | ".join(text_parts))

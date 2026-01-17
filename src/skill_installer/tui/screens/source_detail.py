"""Source detail modal screen."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static

from skill_installer.tui.models import DisplaySource
from skill_installer.tui.widgets.options import SourceDetailOption


class SourceDetailScreen(ModalScreen[tuple[str, DisplaySource] | None]):
    """Modal screen for viewing source details."""

    DEFAULT_CSS = """
    SourceDetailScreen {
        align: center middle;
    }
    SourceDetailScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 80%;
        height: auto;
        max-height: 80%;
        padding: 1 2;
    }
    SourceDetailScreen #detail-header {
        height: auto;
        padding: 1 2;
        background: $primary-background;
    }
    SourceDetailScreen #detail-name {
        text-style: bold;
        color: $secondary;
    }
    SourceDetailScreen #detail-url {
        color: $text-muted;
    }
    SourceDetailScreen #detail-stats {
        color: $text;
        padding: 1 0;
    }
    SourceDetailScreen #detail-options {
        height: auto;
        padding: 1 0;
    }
    SourceDetailScreen #detail-footer {
        height: 3;
        padding: 1 2;
        background: $primary-background;
        color: $text-muted;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("enter", "select_option", "Select"),
        Binding("escape", "cancel", "Close"),
    ]

    selected_index = reactive(0)

    def __init__(self, source: DisplaySource, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = source
        self._options: list[tuple[str, str, str]] = []
        self._option_widgets: list[SourceDetailOption] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Vertical(id="detail-header"):
                yield Static(self.source.display_name, id="detail-name")
                yield Static(self.source.url, id="detail-url")
                yield Static("", id="detail-stats")
            with Vertical(id="detail-options"):
                pass  # Options will be added dynamically
            yield Static("Enter to select, Escape to go back", id="detail-footer")

    def on_mount(self) -> None:
        """Populate options when mounted."""
        source = self.source

        # Pluralize "plugins" vs "plugin"
        plugin_word = "plugins" if source.available_count != 1 else "plugin"
        stats_text = f"{source.available_count} available {plugin_word}"
        self.query_one("#detail-stats", Static).update(stats_text)

        # Determine auto-update label based on current state
        raw_source = source.raw_data
        auto_update_enabled = getattr(raw_source, "auto_update", False) if raw_source else False
        auto_update_label = "Disable auto-update" if auto_update_enabled else "Enable auto-update"

        # Build options
        self._options = [
            ("browse", f"Browse {plugin_word} ({source.available_count})", ""),
            ("update", f"Update marketplace (last updated {source.last_sync})", ""),
            ("auto_update", auto_update_label, ""),
            ("remove", "Remove marketplace", ""),
            ("back", "Back to list", ""),
        ]

        # Add option widgets
        options_container = self.query_one("#detail-options", Vertical)
        for i, (option_id, label, meta) in enumerate(self._options):
            option = SourceDetailOption(label, meta, id=f"option-{option_id}")
            option.selected = i == 0
            self._option_widgets.append(option)
            options_container.mount(option)

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if 0 <= old_index < len(self._option_widgets):
            self._option_widgets[old_index].selected = False
        if 0 <= new_index < len(self._option_widgets):
            self._option_widgets[new_index].selected = True
            self._option_widgets[new_index].scroll_visible()

    def action_cursor_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_cursor_down(self) -> None:
        if self.selected_index < len(self._options) - 1:
            self.selected_index += 1

    def action_select_option(self) -> None:
        """Select the current option."""
        if 0 <= self.selected_index < len(self._options):
            option_id = self._options[self.selected_index][0]
            if option_id == "back":
                self.dismiss(None)
            else:
                self.dismiss((option_id, self.source))

    def action_cancel(self) -> None:
        """Close the screen."""
        self.dismiss(None)

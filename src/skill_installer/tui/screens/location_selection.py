"""Location selection modal screen."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static

from skill_installer.tui.models import DisplayItem
from skill_installer.tui.widgets.options import LocationOption


class LocationSelectionScreen(ModalScreen[tuple[list[str], DisplayItem] | None]):
    """Modal screen for selecting installation locations."""

    DEFAULT_CSS = """
    LocationSelectionScreen {
        align: center middle;
    }
    LocationSelectionScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 80%;
        height: auto;
        max-height: 80%;
        padding: 1 2;
    }
    LocationSelectionScreen #location-header {
        height: auto;
        padding: 1 2;
        background: $primary-background;
    }
    LocationSelectionScreen #location-title {
        text-style: bold;
        color: $text;
        padding: 0 0 1 0;
    }
    LocationSelectionScreen #location-subtitle {
        color: $text-muted;
        padding: 0 0 1 0;
    }
    LocationSelectionScreen #location-options {
        height: auto;
        padding: 1 0;
    }
    LocationSelectionScreen #location-actions {
        height: auto;
        padding: 1 2;
        background: $primary-background;
    }
    LocationSelectionScreen #location-footer {
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
        Binding("space", "toggle_selection", "Toggle", show=False),
        Binding("enter", "confirm", "Install"),
        Binding("escape", "cancel", "Cancel"),
    ]

    selected_index = reactive(0)

    def __init__(
        self,
        item: DisplayItem,
        available_platforms: list[dict[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.available_platforms = available_platforms
        self._location_options: list[LocationOption] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Vertical(id="location-header"):
                yield Static("Select installation locations", id="location-title")
                yield Static(f"Choose where to install '{self.item.name}'", id="location-subtitle")
            with Vertical(id="location-options"):
                pass  # Options will be added dynamically
            with Vertical(id="location-actions"):
                yield Static("", id="location-action-hint")
            yield Static(
                "Press SPACE to toggle, ENTER to install, ESC to cancel", id="location-footer"
            )

    def on_mount(self) -> None:
        """Populate location options when mounted."""
        options_container = self.query_one("#location-options", Vertical)

        for i, platform_info in enumerate(self.available_platforms):
            option = LocationOption(
                platform_id=platform_info["id"],
                name=platform_info["name"],
                path=platform_info["path_description"],
                id=f"location-option-{platform_info['id']}",
            )
            option.selected = i == 0
            option.checked = False
            self._location_options.append(option)
            options_container.mount(option)

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if 0 <= old_index < len(self._location_options):
            self._location_options[old_index].selected = False
        if 0 <= new_index < len(self._location_options):
            self._location_options[new_index].selected = True
            self._location_options[new_index].scroll_visible()

    def action_cursor_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_cursor_down(self) -> None:
        if self.selected_index < len(self._location_options) - 1:
            self.selected_index += 1

    def action_toggle_selection(self) -> None:
        """Toggle checkbox for current option."""
        if 0 <= self.selected_index < len(self._location_options):
            self._location_options[self.selected_index].toggle_checked()

    def action_confirm(self) -> None:
        """Confirm selection and install."""
        checked_platforms = [opt.platform_id for opt in self._location_options if opt.checked]

        if not checked_platforms:
            self.query_one("#location-action-hint", Static).update(
                "⚠ Please select at least one location"
            )
            return

        self.dismiss((checked_platforms, self.item))

    def action_cancel(self) -> None:
        """Cancel location selection."""
        self.dismiss(None)

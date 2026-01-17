"""Installed item detail modal screen."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static

from skill_installer.tui.models import DisplayItem
from skill_installer.tui.widgets.options import ItemDetailOption


class InstalledItemDetailScreen(ModalScreen[tuple[str, DisplayItem] | None]):
    """Modal screen for viewing installed item details."""

    DEFAULT_CSS = """
    InstalledItemDetailScreen {
        align: center middle;
    }
    InstalledItemDetailScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 80%;
        height: auto;
        max-height: 80%;
        padding: 1 2;
    }
    InstalledItemDetailScreen #installed-detail-header {
        height: auto;
        padding: 1 2;
        background: $primary-background;
    }
    InstalledItemDetailScreen #installed-detail-name {
        text-style: bold;
        color: $text;
        height: auto;
        padding: 0 0 1 0;
    }
    InstalledItemDetailScreen #installed-detail-scope {
        color: $text-muted;
        height: auto;
    }
    InstalledItemDetailScreen #installed-detail-description {
        color: $text;
        padding: 1 0;
        height: auto;
    }
    InstalledItemDetailScreen #installed-detail-author {
        color: $text-muted;
        padding: 0 0 1 0;
        height: auto;
    }
    InstalledItemDetailScreen #installed-detail-components-header {
        text-style: bold;
        color: $text;
        padding: 1 0 0 0;
        height: auto;
    }
    InstalledItemDetailScreen #installed-detail-components {
        color: $text-muted;
        padding: 0 0 1 0;
        height: auto;
    }
    InstalledItemDetailScreen #installed-detail-options {
        height: auto;
        padding: 1 0;
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

    def __init__(
        self,
        item: DisplayItem,
        registry_manager: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.item = item
        self.registry_manager = registry_manager
        self._options: list[tuple[str, str]] = []
        self._option_widgets: list[ItemDetailOption] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Vertical(id="installed-detail-header"):
                yield Static("", id="installed-detail-name")
                yield Static("", id="installed-detail-scope")
                yield Static("", id="installed-detail-description")
                yield Static("", id="installed-detail-author")
                yield Static("Installed components", id="installed-detail-components-header")
                yield Static("", id="installed-detail-components")
            with Vertical(id="installed-detail-options"):
                pass  # Options will be added dynamically

    def on_mount(self) -> None:
        """Populate the screen with item data when mounted."""
        item = self.item

        # Name @ source
        name_text = f"{item.name} @ {item.source_name}"
        self.query_one("#installed-detail-name", Static).update(name_text)

        # Scope - derive from installed platforms
        scope_text = self._get_scope_text()
        self.query_one("#installed-detail-scope", Static).update(f"Scope: {scope_text}")

        # Description
        self.query_one("#installed-detail-description", Static).update(
            item.description or "No description"
        )

        # Author (from frontmatter if available)
        author = ""
        if hasattr(item.raw_data, "frontmatter") and item.raw_data.frontmatter:
            author = item.raw_data.frontmatter.get("author", "")
        if author:
            self.query_one("#installed-detail-author", Static).update(f"Author: {author}")
        else:
            self.query_one("#installed-detail-author", Static).update("")

        # Installed components
        components_text = self._get_components_text()
        self.query_one("#installed-detail-components", Static).update(components_text)

        # Build options
        self._options = [
            ("update", "Update now"),
            ("uninstall", "Uninstall"),
            ("back", "Back to plugin list"),
        ]

        # Add option widgets
        options_container = self.query_one("#installed-detail-options", Vertical)
        for i, (option_id, label) in enumerate(self._options):
            option = ItemDetailOption(label, id=f"installed-option-{option_id}")
            option.selected = i == 0
            self._option_widgets.append(option)
            options_container.mount(option)

    def _get_scope_text(self) -> str:
        """Get the scope text based on installed platforms."""
        if not self.registry_manager:
            return "user"

        # Check if any installed items are project scope
        installed_items = self.registry_manager.list_installed()
        item_id = self.item.unique_id

        scopes = set()
        for installed in installed_items:
            if installed.id == item_id:
                scopes.add(installed.scope)

        if "project" in scopes and "user" in scopes:
            return "user, project"
        elif "project" in scopes:
            return "project"
        return "user"

    def _get_components_text(self) -> str:
        """Get the installed components text."""
        item = self.item
        item_type = item.item_type.capitalize() if item.item_type else "Skill"
        # Show as bullet list
        return f"* {item_type}s: {item.name}"

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
                self.dismiss((option_id, self.item))

    def action_cancel(self) -> None:
        """Close the screen."""
        self.dismiss(None)

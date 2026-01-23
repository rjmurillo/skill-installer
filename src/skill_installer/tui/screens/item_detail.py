"""Item detail modal screen."""

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


class ItemDetailScreen(ModalScreen[tuple[str, DisplayItem] | None]):
    """Modal screen for viewing item details."""

    DEFAULT_CSS = """
    ItemDetailScreen {
        align: center middle;
    }
    ItemDetailScreen > Vertical {
        background: $surface;
        border: thick $primary;
        width: 80%;
        height: 80%;
        padding: 1 2;
    }
    ItemDetailScreen #item-detail-header {
        height: auto;
        padding: 1 2;
        background: $primary-background;
    }
    ItemDetailScreen #item-detail-title {
        text-style: bold;
        color: $text;
        padding: 0 0 1 0;
    }
    ItemDetailScreen #item-detail-name {
        text-style: bold;
        color: $text-muted;
        height: auto;
    }
    ItemDetailScreen #item-detail-source {
        color: $text-muted;
        padding: 0 0 1 0;
    }
    ItemDetailScreen #item-detail-license {
        color: $text-muted;
        padding: 0;
    }
    ItemDetailScreen #item-detail-description {
        color: $text;
        padding: 1 0;
        height: auto;
    }
    ItemDetailScreen #item-detail-author {
        color: $text;
        padding: 1 0;
    }
    ItemDetailScreen #item-detail-warning {
        color: $warning;
        text-style: italic;
        padding: 1 0;
        height: auto;
    }
    ItemDetailScreen #item-detail-options {
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
            with Vertical(id="item-detail-header"):
                yield Static("Plugin details", id="item-detail-title")
                yield Static("", id="item-detail-name")
                yield Static("", id="item-detail-source")
                yield Static("", id="item-detail-license")
                yield Static("", id="item-detail-description")
                yield Static("", id="item-detail-author")
                yield Static(
                    "Make sure you trust a plugin before installing, updating, or using it. See each plugin's homepage for more information.",
                    id="item-detail-warning",
                )
            with Vertical(id="item-detail-options"):
                pass  # Options will be added dynamically

    def on_mount(self) -> None:
        """Populate the screen with item data when mounted."""
        item = self.item

        # Update title based on item type
        title_map = {
            "agent": "Agent details",
            "skill": "Skill details",
            "command": "Command details",
        }
        title = title_map.get(item.item_type, "Plugin details")
        self.query_one("#item-detail-title", Static).update(title)

        # Update header - name and source
        self.query_one("#item-detail-name", Static).update(item.name)
        self.query_one("#item-detail-source", Static).update(f"from {item.source_name}")

        # License (from frontmatter if available, otherwise from repository)
        license_text = ""
        if hasattr(item.raw_data, "frontmatter") and item.raw_data.frontmatter:
            license_text = item.raw_data.frontmatter.get("license", "")

        # Fall back to repository license if frontmatter doesn't have it
        if not license_text and self.registry_manager:
            registry = self.registry_manager.load_sources()
            for source in registry.sources:
                if source.name == item.source_name:
                    license_text = source.license or ""
                    break

        if license_text:
            self.query_one("#item-detail-license", Static).update(f"License: {license_text}")
        else:
            self.query_one("#item-detail-license", Static).update("")

        # Description
        self.query_one("#item-detail-description", Static).update(
            item.description or "No description"
        )

        # Author (from frontmatter if available)
        author = ""
        if hasattr(item.raw_data, "frontmatter") and item.raw_data.frontmatter:
            author = item.raw_data.frontmatter.get("author", "")
        if author:
            self.query_one("#item-detail-author", Static).update(f"By: {author}")
        else:
            self.query_one("#item-detail-author", Static).update("")

        # Build options
        self._options = []
        if item.installed_platforms:
            self._options.append(("uninstall", "Uninstall"))
        else:
            self._options.append(("install_user", "Install for you (user scope)"))
            self._options.append(
                (
                    "install_project",
                    "Install for all collaborators on a git repository (project scope)",
                )
            )

        # Homepage option (from frontmatter or source URL)
        homepage = ""
        if hasattr(item.raw_data, "frontmatter") and item.raw_data.frontmatter:
            homepage = item.raw_data.frontmatter.get(
                "homepage", ""
            ) or item.raw_data.frontmatter.get("url", "")
        # Fall back to source URL if no homepage in frontmatter
        if not homepage and item.source_url:
            homepage = item.source_url
        if homepage:
            self._options.append(("open_homepage", "Open homepage"))

        self._options.append(("back", "Back to list"))

        # Add option widgets
        options_container = self.query_one("#item-detail-options", Vertical)
        for i, (option_id, label) in enumerate(self._options):
            option = ItemDetailOption(label, id=f"item-option-{option_id}")
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
                self.dismiss((option_id, self.item))

    def action_cancel(self) -> None:
        """Close the screen."""
        self.dismiss(None)

"""Rich TUI components for interactive installation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rich.console import Console


def _sanitize_css_id(value: str) -> str:
    """Sanitize a string for use as a CSS ID.

    CSS IDs can only contain letters, numbers, underscores, or hyphens,
    and must not begin with a number.

    Args:
        value: The string to sanitize.

    Returns:
        A valid CSS ID string.
    """
    # Replace common separators with hyphens
    sanitized = value.replace("/", "--").replace(" ", "-")
    # Remove any remaining invalid characters
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", sanitized)
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"id-{sanitized}"
    return sanitized or "item"


from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Input, Label, Static, TabbedContent, TabPane

if TYPE_CHECKING:
    from skill_installer.discovery import DiscoveredItem
    from skill_installer.registry import InstalledItem, Source

console = Console()


# =============================================================================
# Data Types for TUI
# =============================================================================


@dataclass
class DisplayItem:
    """Generic item for display in the TUI."""

    name: str
    item_type: str
    description: str
    source_name: str
    platforms: list[str]
    installed_platforms: list[str]
    raw_data: Any

    @property
    def unique_id(self) -> str:
        """Generate a unique ID for this item (source/type/name)."""
        return f"{self.source_name}/{self.item_type}/{self.name}"


# =============================================================================
# Custom Widgets
# =============================================================================


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
    ItemRow .item-name {
        color: $secondary;
    }
    ItemRow .item-source {
        color: $text-muted;
    }
    ItemRow .item-description {
        color: $text;
    }
    ItemRow .item-status {
        color: $success;
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

        with Horizontal():
            self._indicator = Static(indicator, classes="item-indicator")
            yield self._indicator
            with Vertical():
                with Horizontal():
                    yield Static(self.item.name, classes="item-name")
                    yield Static(f" ({self.item.source_name})", classes="item-source")
                    yield Static(f" {status}", classes="item-status")
                yield Static(self.item.description or "No description", classes="item-description")

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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.items: list[DisplayItem] = []
        self._rows: list[ItemRow] = []
        self._checked_items: set[str] = set()  # Track checked items by unique_id

    def _make_row_id(self, index: int, item: DisplayItem) -> str:
        """Create a unique row ID using list ID prefix and item unique ID."""
        sanitized = _sanitize_css_id(item.unique_id)
        # Include list ID prefix and index to handle duplicates within same list
        return f"{self.id}--{index}--{sanitized}"

    def compose(self) -> ComposeResult:
        for i, item in enumerate(self.items):
            row = ItemRow(item, id=self._make_row_id(i, item))
            row.selected = i == self.selected_index
            self._rows.append(row)
            yield row

    def set_items(self, items: list[DisplayItem]) -> None:
        """Update the list items."""
        self.items = items
        self.selected_index = 0
        self._rows = []
        self.remove_children()
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


class SourceRow(Widget):
    """A source row for the Marketplaces tab."""

    DEFAULT_CSS = """
    SourceRow {
        height: 3;
        padding: 0 2;
    }
    SourceRow.selected {
        background: $accent;
    }
    SourceRow .source-name {
        color: $secondary;
    }
    SourceRow .source-url {
        color: $text-muted;
    }
    SourceRow .source-sync {
        color: $text;
    }
    """

    selected = reactive(False)

    def __init__(self, source: Source, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.source = source

    def compose(self) -> ComposeResult:
        last_sync = self.source.last_sync.strftime("%Y-%m-%d %H:%M") if self.source.last_sync else "Never"

        with Vertical():
            with Horizontal():
                yield Static(self.source.name, classes="source-name")
                yield Static(f" - {self.source.url}", classes="source-url")
            yield Static(f"Last sync: {last_sync} | Platforms: {', '.join(self.source.platforms)}", classes="source-sync")

    def watch_selected(self, selected: bool) -> None:
        self.set_class(selected, "selected")


class SourceListView(VerticalScroll):
    """List view for sources (marketplaces)."""

    DEFAULT_CSS = """
    SourceListView {
        height: 1fr;
        border: solid $primary-background;
    }
    SourceListView:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
    ]

    class SourceSelected(Message):
        """Posted when a source is selected."""

        def __init__(self, source: Source) -> None:
            super().__init__()
            self.source = source

    selected_index = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sources: list[Source] = []
        self._rows: list[SourceRow] = []

    def _make_row_id(self, index: int, source: Source) -> str:
        """Create a unique row ID using list ID prefix and source name."""
        sanitized = _sanitize_css_id(source.name)
        return f"{self.id}--{index}--{sanitized}"

    def set_sources(self, sources: list[Source]) -> None:
        """Update the sources list."""
        self.sources = sources
        self.selected_index = 0
        self._rows = []
        self.remove_children()
        for i, source in enumerate(sources):
            row = SourceRow(source, id=self._make_row_id(i, source))
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
        if self.selected_index < len(self.sources) - 1:
            self.selected_index += 1

    def action_select(self) -> None:
        if self.sources:
            self.post_message(self.SourceSelected(self.sources[self.selected_index]))


# =============================================================================
# Tab Panes
# =============================================================================


class DiscoverPane(Container):
    """Discover tab - browse available skills/agents from all sources."""

    DEFAULT_CSS = """
    DiscoverPane {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._all_items: list[DisplayItem] = []
        self._search_query = ""

    def compose(self) -> ComposeResult:
        yield SearchInput(id="discover-search")
        yield ItemListView(id="discover-list")
        yield ScrollIndicator(id="discover-scroll-indicator")

    def set_items(self, items: list[DisplayItem]) -> None:
        """Set the items to display."""
        self._all_items = items
        self._filter_items()

    def _filter_items(self) -> None:
        """Filter items based on search query."""
        query = self._search_query.lower()
        if query:
            filtered = [
                item for item in self._all_items
                if query in item.name.lower()
                or query in item.description.lower()
                or query in item.source_name.lower()
                or query in item.item_type.lower()
            ]
        else:
            filtered = self._all_items

        list_view = self.query_one("#discover-list", ItemListView)
        list_view.set_items(filtered)

    @on(Input.Changed, "#discover-search Input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._search_query = event.value
        self._filter_items()


class InstalledPane(Container):
    """Installed tab - view installed items."""

    DEFAULT_CSS = """
    InstalledPane {
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._all_items: list[DisplayItem] = []
        self._search_query = ""

    def compose(self) -> ComposeResult:
        yield SearchInput(id="installed-search")
        yield ItemListView(id="installed-list")
        yield ScrollIndicator(id="installed-scroll-indicator")

    def set_items(self, items: list[DisplayItem]) -> None:
        """Set the items to display."""
        self._all_items = items
        self._filter_items()

    def _filter_items(self) -> None:
        """Filter items based on search query."""
        query = self._search_query.lower()
        if query:
            filtered = [
                item for item in self._all_items
                if query in item.name.lower()
                or query in item.description.lower()
                or query in item.source_name.lower()
            ]
        else:
            filtered = self._all_items

        list_view = self.query_one("#installed-list", ItemListView)
        list_view.set_items(filtered)

    @on(Input.Changed, "#installed-search Input")
    def on_search_changed(self, event: Input.Changed) -> None:
        self._search_query = event.value
        self._filter_items()


class MarketplacesPane(Container):
    """Marketplaces tab - manage sources."""

    DEFAULT_CSS = """
    MarketplacesPane {
        height: 1fr;
    }
    MarketplacesPane #marketplaces-header {
        height: 3;
        padding: 1 2;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Configured source repositories:", id="marketplaces-header")
        yield SourceListView(id="marketplaces-list")

    def set_sources(self, sources: list[Source]) -> None:
        """Set the sources to display."""
        list_view = self.query_one("#marketplaces-list", SourceListView)
        list_view.set_sources(sources)


# =============================================================================
# Main Application
# =============================================================================


class SkillInstallerApp(App):
    """Skill Installer TUI Application."""

    TITLE = "Skill Installer"

    CSS = """
    Screen {
        background: $surface;
    }

    #app-title {
        dock: top;
        height: 3;
        padding: 1 2;
        background: $primary-background;
        text-style: bold;
        color: $text;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
    }

    Footer {
        background: $primary-background;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $primary-background;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "next_tab", "Next Tab"),
        Binding("shift+tab", "prev_tab", "Prev Tab"),
        Binding("left", "prev_tab", "Prev Tab", show=False),
        Binding("right", "next_tab", "Next Tab", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_source", "Add Source"),
        Binding("i", "install", "Install"),
    ]

    def __init__(
        self,
        registry_manager: Any = None,
        gitops: Any = None,
        discovery: Any = None,
        installer: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.registry_manager = registry_manager
        self.gitops = gitops
        self.discovery = discovery
        self.installer = installer

    def compose(self) -> ComposeResult:
        yield Static("Skill Installer", id="app-title")
        with TabbedContent(initial="discover"):
            with TabPane("Discover", id="discover"):
                yield DiscoverPane()
            with TabPane("Installed", id="installed"):
                yield InstalledPane()
            with TabPane("Marketplaces", id="marketplaces"):
                yield MarketplacesPane()
        yield Static("Loading...", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load data when app mounts."""
        self._load_data()

    def _load_data(self) -> None:
        """Load all data from registry."""
        if not self.registry_manager:
            self._update_status("No registry manager configured")
            return

        # Load sources
        sources = self.registry_manager.list_sources()

        # Load installed items
        installed_items = self.registry_manager.list_installed()
        installed_map: dict[str, list[str]] = {}
        for item in installed_items:
            if item.id not in installed_map:
                installed_map[item.id] = []
            installed_map[item.id].append(item.platform)

        # Discover items from all sources
        all_discovered: list[DisplayItem] = []
        installed_display: list[DisplayItem] = []

        for source in sources:
            if self.gitops and self.discovery:
                repo_path = self.gitops.get_repo_path(source.name)
                if repo_path.exists():
                    items = self.discovery.discover_all(repo_path)
                    for item in items:
                        item_id = f"{source.name}/{item.item_type}/{item.name}"
                        platforms_installed = installed_map.get(item_id, [])
                        display_item = DisplayItem(
                            name=item.name,
                            item_type=item.item_type,
                            description=item.description,
                            source_name=source.name,
                            platforms=item.platforms,
                            installed_platforms=platforms_installed,
                            raw_data=item,
                        )
                        all_discovered.append(display_item)

        # Build installed display items
        for item in installed_items:
            display_item = DisplayItem(
                name=item.name,
                item_type=item.item_type,
                description="",
                source_name=item.source,
                platforms=[item.platform],
                installed_platforms=[item.platform],
                raw_data=item,
            )
            installed_display.append(display_item)

        # Update UI
        discover_pane = self.query_one(DiscoverPane)
        discover_pane.set_items(all_discovered)

        installed_pane = self.query_one(InstalledPane)
        installed_pane.set_items(installed_display)

        marketplaces_pane = self.query_one(MarketplacesPane)
        marketplaces_pane.set_sources(sources)

        item_count = len(all_discovered)
        source_count = len(sources)
        installed_count = len(installed_items)
        self._update_status(f"{item_count} items from {source_count} sources | {installed_count} installed")

    def _update_status(self, message: str) -> None:
        """Update status bar."""
        status = self.query_one("#status-bar", Static)
        status.update(message)

    def action_next_tab(self) -> None:
        """Move to next tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.action_next_tab()

    def action_prev_tab(self) -> None:
        """Move to previous tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.action_previous_tab()

    def action_refresh(self) -> None:
        """Refresh data."""
        self._update_status("Refreshing...")
        self._load_data()

    def action_add_source(self) -> None:
        """Show add source dialog."""
        self.notify("Add source: Run 'skill-installer source add <url>' from CLI")

    def action_install(self) -> None:
        """Install checked items, or selected item if none checked."""
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            discover_pane = self.query_one(DiscoverPane)
            list_view = discover_pane.query_one("#discover-list", ItemListView)
            checked_items = list_view.get_checked_items()
            if checked_items:
                # Install all checked items
                for item in checked_items:
                    self._install_item(item)
                list_view.clear_checked()
            elif list_view.items:
                # Install currently selected item
                item = list_view.items[list_view.selected_index]
                self._install_item(item)

    def _install_item(self, item: DisplayItem) -> None:
        """Install an item."""
        if not self.installer:
            self.notify("Installer not configured", severity="error")
            return

        source = self.registry_manager.get_source(item.source_name)
        if not source:
            self.notify(f"Source '{item.source_name}' not found", severity="error")
            return

        for platform in source.platforms:
            result = self.installer.install_item(item.raw_data, item.source_name, platform)
            if result.success:
                self.notify(f"Installed {item.name} to {platform}")
            else:
                self.notify(f"Failed: {result.error}", severity="error")

        self._load_data()

    @on(ItemListView.ItemSelected)
    def on_item_selected(self, event: ItemListView.ItemSelected) -> None:
        """Handle item selection."""
        item = event.item
        self.notify(f"Selected: {item.name} ({item.item_type}) from {item.source_name}")

    @on(ItemListView.ItemToggled)
    def on_item_toggled(self, event: ItemListView.ItemToggled) -> None:
        """Handle item toggle - update status bar with checked count."""
        # Update status bar with count of checked items
        discover_pane = self.query_one(DiscoverPane)
        list_view = discover_pane.query_one("#discover-list", ItemListView)
        checked_count = len(list_view.get_checked_items())
        if checked_count > 0:
            self._update_status(f"{checked_count} item(s) selected for installation")
        else:
            self._load_data()  # Reset status to default

    @on(SourceListView.SourceSelected)
    def on_source_selected(self, event: SourceListView.SourceSelected) -> None:
        """Handle source selection."""
        source = event.source
        self.notify(f"Source: {source.name} - {source.url}")


# =============================================================================
# Legacy TUI Class (for non-interactive CLI output)
# =============================================================================


class TUI:
    """Text User Interface for skill-installer (non-interactive mode)."""

    def __init__(self) -> None:
        """Initialize TUI."""
        self.console = Console()

    def show_welcome(self) -> None:
        """Display welcome banner."""
        self.console.print(
            Panel(
                "[bold blue]Skill Installer[/bold blue] v0.1.0\n"
                "Universal skill/agent installer for AI coding platforms",
                title="Welcome",
                border_style="blue",
            )
        )

    def show_main_menu(self) -> str:
        """Display main menu and get selection.

        Returns:
            Selected option key.
        """
        self.console.print()
        self.console.print("[bold]Main Menu[/bold]")
        self.console.print("  [1] Add Source")
        self.console.print("  [2] Browse & Install")
        self.console.print("  [3] Status")
        self.console.print("  [4] Sync All")
        self.console.print("  [5] Settings")
        self.console.print("  [q] Quit")
        self.console.print()

        choice = Prompt.ask(
            "Select option",
            choices=["1", "2", "3", "4", "5", "q"],
            default="q",
        )
        return choice

    def prompt_source_url(self) -> str:
        """Prompt for source URL.

        Returns:
            Entered URL.
        """
        return Prompt.ask("Enter repository URL")

    def prompt_source_name(self, default: str) -> str:
        """Prompt for source name.

        Args:
            default: Default name derived from URL.

        Returns:
            Entered or default name.
        """
        return Prompt.ask("Source name", default=default)

    def prompt_source_ref(self) -> str:
        """Prompt for branch/tag reference.

        Returns:
            Entered reference.
        """
        return Prompt.ask("Branch/tag", default="main")

    def prompt_platforms(self) -> list[str]:
        """Prompt for target platforms.

        Returns:
            List of selected platforms.
        """
        platforms_str = Prompt.ask(
            "Target platforms (comma-separated)",
            default="claude,vscode",
        )
        return [p.strip() for p in platforms_str.split(",")]

    def confirm(self, message: str, default: bool = True) -> bool:
        """Show confirmation prompt.

        Args:
            message: Confirmation message.
            default: Default response.

        Returns:
            User's response.
        """
        return Confirm.ask(message, default=default)

    def show_sources(self, sources: list[Source]) -> None:
        """Display sources table.

        Args:
            sources: List of Source objects.
        """
        if not sources:
            self.console.print("[yellow]No sources configured[/yellow]")
            return

        table = Table(title="Configured Sources")
        table.add_column("Name", style="cyan")
        table.add_column("URL")
        table.add_column("Branch")
        table.add_column("Platforms")
        table.add_column("Last Sync")

        for source in sources:
            platforms = ", ".join(source.platforms)
            last_sync = source.last_sync.isoformat() if source.last_sync else "Never"
            table.add_row(
                source.name,
                source.url,
                source.ref,
                platforms,
                last_sync,
            )

        self.console.print(table)

    def show_items(
        self,
        items: list[DiscoveredItem],
        installed: dict[str, list[str]],
        source_name: str,
    ) -> None:
        """Display discovered items.

        Args:
            items: List of discovered items.
            installed: Dict mapping item IDs to installed platforms.
            source_name: Name of the source.
        """
        if not items:
            self.console.print(f"[yellow]No items found in {source_name}[/yellow]")
            return

        # Group by type
        agents = [i for i in items if i.item_type == "agent"]
        skills = [i for i in items if i.item_type == "skill"]
        commands = [i for i in items if i.item_type == "command"]

        self.console.print(f"\n[bold]Source: {source_name}[/bold]")

        for group_name, group_items in [
            ("AGENTS", agents),
            ("SKILLS", skills),
            ("COMMANDS", commands),
        ]:
            if group_items:
                self.console.print(f"\n[bold]{group_name}[/bold]")
                for item in group_items:
                    item_id = f"{source_name}/{item.item_type}/{item.name}"
                    platforms_installed = installed.get(item_id, [])

                    if platforms_installed:
                        status = f"[green]\u2713 {', '.join(platforms_installed)}[/green]"
                    else:
                        status = "[dim]\u25cb not installed[/dim]"

                    desc = f" - {item.description}" if item.description else ""
                    self.console.print(f"  {item.name}{desc} {status}")

    def show_installed(self, items: list[InstalledItem]) -> None:
        """Display installed items table.

        Args:
            items: List of installed items.
        """
        if not items:
            self.console.print("[yellow]No items installed[/yellow]")
            return

        table = Table(title="Installed Items")
        table.add_column("ID", style="cyan")
        table.add_column("Platform")
        table.add_column("Path")
        table.add_column("Installed")

        for item in items:
            table.add_row(
                item.id,
                item.platform,
                item.installed_path,
                item.installed_at.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)

    def show_success(self, message: str) -> None:
        """Show success message.

        Args:
            message: Success message.
        """
        self.console.print(f"[green]\u2713[/green] {message}")

    def show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message.
        """
        self.console.print(f"[red]\u2717[/red] {message}")

    def show_warning(self, message: str) -> None:
        """Show warning message.

        Args:
            message: Warning message.
        """
        self.console.print(f"[yellow]![/yellow] {message}")

    def show_info(self, message: str) -> None:
        """Show info message.

        Args:
            message: Info message.
        """
        self.console.print(f"[blue]i[/blue] {message}")

    def select_item(self, items: list[DiscoveredItem]) -> DiscoveredItem | None:
        """Prompt user to select an item.

        Args:
            items: List of items to choose from.

        Returns:
            Selected item or None.
        """
        if not items:
            return None

        self.console.print("\nAvailable items:")
        for i, item in enumerate(items, 1):
            self.console.print(f"  [{i}] {item.name} ({item.item_type})")

        self.console.print("  [0] Cancel")

        choice = Prompt.ask("Select item", default="0")
        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]
        except ValueError:
            pass
        return None

    def select_source(self, sources: list[Source]) -> Source | None:
        """Prompt user to select a source.

        Args:
            sources: List of sources to choose from.

        Returns:
            Selected source or None.
        """
        if not sources:
            return None

        self.console.print("\nAvailable sources:")
        for i, source in enumerate(sources, 1):
            self.console.print(f"  [{i}] {source.name} ({source.url})")

        self.console.print("  [0] Cancel")

        choice = Prompt.ask("Select source", default="0")
        try:
            idx = int(choice)
            if 1 <= idx <= len(sources):
                return sources[idx - 1]
        except ValueError:
            pass
        return None

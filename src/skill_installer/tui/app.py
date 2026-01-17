"""Main Skill Installer TUI Application."""

from __future__ import annotations

import logging
import webbrowser
from typing import Any

logger = logging.getLogger(__name__)

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static, TabbedContent, TabPane

from skill_installer.tui.data_manager import DataManager
from skill_installer.tui.handlers import ScreenHandlers
from skill_installer.tui.models import DisplaySource
from skill_installer.tui.operations import ItemOperations
from skill_installer.tui.panes.discover import DiscoverPane
from skill_installer.tui.panes.installed import InstalledPane
from skill_installer.tui.panes.marketplaces import MarketplacesPane
from skill_installer.tui.screens.add_source import AddSourceScreen
from skill_installer.tui.screens.installed_item_detail import InstalledItemDetailScreen
from skill_installer.tui.screens.item_detail import ItemDetailScreen
from skill_installer.tui.screens.source_detail import SourceDetailScreen
from skill_installer.tui.styles import APP_CSS
from skill_installer.tui.widgets.item_list import ItemListView
from skill_installer.tui.widgets.source_list import SourceListView


class SkillInstallerApp(App):
    """Skill Installer TUI Application."""

    TITLE = "Skill Installer"
    CSS = APP_CSS

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

        self._data_manager = DataManager(
            registry_manager=registry_manager,
            gitops=gitops,
            discovery=discovery,
        )
        self._operations = ItemOperations(
            registry_manager=registry_manager,
            gitops=gitops,
            installer=installer,
            notify=self._notify_wrapper,
            load_data=self._load_data,
        )
        self._handlers = ScreenHandlers(
            registry_manager=registry_manager,
            installer=installer,
            notify=self._notify_wrapper,
            load_data=self._load_data,
            install_item=self._operations.install_item,
            uninstall_item=self._operations.uninstall_item,
            update_item=self._operations.update_item,
            install_item_to_project=self._operations.install_item_to_project,
            update_source=self._update_source,
            remove_source=self._remove_source,
            open_url=self._open_url,
            push_screen=self.push_screen,
            switch_to_discover=self._switch_to_discover,
        )

    def _notify_wrapper(self, message: str, severity: str = "information") -> None:
        """Wrapper for notify to match handler signature."""
        self.notify(message, severity=severity)

    def compose(self) -> ComposeResult:
        yield Static("Skill Installer", id="app-title")
        with TabbedContent(initial="discover"):
            with TabPane("Discover", id="discover"):
                yield DiscoverPane(registry_manager=self.registry_manager)
            with TabPane("Installed", id="installed"):
                yield InstalledPane()
            with TabPane("Marketplaces", id="marketplaces"):
                yield MarketplacesPane()
        yield Static("Loading...", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Load data when app mounts."""
        self._data_manager.update_stale_sources()
        self._load_data()
        self.call_after_refresh(self._set_tab_focus)

    def _load_data(self) -> None:
        """Load all data from registry."""
        discovered, installed, sources, status = self._data_manager.load_all_data()

        discover_pane = self.query_one(DiscoverPane)
        discover_pane.set_items(discovered)

        installed_pane = self.query_one(InstalledPane)
        installed_pane.set_items(installed)

        marketplaces_pane = self.query_one(MarketplacesPane)
        marketplaces_pane.set_sources(sources)

        self._update_status(status)

    def _update_status(self, message: str) -> None:
        """Update the status bar."""
        self.query_one("#status-bar", Static).update(message)

    def _open_url(self, url: str) -> bool:
        """Open a URL in the default browser.

        Args:
            url: The URL to open.

        Returns:
            True if the browser was opened successfully, False otherwise.
        """
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.debug("Failed to open browser for URL %s: %s", url, e)
            return False

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabbed = self.query_one(TabbedContent)
        tabs = ["discover", "installed", "marketplaces"]
        current_idx = tabs.index(tabbed.active)
        next_idx = (current_idx + 1) % len(tabs)
        tabbed.active = tabs[next_idx]
        self.call_after_refresh(self._set_tab_focus)

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabbed = self.query_one(TabbedContent)
        tabs = ["discover", "installed", "marketplaces"]
        current_idx = tabs.index(tabbed.active)
        prev_idx = (current_idx - 1) % len(tabs)
        tabbed.active = tabs[prev_idx]
        self.call_after_refresh(self._set_tab_focus)

    def _set_tab_focus(self) -> None:
        """Set focus to the list in the active tab."""
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            discover_pane = self.query_one(DiscoverPane)
            list_view = discover_pane.query_one("#discover-list", ItemListView)
            list_view.focus()
        elif tabbed.active == "installed":
            installed_pane = self.query_one(InstalledPane)
            list_view = installed_pane.query_one("#installed-list", ItemListView)
            list_view.focus()
        elif tabbed.active == "marketplaces":
            marketplaces_pane = self.query_one(MarketplacesPane)
            list_view = marketplaces_pane.query_one("#marketplaces-list", SourceListView)
            list_view.focus()

    def action_refresh(self) -> None:
        """Refresh data."""
        self._update_status("Refreshing...")
        self._load_data()

    def action_add_source(self) -> None:
        """Show add source dialog."""
        self.push_screen(AddSourceScreen(), self._handle_add_source_result)

    def _handle_add_source_result(self, url: str | None) -> None:
        """Handle the result from AddSourceScreen.

        Args:
            url: The URL to add, or None if cancelled.
        """
        if url is None:
            return

        if not self.registry_manager:
            self.notify("Registry not configured", severity="error")
            return

        try:
            source = self.registry_manager.add_source(url)
            self.notify(f"Added source: {source.name}")

            # Sync the new source if gitops is available
            if self.gitops:
                self._update_status(f"Syncing {source.name}...")
                try:
                    self.gitops.clone_or_fetch(source.url, source.name)
                    self.registry_manager.update_source_sync_time(source.name)
                except Exception as e:
                    self.notify(f"Failed to sync: {e}", severity="warning")

            self._load_data()
        except ValueError as e:
            self.notify(str(e), severity="error")

    def action_install(self) -> None:
        """Install checked items, or selected item if none checked."""
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            discover_pane = self.query_one(DiscoverPane)
            list_view = discover_pane.query_one("#discover-list", ItemListView)
            checked_items = list_view.get_checked_items()
            if checked_items:
                for item in checked_items:
                    self._operations.install_item(item, reload_data=False)
                list_view.clear_checked()
                self._load_data()
            elif list_view.items and list_view.cursor_row is not None:
                item = list_view.items[list_view.cursor_row]
                self._operations.install_item(item)

    @on(ItemListView.ItemSelected)
    def on_item_selected(self, event: ItemListView.ItemSelected) -> None:
        """Handle item selection - show detail view."""
        item = event.item
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            self.push_screen(
                ItemDetailScreen(item, registry_manager=self.registry_manager),
                self._handlers.handle_item_detail_result,
            )
        elif tabbed.active == "installed":
            self.push_screen(
                InstalledItemDetailScreen(item, registry_manager=self.registry_manager),
                self._handlers.handle_installed_item_detail_result,
            )

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

    def _switch_to_discover(self, source_name: str) -> None:
        """Switch to Discover tab and filter by source.

        Args:
            source_name: Name of the source to filter by.
        """
        discover_pane = self.query_one(DiscoverPane)
        discover_pane.set_source_filter(source_name)

        tabbed = self.query_one(TabbedContent)
        tabbed.active = "discover"

        def focus_discover() -> None:
            list_view = discover_pane.query_one("#discover-list", ItemListView)
            list_view.focus()

        self.call_after_refresh(focus_discover)

    @on(SourceListView.SourceSelected)
    def on_source_selected(self, event: SourceListView.SourceSelected) -> None:
        """Handle source selection - show detail view."""
        source = event.source
        self.push_screen(
            SourceDetailScreen(source),
            self._handlers.handle_source_detail_result,
        )

    def _update_source(self, source: DisplaySource) -> None:
        """Update a source repository."""
        self._operations.update_source(source, self._update_status)

    def _remove_source(self, source: DisplaySource) -> None:
        """Remove a source repository."""
        self._operations.remove_source(source)

    @on(SourceListView.SourceUpdate)
    def on_source_update(self, event: SourceListView.SourceUpdate) -> None:
        """Handle source update request (U key shortcut)."""
        self._update_source(event.source)

    @on(SourceListView.SourceRemove)
    def on_source_remove(self, event: SourceListView.SourceRemove) -> None:
        """Handle source remove request (R key shortcut)."""
        self._remove_source(event.source)

"""Main Skill Installer TUI Application."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static, TabbedContent, TabPane

from skill_installer.tui.models import DisplayItem, DisplaySource
from skill_installer.tui.panes.discover import DiscoverPane
from skill_installer.tui.panes.installed import InstalledPane
from skill_installer.tui.panes.marketplaces import MarketplacesPane
from skill_installer.tui.screens.confirmation import ConfirmationScreen
from skill_installer.tui.screens.item_detail import ItemDetailScreen
from skill_installer.tui.screens.location_selection import LocationSelectionScreen
from skill_installer.tui.screens.source_detail import SourceDetailScreen
from skill_installer.tui.widgets.item_list import ItemListView
from skill_installer.tui.widgets.source_list import SourceListView


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
        self._pending_uninstall_item: DisplayItem | None = None
        self._pending_project_install: tuple[DisplayItem, Path] | None = None

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
        self._update_stale_sources()
        self._load_data()
        # Set initial focus
        self.call_after_refresh(self._set_tab_focus)

    def _update_stale_sources(self) -> None:
        """Update sources with auto_update enabled that are stale."""
        if not self.registry_manager or not self.gitops:
            return

        stale_sources = self.registry_manager.get_stale_auto_update_sources()
        for source in stale_sources:
            try:
                self.gitops.clone_or_fetch(source.url, source.name)
                self.registry_manager.update_source_sync_time(source.name)
            except Exception:
                # Silently ignore update failures during startup
                pass

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
        installed_by_source: dict[str, int] = {}
        for item in installed_items:
            if item.id not in installed_map:
                installed_map[item.id] = []
            installed_map[item.id].append(item.platform)
            # Count installed items per source
            installed_by_source[item.source] = installed_by_source.get(item.source, 0) + 1

        # Discover items from all sources
        all_discovered: list[DisplayItem] = []
        installed_display: list[DisplayItem] = []
        display_sources: list[DisplaySource] = []
        items_by_source: dict[str, int] = {}

        for source in sources:
            source_item_count = 0
            display_name = source.name  # Default to source name

            if self.gitops and self.discovery:
                repo_path = self.gitops.get_repo_path(source.name)
                if repo_path.exists():
                    items = self.discovery.discover_all(repo_path, None)
                    source_item_count = len(items)
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
                            source_url=source.url,
                        )
                        all_discovered.append(display_item)

                        if platforms_installed:
                            installed_display.append(display_item)

                    # Try to get display name from marketplace.json
                    marketplace_file = repo_path / "marketplace.json"
                    if marketplace_file.exists():
                        import json
                        try:
                            with open(marketplace_file) as f:
                                marketplace_data = json.load(f)
                                display_name = marketplace_data.get("name", source.name)
                        except (json.JSONDecodeError, OSError):
                            pass

            items_by_source[source.name] = source_item_count

            # Format last_sync for display
            last_sync_str = source.last_sync.strftime("%Y-%m-%d %H:%M") if source.last_sync else "Never"

            display_sources.append(DisplaySource(
                name=source.name,
                display_name=display_name,
                url=source.url,
                available_count=source_item_count,
                installed_count=installed_by_source.get(source.name, 0),
                last_sync=last_sync_str,
                raw_data=source,
            ))

        # Update panes
        discover_pane = self.query_one(DiscoverPane)
        discover_pane.set_items(all_discovered)

        installed_pane = self.query_one(InstalledPane)
        installed_pane.set_items(installed_display)

        marketplaces_pane = self.query_one(MarketplacesPane)
        marketplaces_pane.set_sources(display_sources)

        # Update status bar
        total_items = len(all_discovered)
        total_installed = len(installed_display)
        self._update_status(f"{total_items} items available, {total_installed} installed")

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
        except Exception:
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
        self.notify("Add source: Run 'skill-installer source add <url>' from CLI")

    def action_install(self) -> None:
        """Install checked items, or selected item if none checked."""
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            discover_pane = self.query_one(DiscoverPane)
            list_view = discover_pane.query_one("#discover-list", ItemListView)
            checked_items = list_view.get_checked_items()
            if checked_items:
                # Install all checked items without reloading until done
                for item in checked_items:
                    self._install_item(item, reload_data=False)
                list_view.clear_checked()
                self._load_data()
            elif list_view.items:
                # Install currently selected item
                item = list_view.items[list_view.selected_index]
                self._install_item(item)

    def _install_item(
        self,
        item: DisplayItem,
        platforms: list[str] | None = None,
        reload_data: bool = True,
    ) -> None:
        """Install an item.

        Args:
            item: The item to install.
            platforms: Optional list of platform IDs to install to.
                If None, installs to all platforms from the source.
            reload_data: Whether to reload UI data after installation.
                Set to False when batch installing to avoid duplicate widget IDs.
        """
        if not self.installer:
            self.notify("Installer not configured", severity="error")
            return

        source = self.registry_manager.get_source(item.source_name)
        if not source:
            self.notify(f"Source '{item.source_name}' not found", severity="error")
            return

        # Use specified platforms or all source platforms
        target_platforms = platforms if platforms is not None else source.platforms

        for platform in target_platforms:
            result = self.installer.install_item(item.raw_data, item.source_name, platform)
            if result.success:
                self.notify(f"Installed {item.name} to {platform}")
            else:
                self.notify(f"Failed: {result.error}", severity="error")

        if reload_data:
            self._load_data()

    def _uninstall_item(self, item: DisplayItem) -> None:
        """Uninstall an item from all platforms.

        Args:
            item: The item to uninstall.
        """
        if not self.installer:
            self.notify("Installer not configured", severity="error")
            return

        results = self.installer.uninstall_item(item.unique_id)

        if not results:
            self.notify(f"No installations found for {item.name}", severity="warning")
            return

        success_count = 0
        for result in results:
            if result.success:
                success_count += 1
                self.notify(f"Uninstalled {item.name} from {result.platform}")
            else:
                self.notify(f"Failed to uninstall from {result.platform}: {result.error}", severity="error")

        if success_count > 0:
            self._load_data()

    def _install_item_to_project(self, item: DisplayItem, project_root: Path) -> None:
        """Install an item to project scope.

        Args:
            item: The item to install.
            project_root: Root directory of the project.
        """
        if not self.installer:
            self.notify("Installer not configured", severity="error")
            return

        source = self.registry_manager.get_source(item.source_name)
        if not source:
            self.notify(f"Source '{item.source_name}' not found", severity="error")
            return

        # Install to all platforms from the source
        success_count = 0
        for platform in source.platforms:
            result = self.installer.install_item(
                item.raw_data,
                item.source_name,
                platform,
                scope="project",
                project_root=project_root,
            )
            if result.success:
                success_count += 1
                self.notify(f"Installed {item.name} to {platform} (project scope)")
            else:
                self.notify(f"Failed: {result.error}", severity="error")

        if success_count > 0:
            self._load_data()

    @on(ItemListView.ItemSelected)
    def on_item_selected(self, event: ItemListView.ItemSelected) -> None:
        """Handle item selection - show detail view."""
        item = event.item
        tabbed = self.query_one(TabbedContent)
        if tabbed.active == "discover":
            self.push_screen(
                ItemDetailScreen(item, registry_manager=self.registry_manager),
                self._handle_item_detail_result
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

    @on(SourceListView.SourceSelected)
    def on_source_selected(self, event: SourceListView.SourceSelected) -> None:
        """Handle source selection - show detail view."""
        source = event.source
        self.push_screen(
            SourceDetailScreen(source),
            self._handle_source_detail_result
        )

    def _handle_source_detail_result(
        self, result: tuple[str, DisplaySource] | None
    ) -> None:
        """Handle result from SourceDetailScreen."""
        if result is None:
            # User cancelled or pressed back
            return

        option_id, source = result

        if option_id == "browse":
            # Browse items from this source - navigate to Discover tab and filter
            discover_pane = self.query_one(DiscoverPane)
            discover_pane.set_source_filter(source.name)

            # Switch to Discover tab
            tabbed = self.query_one(TabbedContent)
            tabbed.active = "discover"

            # Ensure the discover list is focused after tab switch
            def focus_discover():
                list_view = discover_pane.query_one("#discover-list", ItemListView)
                list_view.focus()

            self.call_after_refresh(focus_discover)

        elif option_id == "update":
            self._update_source(source)

        elif option_id == "auto_update":
            if self.registry_manager:
                new_state = self.registry_manager.toggle_source_auto_update(source.name)
                state_text = "enabled" if new_state else "disabled"
                self.notify(f"Auto-update {state_text} for {source.display_name}")
                self._load_data()

        elif option_id == "remove":
            self._remove_source(source)

    def _handle_item_detail_result(
        self, result: tuple[str, DisplayItem] | None
    ) -> None:
        """Handle result from ItemDetailScreen."""
        if result is None:
            # User cancelled or pressed back
            return

        option_id, item = result

        if option_id == "install_user":
            # Show location selection screen
            from skill_installer.platforms import get_available_platforms

            available_platforms = get_available_platforms()
            if not available_platforms:
                self.notify("No supported platforms found on this system", severity="warning")
                return

            self.push_screen(
                LocationSelectionScreen(item, available_platforms),
                self._handle_location_selection_result
            )

        elif option_id == "install_project":
            from skill_installer.install import get_project_root

            project_root = get_project_root()
            if not project_root:
                self.notify(
                    "Not in a git project. Cannot install to project scope.",
                    severity="warning"
                )
                return
            # Show confirmation with project path
            self._pending_project_install = (item, project_root)
            self.push_screen(
                ConfirmationScreen(
                    "Install for Project",
                    f"Install '{item.name}' to project at:\n{project_root}?",
                ),
                self._handle_project_install_confirmation
            )

        elif option_id == "uninstall":
            # Store item for callback
            self._pending_uninstall_item = item
            self.push_screen(
                ConfirmationScreen(
                    "Confirm Uninstall",
                    f"Are you sure you want to uninstall '{item.name}'?\n"
                    f"This will remove it from: {', '.join(item.installed_platforms)}",
                ),
                self._handle_uninstall_confirmation
            )

        elif option_id == "open_homepage":
            homepage = ""
            if hasattr(item.raw_data, 'frontmatter') and item.raw_data.frontmatter:
                homepage = item.raw_data.frontmatter.get("homepage", "") or item.raw_data.frontmatter.get("url", "")
            if not homepage and item.source_url:
                homepage = item.source_url
            if homepage:
                self.notify("Opening homepage...")
                if not self._open_url(homepage):
                    self.notify(f"Could not open browser. URL: {homepage}", severity="warning")
            else:
                self.notify("No homepage available", severity="warning")

    def _handle_location_selection_result(
        self, result: tuple[list[str], DisplayItem] | None
    ) -> None:
        """Handle result from LocationSelectionScreen."""
        if result is None:
            # User cancelled
            return

        selected_platforms, item = result
        self._install_item(item, selected_platforms)

    def _handle_uninstall_confirmation(self, confirmed: bool) -> None:
        """Handle result from uninstall confirmation dialog."""
        if not confirmed:
            return

        item = self._pending_uninstall_item
        self._pending_uninstall_item = None

        if item:
            self._uninstall_item(item)

    def _handle_project_install_confirmation(self, confirmed: bool) -> None:
        """Handle result from project install confirmation dialog."""
        if not confirmed:
            self._pending_project_install = None
            return

        if not self._pending_project_install:
            return

        item, project_root = self._pending_project_install
        self._pending_project_install = None

        self._install_item_to_project(item, project_root)

    def _update_source(self, source: DisplaySource) -> None:
        """Update a source repository."""
        self._update_status(f"Updating {source.display_name}...")

        if self.gitops:
            try:
                # Get the raw Source from raw_data
                raw_source = source.raw_data
                self.gitops.clone_or_fetch(raw_source.url, raw_source.name)
                if self.registry_manager:
                    self.registry_manager.update_source_sync_time(source.name)
                self.notify(f"Updated {source.display_name}")
                self._load_data()  # Refresh to show new data
            except Exception as e:
                self.notify(f"Failed to update: {e}", severity="error")
        else:
            self.notify("Git operations not configured", severity="warning")

    def _remove_source(self, source: DisplaySource) -> None:
        """Remove a source repository."""
        if self.registry_manager:
            # Remove from registry
            removed = self.registry_manager.remove_source(source.name)
            if removed:
                # Also remove cached repo
                if self.gitops:
                    self.gitops.remove_cached(source.name)
                self.notify(f"Removed {source.display_name}")
                self._load_data()  # Refresh list
            else:
                self.notify(f"Source not found: {source.name}", severity="error")
        else:
            self.notify("Registry not configured", severity="warning")

    @on(SourceListView.SourceUpdate)
    def on_source_update(self, event: SourceListView.SourceUpdate) -> None:
        """Handle source update request (U key shortcut)."""
        self._update_source(event.source)

    @on(SourceListView.SourceRemove)
    def on_source_remove(self, event: SourceListView.SourceRemove) -> None:
        """Handle source remove request (R key shortcut)."""
        self._remove_source(event.source)

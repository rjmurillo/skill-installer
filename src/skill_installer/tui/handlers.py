"""Screen result handlers for the Skill Installer TUI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from skill_installer.tui.models import DisplayItem, DisplaySource


class ScreenHandlers:
    """Handles screen result callbacks for the TUI application."""

    def __init__(
        self,
        *,
        registry_manager: Any = None,
        installer: Any = None,
        notify: Callable[[str, str], None] | None = None,
        load_data: Callable[[], None] | None = None,
        install_item: Callable[[DisplayItem, list[str] | None, bool], None] | None = None,
        uninstall_item: Callable[[DisplayItem], None] | None = None,
        install_item_to_project: Callable[[DisplayItem, Path], None] | None = None,
        update_source: Callable[[DisplaySource], None] | None = None,
        remove_source: Callable[[DisplaySource], None] | None = None,
        open_url: Callable[[str], bool] | None = None,
        push_screen: Callable[..., None] | None = None,
        switch_to_discover: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize handlers with required callbacks.

        Args:
            registry_manager: Registry manager instance.
            installer: Installer instance.
            notify: Callback to show notifications.
            load_data: Callback to reload UI data.
            install_item: Callback to install an item.
            uninstall_item: Callback to uninstall an item.
            install_item_to_project: Callback to install to project scope.
            update_source: Callback to update a source.
            remove_source: Callback to remove a source.
            open_url: Callback to open URLs.
            push_screen: Callback to push a new screen.
            switch_to_discover: Callback to switch to discover tab with filter.
        """
        self.registry_manager = registry_manager
        self.installer = installer
        self._notify = notify
        self._load_data = load_data
        self._install_item = install_item
        self._uninstall_item = uninstall_item
        self._install_item_to_project = install_item_to_project
        self._update_source = update_source
        self._remove_source = remove_source
        self._open_url = open_url
        self._push_screen = push_screen
        self._switch_to_discover = switch_to_discover

        # Pending state for confirmations
        self._pending_uninstall_item: DisplayItem | None = None
        self._pending_project_install: tuple[DisplayItem, Path] | None = None

    def notify(self, message: str, severity: str = "information") -> None:
        """Show a notification."""
        if self._notify:
            self._notify(message, severity)

    def handle_source_detail_result(
        self, result: tuple[str, DisplaySource] | None
    ) -> None:
        """Handle result from SourceDetailScreen.

        Args:
            result: Tuple of (option_id, source) or None if cancelled.
        """
        if result is None:
            return

        option_id, source = result

        if option_id == "browse":
            if self._switch_to_discover:
                self._switch_to_discover(source.name)

        elif option_id == "update":
            if self._update_source:
                self._update_source(source)

        elif option_id == "auto_update":
            if self.registry_manager:
                new_state = self.registry_manager.toggle_source_auto_update(source.name)
                state_text = "enabled" if new_state else "disabled"
                self.notify(f"Auto-update {state_text} for {source.display_name}")
                if self._load_data:
                    self._load_data()

        elif option_id == "remove":
            if self._remove_source:
                self._remove_source(source)

    def handle_item_detail_result(
        self, result: tuple[str, DisplayItem] | None
    ) -> None:
        """Handle result from ItemDetailScreen.

        Args:
            result: Tuple of (option_id, item) or None if cancelled.
        """
        if result is None:
            return

        option_id, item = result

        if option_id == "install_user":
            self._handle_install_user(item)

        elif option_id == "install_project":
            self._handle_install_project(item)

        elif option_id == "uninstall":
            self._handle_uninstall(item)

        elif option_id == "open_homepage":
            self._handle_open_homepage(item)

    def _handle_install_user(self, item: DisplayItem) -> None:
        """Handle install to user scope."""
        from skill_installer.platforms import get_available_platforms
        from skill_installer.tui.screens.location_selection import (
            LocationSelectionScreen,
        )

        available_platforms = get_available_platforms()
        if not available_platforms:
            self.notify(
                "No supported platforms found on this system",
                severity="warning",
            )
            return

        if self._push_screen:
            self._push_screen(
                LocationSelectionScreen(item, available_platforms),
                self.handle_location_selection_result,
            )

    def _handle_install_project(self, item: DisplayItem) -> None:
        """Handle install to project scope."""
        from skill_installer.install import get_project_root
        from skill_installer.tui.screens.confirmation import ConfirmationScreen

        project_root = get_project_root()
        if not project_root:
            self.notify(
                "Not in a git project. Cannot install to project scope.",
                severity="warning",
            )
            return

        self._pending_project_install = (item, project_root)
        if self._push_screen:
            self._push_screen(
                ConfirmationScreen(
                    "Install for Project",
                    f"Install '{item.name}' to project at:\n{project_root}?",
                ),
                self.handle_project_install_confirmation,
            )

    def _handle_uninstall(self, item: DisplayItem) -> None:
        """Handle uninstall request."""
        from skill_installer.tui.screens.confirmation import ConfirmationScreen

        self._pending_uninstall_item = item
        if self._push_screen:
            self._push_screen(
                ConfirmationScreen(
                    "Confirm Uninstall",
                    f"Are you sure you want to uninstall '{item.name}'?\n"
                    f"This will remove it from: {', '.join(item.installed_platforms)}",
                ),
                self.handle_uninstall_confirmation,
            )

    def _handle_open_homepage(self, item: DisplayItem) -> None:
        """Handle open homepage request."""
        homepage = ""
        if hasattr(item.raw_data, "frontmatter") and item.raw_data.frontmatter:
            homepage = item.raw_data.frontmatter.get(
                "homepage", ""
            ) or item.raw_data.frontmatter.get("url", "")
        if not homepage and item.source_url:
            homepage = item.source_url
        if homepage:
            self.notify("Opening homepage...")
            if self._open_url and not self._open_url(homepage):
                self.notify(
                    f"Could not open browser. URL: {homepage}",
                    severity="warning",
                )
        else:
            self.notify("No homepage available", severity="warning")

    def handle_location_selection_result(
        self, result: tuple[list[str], DisplayItem] | None
    ) -> None:
        """Handle result from LocationSelectionScreen.

        Args:
            result: Tuple of (selected_platforms, item) or None if cancelled.
        """
        if result is None:
            return

        selected_platforms, item = result
        if self._install_item:
            self._install_item(item, selected_platforms, True)

    def handle_uninstall_confirmation(self, confirmed: bool) -> None:
        """Handle result from uninstall confirmation dialog.

        Args:
            confirmed: Whether the user confirmed the action.
        """
        if not confirmed:
            return

        item = self._pending_uninstall_item
        self._pending_uninstall_item = None

        if item and self._uninstall_item:
            self._uninstall_item(item)

    def handle_project_install_confirmation(self, confirmed: bool) -> None:
        """Handle result from project install confirmation dialog.

        Args:
            confirmed: Whether the user confirmed the action.
        """
        if not confirmed:
            self._pending_project_install = None
            return

        if not self._pending_project_install:
            return

        item, project_root = self._pending_project_install
        self._pending_project_install = None

        if self._install_item_to_project:
            self._install_item_to_project(item, project_root)

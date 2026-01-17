"""Installation operations for the Skill Installer TUI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from skill_installer.tui.models import DisplayItem, DisplaySource


class ItemOperations:
    """Handles item installation and uninstallation operations."""

    def __init__(
        self,
        *,
        registry_manager: Any = None,
        gitops: Any = None,
        installer: Any = None,
        notify: Callable[[str, str], None] | None = None,
        load_data: Callable[[], None] | None = None,
    ) -> None:
        """Initialize operations with required dependencies.

        Args:
            registry_manager: Registry manager instance.
            gitops: Git operations instance.
            installer: Installer instance.
            notify: Callback to show notifications.
            load_data: Callback to reload UI data.
        """
        self.registry_manager = registry_manager
        self.gitops = gitops
        self.installer = installer
        self._notify = notify
        self._load_data = load_data

    def notify(self, message: str, severity: str = "information") -> None:
        """Show a notification."""
        if self._notify:
            self._notify(message, severity)

    def install_item(
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
            self.notify("Installer not configured", "error")
            return

        source = self.registry_manager.get_source(item.source_name)
        if not source:
            self.notify(f"Source '{item.source_name}' not found", "error")
            return

        target_platforms = platforms if platforms is not None else source.platforms

        for platform in target_platforms:
            result = self.installer.install_item(
                item.raw_data, item.source_name, platform
            )
            if result.success:
                self.notify(f"Installed {item.name} to {platform}")
            else:
                self.notify(f"Failed: {result.error}", "error")

        if reload_data and self._load_data:
            self._load_data()

    def uninstall_item(self, item: DisplayItem) -> None:
        """Uninstall an item from all platforms.

        Args:
            item: The item to uninstall.
        """
        if not self.installer:
            self.notify("Installer not configured", "error")
            return

        results = self.installer.uninstall_item(item.unique_id)

        if not results:
            self.notify(f"No installations found for {item.name}", "warning")
            return

        success_count = 0
        for result in results:
            if result.success:
                success_count += 1
                self.notify(f"Uninstalled {item.name} from {result.platform}")
            else:
                self.notify(
                    f"Failed to uninstall from {result.platform}: {result.error}",
                    "error",
                )

        if success_count > 0 and self._load_data:
            self._load_data()

    def install_item_to_project(self, item: DisplayItem, project_root: Path) -> None:
        """Install an item to project scope.

        Args:
            item: The item to install.
            project_root: Root directory of the project.
        """
        if not self.installer:
            self.notify("Installer not configured", "error")
            return

        source = self.registry_manager.get_source(item.source_name)
        if not source:
            self.notify(f"Source '{item.source_name}' not found", "error")
            return

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
                self.notify(f"Failed: {result.error}", "error")

        if success_count > 0 and self._load_data:
            self._load_data()

    def update_source(self, source: DisplaySource, update_status: Callable[[str], None] | None = None) -> None:
        """Update a source repository.

        Args:
            source: The source to update.
            update_status: Callback to update status bar.
        """
        if update_status:
            update_status(f"Updating {source.display_name}...")

        if self.gitops:
            try:
                raw_source = source.raw_data
                self.gitops.clone_or_fetch(raw_source.url, raw_source.name)
                if self.registry_manager:
                    self.registry_manager.update_source_sync_time(source.name)
                self.notify(f"Updated {source.display_name}")
                if self._load_data:
                    self._load_data()
            except Exception as e:
                self.notify(f"Failed to update: {e}", "error")
        else:
            self.notify("Git operations not configured", "warning")

    def remove_source(self, source: DisplaySource) -> None:
        """Remove a source repository.

        Args:
            source: The source to remove.
        """
        if self.registry_manager:
            removed = self.registry_manager.remove_source(source.name)
            if removed:
                if self.gitops:
                    self.gitops.remove_cached(source.name)
                self.notify(f"Removed {source.display_name}")
                if self._load_data:
                    self._load_data()
            else:
                self.notify(f"Source not found: {source.name}", "error")
        else:
            self.notify("Registry not configured", "warning")

"""Data loading and management for the Skill Installer TUI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from skill_installer.tui.models import DisplayItem, DisplaySource

if TYPE_CHECKING:
    from pathlib import Path


class DataManager:
    """Manages data loading for the TUI application."""

    def __init__(
        self,
        registry_manager: Any = None,
        gitops: Any = None,
        discovery: Any = None,
    ) -> None:
        """Initialize the data manager.

        Args:
            registry_manager: Registry manager instance.
            gitops: Git operations instance.
            discovery: Discovery service instance.
        """
        self.registry_manager = registry_manager
        self.gitops = gitops
        self.discovery = discovery

    def update_stale_sources(self) -> None:
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

    def load_all_data(self) -> tuple[
        list[DisplayItem],
        list[DisplayItem],
        list[DisplaySource],
        str,
    ]:
        """Load all data from registry.

        Returns:
            Tuple of (discovered_items, installed_items, sources, status_message).
        """
        if not self.registry_manager:
            return [], [], [], "No registry manager configured"

        sources = self.registry_manager.list_sources()
        installed_map, installed_by_source = self._build_installed_maps()

        all_discovered: list[DisplayItem] = []
        installed_display: list[DisplayItem] = []
        display_sources: list[DisplaySource] = []

        for source in sources:
            discovered, installed, display_source = self._load_source_data(
                source, installed_map, installed_by_source
            )
            all_discovered.extend(discovered)
            installed_display.extend(installed)
            display_sources.append(display_source)

        total_items = len(all_discovered)
        total_installed = len(installed_display)
        status = f"{total_items} items available, {total_installed} installed"

        return all_discovered, installed_display, display_sources, status

    def _build_installed_maps(self) -> tuple[dict[str, list[str]], dict[str, int]]:
        """Build maps of installed items.

        Returns:
            Tuple of (installed_map by id, installed_count by source).
        """
        installed_items = self.registry_manager.list_installed()
        installed_map: dict[str, list[str]] = {}
        installed_by_source: dict[str, int] = {}

        for item in installed_items:
            if item.id not in installed_map:
                installed_map[item.id] = []
            installed_map[item.id].append(item.platform)
            installed_by_source[item.source] = (
                installed_by_source.get(item.source, 0) + 1
            )

        return installed_map, installed_by_source

    def _load_source_data(
        self,
        source: Any,
        installed_map: dict[str, list[str]],
        installed_by_source: dict[str, int],
    ) -> tuple[list[DisplayItem], list[DisplayItem], DisplaySource]:
        """Load data for a single source.

        Args:
            source: Source object from registry.
            installed_map: Map of item IDs to installed platforms.
            installed_by_source: Map of source names to installed counts.

        Returns:
            Tuple of (discovered items, installed items, display source).
        """
        discovered: list[DisplayItem] = []
        installed: list[DisplayItem] = []
        source_item_count = 0
        display_name = source.name

        if self.gitops and self.discovery:
            repo_path = self.gitops.get_repo_path(source.name)
            if repo_path.exists():
                discovered, installed, source_item_count = self._discover_items(
                    source, repo_path, installed_map
                )
                display_name = self._get_display_name(repo_path, source.name)

        last_sync_str = (
            source.last_sync.strftime("%Y-%m-%d %H:%M")
            if source.last_sync
            else "Never"
        )

        display_source = DisplaySource(
            name=source.name,
            display_name=display_name,
            url=source.url,
            available_count=source_item_count,
            installed_count=installed_by_source.get(source.name, 0),
            last_sync=last_sync_str,
            raw_data=source,
        )

        return discovered, installed, display_source

    def _discover_items(
        self,
        source: Any,
        repo_path: Path,
        installed_map: dict[str, list[str]],
    ) -> tuple[list[DisplayItem], list[DisplayItem], int]:
        """Discover items from a source repository.

        Args:
            source: Source object from registry.
            repo_path: Path to the repository.
            installed_map: Map of item IDs to installed platforms.

        Returns:
            Tuple of (all discovered, installed only, total count).
        """
        discovered: list[DisplayItem] = []
        installed: list[DisplayItem] = []

        items = self.discovery.discover_all(repo_path, None)
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
            discovered.append(display_item)
            if platforms_installed:
                installed.append(display_item)

        return discovered, installed, len(items)

    def _get_display_name(self, repo_path: Path, default_name: str) -> str:
        """Get display name from marketplace.json if available.

        Args:
            repo_path: Path to the repository.
            default_name: Default name to use if not found.

        Returns:
            Display name from marketplace.json or default.
        """
        marketplace_file = repo_path / "marketplace.json"
        if marketplace_file.exists():
            try:
                with open(marketplace_file) as f:
                    marketplace_data = json.load(f)
                    return marketplace_data.get("name", default_name)
            except (json.JSONDecodeError, OSError):
                pass
        return default_name

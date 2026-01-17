"""Registry management for sources and installed items."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Default registry location
REGISTRY_DIR = Path.home() / ".skill-installer"


class SourcePaths(BaseModel):
    """Paths within a source repository."""

    agents: str = "src"
    skills: str = ".claude/skills"
    commands: str = ".claude/commands"


class Source(BaseModel):
    """A registered source repository."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    url: str
    ref: str = "main"
    paths: SourcePaths = Field(default_factory=SourcePaths)
    platforms: list[str] = Field(default_factory=lambda: ["claude", "vscode"])
    last_sync: datetime | None = Field(default=None, alias="lastSync")


class SourceRegistry(BaseModel):
    """Registry of source repositories."""

    version: str = "1.0"
    sources: list[Source] = Field(default_factory=list)
    defaults: dict[str, Any] = Field(
        default_factory=lambda: {"targetPlatforms": ["claude", "vscode"]}
    )


class InstalledItem(BaseModel):
    """An installed skill/agent."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    source: str
    item_type: str = Field(alias="type")
    name: str
    platform: str
    scope: str = "global"
    installed_path: str = Field(alias="installedPath")
    source_hash: str = Field(alias="sourceHash")
    installed_at: datetime = Field(alias="installedAt")


class InstalledRegistry(BaseModel):
    """Registry of installed items."""

    version: str = "1.0"
    items: list[InstalledItem] = Field(default_factory=list)


class RegistryManager:
    """Manages source and installed registries."""

    def __init__(self, registry_dir: Path | None = None) -> None:
        """Initialize the registry manager.

        Args:
            registry_dir: Directory for registry files. Defaults to ~/.skill-installer.
        """
        self.registry_dir = registry_dir or REGISTRY_DIR
        self.sources_file = self.registry_dir / "sources.json"
        self.installed_file = self.registry_dir / "installed.json"

    def ensure_registry_dir(self) -> None:
        """Create registry directory if it doesn't exist."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def load_sources(self) -> SourceRegistry:
        """Load source registry from disk.

        Returns:
            SourceRegistry with configured sources.
        """
        if not self.sources_file.exists():
            return SourceRegistry()

        data = json.loads(self.sources_file.read_text())
        return SourceRegistry.model_validate(data)

    def save_sources(self, registry: SourceRegistry) -> None:
        """Save source registry to disk.

        Args:
            registry: SourceRegistry to save.
        """
        self.ensure_registry_dir()
        data = registry.model_dump(by_alias=True, exclude_none=True)
        self.sources_file.write_text(json.dumps(data, indent=2, default=str))

    def load_installed(self) -> InstalledRegistry:
        """Load installed registry from disk.

        Returns:
            InstalledRegistry with installed items.
        """
        if not self.installed_file.exists():
            return InstalledRegistry()

        data = json.loads(self.installed_file.read_text())
        return InstalledRegistry.model_validate(data)

    def save_installed(self, registry: InstalledRegistry) -> None:
        """Save installed registry to disk.

        Args:
            registry: InstalledRegistry to save.
        """
        self.ensure_registry_dir()
        data = registry.model_dump(by_alias=True, exclude_none=True)
        self.installed_file.write_text(json.dumps(data, indent=2, default=str))

    def add_source(
        self,
        url: str,
        name: str | None = None,
        ref: str = "main",
        platforms: list[str] | None = None,
    ) -> Source:
        """Add a new source repository.

        Args:
            url: Git repository URL.
            name: Optional alias for the source.
            ref: Branch/tag reference. Defaults to "main".
            platforms: Target platforms. Defaults to ["claude", "vscode"].

        Returns:
            The created Source.

        Raises:
            ValueError: If source with same name already exists.
        """
        registry = self.load_sources()

        # Derive name from URL if not provided
        if name is None:
            # Extract repo name from URL (e.g., "ai-agents" from github.com/user/ai-agents)
            name = url.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]

        # Check for duplicates
        for source in registry.sources:
            if source.name == name:
                raise ValueError(f"Source '{name}' already exists")

        source = Source(
            name=name,
            url=url,
            ref=ref,
            platforms=platforms or ["claude", "vscode"],
        )
        registry.sources.append(source)
        self.save_sources(registry)
        return source

    def remove_source(self, name: str) -> bool:
        """Remove a source repository.

        Args:
            name: Name of the source to remove.

        Returns:
            True if removed, False if not found.
        """
        registry = self.load_sources()
        original_count = len(registry.sources)
        registry.sources = [s for s in registry.sources if s.name != name]

        if len(registry.sources) < original_count:
            self.save_sources(registry)
            return True
        return False

    def get_source(self, name: str) -> Source | None:
        """Get a source by name.

        Args:
            name: Name of the source.

        Returns:
            Source if found, None otherwise.
        """
        registry = self.load_sources()
        for source in registry.sources:
            if source.name == name:
                return source
        return None

    def list_sources(self) -> list[Source]:
        """List all registered sources.

        Returns:
            List of Source objects.
        """
        return self.load_sources().sources

    def update_source_sync_time(self, name: str) -> None:
        """Update the last sync time for a source.

        Args:
            name: Name of the source.
        """
        registry = self.load_sources()
        for source in registry.sources:
            if source.name == name:
                source.last_sync = datetime.now(timezone.utc)
                self.save_sources(registry)
                break

    def add_installed(
        self,
        source_name: str,
        item_type: str,
        name: str,
        platform: str,
        installed_path: str,
        source_hash: str,
    ) -> InstalledItem:
        """Add an installed item to the registry.

        Args:
            source_name: Name of the source repository.
            item_type: Type of item (agent, skill, command).
            name: Name of the item.
            platform: Target platform.
            installed_path: Path where item was installed.
            source_hash: Hash of source content.

        Returns:
            The created InstalledItem.
        """
        registry = self.load_installed()

        item_id = f"{source_name}/{item_type}/{name}"

        # Remove existing entry if present
        registry.items = [i for i in registry.items if i.id != item_id or i.platform != platform]

        item = InstalledItem(
            id=item_id,
            source=source_name,
            type=item_type,
            name=name,
            platform=platform,
            installedPath=installed_path,
            sourceHash=source_hash,
            installedAt=datetime.now(timezone.utc),
        )
        registry.items.append(item)
        self.save_installed(registry)
        return item

    def remove_installed(self, item_id: str, platform: str | None = None) -> bool:
        """Remove an installed item from the registry.

        Args:
            item_id: ID of the item to remove.
            platform: Optional platform filter.

        Returns:
            True if removed, False if not found.
        """
        registry = self.load_installed()
        original_count = len(registry.items)

        if platform:
            registry.items = [
                i for i in registry.items if not (i.id == item_id and i.platform == platform)
            ]
        else:
            registry.items = [i for i in registry.items if i.id != item_id]

        if len(registry.items) < original_count:
            self.save_installed(registry)
            return True
        return False

    def get_installed(self, item_id: str, platform: str | None = None) -> list[InstalledItem]:
        """Get installed items by ID.

        Args:
            item_id: ID of the item.
            platform: Optional platform filter.

        Returns:
            List of matching InstalledItem objects.
        """
        registry = self.load_installed()
        items = [i for i in registry.items if i.id == item_id]
        if platform:
            items = [i for i in items if i.platform == platform]
        return items

    def list_installed(
        self, source: str | None = None, platform: str | None = None
    ) -> list[InstalledItem]:
        """List installed items.

        Args:
            source: Optional source filter.
            platform: Optional platform filter.

        Returns:
            List of InstalledItem objects.
        """
        registry = self.load_installed()
        items = registry.items

        if source:
            items = [i for i in items if i.source == source]
        if platform:
            items = [i for i in items if i.platform == platform]

        return items

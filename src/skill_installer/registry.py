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
    """Paths within a source repository (reserved for future use)."""

    pass


class MarketplaceOwner(BaseModel):
    """Owner information for a marketplace."""

    name: str
    email: str = ""


class MarketplaceMetadata(BaseModel):
    """Metadata for a marketplace."""

    description: str = ""
    version: str = "1.0.0"


class MarketplacePlugin(BaseModel):
    """A plugin within a marketplace."""

    name: str
    description: str = ""
    source: str = "./"
    strict: bool = False
    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)


class MarketplaceManifest(BaseModel):
    """Marketplace manifest from .claude-plugin/marketplace.json."""

    name: str
    owner: MarketplaceOwner | None = None
    metadata: MarketplaceMetadata = Field(default_factory=MarketplaceMetadata)
    plugins: list[MarketplacePlugin] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> MarketplaceManifest:
        """Load marketplace manifest from a JSON file.

        Args:
            path: Path to marketplace.json file.

        Returns:
            Parsed MarketplaceManifest.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If JSON is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Marketplace manifest not found: {path}")

        data = json.loads(path.read_text())
        return cls.model_validate(data)


class Source(BaseModel):
    """A registered source repository."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    url: str
    ref: str = "main"
    paths: SourcePaths = Field(default_factory=SourcePaths)
    platforms: list[str] = Field(default_factory=lambda: ["claude", "vscode"])
    last_sync: datetime | None = Field(default=None, alias="lastSync")
    marketplace_enabled: bool = Field(default=False, alias="marketplaceEnabled")
    license: str | None = None
    auto_update: bool = Field(default=False, alias="autoUpdate")


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

        Note:
            Prefer using factory methods `create()` or `create_default()` for construction.
        """
        self.registry_dir = registry_dir or REGISTRY_DIR
        self.sources_file = self.registry_dir / "sources.json"
        self.installed_file = self.registry_dir / "installed.json"

    @classmethod
    def create(cls, registry_dir: Path) -> "RegistryManager":
        """Create a registry manager with a custom directory.

        Args:
            registry_dir: Directory for registry files.

        Returns:
            Configured RegistryManager instance.
        """
        return cls(registry_dir=registry_dir)

    @classmethod
    def create_default(cls) -> "RegistryManager":
        """Create a registry manager with the default directory.

        Uses ~/.skill-installer as the registry location.

        Returns:
            RegistryManager configured with default paths.
        """
        return cls()

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
            # Extract owner/repo from URL (e.g., "anthropics/skills" from github.com/anthropics/skills)
            parts = url.rstrip("/").rstrip(".git").split("/")
            if len(parts) >= 2:
                name = f"{parts[-2]}/{parts[-1]}"
            else:
                name = parts[-1]

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

    def update_source_license(self, name: str, license_text: str | None) -> None:
        """Update the license for a source.

        Args:
            name: Name of the source.
            license_text: License text to store.
        """
        registry = self.load_sources()
        for source in registry.sources:
            if source.name == name:
                source.license = license_text
                self.save_sources(registry)
                break

    def toggle_source_auto_update(self, source_name: str) -> bool:
        """Toggle auto_update flag for a source.

        Args:
            source_name: Name of the source.

        Returns:
            New auto_update value.
        """
        registry = self.load_sources()
        for source in registry.sources:
            if source.name == source_name:
                source.auto_update = not source.auto_update
                self.save_sources(registry)
                return source.auto_update
        return False

    def get_stale_auto_update_sources(self, max_age_hours: int = 24) -> list[Source]:
        """Get sources with auto_update enabled that haven't been synced recently.

        Args:
            max_age_hours: Maximum age in hours before source is considered stale.

        Returns:
            List of stale sources that need updating.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        registry = self.load_sources()
        stale = []
        for source in registry.sources:
            if source.auto_update:
                if source.last_sync is None or source.last_sync < cutoff:
                    stale.append(source)
        return stale

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

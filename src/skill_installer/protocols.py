"""Protocol definitions for core abstractions.

This module defines abstract interfaces (Protocols) for the core services.
Designing to interfaces enables:
- Loose coupling between components
- Easy substitution of test doubles
- Clear contracts for implementations

All concrete implementations satisfy these protocols structurally (duck typing).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from skill_installer.types import InstallResult

if TYPE_CHECKING:
    from skill_installer.discovery import DiscoveredItem
    from skill_installer.registry import InstalledItem, Source



@runtime_checkable
class SourceRepository(Protocol):
    """Protocol for git repository operations.

    Implementations manage cloning, fetching, and caching of source repositories.
    """

    def clone_or_fetch(self, url: str, name: str, ref: str = "main") -> Path:
        """Clone a repository or fetch updates if already cloned.

        Args:
            url: Git repository URL.
            name: Name for the local clone.
            ref: Branch/tag to checkout.

        Returns:
            Path to the local clone.
        """
        ...

    def get_tree_hash(self, path: Path) -> str:
        """Get combined hash of all files in a directory.

        Args:
            path: Path to the directory or file.

        Returns:
            Hex digest of the hash.
        """
        ...

    def get_repo_path(self, source_name: str) -> Path:
        """Get the local path for a source repository.

        Args:
            source_name: Name of the source.

        Returns:
            Path to the local clone.
        """
        ...

    def remove_cached(self, name: str) -> bool:
        """Remove a cached repository.

        Args:
            name: Name of the source.

        Returns:
            True if removed, False if not found.
        """
        ...

    def is_cached(self, name: str) -> bool:
        """Check if a repository is cached.

        Args:
            name: Name of the source.

        Returns:
            True if cached, False otherwise.
        """
        ...

    def get_license(self, name: str) -> str | None:
        """Extract license information from a cached repository.

        Args:
            name: Name of the source.

        Returns:
            License string if found, None otherwise.
        """
        ...


@runtime_checkable
class ItemRegistry(Protocol):
    """Protocol for item registry operations.

    Implementations manage source registration and installed item tracking.
    """

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
            ref: Branch/tag reference.
            platforms: Target platforms.

        Returns:
            The created Source.
        """
        ...

    def remove_source(self, name: str) -> bool:
        """Remove a source repository.

        Args:
            name: Name of the source to remove.

        Returns:
            True if removed, False if not found.
        """
        ...

    def get_source(self, name: str) -> Source | None:
        """Get a source by name.

        Args:
            name: Name of the source.

        Returns:
            Source if found, None otherwise.
        """
        ...

    def list_sources(self) -> list[Source]:
        """List all registered sources.

        Returns:
            List of Source objects.
        """
        ...

    def update_source_sync_time(self, name: str) -> None:
        """Update the last sync time for a source.

        Args:
            name: Name of the source.
        """
        ...

    def update_source_license(self, name: str, license_text: str | None) -> None:
        """Update the license for a source.

        Args:
            name: Name of the source.
            license_text: License text to store.
        """
        ...

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
        ...

    def remove_installed(self, item_id: str, platform: str | None = None) -> bool:
        """Remove an installed item from the registry.

        Args:
            item_id: ID of the item to remove.
            platform: Optional platform filter.

        Returns:
            True if removed, False if not found.
        """
        ...

    def get_installed(
        self, item_id: str, platform: str | None = None
    ) -> list[InstalledItem]:
        """Get installed items by ID.

        Args:
            item_id: ID of the item.
            platform: Optional platform filter.

        Returns:
            List of matching InstalledItem objects.
        """
        ...

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
        ...


@runtime_checkable
class ItemDiscovery(Protocol):
    """Protocol for item discovery operations.

    Implementations discover agents, skills, and commands in source repositories.
    """

    def discover_all(
        self, repo_path: Path, platform: str | None
    ) -> list[DiscoveredItem]:
        """Discover all items in a repository.

        Args:
            repo_path: Path to the repository root.
            platform: Platform filter or None for all.

        Returns:
            List of discovered items.
        """
        ...

    def get_item_content(self, item: DiscoveredItem) -> str:
        """Get the content of a discovered item.

        Args:
            item: The discovered item.

        Returns:
            File content or combined content for skills.
        """
        ...

    def is_marketplace_repo(self, repo_path: Path) -> bool:
        """Check if a repository is marketplace-enabled.

        Args:
            repo_path: Path to the repository root.

        Returns:
            True if marketplace.json exists.
        """
        ...


@runtime_checkable
class ItemInstaller(Protocol):
    """Protocol for item installation operations.

    Implementations handle installation and uninstallation of items.
    """

    def install_item(
        self,
        item: DiscoveredItem,
        source_name: str,
        target_platform: str,
        source_platform: str | None = None,
        scope: str = "user",
        project_root: Path | None = None,
    ) -> InstallResult:
        """Install a discovered item to a target platform.

        Args:
            item: The discovered item to install.
            source_name: Name of the source repository.
            target_platform: Target platform name.
            source_platform: Source platform name (auto-detected if None).
            scope: Installation scope ("user" or "project").
            project_root: Root directory of the project.

        Returns:
            InstallResult with installation details.
        """
        ...

    def uninstall_item(
        self, item_id: str, platform: str | None = None
    ) -> list[InstallResult]:
        """Uninstall an item.

        Args:
            item_id: ID of the item to uninstall.
            platform: Optional platform filter.

        Returns:
            List of InstallResult for each uninstallation.
        """
        ...

    def check_update_needed(
        self, item: DiscoveredItem, source_name: str, platform: str
    ) -> bool:
        """Check if an installed item needs updating.

        Args:
            item: The discovered item.
            source_name: Name of the source repository.
            platform: Target platform.

        Returns:
            True if update needed, False otherwise.
        """
        ...


@runtime_checkable
class FileSystem(Protocol):
    """Protocol for filesystem operations.

    Abstracts filesystem access to enable testing without real I/O.
    Implementations handle reading, writing, and directory operations.
    """

    def read_text(self, path: Path) -> str:
        """Read text content from a file.

        Args:
            path: Path to the file.

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        ...

    def write_text(self, path: Path, content: str) -> None:
        """Write text content to a file.

        Args:
            path: Path to the file.
            content: Content to write.
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if a path exists.

        Args:
            path: Path to check.

        Returns:
            True if path exists, False otherwise.
        """
        ...

    def is_dir(self, path: Path) -> bool:
        """Check if a path is a directory.

        Args:
            path: Path to check.

        Returns:
            True if path is a directory, False otherwise.
        """
        ...

    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        """Create a directory.

        Args:
            path: Path to create.
            parents: Create parent directories if needed.
            exist_ok: Don't raise if directory exists.
        """
        ...

    def unlink(self, path: Path) -> None:
        """Remove a file.

        Args:
            path: Path to remove.
        """
        ...

    def rmtree(self, path: Path) -> None:
        """Remove a directory tree.

        Args:
            path: Path to remove.
        """
        ...

    def copytree(self, src: Path, dst: Path) -> None:
        """Copy a directory tree.

        Args:
            src: Source directory.
            dst: Destination directory.
        """
        ...


@runtime_checkable
class TransformStrategy(Protocol):
    """Protocol for content transformation between platform formats.

    Each strategy encapsulates the transformation logic for a specific
    source/target platform pair. This follows the Strategy pattern to
    eliminate switch statements in the TransformEngine.
    """

    source_platform: str
    target_platform: str

    def transform_frontmatter(self, frontmatter: dict) -> dict:
        """Transform frontmatter fields for the target platform.

        Args:
            frontmatter: Source frontmatter dictionary.

        Returns:
            Transformed frontmatter for target platform.
        """
        ...

    def transform_syntax(self, body: str) -> str:
        """Transform body syntax for the target platform.

        Args:
            body: Source content body.

        Returns:
            Transformed body with target platform syntax.
        """
        ...

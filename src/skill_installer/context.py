"""Application context for dependency injection.

This module separates object creation from object use, enabling testability
and reducing coupling in CLI commands.

Dependencies are typed using Protocols (abstract interfaces) rather than
concrete implementations. This follows "Design to Interfaces" wisdom,
enabling loose coupling and easy substitution of test doubles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from skill_installer.protocols import (
    FileSystem,
    ItemDiscovery,
    ItemInstaller,
    ItemRegistry,
    SourceRepository,
)

if TYPE_CHECKING:
    pass



def _default_filesystem() -> FileSystem:
    """Create the default filesystem implementation."""
    from skill_installer.filesystem import RealFileSystem
    return RealFileSystem()

@dataclass
class AppContext:
    """Container for application dependencies.

    Provides a single injection point for all services used by CLI commands.
    This separates object creation from object use, improving testability.

    All dependencies are typed using Protocol interfaces, not concrete classes.
    This allows test doubles to be injected without inheritance.
    """

    registry: ItemRegistry
    gitops: SourceRepository
    discovery: ItemDiscovery
    installer: ItemInstaller
    filesystem: FileSystem = field(default_factory=_default_filesystem)




def create_context(
    registry_dir: Path | None = None,
    cache_dir: Path | None = None,
) -> AppContext:
    """Factory for application dependencies.

    Creates all services with proper wiring. Use this in production code.
    For tests, construct AppContext directly with test doubles.

    Args:
        registry_dir: Override registry directory (for testing).
        cache_dir: Override git cache directory (for testing).

    Returns:
        Configured AppContext with all dependencies.
    """
    from skill_installer.discovery import Discovery
    from skill_installer.filesystem import RealFileSystem
    from skill_installer.gitops import GitOps
    from skill_installer.install import Installer
    from skill_installer.registry import RegistryManager

    registry = (
        RegistryManager.create(registry_dir)
        if registry_dir
        else RegistryManager.create_default()
    )
    gitops = GitOps.create(cache_dir) if cache_dir else GitOps.create_default()
    discovery = Discovery.create()
    filesystem = RealFileSystem()
    installer = Installer.create(registry=registry, gitops=gitops, filesystem=filesystem)

    return AppContext(
        registry=registry,
        gitops=gitops,
        discovery=discovery,
        installer=installer,
        filesystem=filesystem,
    )

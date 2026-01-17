"""Universal skill/agent installer for AI coding platforms."""

__version__ = "0.1.0"

# Export protocol interfaces for type hints and dependency injection
from skill_installer.protocols import (
    ItemDiscovery,
    ItemInstaller,
    ItemRegistry,
    SourceRepository,
)

__all__ = [
    "__version__",
    "ItemDiscovery",
    "ItemInstaller",
    "ItemRegistry",
    "SourceRepository",
]

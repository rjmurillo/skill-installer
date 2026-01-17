"""Platform-specific implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .base import BasePlatform
from .claude import ClaudePlatform
from .codex import CodexPlatform
from .copilot import CopilotPlatform
from .vscode import VSCodePlatform


@runtime_checkable
class Platform(Protocol):
    """Protocol defining the interface for platform implementations.

    All platform handlers must implement this interface to support
    the Open-Closed Principle: new platforms can be added without
    modifying existing code.
    """

    name: str
    agent_extension: str
    supports_skills: bool

    @property
    def base_dir(self) -> Path:
        """Get the base directory for this platform."""
        raise NotImplementedError

    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        raise NotImplementedError

    def get_install_path(self, item_type: str, name: str) -> Path:
        """Get the installation path for an item.

        Args:
            item_type: Type of item (agent, skill, command).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        raise NotImplementedError

    def validate_agent(self, content: str) -> list[str]:
        """Validate agent/skill content for this platform's format.

        Args:
            content: File content to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if this platform is available on the current system.

        Returns:
            True if the platform appears to be installed.
        """
        raise NotImplementedError

    def get_project_install_path(
        self, project_root: Path, item_type: str, name: str
    ) -> Path:
        """Get the project-local installation path for an item.

        Args:
            project_root: Root directory of the project.
            item_type: Type of item (agent, skill, command).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        raise NotImplementedError


__all__ = [
    "BasePlatform",
    "Platform",
    "ClaudePlatform",
    "VSCodePlatform",
    "CopilotPlatform",
    "CodexPlatform",
    "get_platform",
    "get_available_platforms",
]


PLATFORMS: dict[str, type[Platform]] = {
    "claude": ClaudePlatform,
    "vscode": VSCodePlatform,
    "vscode-insiders": VSCodePlatform,  # Uses same class with different config
    "copilot": CopilotPlatform,
    "codex": CodexPlatform,
}


def get_platform(name: str) -> Platform:
    """Get a platform instance by name.

    Args:
        name: Platform name (claude, vscode, vscode-insiders, copilot, codex).

    Returns:
        Platform instance.

    Raises:
        ValueError: If platform is not supported.
    """
    if name not in PLATFORMS:
        raise ValueError(f"Unknown platform: {name}. Supported: {list(PLATFORMS.keys())}")

    platform_class = PLATFORMS[name]
    if name == "vscode-insiders":
        return platform_class(insiders=True)
    return platform_class()


def get_available_platforms() -> list[dict[str, str]]:
    """Get all available platforms on the current system.

    Returns:
        List of dicts with keys: id, name, path_description.
        Empty list if no platforms are available.
    """
    available = []

    for platform_id in PLATFORMS:
        try:
            platform = get_platform(platform_id)
            if platform.is_available():
                info = {
                    "id": platform_id,
                    "name": _get_platform_display_name(platform_id),
                    "path_description": _get_platform_path_description(platform, platform_id),
                }
                available.append(info)
        except Exception:
            continue

    return available


def _get_platform_display_name(platform_id: str) -> str:
    """Get display name for a platform.

    Args:
        platform_id: Platform identifier.

    Returns:
        Human-readable platform name.
    """
    names = {
        "claude": "Claude Code",
        "vscode": "VS Code",
        "vscode-insiders": "VS Code Insiders",
        "copilot": "Copilot CLI",
        "codex": "Codex CLI",
    }
    return names.get(platform_id, platform_id)


def _get_platform_path_description(
    platform: Platform,
    platform_id: str,
) -> str:
    """Get path description for a platform.

    Args:
        platform: Platform instance.
        platform_id: Platform identifier.

    Returns:
        Human-readable path description.
    """
    # All platforms expose base_dir via the Protocol.
    # Platform-specific subdirectories are implementation details.
    return str(platform.base_dir)

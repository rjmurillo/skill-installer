"""Platform-specific implementations."""

from __future__ import annotations

from .claude import ClaudePlatform
from .copilot import CopilotPlatform
from .vscode import VSCodePlatform

__all__ = ["ClaudePlatform", "VSCodePlatform", "CopilotPlatform", "get_platform"]


PLATFORMS = {
    "claude": ClaudePlatform,
    "vscode": VSCodePlatform,
    "vscode-insiders": VSCodePlatform,  # Uses same class with different config
    "copilot": CopilotPlatform,
}


def get_platform(name: str) -> ClaudePlatform | VSCodePlatform | CopilotPlatform:
    """Get a platform instance by name.

    Args:
        name: Platform name (claude, vscode, vscode-insiders, copilot).

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

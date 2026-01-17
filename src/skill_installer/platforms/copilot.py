"""GitHub Copilot CLI platform implementation."""

from __future__ import annotations

import sys
from pathlib import Path

from skill_installer.platforms.base import BasePlatform


class CopilotPlatform(BasePlatform):
    """GitHub Copilot CLI platform handler."""

    name = "copilot"
    agent_extension = ".agent.md"
    supports_skills = False

    def __init__(self) -> None:
        """Initialize Copilot CLI platform."""
        self._base_dir: Path | None = None

    @property
    def base_dir(self) -> Path:
        """Get the base directory for Copilot CLI.

        Returns:
            Path to ~/.copilot/
        """
        if self._base_dir is None:
            self._base_dir = Path.home() / ".copilot"
        return self._base_dir

    @property
    def agents_dir(self) -> Path:
        """Get the agents directory.

        Returns:
            Path to ~/.copilot/agents/
        """
        return self.base_dir / "agents"

    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)

    def get_install_path(self, item_type: str, name: str) -> Path:
        """Get the installation path for an item.

        Args:
            item_type: Type of item (agent only for Copilot).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        if item_type == "agent":
            return self.agents_dir / f"{name}{self.agent_extension}"
        if item_type in ("skill", "command"):
            raise ValueError(f"Copilot CLI does not support {item_type}s")
        raise ValueError(f"Unknown item type: {item_type}")

    def get_required_fields(self) -> list[str]:
        """Copilot agents have no required frontmatter fields per spec."""
        return []

    def get_field_error_message(self, field: str) -> str:
        """Provide Copilot-specific error messages."""
        if field == "name:":
            return "Copilot agents must include 'name' field"
        if field == "tools:":
            return "Copilot agents must include 'tools' field"
        return super().get_field_error_message(field)

    def is_available(self) -> bool:
        """Check if Copilot CLI is available on this system.

        Returns:
            True if Copilot CLI appears to be installed.
        """
        if sys.platform == "win32":
            # Check for gh copilot extension
            gh_path = Path.home() / "AppData" / "Local" / "GitHub CLI" / "extensions"
            return (gh_path / "gh-copilot").exists()
        # Linux/macOS
        gh_path = Path.home() / ".local" / "share" / "gh" / "extensions"
        return (gh_path / "gh-copilot").exists()

    def get_project_install_path(
        self, project_root: Path, item_type: str, name: str
    ) -> Path:
        """Get the project-local installation path for an item.

        Args:
            project_root: Root directory of the project.
            item_type: Type of item (agent only for Copilot).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        base = project_root / ".github" / "copilot"
        if item_type == "agent":
            return base / "agents" / f"{name}{self.agent_extension}"
        if item_type in ("skill", "command"):
            raise ValueError(f"Copilot CLI does not support {item_type}s")
        raise ValueError(f"Unknown item type: {item_type}")

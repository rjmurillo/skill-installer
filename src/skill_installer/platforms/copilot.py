"""GitHub Copilot CLI platform implementation."""

from __future__ import annotations

import sys
from pathlib import Path


class CopilotPlatform:
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

    def validate_agent(self, content: str) -> list[str]:
        """Validate agent content for Copilot CLI format.

        Args:
            content: Agent file content.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Check for frontmatter
        if not content.startswith("---"):
            errors.append("Agent must have YAML frontmatter")
            return errors

        # Parse frontmatter
        try:
            end_idx = content.index("---", 3)
            frontmatter = content[3:end_idx].strip()
        except ValueError:
            errors.append("Invalid frontmatter: missing closing ---")
            return errors

        # Check required fields for Copilot
        if "name:" not in frontmatter:
            errors.append("Copilot agents must include 'name' field")
        if "tools:" not in frontmatter:
            errors.append("Copilot agents must include 'tools' field")

        return errors

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

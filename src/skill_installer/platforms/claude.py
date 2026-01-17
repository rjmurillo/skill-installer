"""Claude Code platform implementation."""

from __future__ import annotations

import sys
from pathlib import Path

from skill_installer.platforms.base import BasePlatform


class ClaudePlatform(BasePlatform):
    """Claude Code platform handler."""

    name = "claude"
    agent_extension = ".md"
    supports_skills = True

    def __init__(self) -> None:
        """Initialize Claude platform."""
        self._base_dir: Path | None = None

    @property
    def base_dir(self) -> Path:
        """Get the base directory for Claude Code.

        Returns:
            Path to ~/.claude/
        """
        if self._base_dir is None:
            self._base_dir = Path.home() / ".claude"
        return self._base_dir

    @property
    def agents_dir(self) -> Path:
        """Get the agents directory.

        Returns:
            Path to ~/.claude/agents/
        """
        return self.base_dir / "agents"

    @property
    def skills_dir(self) -> Path:
        """Get the skills directory.

        Returns:
            Path to ~/.claude/skills/
        """
        return self.base_dir / "skills"

    @property
    def commands_dir(self) -> Path:
        """Get the commands directory.

        Returns:
            Path to ~/.claude/commands/
        """
        return self.base_dir / "commands"

    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.commands_dir.mkdir(parents=True, exist_ok=True)

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
        if item_type == "agent":
            return self.agents_dir / f"{name}{self.agent_extension}"
        if item_type == "skill":
            return self.skills_dir / name
        if item_type == "command":
            return self.commands_dir / f"{name}{self.agent_extension}"
        raise ValueError(f"Unknown item type: {item_type}")

    def get_required_fields(self) -> list[str]:
        """Claude Code requires 'name' field in frontmatter."""
        return ["name:"]

    def is_available(self) -> bool:
        """Check if Claude Code is available on this system.

        Returns:
            True if Claude Code appears to be installed.
        """
        # Check for claude command
        if sys.platform == "win32":
            claude_path = Path.home() / "AppData" / "Local" / "Programs" / "claude"
            return claude_path.exists() or self.base_dir.exists()
        return self.base_dir.exists()

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
        base = project_root / ".claude"
        if item_type == "agent":
            return base / "agents" / f"{name}{self.agent_extension}"
        if item_type == "skill":
            return base / "skills" / name
        if item_type == "command":
            return base / "commands" / f"{name}{self.agent_extension}"
        raise ValueError(f"Unknown item type: {item_type}")

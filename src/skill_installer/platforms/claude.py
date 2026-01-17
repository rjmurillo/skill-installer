"""Claude Code platform implementation."""

from __future__ import annotations

import sys
from pathlib import Path


class ClaudePlatform:
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

    def validate_agent(self, content: str) -> list[str]:
        """Validate agent content for Claude format.

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

        # Check required fields
        if "name:" not in frontmatter:
            errors.append("Frontmatter must include 'name' field")

        return errors

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

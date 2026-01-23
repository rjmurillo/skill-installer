"""Codex CLI / OpenAI Codex platform implementation."""

from __future__ import annotations

from pathlib import Path

from skill_installer.platforms.base import BasePlatform


class CodexPlatform(BasePlatform):
    """Codex CLI / OpenAI Codex platform handler."""

    name = "codex"
    agent_extension = ".md"
    supports_skills = True

    def __init__(self) -> None:
        """Initialize Codex platform."""
        self._base_dir: Path | None = None

    @property
    def base_dir(self) -> Path:
        """Get the base directory for Codex.

        Returns:
            Path to ~/.config/opencode/
        """
        if self._base_dir is None:
            self._base_dir = Path.home() / ".config" / "opencode"
        return self._base_dir

    @property
    def skills_dir(self) -> Path:
        """Get the skills directory.

        Returns:
            Path to ~/.config/opencode/skill/
        """
        return self.base_dir / "skill"

    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def get_install_path(self, item_type: str, name: str) -> Path:
        """Get the installation path for an item.

        Args:
            item_type: Type of item (skill only for Codex).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        if item_type == "skill":
            return self.skills_dir / name
        raise ValueError(f"Codex only supports skills, not {item_type}")

    # validate_agent inherited from BasePlatform
    # get_required_fields returns ["name:"] by default, which is correct for Codex

    def is_available(self) -> bool:
        """Check if Codex CLI is available on this system.

        Returns:
            True if Codex appears to be installed.
        """
        # Check if the config directory exists
        return self.base_dir.exists() or self.skills_dir.exists()

    def get_project_install_path(self, project_root: Path, item_type: str, name: str) -> Path:
        """Get the project-local installation path for an item.

        Args:
            project_root: Root directory of the project.
            item_type: Type of item (skill only for Codex).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        # Codex uses .codex directory for project-local skills
        base = project_root / ".codex"
        if item_type == "skill":
            return base / "skills" / name
        raise ValueError(f"Codex only supports skills, not {item_type}")

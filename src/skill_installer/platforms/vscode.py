"""VS Code platform implementation."""

from __future__ import annotations

import sys
from pathlib import Path

from skill_installer.platforms.base import BasePlatform


class VSCodePlatform(BasePlatform):
    """VS Code platform handler."""

    name = "vscode"
    agent_extension = ".agent.md"
    supports_skills = False

    def __init__(self, insiders: bool = False) -> None:
        """Initialize VS Code platform.

        Args:
            insiders: Use VS Code Insiders paths.
        """
        self.insiders = insiders
        self._base_dir: Path | None = None

        if insiders:
            self.name = "vscode-insiders"

    @property
    def base_dir(self) -> Path:
        """Get the base directory for VS Code prompts.

        Returns:
            Platform-specific path to VS Code User/prompts directory.
        """
        if self._base_dir is None:
            if sys.platform == "darwin":
                base = Path.home() / "Library" / "Application Support"
            elif sys.platform == "win32":
                base = Path.home() / "AppData" / "Roaming"
            else:
                base = Path.home() / ".config"

            if self.insiders:
                self._base_dir = base / "Code - Insiders" / "User" / "prompts"
            else:
                self._base_dir = base / "Code" / "User" / "prompts"
        return self._base_dir

    @property
    def agents_dir(self) -> Path:
        """Get the agents directory.

        Returns:
            Path to prompts directory (VS Code doesn't separate agents).
        """
        return self.base_dir

    def ensure_dirs(self) -> None:
        """Create platform directories if they don't exist."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_install_path(self, item_type: str, name: str) -> Path:
        """Get the installation path for an item.

        Args:
            item_type: Type of item (agent only for VS Code).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        if item_type == "agent":
            return self.base_dir / f"{name}{self.agent_extension}"
        if item_type in ("skill", "command"):
            raise ValueError(f"VS Code does not support {item_type}s")
        raise ValueError(f"Unknown item type: {item_type}")

    def get_required_fields(self) -> list[str]:
        """VS Code agents have no required frontmatter fields per spec."""
        return []

    def get_field_error_message(self, field: str) -> str:
        """Provide VS Code-specific error message."""
        if field == "tools:":
            return "VS Code agents must include 'tools' field"
        return super().get_field_error_message(field)

    def is_available(self) -> bool:
        """Check if VS Code is available on this system.

        Returns:
            True if VS Code appears to be installed.
        """
        if sys.platform == "darwin":
            app_path = Path("/Applications/Visual Studio Code.app")
            if self.insiders:
                app_path = Path("/Applications/Visual Studio Code - Insiders.app")
            return app_path.exists()
        if sys.platform == "win32":
            # Check common install locations
            program_files = Path("C:/Program Files/Microsoft VS Code")
            if self.insiders:
                program_files = Path("C:/Program Files/Microsoft VS Code Insiders")
            return program_files.exists()
        # Linux: check if code command exists in common locations
        code_cmd = "code-insiders" if self.insiders else "code"
        search_paths = [
            Path("/usr/bin") / code_cmd,
            Path("/usr/local/bin") / code_cmd,
            Path("/snap/bin") / code_cmd,
        ]
        return any(p.exists() for p in search_paths)

    def get_project_install_path(
        self, project_root: Path, item_type: str, name: str
    ) -> Path:
        """Get the project-local installation path for an item.

        Args:
            project_root: Root directory of the project.
            item_type: Type of item (agent only for VS Code).
            name: Name of the item.

        Returns:
            Full path where item should be installed.

        Raises:
            ValueError: If item type is not supported.
        """
        base = project_root / ".vscode"
        if item_type == "agent":
            return base / "agents" / f"{name}{self.agent_extension}"
        if item_type in ("skill", "command"):
            raise ValueError(f"VS Code does not support {item_type}s")
        raise ValueError(f"Unknown item type: {item_type}")

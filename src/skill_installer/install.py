"""Installation operations for skills and agents."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skill_installer.discovery import DiscoveredItem
from skill_installer.gitops import GitOps
from skill_installer.platforms import get_platform
from skill_installer.registry import RegistryManager
from skill_installer.transform import TransformEngine

if TYPE_CHECKING:
    pass


@dataclass
class InstallResult:
    """Result of an installation operation."""

    success: bool
    item_id: str
    platform: str
    installed_path: Path | None
    error: str | None = None


class Installer:
    """Handles installation of skills and agents."""

    def __init__(
        self,
        registry: RegistryManager | None = None,
        gitops: GitOps | None = None,
        transformer: TransformEngine | None = None,
    ) -> None:
        """Initialize installer.

        Args:
            registry: Registry manager instance.
            gitops: Git operations instance.
            transformer: Transform engine instance.
        """
        self.registry = registry or RegistryManager()
        self.gitops = gitops or GitOps()
        self.transformer = transformer or TransformEngine()

    def install_item(
        self,
        item: DiscoveredItem,
        source_name: str,
        target_platform: str,
        source_platform: str | None = None,
    ) -> InstallResult:
        """Install a discovered item to a target platform.

        Args:
            item: The discovered item to install.
            source_name: Name of the source repository.
            target_platform: Target platform name.
            source_platform: Source platform name (auto-detected if None).

        Returns:
            InstallResult with installation details.
        """
        item_id = f"{source_name}/{item.item_type}/{item.name}"

        try:
            # Get target platform handler
            platform = get_platform(target_platform)

            # Ensure target directories exist
            platform.ensure_dirs()

            # Detect source platform if not specified
            if source_platform is None:
                source_platform = self._detect_source_platform(item)

            # Get content and transform if needed
            content = self._get_content(item)
            if source_platform != target_platform:
                content = self.transformer.transform(content, source_platform, target_platform)

            # Validate content
            errors = platform.validate_agent(content)
            if errors:
                return InstallResult(
                    success=False,
                    item_id=item_id,
                    platform=target_platform,
                    installed_path=None,
                    error=f"Validation failed: {'; '.join(errors)}",
                )

            # Determine install path
            install_path = platform.get_install_path(item.item_type, item.name)

            # Install content
            if item.item_type == "skill":
                self._install_skill(item.path, install_path)
            else:
                install_path.parent.mkdir(parents=True, exist_ok=True)
                install_path.write_text(content)

            # Calculate source hash
            source_hash = self.gitops.get_tree_hash(item.path)

            # Register installation
            self.registry.add_installed(
                source_name=source_name,
                item_type=item.item_type,
                name=item.name,
                platform=target_platform,
                installed_path=str(install_path),
                source_hash=source_hash,
            )

            return InstallResult(
                success=True,
                item_id=item_id,
                platform=target_platform,
                installed_path=install_path,
            )

        except Exception as e:
            return InstallResult(
                success=False,
                item_id=item_id,
                platform=target_platform,
                installed_path=None,
                error=str(e),
            )

    def uninstall_item(self, item_id: str, platform: str | None = None) -> list[InstallResult]:
        """Uninstall an item.

        Args:
            item_id: ID of the item to uninstall.
            platform: Optional platform filter.

        Returns:
            List of InstallResult for each uninstallation.
        """
        results = []
        installed = self.registry.get_installed(item_id, platform)

        for item in installed:
            try:
                path = Path(item.installed_path)
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

                self.registry.remove_installed(item_id, item.platform)

                results.append(
                    InstallResult(
                        success=True,
                        item_id=item_id,
                        platform=item.platform,
                        installed_path=path,
                    )
                )
            except Exception as e:
                results.append(
                    InstallResult(
                        success=False,
                        item_id=item_id,
                        platform=item.platform,
                        installed_path=None,
                        error=str(e),
                    )
                )

        return results

    def check_update_needed(
        self, item: DiscoveredItem, source_name: str, platform: str
    ) -> bool:
        """Check if an installed item needs updating.

        Args:
            item: The discovered item.
            source_name: Name of the source repository.
            platform: Target platform.

        Returns:
            True if update needed, False otherwise.
        """
        item_id = f"{source_name}/{item.item_type}/{item.name}"
        installed = self.registry.get_installed(item_id, platform)

        if not installed:
            return True  # Not installed, needs install

        current_hash = self.gitops.get_tree_hash(item.path)
        return installed[0].source_hash != current_hash

    def _get_content(self, item: DiscoveredItem) -> str:
        """Get content for an item.

        Args:
            item: The discovered item.

        Returns:
            File content.
        """
        if item.item_type == "skill":
            skill_file = item.path / "SKILL.md"
            return skill_file.read_text()
        return item.path.read_text()

    def _detect_source_platform(self, item: DiscoveredItem) -> str:
        """Detect the source platform of an item.

        Args:
            item: The discovered item.

        Returns:
            Platform name.
        """
        if item.platforms:
            return item.platforms[0]

        # Check file extension
        if item.path.name.endswith(".agent.md"):
            return "vscode"
        return "claude"

    def _install_skill(self, source_path: Path, install_path: Path) -> None:
        """Install a skill directory.

        Args:
            source_path: Source skill directory.
            install_path: Target installation directory.
        """
        # Remove existing if present
        if install_path.exists():
            shutil.rmtree(install_path)

        # Copy entire skill directory
        shutil.copytree(source_path, install_path)

"""Installation operations for skills and agents."""

from __future__ import annotations

import logging
from pathlib import Path

from skill_installer.discovery import DiscoveredItem
from skill_installer.filesystem import RealFileSystem
from skill_installer.gitops import GitOps

from skill_installer.platforms import get_platform
from skill_installer.protocols import FileSystem
from skill_installer.registry import RegistryManager
from skill_installer.transform import TransformEngine
from skill_installer.types import InstallResult

logger = logging.getLogger(__name__)


def get_project_root(start_path: Path | None = None) -> Path | None:
    """Find nearest parent directory containing .git.

    Args:
        start_path: Starting directory. Defaults to cwd.

    Returns:
        Path to project root or None if not in a git repo.
    """
    path = start_path or Path.cwd()
    # Resolve to handle symlinks and get absolute path
    path = path.resolve()
    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent
    # Check root directory as well
    if (path / ".git").exists():
        return path
    return None


class Installer:
    """Handles installation of skills and agents.

    Follows Separate Use from Creation: constructor requires all dependencies.
    Use factory method `create()` for production instantiation with defaults.
    """

    def __init__(
        self,
        registry: RegistryManager,
        gitops: GitOps,
        transformer: "TransformEngine",
        filesystem: FileSystem,
    ) -> None:
        """Initialize installer with required dependencies.

        Args:
            registry: Registry manager instance (required).
            gitops: Git operations instance (required).
            transformer: Transform engine instance (required).
            filesystem: Filesystem abstraction (required).

        Note:
            Use factory method `create()` for production code.
            Direct construction is for testing with explicit dependencies.
        """
        self.registry = registry
        self.gitops = gitops
        self.transformer = transformer
        self.fs = filesystem

    @classmethod
    def create(
        cls,
        registry: RegistryManager,
        gitops: GitOps,
        transformer: "TransformEngine" | None = None,
        filesystem: FileSystem | None = None,
    ) -> Installer:
        """Factory method for production instantiation.

        Creates an installer with optional default dependencies.
        This is the only place where defaults are created, separating
        object creation from object use.

        Args:
            registry: Registry manager instance.
            gitops: Git operations instance.
            transformer: Optional transform engine (created if not provided).
            filesystem: Optional filesystem abstraction (created if not provided).

        Returns:
            Configured Installer instance.
        """
        return cls(
            registry=registry,
            gitops=gitops,
            transformer=transformer or TransformEngine(),
            filesystem=filesystem or RealFileSystem(),
        )

    def install_item(
        self,
        item: DiscoveredItem,
        source_name: str,
        target_platform: str,
        source_platform: str | None = None,
        scope: str = "user",
        project_root: Path | None = None,
    ) -> InstallResult:
        """Install a discovered item to a target platform.

        Args:
            item: The discovered item to install.
            source_name: Name of the source repository.
            target_platform: Target platform name.
            source_platform: Source platform name (auto-detected if None).
            scope: Installation scope, either "user" or "project".
            project_root: Root directory of the project (required if scope="project").

        Returns:
            InstallResult with installation details.

        Raises:
            ValueError: If scope="project" but project_root is None.
        """
        item_id = item.make_item_id(source_name)

        # Validate project scope parameters
        if scope == "project" and project_root is None:
            return InstallResult(
                success=False,
                item_id=item_id,
                platform=target_platform,
                installed_path=None,
                error="project_root is required when scope='project'",
            )

        try:
            # Get target platform handler
            platform = get_platform(target_platform)

            # Ensure target directories exist (only for user scope)
            if scope == "user":
                platform.ensure_dirs()

            # Detect source platform if not specified
            if source_platform is None:
                source_platform = self._detect_source_platform(item)

            # Block cross-platform installation between incompatible platforms
            # Claude Code and VSCode/Copilot use incompatible frontmatter formats
            error = self._check_cross_platform_compatibility(source_platform, target_platform)
            if error:
                return InstallResult(
                    success=False,
                    item_id=item_id,
                    platform=target_platform,
                    installed_path=None,
                    error=error,
                )

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

            # Determine install path based on scope
            if scope == "project" and project_root is not None:
                install_path = platform.get_project_install_path(
                    project_root, item.item_type, item.name
                )
            else:
                install_path = platform.get_install_path(item.item_type, item.name)

            # Install content
            if item.item_type == "skill":
                self._install_skill(item.path, install_path)
            else:
                self.fs.mkdir(install_path.parent, parents=True, exist_ok=True)
                self.fs.write_text(install_path, content)

            # Calculate source hash
            source_hash = self.gitops.get_tree_hash(item.path)

            # Register installation
            self.registry.add_installed(
                source_name=source_name,
                item_type=item.item_type,
                name=item.item_key,
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
            logger.exception("Installation failed for %s", item_id)
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
                if self.fs.exists(path):
                    if self.fs.is_dir(path):
                        self.fs.rmtree(path)
                    else:
                        self.fs.unlink(path)

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
                logger.exception("Uninstallation failed for %s on %s", item_id, item.platform)
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

    def check_update_needed(self, item: DiscoveredItem, source_name: str, platform: str) -> bool:
        """Check if an installed item needs updating.

        Args:
            item: The discovered item.
            source_name: Name of the source repository.
            platform: Target platform.

        Returns:
            True if update needed, False otherwise.
        """
        item_id = item.make_item_id(source_name)
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
            return self.fs.read_text(skill_file)
        return self.fs.read_text(item.path)

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

    def _check_cross_platform_compatibility(
        self, source_platform: str, target_platform: str
    ) -> str | None:
        """Check if cross-platform installation is allowed.

        Claude Code and VSCode/Copilot use incompatible frontmatter formats.
        Cross-installation between these platform families is blocked.

        References:
            - Claude Code: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/agents
            - Copilot: https://docs.github.com/en/copilot/reference/custom-agents-configuration
            - VSCode: https://code.visualstudio.com/docs/copilot/customization/custom-agents

        Args:
            source_platform: Source platform name.
            target_platform: Target platform name.

        Returns:
            Error message if incompatible, None if compatible.
        """
        if source_platform == target_platform:
            return None

        claude_platforms = {"claude"}
        vscode_platforms = {"vscode", "vscode-insiders", "copilot"}

        source_is_claude = source_platform.lower() in claude_platforms
        target_is_claude = target_platform.lower() in claude_platforms
        source_is_vscode = source_platform.lower() in vscode_platforms
        target_is_vscode = target_platform.lower() in vscode_platforms

        # Block Claude to VSCode/Copilot
        if source_is_claude and target_is_vscode:
            return (
                f"Cannot install Claude agent to {target_platform}: "
                "incompatible frontmatter formats. "
                "See ROADMAP.md for details."
            )

        # Block VSCode/Copilot to Claude
        if source_is_vscode and target_is_claude:
            return (
                f"Cannot install {source_platform} agent to Claude: "
                "incompatible frontmatter formats. "
                "See ROADMAP.md for details."
            )

        return None

    def _install_skill(self, source_path: Path, install_path: Path) -> None:
        """Install a skill directory.

        Args:
            source_path: Source skill directory.
            install_path: Target installation directory.
        """
        # Remove existing if present
        if self.fs.exists(install_path):
            self.fs.rmtree(install_path)

        # Copy entire skill directory
        self.fs.copytree(source_path, install_path)

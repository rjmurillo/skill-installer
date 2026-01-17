"""Discovery of agents, skills, and commands in source repositories."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from skill_installer.registry import MarketplaceManifest


@dataclass
class DiscoveredItem:
    """A discovered item in a source repository."""

    name: str
    item_type: str  # agent, skill, command
    path: Path
    description: str = ""
    platforms: list[str] = field(default_factory=list)
    frontmatter: dict = field(default_factory=dict)


class Discovery:
    """Discovers content in source repositories."""

    SKILL_PATTERN = "SKILL.md"
    MARKETPLACE_DIR = ".claude-plugin"
    MARKETPLACE_FILE = "marketplace.json"
    # Directories to skip during auto-discovery
    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"}
    # Files to skip (common non-agent markdown files)
    SKIP_FILES = {"README.md", "CHANGELOG.md", "CONTRIBUTING.md", "LICENSE.md", "SECURITY.md"}

    def __init__(self) -> None:
        """Initialize discovery."""
        pass

    def is_marketplace_repo(self, repo_path: Path) -> bool:
        """Check if a repository is marketplace-enabled.

        Args:
            repo_path: Path to the repository root.

        Returns:
            True if marketplace.json exists.
        """
        marketplace_path = repo_path / self.MARKETPLACE_DIR / self.MARKETPLACE_FILE
        return marketplace_path.exists()

    def load_marketplace_manifest(self, repo_path: Path) -> MarketplaceManifest | None:
        """Load and parse marketplace manifest.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Parsed MarketplaceManifest or None if not found/invalid.
        """
        from skill_installer.registry import MarketplaceManifest

        marketplace_path = repo_path / self.MARKETPLACE_DIR / self.MARKETPLACE_FILE
        if not marketplace_path.exists():
            return None

        try:
            return MarketplaceManifest.from_file(marketplace_path)
        except (json.JSONDecodeError, ValueError):
            return None

    def discover_from_marketplace(self, repo_path: Path) -> list[DiscoveredItem]:
        """Discover items using marketplace manifest.

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered items from marketplace plugins.
        """
        manifest = self.load_marketplace_manifest(repo_path)
        if not manifest:
            return []

        items: list[DiscoveredItem] = []
        for plugin in manifest.plugins:
            for skill_path_str in plugin.skills:
                skill_path = repo_path / skill_path_str.lstrip("./")
                if skill_path.is_dir():
                    item = self._parse_skill_dir(skill_path, plugin_name=plugin.name)
                    if item:
                        items.append(item)

        return items

    def discover_all(self, repo_path: Path) -> list[DiscoveredItem]:
        """Discover all items in a repository.

        For marketplace-enabled repos, uses the marketplace manifest.
        Otherwise, auto-discovers:
        - Agents: *.agent.md files, or *.md files with frontmatter containing 'name'
        - Skills: Directories containing SKILL.md
        - Commands: *.md files in .claude/commands/ directories with frontmatter

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered items.
        """
        # Check if this is a marketplace repo first
        if self.is_marketplace_repo(repo_path):
            return self.discover_from_marketplace(repo_path)

        items: list[DiscoveredItem] = []

        # Auto-discover agents
        items.extend(self._auto_discover_agents(repo_path))

        # Auto-discover skills
        items.extend(self._auto_discover_skills(repo_path))

        # Auto-discover commands
        items.extend(self._auto_discover_commands(repo_path))

        return items

    def _auto_discover_agents(self, repo_path: Path) -> list[DiscoveredItem]:
        """Auto-discover agents by searching for agent files.

        Discovers:
        - *.agent.md files anywhere (VS Code/Copilot agents)
        - *.md files with valid frontmatter (name field required)

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered agents.
        """
        items = []
        seen_paths: set[Path] = set()

        # 1. Find all .agent.md files (unambiguous agent marker)
        for agent_file in repo_path.glob("**/*.agent.md"):
            if any(skip_dir in agent_file.parts for skip_dir in self.SKIP_DIRS):
                continue
            if agent_file not in seen_paths:
                item = self._parse_agent_file(agent_file, "agent")
                if item:
                    items.append(item)
                    seen_paths.add(agent_file)

        # 2. Find .md files with valid agent frontmatter (must have 'name' field)
        for md_file in repo_path.glob("**/*.md"):
            if any(skip_dir in md_file.parts for skip_dir in self.SKIP_DIRS):
                continue
            if md_file.name in self.SKIP_FILES:
                continue
            if md_file.name.endswith(".agent.md"):
                continue  # Already handled above
            if md_file.name == self.SKILL_PATTERN:
                continue  # Skills are handled separately
            if md_file in seen_paths:
                continue

            item = self._parse_agent_file(md_file, "agent", require_frontmatter=True)
            if item:
                items.append(item)
                seen_paths.add(md_file)

        return items

    def _discover_skills(self, skills_dir: Path) -> list[DiscoveredItem]:
        """Discover skills in a directory.

        Args:
            skills_dir: Path to skills directory.

        Returns:
            List of discovered skills.
        """
        items = []

        # Skills are directories containing SKILL.md
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                skill_file = skill_path / self.SKILL_PATTERN
                if skill_file.exists():
                    item = self._parse_skill_dir(skill_path)
                    if item:
                        items.append(item)

        return items

    def _auto_discover_skills(self, repo_path: Path) -> list[DiscoveredItem]:
        """Auto-discover skills by searching for SKILL.md files recursively.

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered skills.
        """
        items = []

        for skill_file in repo_path.glob("**/SKILL.md"):
            # Skip if in a directory we should ignore
            if any(skip_dir in skill_file.parts for skip_dir in self.SKIP_DIRS):
                continue

            # The skill directory is the parent of SKILL.md
            skill_path = skill_file.parent

            # Skip if it's the repo root itself (SKILL.md shouldn't be at root)
            if skill_path == repo_path:
                continue

            item = self._parse_skill_dir(skill_path)
            if item:
                items.append(item)

        return items

    def _auto_discover_commands(self, repo_path: Path) -> list[DiscoveredItem]:
        """Auto-discover commands by searching for .claude/commands/ directories.

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered commands.
        """
        items = []

        # Search for commands directories (typically .claude/commands/)
        for commands_dir in repo_path.glob("**/.claude/commands"):
            if not commands_dir.is_dir():
                continue
            if any(skip_dir in commands_dir.parts for skip_dir in self.SKIP_DIRS):
                continue

            # Commands are .md files with frontmatter
            for path in commands_dir.glob("*.md"):
                if path.is_file() and path.name not in self.SKIP_FILES:
                    item = self._parse_agent_file(path, "command", require_frontmatter=True)
                    if item:
                        items.append(item)

        return items

    def _parse_agent_file(
        self, path: Path, item_type: str, require_frontmatter: bool = False
    ) -> DiscoveredItem | None:
        """Parse an agent/command file.

        Args:
            path: Path to the file.
            item_type: Type of item (agent, command).
            require_frontmatter: If True, only return item if frontmatter has 'name' field.

        Returns:
            DiscoveredItem or None if parsing fails or validation fails.
        """
        try:
            content = path.read_text()
            frontmatter = self._parse_frontmatter(content)

            # If frontmatter is required, must have 'name' field
            if require_frontmatter:
                if not frontmatter or "name" not in frontmatter:
                    return None

            # Derive name from frontmatter or filename
            name = frontmatter.get("name", path.stem)
            if name.endswith(".agent"):
                name = name[:-6]

            description = frontmatter.get("description", "")

            # Determine platforms based on file extension
            platforms = []
            if path.suffix == ".md" and not path.name.endswith(".agent.md"):
                platforms = ["claude"]
            elif path.name.endswith(".agent.md"):
                platforms = ["vscode", "copilot"]

            return DiscoveredItem(
                name=name,
                item_type=item_type,
                path=path,
                description=description,
                platforms=platforms,
                frontmatter=frontmatter,
            )
        except Exception:
            return None

    def _parse_skill_dir(
        self, path: Path, plugin_name: str | None = None
    ) -> DiscoveredItem | None:
        """Parse a skill directory.

        Args:
            path: Path to the skill directory.
            plugin_name: Optional plugin name from marketplace manifest.

        Returns:
            DiscoveredItem or None if parsing fails.
        """
        skill_file = path / self.SKILL_PATTERN
        try:
            content = skill_file.read_text()
            frontmatter = self._parse_frontmatter(content)

            # Add plugin name to frontmatter if from marketplace
            if plugin_name:
                frontmatter["plugin"] = plugin_name

            name = frontmatter.get("name", path.name)
            description = frontmatter.get("description", "")

            return DiscoveredItem(
                name=name,
                item_type="skill",
                path=path,
                description=description,
                platforms=["claude"],  # Skills only for Claude
                frontmatter=frontmatter,
            )
        except Exception:
            return None

    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from content.

        Args:
            content: File content with frontmatter.

        Returns:
            Parsed frontmatter dict, empty if none found.
        """
        if not content.startswith("---"):
            return {}

        try:
            end_idx = content.index("---", 3)
            frontmatter_str = content[3:end_idx].strip()
            return yaml.safe_load(frontmatter_str) or {}
        except (ValueError, yaml.YAMLError):
            return {}

    def get_item_content(self, item: DiscoveredItem) -> str:
        """Get the content of a discovered item.

        Args:
            item: The discovered item.

        Returns:
            File content or combined content for skills.
        """
        if item.item_type == "skill":
            # For skills, return SKILL.md content
            skill_file = item.path / self.SKILL_PATTERN
            return skill_file.read_text()
        return item.path.read_text()

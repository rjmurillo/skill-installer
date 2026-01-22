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
    item_type: str  # agent, skill, command, prompt
    path: Path
    description: str = ""
    platforms: list[str] = field(default_factory=list)
    frontmatter: dict = field(default_factory=dict)
    relative_path: str = ""  # Path relative to repo root for disambiguation

    @property
    def item_key(self) -> str:
        """The unique key for this item within its type.

        Uses relative_path if available for disambiguation, otherwise name.
        This is the single source of truth for item identification.
        """
        return self.relative_path if self.relative_path else self.name

    def make_item_id(self, source_name: str) -> str:
        """Build the canonical item ID.

        Args:
            source_name: Name of the source repository.

        Returns:
            The canonical item ID in format: {source}/{type}/{key}
        """
        return f"{source_name}/{self.item_type}/{self.item_key}"


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
        """Initialize discovery.

        Note:
            Prefer using factory method `create()` for construction.
        """
        pass

    @classmethod
    def create(cls) -> "Discovery":
        """Create a discovery instance.

        Returns:
            Configured Discovery instance.
        """
        return cls()

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
            for agent_path_str in plugin.agents:
                agent_path = repo_path / agent_path_str.lstrip("./")
                if agent_path.is_file():
                    item = self._parse_agent_file(
                        agent_path,
                        "agent",
                        repo_path=repo_path,
                    )
                    if item:
                        items.append(item)
            for command_path_str in plugin.commands:
                command_path = repo_path / command_path_str.lstrip("./")
                if command_path.is_file():
                    item = self._parse_agent_file(
                        command_path,
                        "command",
                        require_frontmatter=True,
                        repo_path=repo_path,
                    )
                    if item:
                        items.append(item)

        return items

    def discover_all(self, repo_path: Path, platform: str | None) -> list[DiscoveredItem]:
        """Discover all items in a repository.

        For marketplace-enabled repos, uses the marketplace manifest.
        Otherwise, auto-discovers:
        - Agents: *.agent.md files, or *.md files with frontmatter containing 'name'
        - Skills: Directories containing SKILL.md
        - Commands: *.md files in .claude/commands/ directories with frontmatter

        Args:
            repo_path: Path to the repository root.
            platform: Platform filter (claude, vscode, vscode-insiders, copilot) or None for all.

        Returns:
            List of discovered items, filtered by platform if specified.
        """
        # Check if this is a marketplace repo first
        if self.is_marketplace_repo(repo_path):
            items = self.discover_from_marketplace(repo_path)
        else:
            items: list[DiscoveredItem] = []
            items.extend(self._auto_discover_agents(repo_path))
            items.extend(self._auto_discover_skills(repo_path))
            items.extend(self._auto_discover_commands(repo_path))

        return self._filter_by_platform(items, platform) if platform else items

    def _auto_discover_agents(self, repo_path: Path) -> list[DiscoveredItem]:
        """Auto-discover agents and prompts by searching for agent/prompt files.

        Discovers:
        - *.agent.md files anywhere (VS Code/Copilot agents)
        - *.prompt.md files anywhere (VS Code prompts)
        - *.md files with valid frontmatter (name field required)

        Args:
            repo_path: Path to the repository root.

        Returns:
            List of discovered agents and prompts.
        """
        items = []
        seen_paths: set[Path] = set()

        # 1. Find all .agent.md files (unambiguous agent marker)
        for agent_file in repo_path.glob("**/*.agent.md"):
            if any(skip_dir in agent_file.parts for skip_dir in self.SKIP_DIRS):
                continue
            if agent_file not in seen_paths:
                item = self._parse_agent_file(agent_file, "agent", repo_path=repo_path)
                if item:
                    items.append(item)
                    seen_paths.add(agent_file)

        # 2. Find all .prompt.md files (VS Code prompts)
        for prompt_file in repo_path.glob("**/*.prompt.md"):
            if any(skip_dir in prompt_file.parts for skip_dir in self.SKIP_DIRS):
                continue
            if prompt_file not in seen_paths:
                item = self._parse_agent_file(prompt_file, "prompt", repo_path=repo_path)
                if item:
                    items.append(item)
                    seen_paths.add(prompt_file)

        # 3. Find .md files with valid agent frontmatter (must have 'name' field)
        for md_file in repo_path.glob("**/*.md"):
            if any(skip_dir in md_file.parts for skip_dir in self.SKIP_DIRS):
                continue
            if md_file.name in self.SKIP_FILES:
                continue
            if md_file.name.endswith(".agent.md") or md_file.name.endswith(".prompt.md"):
                continue  # Already handled above
            if md_file.name == self.SKILL_PATTERN:
                continue  # Skills are handled separately
            if md_file in seen_paths:
                continue

            item = self._parse_agent_file(
                md_file, "agent", require_frontmatter=True, repo_path=repo_path
            )
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

            item = self._parse_skill_dir(skill_path, repo_path=repo_path)
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
                    item = self._parse_agent_file(
                        path, "command", require_frontmatter=True, repo_path=repo_path
                    )
                    if item:
                        items.append(item)

        return items

    def _parse_agent_file(
        self,
        path: Path,
        item_type: str,
        require_frontmatter: bool = False,
        repo_path: Path | None = None,
    ) -> DiscoveredItem | None:
        """Parse an agent/command/prompt file.

        Args:
            path: Path to the file.
            item_type: Type of item (agent, command, prompt).
            require_frontmatter: If True, only return item if frontmatter has 'name' field.
            repo_path: Repository root path for computing relative_path.

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
            if name.endswith(".prompt"):
                name = name[:-7]

            description = frontmatter.get("description", "")

            # Determine platforms based on file extension
            platforms = []
            if path.name.endswith(".agent.md") or path.name.endswith(".prompt.md"):
                platforms = ["vscode", "copilot"]
            elif path.suffix == ".md":
                platforms = ["claude"]

            # Compute relative path from repo root
            relative_path = ""
            if repo_path:
                try:
                    relative_path = str(path.relative_to(repo_path))
                except ValueError:
                    relative_path = path.name

            return DiscoveredItem(
                name=name,
                item_type=item_type,
                path=path,
                description=description,
                platforms=platforms,
                frontmatter=frontmatter,
                relative_path=relative_path,
            )
        except Exception:
            return None

    def _parse_skill_dir(
        self,
        path: Path,
        plugin_name: str | None = None,
        repo_path: Path | None = None,
    ) -> DiscoveredItem | None:
        """Parse a skill directory.

        Args:
            path: Path to the skill directory.
            plugin_name: Optional plugin name from marketplace manifest.
            repo_path: Repository root path for computing relative_path.

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

            # Compute relative path from repo root
            relative_path = ""
            if repo_path:
                try:
                    relative_path = str(path.relative_to(repo_path))
                except ValueError:
                    relative_path = path.name

            return DiscoveredItem(
                name=name,
                item_type="skill",
                path=path,
                description=description,
                platforms=["claude"],  # Skills only for Claude
                frontmatter=frontmatter,
                relative_path=relative_path,
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

    def _filter_by_platform(self, items: list[DiscoveredItem], platform: str) -> list[DiscoveredItem]:
        """Filter discovered items by platform compatibility.

        Args:
            items: List of discovered items to filter.
            platform: Platform identifier (claude, vscode, vscode-insiders, copilot).

        Returns:
            Filtered list of items compatible with the specified platform.
        """
        normalized = "vscode" if platform == "vscode-insiders" else platform
        return [
            item for item in items
            if item.platforms and normalized in [
                "vscode" if p == "vscode-insiders" else p for p in item.platforms
            ]
        ]

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

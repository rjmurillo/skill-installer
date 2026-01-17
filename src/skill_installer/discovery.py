"""Discovery of agents, skills, and commands in source repositories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    pass


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

    # File patterns for different item types
    AGENT_PATTERNS = ["*.md", "*.agent.md"]
    SKILL_PATTERN = "SKILL.md"

    def __init__(self) -> None:
        """Initialize discovery."""
        pass

    def discover_all(
        self,
        repo_path: Path,
        agents_path: str = "src",
        skills_path: str = ".claude/skills",
        commands_path: str = ".claude/commands",
    ) -> list[DiscoveredItem]:
        """Discover all items in a repository.

        Args:
            repo_path: Path to the repository root.
            agents_path: Relative path to agents directory.
            skills_path: Relative path to skills directory.
            commands_path: Relative path to commands directory.

        Returns:
            List of discovered items.
        """
        items: list[DiscoveredItem] = []

        # Discover agents
        agents_dir = repo_path / agents_path
        if agents_dir.exists():
            items.extend(self._discover_agents(agents_dir))

        # Discover skills
        skills_dir = repo_path / skills_path
        if skills_dir.exists():
            items.extend(self._discover_skills(skills_dir))

        # Discover commands
        commands_dir = repo_path / commands_path
        if commands_dir.exists():
            items.extend(self._discover_commands(commands_dir))

        return items

    def _discover_agents(self, agents_dir: Path) -> list[DiscoveredItem]:
        """Discover agents in a directory.

        Args:
            agents_dir: Path to agents directory.

        Returns:
            List of discovered agents.
        """
        items = []

        # Look for markdown files
        for pattern in self.AGENT_PATTERNS:
            for path in agents_dir.glob(pattern):
                if path.is_file():
                    item = self._parse_agent_file(path, "agent")
                    if item:
                        items.append(item)

        # Also check subdirectories (e.g., claude/, vs-code-agents/)
        for subdir in agents_dir.iterdir():
            if subdir.is_dir():
                for pattern in self.AGENT_PATTERNS:
                    for path in subdir.glob(pattern):
                        if path.is_file():
                            item = self._parse_agent_file(path, "agent")
                            if item:
                                items.append(item)

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

    def _discover_commands(self, commands_dir: Path) -> list[DiscoveredItem]:
        """Discover commands in a directory.

        Args:
            commands_dir: Path to commands directory.

        Returns:
            List of discovered commands.
        """
        items = []

        for pattern in self.AGENT_PATTERNS:
            for path in commands_dir.glob(pattern):
                if path.is_file():
                    item = self._parse_agent_file(path, "command")
                    if item:
                        items.append(item)

        return items

    def _parse_agent_file(self, path: Path, item_type: str) -> DiscoveredItem | None:
        """Parse an agent/command file.

        Args:
            path: Path to the file.
            item_type: Type of item (agent, command).

        Returns:
            DiscoveredItem or None if parsing fails.
        """
        try:
            content = path.read_text()
            frontmatter = self._parse_frontmatter(content)

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

    def _parse_skill_dir(self, path: Path) -> DiscoveredItem | None:
        """Parse a skill directory.

        Args:
            path: Path to the skill directory.

        Returns:
            DiscoveredItem or None if parsing fails.
        """
        skill_file = path / self.SKILL_PATTERN
        try:
            content = skill_file.read_text()
            frontmatter = self._parse_frontmatter(content)

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

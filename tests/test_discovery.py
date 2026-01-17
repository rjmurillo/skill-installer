"""Tests for discovery module."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_installer.discovery import DiscoveredItem, Discovery


@pytest.fixture
def discovery() -> Discovery:
    """Create a Discovery instance."""
    return Discovery()


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a sample repository structure."""
    # Create agents directory
    agents_dir = tmp_path / "src" / "claude"
    agents_dir.mkdir(parents=True)
    (agents_dir / "analyst.md").write_text(
        """---
name: analyst
description: Research and investigation specialist
---

# Analyst Agent

Investigates issues and gathers evidence.
"""
    )

    # Create VS Code agents
    vscode_dir = tmp_path / "src" / "vs-code-agents"
    vscode_dir.mkdir(parents=True)
    (vscode_dir / "analyst.agent.md").write_text(
        """---
name: analyst
description: Research specialist
tools:
  - read
  - search
---

# Analyst Agent
"""
    )

    # Create skills directory
    skills_dir = tmp_path / ".claude" / "skills" / "github"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        """---
name: github
description: GitHub operations skill
---

# GitHub Skill

Provides GitHub operations.
"""
    )

    # Create commands directory
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "commit.md").write_text(
        """---
name: commit
description: Create a git commit
---

# Commit Command
"""
    )

    return tmp_path


class TestDiscovery:
    """Tests for Discovery class."""

    def test_discover_all(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test discovering all items in a repository."""
        items = discovery.discover_all(sample_repo)

        # Should find agents, skills, and commands
        agents = [i for i in items if i.item_type == "agent"]
        skills = [i for i in items if i.item_type == "skill"]
        commands = [i for i in items if i.item_type == "command"]

        assert len(agents) >= 1
        assert len(skills) == 1
        assert len(commands) == 1

    def test_discover_agents(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test auto-discovering agents."""
        items = discovery._auto_discover_agents(sample_repo)

        names = [i.name for i in items]
        assert "analyst" in names

    def test_discover_skills(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test discovering skills."""
        skills_dir = sample_repo / ".claude" / "skills"
        items = discovery._discover_skills(skills_dir)

        assert len(items) == 1
        assert items[0].name == "github"
        assert items[0].item_type == "skill"

    def test_discover_commands(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test auto-discovering commands."""
        items = discovery._auto_discover_commands(sample_repo)

        assert len(items) == 1
        assert items[0].name == "commit"
        assert items[0].item_type == "command"

    def test_parse_frontmatter(self, discovery: Discovery) -> None:
        """Test parsing YAML frontmatter."""
        content = """---
name: test
description: Test agent
---

# Content
"""
        frontmatter = discovery._parse_frontmatter(content)
        assert frontmatter["name"] == "test"
        assert frontmatter["description"] == "Test agent"

    def test_parse_frontmatter_empty(self, discovery: Discovery) -> None:
        """Test parsing content without frontmatter."""
        content = "# Just content"
        frontmatter = discovery._parse_frontmatter(content)
        assert frontmatter == {}

    def test_parse_frontmatter_invalid(self, discovery: Discovery) -> None:
        """Test parsing invalid frontmatter."""
        content = "---\ninvalid: [\n---\n"
        frontmatter = discovery._parse_frontmatter(content)
        assert frontmatter == {}

    def test_get_item_content_agent(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test getting content for an agent."""
        item = DiscoveredItem(
            name="analyst",
            item_type="agent",
            path=sample_repo / "src" / "claude" / "analyst.md",
        )
        content = discovery.get_item_content(item)
        assert "name: analyst" in content

    def test_get_item_content_skill(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test getting content for a skill."""
        item = DiscoveredItem(
            name="github",
            item_type="skill",
            path=sample_repo / ".claude" / "skills" / "github",
        )
        content = discovery.get_item_content(item)
        assert "name: github" in content

    def test_parse_agent_file_derives_name(self, discovery: Discovery, tmp_path: Path) -> None:
        """Test that agent name is derived from filename if not in frontmatter."""
        agent_file = tmp_path / "my-agent.md"
        agent_file.write_text(
            """---
description: No name field
---

Content
"""
        )
        item = discovery._parse_agent_file(agent_file, "agent")
        assert item is not None
        assert item.name == "my-agent"

    def test_parse_agent_file_strips_extension(self, discovery: Discovery, tmp_path: Path) -> None:
        """Test that .agent extension is stripped from name."""
        agent_file = tmp_path / "my-agent.agent.md"
        agent_file.write_text(
            """---
name: my-agent.agent
---

Content
"""
        )
        item = discovery._parse_agent_file(agent_file, "agent")
        assert item is not None
        assert item.name == "my-agent"


class TestDiscoveredItem:
    """Tests for DiscoveredItem dataclass."""

    def test_discovered_item(self, tmp_path: Path) -> None:
        """Test DiscoveredItem creation."""
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=tmp_path / "test.md",
            description="Test agent",
            platforms=["claude"],
            frontmatter={"name": "test"},
        )
        assert item.name == "test"
        assert item.item_type == "agent"
        assert item.platforms == ["claude"]

    def test_discovered_item_defaults(self, tmp_path: Path) -> None:
        """Test DiscoveredItem default values."""
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=tmp_path / "test.md",
        )
        assert item.description == ""
        assert item.platforms == []
        assert item.frontmatter == {}

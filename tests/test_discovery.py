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
        items = discovery.discover_all(sample_repo, None)

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


@pytest.fixture
def marketplace_repo(tmp_path: Path) -> Path:
    """Create a marketplace-enabled repository structure."""
    # Create .claude-plugin directory with marketplace.json
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "marketplace.json").write_text(
        """{
  "name": "test-marketplace",
  "owner": {
    "name": "Test Author",
    "email": "test@example.com"
  },
  "metadata": {
    "description": "Test marketplace",
    "version": "1.0.0"
  },
  "plugins": [
    {
      "name": "document-skills",
      "description": "Document processing skills",
      "source": "./",
      "strict": false,
      "skills": [
        "./skills/pdf",
        "./skills/docx"
      ],
      "agents": [
        "./agents/pdf-agent.md"
      ],
      "commands": [
        "./commands/pdf-process.md"
      ]
    }
  ]
}"""
    )

    # Create skills directories
    pdf_skill = tmp_path / "skills" / "pdf"
    pdf_skill.mkdir(parents=True)
    (pdf_skill / "SKILL.md").write_text(
        """---
name: pdf
description: PDF processing toolkit
license: MIT
---

# PDF Skill

Process PDF files.
"""
    )

    docx_skill = tmp_path / "skills" / "docx"
    docx_skill.mkdir(parents=True)
    (docx_skill / "SKILL.md").write_text(
        """---
name: docx
description: Word document processing
---

  # DOCX Skill

Process Word documents.
"""
    )

    # Create agents directory
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "pdf-agent.md").write_text(
        """---
name: pdf-agent
description: PDF processing agent
---

# PDF Agent
"""
    )

    # Create commands directory
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "pdf-process.md").write_text(
        """---
name: pdf-process
description: Process PDF command
---

# PDF Process Command
"""
    )

    return tmp_path


class TestMarketplaceDiscovery:
    """Tests for marketplace discovery functionality."""

    def test_is_marketplace_repo_true(self, discovery: Discovery, marketplace_repo: Path) -> None:
        """Test detecting a marketplace-enabled repository."""
        assert discovery.is_marketplace_repo(marketplace_repo) is True

    def test_is_marketplace_repo_false(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test detecting a non-marketplace repository."""
        assert discovery.is_marketplace_repo(sample_repo) is False

    def test_load_marketplace_manifest(self, discovery: Discovery, marketplace_repo: Path) -> None:
        """Test loading marketplace manifest."""
        manifest = discovery.load_marketplace_manifest(marketplace_repo)
        assert manifest is not None
        assert manifest.name == "test-marketplace"
        assert manifest.owner is not None
        assert manifest.owner.name == "Test Author"
        assert len(manifest.plugins) == 1
        assert manifest.plugins[0].name == "document-skills"

    def test_load_marketplace_manifest_not_found(
        self, discovery: Discovery, sample_repo: Path
    ) -> None:
        """Test loading manifest from non-marketplace repo."""
        manifest = discovery.load_marketplace_manifest(sample_repo)
        assert manifest is None

    def test_load_marketplace_manifest_invalid_json(
        self, discovery: Discovery, tmp_path: Path
    ) -> None:
        """Test loading invalid JSON manifest."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text("{ invalid json }")

        manifest = discovery.load_marketplace_manifest(tmp_path)
        assert manifest is None

    def test_discover_from_marketplace(self, discovery: Discovery, marketplace_repo: Path) -> None:
        """Test discovering skills from marketplace manifest."""
        items = discovery.discover_from_marketplace(marketplace_repo)

        assert len(items) == 4
        names = [i.name for i in items]
        assert "pdf" in names
        assert "docx" in names
        assert "pdf-agent" in names
        assert "pdf-process" in names

        # Check plugin name is in frontmatter for all marketplace items
        pdf_item = next(i for i in items if i.name == "pdf")
        assert pdf_item.frontmatter.get("plugin") == "document-skills"

        pdf_agent = next(i for i in items if i.name == "pdf-agent")
        assert pdf_agent.frontmatter.get("plugin") == "document-skills"

        pdf_process = next(i for i in items if i.name == "pdf-process")
        assert pdf_process.frontmatter.get("plugin") == "document-skills"

    def test_discover_from_marketplace_empty(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test discover_from_marketplace returns empty for non-marketplace repo."""
        items = discovery.discover_from_marketplace(sample_repo)
        assert items == []

    def test_discover_all_marketplace(self, discovery: Discovery, marketplace_repo: Path) -> None:
        """Test discover_all uses marketplace discovery when available."""
        items = discovery.discover_all(marketplace_repo, None)

        # Should find all items from marketplace (skills, agents, commands)
        assert len(items) == 4
        names = [i.name for i in items]
        assert "pdf" in names
        assert "docx" in names
        assert "pdf-agent" in names
        assert "pdf-process" in names

    def test_discover_from_marketplace_missing_skill_dir(
        self, discovery: Discovery, tmp_path: Path
    ) -> None:
        """Test marketplace discovery handles missing skill directories."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text(
            """{
  "name": "test",
  "plugins": [
    {
      "name": "missing",
      "skills": ["./skills/nonexistent"]
    }
  ]
}"""
        )

        items = discovery.discover_from_marketplace(tmp_path)
        assert items == []


class TestPlatformFiltering:
    """Tests for platform filtering functionality."""

    def test_filter_by_claude_platform(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test filtering items by Claude platform."""
        items = discovery.discover_all(sample_repo, platform="claude")

        # Should only find Claude-compatible items (agents with .md and skills)
        assert all("claude" in item.platforms or item.platforms == ["claude"] for item in items)

        # Should include skills (they are Claude-only)
        skills = [i for i in items if i.item_type == "skill"]
        assert len(skills) > 0

    def test_filter_by_vscode_platform(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test filtering items by VS Code platform."""
        items = discovery.discover_all(sample_repo, platform="vscode")

        # Should only find VS Code-compatible items (agents with .agent.md)
        for item in items:
            assert "vscode" in item.platforms or "vscode-insiders" in item.platforms

        # VS Code agents should be present
        agents = [i for i in items if i.item_type == "agent"]
        assert len(agents) > 0

    def test_filter_by_copilot_platform(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test filtering items by Copilot platform."""
        items = discovery.discover_all(sample_repo, platform="copilot")

        # Should only find Copilot-compatible items (agents with .agent.md)
        for item in items:
            assert "copilot" in item.platforms

    def test_filter_by_vscode_insiders(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test filtering by vscode-insiders treats it as vscode."""
        vscode_items = discovery.discover_all(sample_repo, platform="vscode")
        insiders_items = discovery.discover_all(sample_repo, platform="vscode-insiders")

        # Should return the same items
        assert len(vscode_items) == len(insiders_items)
        assert {i.name for i in vscode_items} == {i.name for i in insiders_items}

    def test_filter_none_returns_all(self, discovery: Discovery, sample_repo: Path) -> None:
        """Test that passing None returns all items."""
        all_items = discovery.discover_all(sample_repo, None)

        # Should return all types
        agents = [i for i in all_items if i.item_type == "agent"]
        skills = [i for i in all_items if i.item_type == "skill"]
        commands = [i for i in all_items if i.item_type == "command"]

        assert len(agents) >= 1
        assert len(skills) == 1
        assert len(commands) == 1

    def test_filter_by_platform_empty_result(self, discovery: Discovery, tmp_path: Path) -> None:
        """Test filtering returns empty list when no items match platform."""
        # Create a repo with only Claude items
        claude_dir = tmp_path / ".claude" / "skills" / "test"
        claude_dir.mkdir(parents=True)
        (claude_dir / "SKILL.md").write_text(
            """---
name: test
description: Test skill
---

# Test Skill
"""
        )

        # Filter for VS Code should return empty
        items = discovery.discover_all(tmp_path, platform="vscode")
        assert items == []

    def test_filter_by_platform_helper(self, discovery: Discovery, tmp_path: Path) -> None:
        """Test the _filter_by_platform helper method directly."""
        # Create sample items with different platforms
        items = [
            DiscoveredItem(
                name="claude-agent",
                item_type="agent",
                path=tmp_path / "claude.md",
                platforms=["claude"],
            ),
            DiscoveredItem(
                name="vscode-agent",
                item_type="agent",
                path=tmp_path / "vscode.agent.md",
                platforms=["vscode", "copilot"],
            ),
            DiscoveredItem(
                name="no-platform",
                item_type="agent",
                path=tmp_path / "none.md",
                platforms=[],
            ),
        ]

        # Filter for Claude
        claude_items = discovery._filter_by_platform(items, "claude")
        assert len(claude_items) == 1
        assert claude_items[0].name == "claude-agent"

        # Filter for VS Code
        vscode_items = discovery._filter_by_platform(items, "vscode")
        assert len(vscode_items) == 1
        assert vscode_items[0].name == "vscode-agent"

        # Filter for Copilot
        copilot_items = discovery._filter_by_platform(items, "copilot")
        assert len(copilot_items) == 1
        assert copilot_items[0].name == "vscode-agent"

        # Items with no platform info are excluded
        all_filtered = claude_items + vscode_items
        assert all(item.name != "no-platform" for item in all_filtered)


# ============================================================================
# Fixtures for marketplace auto-discovery fallback tests
# ============================================================================


@pytest.fixture
def marketplace_repo_empty_plugins(tmp_path: Path) -> Path:
    """Create a marketplace repo where plugins have empty item arrays.

    Mimics rjmurillo/ai-agents: valid marketplace.json, but skills/agents/commands
    arrays are empty. Content lives under the plugin's source directory.
    """
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "marketplace.json").write_text(
        """{
  "name": "ai-agents",
  "owner": {"name": "Test Author"},
  "plugins": [
    {
      "name": "claude-agents",
      "description": "Agents for Claude Code",
      "source": "./src/claude",
      "skills": [],
      "agents": [],
      "commands": []
    }
  ]
}"""
    )

    # Content under src/claude (the plugin's source directory)
    src_dir = tmp_path / "src" / "claude"
    src_dir.mkdir(parents=True)
    (src_dir / "analyst.md").write_text(
        """---
name: analyst
description: Research specialist
---

# Analyst Agent
"""
    )
    (src_dir / "planner.md").write_text(
        """---
name: planner
description: Planning specialist
---

# Planner Agent
"""
    )

    skill_dir = src_dir / "skills" / "github"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: github
description: GitHub operations
---

# GitHub Skill
"""
    )

    commands_dir = src_dir / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "deploy.md").write_text(
        """---
name: deploy
description: Deploy command
---

# Deploy
"""
    )

    return tmp_path


@pytest.fixture
def marketplace_repo_mixed_plugins(tmp_path: Path) -> Path:
    """Create a marketplace repo with one explicit plugin and one empty plugin."""
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir(parents=True)

    # Create agent files for explicit plugin
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "explicit-agent.md").write_text(
        """---
name: explicit-agent
description: Explicitly listed agent
---

# Explicit Agent
"""
    )

    # Create content for auto-discovered plugin
    auto_dir = tmp_path / "src" / "auto"
    auto_dir.mkdir(parents=True)
    (auto_dir / "auto-agent.md").write_text(
        """---
name: auto-agent
description: Auto-discovered agent
---

# Auto Agent
"""
    )

    (plugin_dir / "marketplace.json").write_text(
        """{
  "name": "mixed-marketplace",
  "plugins": [
    {
      "name": "explicit-plugin",
      "source": "./",
      "agents": ["./agents/explicit-agent.md"],
      "skills": [],
      "commands": []
    },
    {
      "name": "auto-plugin",
      "source": "./src/auto",
      "skills": [],
      "agents": [],
      "commands": []
    }
  ]
}"""
    )

    return tmp_path


# ============================================================================
# Tests for marketplace auto-discovery fallback (Bug 1)
# ============================================================================


class TestMarketplaceAutoDiscoveryFallback:
    """Tests for per-plugin auto-discovery when item arrays are empty."""

    def test_empty_arrays_trigger_auto_discovery(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Empty skills/agents/commands arrays trigger auto-discovery in source dir."""
        items = discovery.discover_from_marketplace(marketplace_repo_empty_plugins)

        names = {i.name for i in items}
        assert "analyst" in names
        assert "planner" in names
        assert len(items) >= 2

    def test_auto_discovered_items_get_plugin_name(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Auto-discovered items are stamped with the plugin name."""
        items = discovery.discover_from_marketplace(marketplace_repo_empty_plugins)

        for item in items:
            assert item.frontmatter.get("plugin") == "claude-agents"

    def test_relative_paths_are_repo_rooted(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Relative paths are computed from repo root, not source directory."""
        items = discovery.discover_from_marketplace(marketplace_repo_empty_plugins)

        analyst = next(i for i in items if i.name == "analyst")
        assert analyst.relative_path.startswith("src/claude/")

    def test_nonexistent_source_dir_returns_empty(
        self, discovery: Discovery, tmp_path: Path
    ) -> None:
        """Plugin with nonexistent source dir returns no items."""
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text(
            """{
  "name": "test",
  "plugins": [
    {
      "name": "missing",
      "source": "./nonexistent",
      "skills": [],
      "agents": [],
      "commands": []
    }
  ]
}"""
        )

        items = discovery.discover_from_marketplace(tmp_path)
        assert items == []

    def test_mixed_explicit_and_empty_plugins(
        self, discovery: Discovery, marketplace_repo_mixed_plugins: Path
    ) -> None:
        """Explicit plugins use arrays; empty plugins use auto-discovery."""
        items = discovery.discover_from_marketplace(marketplace_repo_mixed_plugins)

        names = {i.name for i in items}
        assert "explicit-agent" in names
        assert "auto-agent" in names

        explicit = next(i for i in items if i.name == "explicit-agent")
        assert explicit.frontmatter["plugin"] == "explicit-plugin"

        auto = next(i for i in items if i.name == "auto-agent")
        assert auto.frontmatter["plugin"] == "auto-plugin"

    def test_existing_explicit_plugins_still_work(
        self, discovery: Discovery, marketplace_repo: Path
    ) -> None:
        """Plugins with explicit items still discover them correctly."""
        items = discovery.discover_from_marketplace(marketplace_repo)

        assert len(items) == 4
        names = {i.name for i in items}
        assert "pdf" in names
        assert "docx" in names
        assert "pdf-agent" in names
        assert "pdf-process" in names

    def test_skills_discovered_in_source_dir(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Skills under the source directory are auto-discovered."""
        items = discovery.discover_from_marketplace(marketplace_repo_empty_plugins)

        skills = [i for i in items if i.item_type == "skill"]
        assert len(skills) == 1
        assert skills[0].name == "github"
        assert skills[0].frontmatter["plugin"] == "claude-agents"

    def test_commands_discovered_in_source_dir(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Commands under the source directory are auto-discovered."""
        items = discovery.discover_from_marketplace(marketplace_repo_empty_plugins)

        commands = [i for i in items if i.item_type == "command"]
        assert len(commands) == 1
        assert commands[0].name == "deploy"
        assert commands[0].frontmatter["plugin"] == "claude-agents"


class TestRepoWideFallback:
    """Tests for repo-wide fallback when marketplace discovery yields nothing."""

    def test_marketplace_no_items_falls_back(self, discovery: Discovery, tmp_path: Path) -> None:
        """When marketplace discovery returns 0 items, repo-wide auto-discovery runs."""
        # Marketplace file with plugin pointing to nonexistent source
        plugin_dir = tmp_path / ".claude-plugin"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "marketplace.json").write_text(
            """{
  "name": "test",
  "plugins": [
    {
      "name": "empty",
      "source": "./nonexistent",
      "skills": [],
      "agents": [],
      "commands": []
    }
  ]
}"""
        )

        # Place agents at repo root level (outside nonexistent source dir)
        (tmp_path / "fallback-agent.md").write_text(
            """---
name: fallback-agent
description: Found by repo-wide fallback
---

# Fallback
"""
        )

        items = discovery.discover_all(tmp_path, None)
        names = {i.name for i in items}
        assert "fallback-agent" in names

    def test_valid_marketplace_no_repo_fallback(
        self, discovery: Discovery, marketplace_repo: Path
    ) -> None:
        """Valid marketplace discovery does NOT trigger repo-wide fallback."""
        items = discovery.discover_all(marketplace_repo, None)

        # Should get exactly the marketplace items, not extras from repo scan
        assert len(items) == 4
        names = {i.name for i in items}
        assert "pdf" in names
        assert "docx" in names

    def test_empty_plugin_auto_discovery_no_repo_fallback(
        self, discovery: Discovery, marketplace_repo_empty_plugins: Path
    ) -> None:
        """Per-plugin auto-discovery finding items prevents repo-wide fallback."""
        items = discovery.discover_all(marketplace_repo_empty_plugins, None)

        # Items found via per-plugin fallback, repo-wide fallback should not run
        names = {i.name for i in items}
        assert "analyst" in names
        assert "planner" in names


class TestPluginHasExplicitItems:
    """Tests for _plugin_has_explicit_items helper."""

    def test_all_empty_returns_false(self, discovery: Discovery) -> None:
        """All-empty arrays return False."""
        from skill_installer.registry import MarketplacePlugin

        plugin = MarketplacePlugin(name="empty", skills=[], agents=[], commands=[])
        assert discovery._plugin_has_explicit_items(plugin) is False

    def test_skills_non_empty_returns_true(self, discovery: Discovery) -> None:
        """Non-empty skills returns True."""
        from skill_installer.registry import MarketplacePlugin

        plugin = MarketplacePlugin(name="test", skills=["./s1"], agents=[], commands=[])
        assert discovery._plugin_has_explicit_items(plugin) is True

    def test_agents_non_empty_returns_true(self, discovery: Discovery) -> None:
        """Non-empty agents returns True."""
        from skill_installer.registry import MarketplacePlugin

        plugin = MarketplacePlugin(name="test", skills=[], agents=["./a1"], commands=[])
        assert discovery._plugin_has_explicit_items(plugin) is True

    def test_commands_non_empty_returns_true(self, discovery: Discovery) -> None:
        """Non-empty commands returns True."""
        from skill_installer.registry import MarketplacePlugin

        plugin = MarketplacePlugin(name="test", skills=[], agents=[], commands=["./c1"])
        assert discovery._plugin_has_explicit_items(plugin) is True

    def test_all_non_empty_returns_true(self, discovery: Discovery) -> None:
        """All arrays non-empty returns True."""
        from skill_installer.registry import MarketplacePlugin

        plugin = MarketplacePlugin(name="test", skills=["./s1"], agents=["./a1"], commands=["./c1"])
        assert discovery._plugin_has_explicit_items(plugin) is True


class TestScanRootParameter:
    """Tests for scan_root parameter on auto-discover methods."""

    def test_scan_root_scopes_agent_discovery(self, discovery: Discovery, tmp_path: Path) -> None:
        """scan_root restricts agent globbing to the specified directory."""
        # Agent outside scan root
        (tmp_path / "outside.md").write_text(
            """---
name: outside
description: Outside scan root
---
"""
        )

        # Agent inside scan root
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "inside.md").write_text(
            """---
name: inside
description: Inside scan root
---
"""
        )

        items = discovery._auto_discover_agents(tmp_path, scan_root=sub_dir)
        names = {i.name for i in items}
        assert "inside" in names
        assert "outside" not in names

    def test_scan_root_none_uses_repo_path(self, discovery: Discovery, sample_repo: Path) -> None:
        """scan_root=None preserves existing behavior (uses repo_path)."""
        items_default = discovery._auto_discover_agents(sample_repo)
        items_none = discovery._auto_discover_agents(sample_repo, scan_root=None)

        assert len(items_default) == len(items_none)
        assert {i.name for i in items_default} == {i.name for i in items_none}

    def test_scan_root_relative_paths_from_repo_root(
        self, discovery: Discovery, tmp_path: Path
    ) -> None:
        """Relative paths are computed from repo_path, not scan_root."""
        sub_dir = tmp_path / "src" / "agents"
        sub_dir.mkdir(parents=True)
        (sub_dir / "test.md").write_text(
            """---
name: test
description: Test
---
"""
        )

        items = discovery._auto_discover_agents(tmp_path, scan_root=sub_dir)
        assert len(items) == 1
        assert items[0].relative_path == "src/agents/test.md"

    def test_scan_root_scopes_skill_discovery(self, discovery: Discovery, tmp_path: Path) -> None:
        """scan_root restricts skill globbing to the specified directory."""
        # Skill outside scan root
        outside_skill = tmp_path / "outside_skill"
        outside_skill.mkdir()
        (outside_skill / "SKILL.md").write_text(
            """---
name: outside
---
"""
        )

        # Skill inside scan root
        sub_dir = tmp_path / "sub"
        inside_skill = sub_dir / "inside_skill"
        inside_skill.mkdir(parents=True)
        (inside_skill / "SKILL.md").write_text(
            """---
name: inside
---
"""
        )

        items = discovery._auto_discover_skills(tmp_path, scan_root=sub_dir)
        names = {i.name for i in items}
        assert "inside" in names
        assert "outside" not in names

    def test_scan_root_scopes_command_discovery(self, discovery: Discovery, tmp_path: Path) -> None:
        """scan_root restricts command globbing to the specified directory."""
        # Command outside scan root
        outside_cmd = tmp_path / ".claude" / "commands"
        outside_cmd.mkdir(parents=True)
        (outside_cmd / "outside.md").write_text(
            """---
name: outside
description: Outside
---
"""
        )

        # Command inside scan root
        sub_dir = tmp_path / "sub"
        inside_cmd = sub_dir / ".claude" / "commands"
        inside_cmd.mkdir(parents=True)
        (inside_cmd / "inside.md").write_text(
            """---
name: inside
description: Inside
---
"""
        )

        items = discovery._auto_discover_commands(tmp_path, scan_root=sub_dir)
        names = {i.name for i in items}
        assert "inside" in names
        assert "outside" not in names

    def test_plugin_name_stamped_with_scan_root(self, discovery: Discovery, tmp_path: Path) -> None:
        """plugin_name is stamped into frontmatter when using scan_root."""
        sub_dir = tmp_path / "src"
        sub_dir.mkdir()
        (sub_dir / "agent.md").write_text(
            """---
name: stamped
description: Test
---
"""
        )

        items = discovery._auto_discover_agents(
            tmp_path, scan_root=sub_dir, plugin_name="my-plugin"
        )
        assert len(items) == 1
        assert items[0].frontmatter["plugin"] == "my-plugin"

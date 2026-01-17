"""Tests for platform modules."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_installer.platforms import (
    ClaudePlatform,
    CodexPlatform,
    CopilotPlatform,
    VSCodePlatform,
    get_platform,
)


class TestGetPlatform:
    """Tests for get_platform factory function."""

    def test_get_claude_platform(self) -> None:
        """Test getting Claude platform."""
        platform = get_platform("claude")
        assert isinstance(platform, ClaudePlatform)

    def test_get_vscode_platform(self) -> None:
        """Test getting VS Code platform."""
        platform = get_platform("vscode")
        assert isinstance(platform, VSCodePlatform)
        assert platform.insiders is False

    def test_get_vscode_insiders_platform(self) -> None:
        """Test getting VS Code Insiders platform."""
        platform = get_platform("vscode-insiders")
        assert isinstance(platform, VSCodePlatform)
        assert platform.insiders is True

    def test_get_copilot_platform(self) -> None:
        """Test getting Copilot platform."""
        platform = get_platform("copilot")
        assert isinstance(platform, CopilotPlatform)

    def test_get_unknown_platform(self) -> None:
        """Test getting unknown platform raises error."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_platform("unknown")


class TestClaudePlatform:
    """Tests for ClaudePlatform."""

    @pytest.fixture
    def platform(self) -> ClaudePlatform:
        """Create a ClaudePlatform instance."""
        return ClaudePlatform()

    def test_name(self, platform: ClaudePlatform) -> None:
        """Test platform name."""
        assert platform.name == "claude"

    def test_agent_extension(self, platform: ClaudePlatform) -> None:
        """Test agent file extension."""
        assert platform.agent_extension == ".md"

    def test_supports_skills(self, platform: ClaudePlatform) -> None:
        """Test skill support flag."""
        assert platform.supports_skills is True

    def test_base_dir(self, platform: ClaudePlatform) -> None:
        """Test base directory."""
        assert platform.base_dir == Path.home() / ".claude"

    def test_agents_dir(self, platform: ClaudePlatform) -> None:
        """Test agents directory."""
        assert platform.agents_dir == Path.home() / ".claude" / "agents"

    def test_skills_dir(self, platform: ClaudePlatform) -> None:
        """Test skills directory."""
        assert platform.skills_dir == Path.home() / ".claude" / "skills"

    def test_commands_dir(self, platform: ClaudePlatform) -> None:
        """Test commands directory."""
        assert platform.commands_dir == Path.home() / ".claude" / "commands"

    def test_ensure_dirs(self, platform: ClaudePlatform, tmp_path: Path) -> None:
        """Test directory creation."""
        platform._base_dir = tmp_path / ".claude"
        platform.ensure_dirs()
        assert platform.agents_dir.exists()
        assert platform.skills_dir.exists()
        assert platform.commands_dir.exists()

    def test_get_install_path_agent(self, platform: ClaudePlatform) -> None:
        """Test getting agent install path."""
        path = platform.get_install_path("agent", "test")
        assert path == platform.agents_dir / "test.md"

    def test_get_install_path_skill(self, platform: ClaudePlatform) -> None:
        """Test getting skill install path."""
        path = platform.get_install_path("skill", "test")
        assert path == platform.skills_dir / "test"

    def test_get_install_path_command(self, platform: ClaudePlatform) -> None:
        """Test getting command install path."""
        path = platform.get_install_path("command", "test")
        assert path == platform.commands_dir / "test.md"

    def test_get_install_path_unknown(self, platform: ClaudePlatform) -> None:
        """Test getting unknown type raises error."""
        with pytest.raises(ValueError, match="Unknown item type"):
            platform.get_install_path("unknown", "test")

    def test_validate_agent_valid(self, platform: ClaudePlatform) -> None:
        """Test validating valid agent content."""
        content = """---
name: test
---

# Test Agent
"""
        errors = platform.validate_agent(content)
        assert errors == []

    def test_validate_agent_no_frontmatter(self, platform: ClaudePlatform) -> None:
        """Test validating agent without frontmatter."""
        content = "# Just content"
        errors = platform.validate_agent(content)
        assert len(errors) == 1
        assert "frontmatter" in errors[0].lower()

    def test_validate_agent_no_name(self, platform: ClaudePlatform) -> None:
        """Test validating agent without name field."""
        content = """---
description: Test
---

# Test
"""
        errors = platform.validate_agent(content)
        assert len(errors) == 1
        assert "name" in errors[0].lower()


class TestVSCodePlatform:
    """Tests for VSCodePlatform."""

    @pytest.fixture
    def platform(self) -> VSCodePlatform:
        """Create a VSCodePlatform instance."""
        return VSCodePlatform()

    @pytest.fixture
    def insiders_platform(self) -> VSCodePlatform:
        """Create a VS Code Insiders platform instance."""
        return VSCodePlatform(insiders=True)

    def test_name(self, platform: VSCodePlatform) -> None:
        """Test platform name."""
        assert platform.name == "vscode"

    def test_insiders_name(self, insiders_platform: VSCodePlatform) -> None:
        """Test insiders platform name."""
        assert insiders_platform.name == "vscode-insiders"

    def test_agent_extension(self, platform: VSCodePlatform) -> None:
        """Test agent file extension."""
        assert platform.agent_extension == ".agent.md"

    def test_supports_skills(self, platform: VSCodePlatform) -> None:
        """Test skill support flag."""
        assert platform.supports_skills is False

    @patch.object(sys, "platform", "linux")
    def test_base_dir_linux(self) -> None:
        """Test base directory on Linux."""
        platform = VSCodePlatform()
        platform._base_dir = None  # Reset cached value
        assert platform.base_dir == Path.home() / ".config" / "Code" / "User" / "prompts"

    @patch.object(sys, "platform", "linux")
    def test_base_dir_linux_insiders(self) -> None:
        """Test insiders base directory on Linux."""
        platform = VSCodePlatform(insiders=True)
        platform._base_dir = None
        assert platform.base_dir == Path.home() / ".config" / "Code - Insiders" / "User" / "prompts"

    def test_get_install_path_agent(self, platform: VSCodePlatform) -> None:
        """Test getting agent install path."""
        path = platform.get_install_path("agent", "test")
        assert str(path).endswith("test.agent.md")

    def test_get_install_path_skill_unsupported(self, platform: VSCodePlatform) -> None:
        """Test getting skill path raises error."""
        with pytest.raises(ValueError, match="does not support"):
            platform.get_install_path("skill", "test")

    def test_validate_agent_valid(self, platform: VSCodePlatform) -> None:
        """Test validating valid VS Code agent."""
        content = """---
name: test
tools:
  - read
  - edit
---

# Test Agent
"""
        errors = platform.validate_agent(content)
        assert errors == []

    def test_validate_agent_no_tools(self, platform: VSCodePlatform) -> None:
        """Test validating agent without tools field passes (tools is optional)."""
        content = """---
name: test
---

# Test
"""
        errors = platform.validate_agent(content)
        assert errors == []  # No required fields per VSCode spec


class TestCopilotPlatform:
    """Tests for CopilotPlatform."""

    @pytest.fixture
    def platform(self) -> CopilotPlatform:
        """Create a CopilotPlatform instance."""
        return CopilotPlatform()

    def test_name(self, platform: CopilotPlatform) -> None:
        """Test platform name."""
        assert platform.name == "copilot"

    def test_agent_extension(self, platform: CopilotPlatform) -> None:
        """Test agent file extension."""
        assert platform.agent_extension == ".agent.md"

    def test_supports_skills(self, platform: CopilotPlatform) -> None:
        """Test skill support flag."""
        assert platform.supports_skills is False

    def test_base_dir(self, platform: CopilotPlatform) -> None:
        """Test base directory."""
        assert platform.base_dir == Path.home() / ".copilot"

    def test_agents_dir(self, platform: CopilotPlatform) -> None:
        """Test agents directory."""
        assert platform.agents_dir == Path.home() / ".copilot" / "agents"

    def test_get_install_path_agent(self, platform: CopilotPlatform) -> None:
        """Test getting agent install path."""
        path = platform.get_install_path("agent", "test")
        assert path == platform.agents_dir / "test.agent.md"

    def test_get_install_path_skill_unsupported(self, platform: CopilotPlatform) -> None:
        """Test getting skill path raises error."""
        with pytest.raises(ValueError, match="does not support"):
            platform.get_install_path("skill", "test")

    def test_validate_agent_valid(self, platform: CopilotPlatform) -> None:
        """Test validating valid Copilot agent."""
        content = """---
name: test
tools:
  - read
  - edit
---

# Test Agent
"""
        errors = platform.validate_agent(content)
        assert errors == []

    def test_validate_agent_missing_fields(self, platform: CopilotPlatform) -> None:
        """Test validating agent with minimal frontmatter passes (all fields optional)."""
        content = """---
description: Test
---

# Test
"""
        errors = platform.validate_agent(content)
        assert errors == []  # No required fields per GitHub Copilot spec


class TestProjectInstallPaths:
    """Tests for get_project_install_path methods across platforms."""

    def test_claude_project_install_path_agent(self, tmp_path: Path) -> None:
        """Test Claude project install path for agents."""
        platform = ClaudePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "agent", "test")
        expected = project_root / ".claude" / "agents" / "test.md"
        assert path == expected

    def test_claude_project_install_path_skill(self, tmp_path: Path) -> None:
        """Test Claude project install path for skills."""
        platform = ClaudePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "skill", "github")
        expected = project_root / ".claude" / "skills" / "github"
        assert path == expected

    def test_claude_project_install_path_command(self, tmp_path: Path) -> None:
        """Test Claude project install path for commands."""
        platform = ClaudePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "command", "deploy")
        expected = project_root / ".claude" / "commands" / "deploy.md"
        assert path == expected

    def test_claude_project_install_path_unknown_type(self, tmp_path: Path) -> None:
        """Test Claude project install path raises error for unknown type."""
        platform = ClaudePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(ValueError, match="Unknown item type"):
            platform.get_project_install_path(project_root, "unknown", "test")

    def test_vscode_project_install_path_agent(self, tmp_path: Path) -> None:
        """Test VS Code project install path for agents."""
        platform = VSCodePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "agent", "test")
        expected = project_root / ".vscode" / "agents" / "test.agent.md"
        assert path == expected

    def test_vscode_project_install_path_skill_unsupported(self, tmp_path: Path) -> None:
        """Test VS Code project install path raises error for skills."""
        platform = VSCodePlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(ValueError, match="does not support"):
            platform.get_project_install_path(project_root, "skill", "test")

    def test_copilot_project_install_path_agent(self, tmp_path: Path) -> None:
        """Test Copilot project install path for agents."""
        platform = CopilotPlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "agent", "test")
        expected = project_root / ".github" / "copilot" / "agents" / "test.agent.md"
        assert path == expected

    def test_copilot_project_install_path_skill_unsupported(self, tmp_path: Path) -> None:
        """Test Copilot project install path raises error for skills."""
        platform = CopilotPlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(ValueError, match="does not support"):
            platform.get_project_install_path(project_root, "skill", "test")

    def test_codex_project_install_path_skill(self, tmp_path: Path) -> None:
        """Test Codex project install path for skills."""
        platform = CodexPlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        path = platform.get_project_install_path(project_root, "skill", "github")
        expected = project_root / ".codex" / "skills" / "github"
        assert path == expected

    def test_codex_project_install_path_agent_unsupported(self, tmp_path: Path) -> None:
        """Test Codex project install path raises error for agents."""
        platform = CodexPlatform()
        project_root = tmp_path / "project"
        project_root.mkdir()

        with pytest.raises(ValueError, match="only supports skills"):
            platform.get_project_install_path(project_root, "agent", "test")


class TestCodexPlatform:
    """Tests for CodexPlatform."""

    @pytest.fixture
    def platform(self) -> CodexPlatform:
        """Create a CodexPlatform instance."""
        return CodexPlatform()

    def test_name(self, platform: CodexPlatform) -> None:
        """Test platform name."""
        assert platform.name == "codex"

    def test_agent_extension(self, platform: CodexPlatform) -> None:
        """Test agent file extension."""
        assert platform.agent_extension == ".md"

    def test_supports_skills(self, platform: CodexPlatform) -> None:
        """Test skill support flag."""
        assert platform.supports_skills is True

    def test_base_dir(self, platform: CodexPlatform) -> None:
        """Test base directory."""
        # Codex base_dir is ~/.config/opencode (not ~/...opencode/skill)
        assert platform.base_dir == Path.home() / ".config" / "opencode"

    def test_skills_dir(self, platform: CodexPlatform) -> None:
        """Test skills directory."""
        assert platform.skills_dir == Path.home() / ".config" / "opencode" / "skill"

    def test_get_install_path_skill(self, platform: CodexPlatform) -> None:
        """Test getting skill install path."""
        path = platform.get_install_path("skill", "test")
        assert path == platform.skills_dir / "test"

    def test_get_install_path_agent_unsupported(self, platform: CodexPlatform) -> None:
        """Test getting agent path raises error."""
        with pytest.raises(ValueError, match="only supports skills"):
            platform.get_install_path("agent", "test")

    def test_validate_agent_valid(self, platform: CodexPlatform) -> None:
        """Test validating valid Codex skill content."""
        content = """---
name: test
---

# Test Skill
"""
        errors = platform.validate_agent(content)
        assert errors == []

    def test_validate_agent_no_frontmatter(self, platform: CodexPlatform) -> None:
        """Test validating skill without frontmatter."""
        content = "# Just content"
        errors = platform.validate_agent(content)
        assert len(errors) == 1
        assert "frontmatter" in errors[0].lower()


class TestPlatformIsAvailable:
    """Tests for is_available method across platforms."""

    def test_claude_is_available_with_dir(self, temp_home: Path) -> None:
        """Test Claude is available when directory exists."""
        platform = ClaudePlatform()
        platform._base_dir = None  # Reset cached value
        (temp_home / ".claude").mkdir(parents=True)
        assert platform.is_available() is True

    def test_claude_is_not_available_without_dir(self, temp_home: Path) -> None:
        """Test Claude is not available when directory missing."""
        platform = ClaudePlatform()
        platform._base_dir = None  # Reset cached value
        assert platform.is_available() is False

    @patch.object(sys, "platform", "linux")
    def test_copilot_is_available_with_extension(self, temp_home: Path) -> None:
        """Test Copilot is available when gh-copilot extension exists."""
        platform = CopilotPlatform()
        platform._base_dir = None  # Reset cached value
        (temp_home / ".local" / "share" / "gh" / "extensions" / "gh-copilot").mkdir(
            parents=True
        )
        assert platform.is_available() is True

    @patch.object(sys, "platform", "linux")
    def test_copilot_is_not_available_without_extension(self, temp_home: Path) -> None:
        """Test Copilot is not available when extension missing."""
        platform = CopilotPlatform()
        platform._base_dir = None  # Reset cached value
        assert platform.is_available() is False

    def test_codex_is_available_with_dir(self, temp_home: Path) -> None:
        """Test Codex is available when directory exists."""
        platform = CodexPlatform()
        platform._base_dir = None  # Reset cached value
        (temp_home / ".config" / "opencode").mkdir(parents=True)
        assert platform.is_available() is True

    def test_codex_is_not_available_without_dir(self, temp_home: Path) -> None:
        """Test Codex is not available when directory missing."""
        platform = CodexPlatform()
        platform._base_dir = None  # Reset cached value
        assert platform.is_available() is False


class TestPlatformEnsureDirs:
    """Tests for ensure_dirs method across platforms."""

    def test_copilot_ensure_dirs(self, temp_home: Path) -> None:
        """Test Copilot creates required directories."""
        platform = CopilotPlatform()
        platform._base_dir = None  # Reset cached value
        platform.ensure_dirs()
        assert platform.agents_dir.exists()

    def test_codex_ensure_dirs(self, temp_home: Path) -> None:
        """Test Codex creates required directories."""
        platform = CodexPlatform()
        platform._base_dir = None  # Reset cached value
        platform.ensure_dirs()
        assert platform.skills_dir.exists()

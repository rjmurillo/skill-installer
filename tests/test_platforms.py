"""Tests for platform modules."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from skill_installer.platforms import (
    ClaudePlatform,
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
        """Test validating agent without tools field."""
        content = """---
name: test
---

# Test
"""
        errors = platform.validate_agent(content)
        assert len(errors) == 1
        assert "tools" in errors[0].lower()


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
        """Test validating agent with missing required fields."""
        content = """---
description: Test
---

# Test
"""
        errors = platform.validate_agent(content)
        assert len(errors) == 2  # Missing both name and tools

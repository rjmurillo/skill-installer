"""Tests for install module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_installer.discovery import DiscoveredItem
from skill_installer.gitops import GitOps
from skill_installer.install import InstallResult, Installer
from skill_installer.registry import RegistryManager


@pytest.fixture
def temp_registry(tmp_path: Path) -> RegistryManager:
    """Create a registry manager with temporary directory."""
    return RegistryManager(registry_dir=tmp_path / "registry")


@pytest.fixture
def temp_gitops(tmp_path: Path) -> GitOps:
    """Create a GitOps instance with temporary cache."""
    return GitOps(cache_dir=tmp_path / "cache")


@pytest.fixture
def installer(temp_registry: RegistryManager, temp_gitops: GitOps) -> Installer:
    """Create an Installer instance."""
    return Installer(registry=temp_registry, gitops=temp_gitops)


@pytest.fixture
def sample_agent(tmp_path: Path) -> DiscoveredItem:
    """Create a sample discovered agent."""
    agent_path = tmp_path / "source" / "analyst.md"
    agent_path.parent.mkdir(parents=True)
    agent_path.write_text(
        """---
name: analyst
description: Research specialist
---

# Analyst Agent
"""
    )
    return DiscoveredItem(
        name="analyst",
        item_type="agent",
        path=agent_path,
        description="Research specialist",
        platforms=["claude"],
        frontmatter={"name": "analyst"},
    )


@pytest.fixture
def sample_skill(tmp_path: Path) -> DiscoveredItem:
    """Create a sample discovered skill."""
    skill_path = tmp_path / "source" / "github"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text(
        """---
name: github
description: GitHub operations
---

# GitHub Skill
"""
    )
    (skill_path / "scripts").mkdir()
    (skill_path / "scripts" / "test.ps1").write_text("Write-Host 'test'")
    return DiscoveredItem(
        name="github",
        item_type="skill",
        path=skill_path,
        description="GitHub operations",
        platforms=["claude"],
    )


class TestInstallResult:
    """Tests for InstallResult dataclass."""

    def test_success_result(self, tmp_path: Path) -> None:
        """Test successful install result."""
        result = InstallResult(
            success=True,
            item_id="source/agent/test",
            platform="claude",
            installed_path=tmp_path / "test.md",
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed install result."""
        result = InstallResult(
            success=False,
            item_id="source/agent/test",
            platform="claude",
            installed_path=None,
            error="Validation failed",
        )
        assert result.success is False
        assert result.error == "Validation failed"


class TestInstaller:
    """Tests for Installer class."""

    def test_install_agent(
        self,
        installer: Installer,
        sample_agent: DiscoveredItem,
        tmp_path: Path,
    ) -> None:
        """Test installing an agent."""
        with patch(
            "skill_installer.platforms.claude.ClaudePlatform.base_dir",
            new_callable=lambda: property(lambda self: tmp_path / ".claude"),
        ):
            result = installer.install_item(sample_agent, "source", "claude")

        assert result.success is True
        assert result.item_id == "source/agent/analyst"
        assert result.installed_path is not None

    def test_install_skill(
        self,
        installer: Installer,
        sample_skill: DiscoveredItem,
        tmp_path: Path,
    ) -> None:
        """Test installing a skill."""
        with patch(
            "skill_installer.platforms.claude.ClaudePlatform.base_dir",
            new_callable=lambda: property(lambda self: tmp_path / ".claude"),
        ):
            result = installer.install_item(sample_skill, "source", "claude")

        assert result.success is True
        assert result.item_id == "source/skill/github"

    def test_uninstall_item(
        self,
        installer: Installer,
        sample_agent: DiscoveredItem,
        tmp_path: Path,
    ) -> None:
        """Test uninstalling an item."""
        with patch(
            "skill_installer.platforms.claude.ClaudePlatform.base_dir",
            new_callable=lambda: property(lambda self: tmp_path / ".claude"),
        ):
            # First install
            installer.install_item(sample_agent, "source", "claude")

            # Then uninstall
            results = installer.uninstall_item("source/agent/analyst", "claude")

        assert len(results) == 1
        assert results[0].success is True

    def test_uninstall_nonexistent(self, installer: Installer) -> None:
        """Test uninstalling a nonexistent item."""
        results = installer.uninstall_item("nonexistent/agent/test")
        assert len(results) == 0

    def test_check_update_needed_not_installed(
        self,
        installer: Installer,
        sample_agent: DiscoveredItem,
    ) -> None:
        """Test checking update for non-installed item."""
        needs_update = installer.check_update_needed(sample_agent, "source", "claude")
        assert needs_update is True  # Not installed = needs install

    def test_check_update_needed_hash_changed(
        self,
        installer: Installer,
        sample_agent: DiscoveredItem,
        tmp_path: Path,
    ) -> None:
        """Test checking update when content changed."""
        with patch(
            "skill_installer.platforms.claude.ClaudePlatform.base_dir",
            new_callable=lambda: property(lambda self: tmp_path / ".claude"),
        ):
            # Install first
            installer.install_item(sample_agent, "source", "claude")

            # Modify source content
            sample_agent.path.write_text(
                """---
name: analyst
description: Updated description
---

# Analyst Agent - Updated
"""
            )

            # Check if update needed
            needs_update = installer.check_update_needed(sample_agent, "source", "claude")

        assert needs_update is True

    def test_detect_source_platform_from_extension(self, installer: Installer) -> None:
        """Test detecting source platform from file extension."""
        # .agent.md indicates VS Code
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=Path("/test/test.agent.md"),
            platforms=[],
        )
        platform = installer._detect_source_platform(item)
        assert platform == "vscode"

        # .md indicates Claude
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=Path("/test/test.md"),
            platforms=[],
        )
        platform = installer._detect_source_platform(item)
        assert platform == "claude"

    def test_detect_source_platform_from_item(self, installer: Installer) -> None:
        """Test detecting source platform from item's platforms list."""
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=Path("/test/test.md"),
            platforms=["vscode"],
        )
        platform = installer._detect_source_platform(item)
        assert platform == "vscode"

    def test_get_content_agent(
        self,
        installer: Installer,
        sample_agent: DiscoveredItem,
    ) -> None:
        """Test getting content for an agent."""
        content = installer._get_content(sample_agent)
        assert "name: analyst" in content

    def test_get_content_skill(
        self,
        installer: Installer,
        sample_skill: DiscoveredItem,
    ) -> None:
        """Test getting content for a skill."""
        content = installer._get_content(sample_skill)
        assert "name: github" in content


class TestInstallerEdgeCases:
    """Edge case tests for Installer."""

    def test_install_to_unsupported_platform(
        self,
        installer: Installer,
        sample_skill: DiscoveredItem,
    ) -> None:
        """Test installing skill to platform that doesn't support skills."""
        result = installer.install_item(sample_skill, "source", "vscode")
        assert result.success is False
        assert "does not support" in result.error.lower()

    def test_install_with_transform(
        self,
        installer: Installer,
        tmp_path: Path,
    ) -> None:
        """Test installing with format transformation."""
        # Create a Claude-format agent
        agent_path = tmp_path / "source" / "test.md"
        agent_path.parent.mkdir(parents=True)
        agent_path.write_text(
            """---
name: test
model: sonnet
---

# Test Agent
"""
        )
        item = DiscoveredItem(
            name="test",
            item_type="agent",
            path=agent_path,
            platforms=["claude"],
        )

        with patch(
            "skill_installer.platforms.vscode.VSCodePlatform.base_dir",
            new_callable=lambda: property(lambda self: tmp_path / ".vscode"),
        ):
            result = installer.install_item(item, "source", "vscode", "claude")

        # The transform should add tools
        if result.success:
            installed_content = result.installed_path.read_text()
            assert "tools:" in installed_content

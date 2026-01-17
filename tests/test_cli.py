"""Tests for CLI commands using context injection.

This module demonstrates the testability improvements from Layer 1.5 remediation.
Commands accept _context parameter for dependency injection, enabling unit tests
without mocking module-level imports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest
import typer

from skill_installer import cli
from skill_installer.context import AppContext
from skill_installer.discovery import DiscoveredItem
from skill_installer.install import InstallResult
from skill_installer.registry import InstalledItem, Source


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock RegistryManager."""
    registry = MagicMock()
    registry.registry_dir = Path("/fake/registry")
    return registry


@pytest.fixture
def mock_gitops() -> MagicMock:
    """Create a mock GitOps."""
    return MagicMock()


@pytest.fixture
def mock_discovery() -> MagicMock:
    """Create a mock Discovery."""
    return MagicMock()


@pytest.fixture
def mock_installer() -> MagicMock:
    """Create a mock Installer."""
    return MagicMock()


@pytest.fixture
def mock_context(
    mock_registry: MagicMock,
    mock_gitops: MagicMock,
    mock_discovery: MagicMock,
    mock_installer: MagicMock,
) -> AppContext:
    """Create a mock AppContext with all dependencies."""
    return AppContext(
        registry=mock_registry,
        gitops=mock_gitops,
        discovery=mock_discovery,
        installer=mock_installer,
    )


class TestSourceCommands:
    """Tests for source management commands."""

    def test_source_add_success(self, mock_context: AppContext) -> None:
        """Test adding a source successfully."""
        # Arrange
        source = Source(name="test-source", url="https://github.com/test/repo")
        mock_context.registry.add_source.return_value = source
        mock_context.gitops.get_license.return_value = "MIT License"

        # Act
        cli.source_add(
            url="https://github.com/test/repo",
            name="test-source",
            ref="main",
            platforms="claude,vscode",
            _context=mock_context,
        )

        # Assert
        mock_context.registry.add_source.assert_called_once_with(
            "https://github.com/test/repo",
            "test-source",
            "main",
            ["claude", "vscode"],
        )
        mock_context.gitops.clone_or_fetch.assert_called_once()
        mock_context.registry.update_source_sync_time.assert_called_once_with("test-source")

    def test_source_add_with_license(self, mock_context: AppContext) -> None:
        """Test adding a source extracts and stores license."""
        # Arrange
        source = Source(name="licensed-source", url="https://github.com/test/repo")
        mock_context.registry.add_source.return_value = source
        mock_context.gitops.get_license.return_value = "Apache 2.0 License"

        # Act
        cli.source_add(
            url="https://github.com/test/repo",
            _context=mock_context,
        )

        # Assert
        mock_context.gitops.get_license.assert_called_once_with("licensed-source")
        mock_context.registry.update_source_license.assert_called_once_with(
            "licensed-source", "Apache 2.0 License"
        )

    def test_source_add_duplicate_error(self, mock_context: AppContext) -> None:
        """Test adding a duplicate source raises error."""
        # Arrange
        mock_context.registry.add_source.side_effect = ValueError("Source already exists")

        # Act & Assert
        with pytest.raises(typer.Exit) as exc_info:
            cli.source_add(
                url="https://github.com/test/repo",
                _context=mock_context,
            )
        assert exc_info.value.exit_code == 1

    def test_source_remove_success(self, mock_context: AppContext) -> None:
        """Test removing a source successfully."""
        # Arrange
        mock_context.registry.remove_source.return_value = True

        # Act
        cli.source_remove(name="test-source", _context=mock_context)

        # Assert
        mock_context.registry.remove_source.assert_called_once_with("test-source")
        mock_context.gitops.remove_cached.assert_called_once_with("test-source")

    def test_source_remove_not_found(self, mock_context: AppContext) -> None:
        """Test removing a non-existent source."""
        # Arrange
        mock_context.registry.remove_source.return_value = False

        # Act & Assert
        with pytest.raises(typer.Exit) as exc_info:
            cli.source_remove(name="unknown", _context=mock_context)
        assert exc_info.value.exit_code == 1

    def test_source_list(self, mock_context: AppContext) -> None:
        """Test listing sources."""
        # Arrange
        sources = [
            Source(name="source1", url="https://github.com/test/repo1"),
            Source(name="source2", url="https://github.com/test/repo2"),
        ]
        mock_context.registry.list_sources.return_value = sources

        # Act
        cli.source_list(_context=mock_context)

        # Assert
        mock_context.registry.list_sources.assert_called_once()

    def test_source_update_all(self, mock_context: AppContext) -> None:
        """Test updating all sources."""
        # Arrange
        sources = [
            Source(name="source1", url="https://github.com/test/repo1"),
            Source(name="source2", url="https://github.com/test/repo2"),
        ]
        mock_context.registry.list_sources.return_value = sources

        # Act
        cli.source_update(name=None, _context=mock_context)

        # Assert
        assert mock_context.gitops.clone_or_fetch.call_count == 2
        assert mock_context.registry.update_source_sync_time.call_count == 2

    def test_source_update_specific(self, mock_context: AppContext) -> None:
        """Test updating a specific source."""
        # Arrange
        sources = [
            Source(name="source1", url="https://github.com/test/repo1"),
            Source(name="source2", url="https://github.com/test/repo2"),
        ]
        mock_context.registry.list_sources.return_value = sources

        # Act
        cli.source_update(name="source1", _context=mock_context)

        # Assert
        mock_context.gitops.clone_or_fetch.assert_called_once()
        mock_context.registry.update_source_sync_time.assert_called_once_with("source1")


class TestInstallCommands:
    """Tests for install/uninstall commands."""

    def test_status_shows_installed(self, mock_context: AppContext) -> None:
        """Test status command shows installed items."""
        # Arrange
        installed = [
            InstalledItem(
                id="source/agent/test",
                source="source",
                type="agent",
                name="test",
                platform="claude",
                installedPath="/path/to/test.md",
                sourceHash="abc123",
                installedAt=datetime.now(timezone.utc),
            )
        ]
        mock_context.registry.list_installed.return_value = installed

        # Act
        cli.status(_context=mock_context)

        # Assert
        mock_context.registry.list_installed.assert_called_once()

    def test_uninstall_item(self, mock_context: AppContext) -> None:
        """Test uninstalling an item."""
        # Arrange
        result = InstallResult(
            success=True,
            item_id="source/agent/test",
            platform="claude",
            installed_path=None,
        )
        mock_context.installer.uninstall_item.return_value = [result]

        # Act
        cli.uninstall(item="source/agent/test", _context=mock_context)

        # Assert
        mock_context.installer.uninstall_item.assert_called_once_with(
            "source/agent/test", None
        )

    def test_uninstall_item_not_found(self, mock_context: AppContext) -> None:
        """Test uninstalling a non-existent item shows warning."""
        # Arrange
        mock_context.installer.uninstall_item.return_value = []

        # Act (should not raise)
        cli.uninstall(item="unknown/agent/test", _context=mock_context)

        # Assert
        mock_context.installer.uninstall_item.assert_called_once()


class TestConfigCommands:
    """Tests for config commands."""

    def test_config_show(self, mock_context: AppContext) -> None:
        """Test showing configuration."""
        # Arrange
        from skill_installer.registry import SourceRegistry

        mock_context.registry.load_sources.return_value = SourceRegistry()

        # Act
        cli.config_show(_context=mock_context)

        # Assert
        mock_context.registry.load_sources.assert_called_once()

    def test_config_set_platforms(self, mock_context: AppContext) -> None:
        """Test setting default platforms."""
        # Arrange
        from skill_installer.registry import SourceRegistry

        registry = SourceRegistry()
        mock_context.registry.load_sources.return_value = registry

        # Act
        cli.config_set(key="default-platforms", value="claude,copilot", _context=mock_context)

        # Assert
        mock_context.registry.save_sources.assert_called_once()
        saved_registry = mock_context.registry.save_sources.call_args[0][0]
        assert saved_registry.defaults["targetPlatforms"] == ["claude", "copilot"]

    def test_config_set_unknown_key(self, mock_context: AppContext) -> None:
        """Test setting an unknown config key."""
        # Arrange
        from skill_installer.registry import SourceRegistry

        mock_context.registry.load_sources.return_value = SourceRegistry()

        # Act & Assert
        with pytest.raises(typer.Exit) as exc_info:
            cli.config_set(key="unknown-key", value="value", _context=mock_context)
        assert exc_info.value.exit_code == 1


class TestHelperFunctions:
    """Tests for CLI helper functions."""

    def test_parse_platforms_with_value(self) -> None:
        """Test parsing platform string."""
        result = cli._parse_platforms("claude, vscode, copilot")
        assert result == ["claude", "vscode", "copilot"]

    def test_parse_platforms_none(self) -> None:
        """Test parsing None returns defaults."""
        result = cli._parse_platforms(None)
        assert result == ["claude", "vscode"]

    def test_parse_item_id_two_parts(self) -> None:
        """Test parsing source/name format."""
        source_name, item_type, item_name = cli._parse_item_id("my-source/my-agent")
        assert source_name == "my-source"
        assert item_type is None
        assert item_name == "my-agent"

    def test_parse_item_id_three_parts(self) -> None:
        """Test parsing source/type/name format."""
        source_name, item_type, item_name = cli._parse_item_id("my-source/agent/my-agent")
        assert source_name == "my-source"
        assert item_type == "agent"
        assert item_name == "my-agent"

    def test_parse_item_id_invalid(self) -> None:
        """Test parsing invalid format raises exit."""
        with pytest.raises(typer.Exit) as exc_info:
            cli._parse_item_id("invalid")
        assert exc_info.value.exit_code == 1


class TestInstallCommand:
    """Tests for install command."""

    def test_install_source_not_found(self, mock_context: AppContext) -> None:
        """Test install with unknown source."""
        mock_context.registry.get_source.return_value = None

        with pytest.raises(typer.Exit) as exc_info:
            cli.install(
                item="unknown-source/agent/test",
                _context=mock_context,
            )
        assert exc_info.value.exit_code == 1

    def test_install_item_not_found(self, mock_context: AppContext) -> None:
        """Test install with unknown item."""
        source = Source(name="test-source", url="https://github.com/test/repo")
        mock_context.registry.get_source.return_value = source
        mock_context.gitops.get_repo_path.return_value = Path("/fake/repo")
        mock_context.discovery.discover_all.return_value = []

        with pytest.raises(typer.Exit) as exc_info:
            cli.install(
                item="test-source/agent/missing",
                _context=mock_context,
            )
        assert exc_info.value.exit_code == 1

    def test_install_success(self, mock_context: AppContext) -> None:
        """Test successful installation."""
        source = Source(name="test-source", url="https://github.com/test/repo")
        mock_context.registry.get_source.return_value = source
        mock_context.gitops.get_repo_path.return_value = Path("/fake/repo")

        item = DiscoveredItem(
            name="test-agent",
            item_type="agent",
            description="Test agent",
            path=Path("/fake/repo/test-agent.md"),
            platforms=["claude"],
        )
        mock_context.discovery.discover_all.return_value = [item]
        mock_context.installer.install_item.return_value = InstallResult(
            success=True,
            item_id="test-source/agent/test-agent",
            platform="claude",
            installed_path=Path("/installed/path"),
        )

        cli.install(
            item="test-source/agent/test-agent",
            _context=mock_context,
        )

        mock_context.installer.install_item.assert_called()


class TestSyncCommand:
    """Tests for sync command."""

    def test_sync_updates_sources(self, mock_context: AppContext) -> None:
        """Test sync updates all sources."""
        sources = [
            Source(name="source1", url="https://github.com/test/repo1"),
            Source(name="source2", url="https://github.com/test/repo2"),
        ]
        mock_context.registry.list_sources.return_value = sources
        mock_context.registry.list_installed.return_value = []

        cli.sync(_context=mock_context)

        assert mock_context.gitops.clone_or_fetch.call_count == 2

    def test_sync_updates_installed_items(self, mock_context: AppContext) -> None:
        """Test sync checks and updates installed items."""
        source = Source(name="test-source", url="https://github.com/test/repo")
        mock_context.registry.list_sources.return_value = [source]
        mock_context.registry.get_source.return_value = source

        installed = InstalledItem(
            id="test-source/agent/test",
            source="test-source",
            type="agent",
            name="test",
            platform="claude",
            installedPath="/path/to/test.md",
            sourceHash="abc123",
            installedAt=datetime.now(timezone.utc),
        )
        mock_context.registry.list_installed.return_value = [installed]
        mock_context.gitops.get_repo_path.return_value = Path("/fake/repo")

        item = DiscoveredItem(
            name="test",
            item_type="agent",
            description="Test",
            path=Path("/fake/repo/test.md"),
            platforms=["claude"],
        )
        mock_context.discovery.discover_all.return_value = [item]
        mock_context.installer.check_update_needed.return_value = False

        cli.sync(_context=mock_context)

        mock_context.installer.check_update_needed.assert_called()

    def test_sync_missing_source(self, mock_context: AppContext) -> None:
        """Test sync handles missing source for installed item."""
        mock_context.registry.list_sources.return_value = []
        mock_context.registry.get_source.return_value = None

        installed = InstalledItem(
            id="missing-source/agent/test",
            source="missing-source",
            type="agent",
            name="test",
            platform="claude",
            installedPath="/path/to/test.md",
            sourceHash="abc123",
            installedAt=datetime.now(timezone.utc),
        )
        mock_context.registry.list_installed.return_value = [installed]

        # Should not raise
        cli.sync(_context=mock_context)

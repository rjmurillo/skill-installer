"""Tests for registry module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_installer.registry import (
    InstalledItem,
    RegistryManager,
    Source,
    SourceRegistry,
)


@pytest.fixture
def temp_registry(tmp_path: Path) -> RegistryManager:
    """Create a registry manager with temporary directory."""
    return RegistryManager(registry_dir=tmp_path)


class TestSourceRegistry:
    """Tests for SourceRegistry model."""

    def test_default_values(self) -> None:
        """Test SourceRegistry has correct defaults."""
        registry = SourceRegistry()
        assert registry.version == "1.0"
        assert registry.sources == []
        assert registry.defaults == {"targetPlatforms": ["claude", "vscode"]}

    def test_with_sources(self) -> None:
        """Test SourceRegistry with sources."""
        source = Source(name="test", url="https://github.com/test/repo")
        registry = SourceRegistry(sources=[source])
        assert len(registry.sources) == 1
        assert registry.sources[0].name == "test"


class TestSource:
    """Tests for Source model."""

    def test_minimal_source(self) -> None:
        """Test Source with minimal fields."""
        source = Source(name="test", url="https://github.com/test/repo")
        assert source.name == "test"
        assert source.url == "https://github.com/test/repo"
        assert source.ref == "main"
        assert source.platforms == ["claude", "vscode"]

    def test_full_source(self) -> None:
        """Test Source with all fields."""
        source = Source(
            name="test",
            url="https://github.com/test/repo",
            ref="develop",
            platforms=["claude"],
        )
        assert source.ref == "develop"
        assert source.platforms == ["claude"]


class TestInstalledItem:
    """Tests for InstalledItem model."""

    def test_installed_item(self) -> None:
        """Test InstalledItem model."""
        now = datetime.now(timezone.utc)
        item = InstalledItem(
            id="source/agent/test",
            source="source",
            type="agent",
            name="test",
            platform="claude",
            installedPath="/path/to/test.md",
            sourceHash="abc123",
            installedAt=now,
        )
        assert item.id == "source/agent/test"
        assert item.item_type == "agent"
        assert item.installed_path == "/path/to/test.md"


class TestRegistryManager:
    """Tests for RegistryManager."""

    def test_ensure_registry_dir(self, temp_registry: RegistryManager) -> None:
        """Test registry directory creation."""
        temp_registry.ensure_registry_dir()
        assert temp_registry.registry_dir.exists()

    def test_load_sources_empty(self, temp_registry: RegistryManager) -> None:
        """Test loading empty sources."""
        registry = temp_registry.load_sources()
        assert registry.sources == []

    def test_save_and_load_sources(self, temp_registry: RegistryManager) -> None:
        """Test saving and loading sources."""
        source = Source(name="test", url="https://github.com/test/repo")
        registry = SourceRegistry(sources=[source])
        temp_registry.save_sources(registry)

        loaded = temp_registry.load_sources()
        assert len(loaded.sources) == 1
        assert loaded.sources[0].name == "test"

    def test_add_source(self, temp_registry: RegistryManager) -> None:
        """Test adding a source."""
        source = temp_registry.add_source("https://github.com/test/repo", "test")
        assert source.name == "test"
        assert source.url == "https://github.com/test/repo"

        # Verify persisted
        registry = temp_registry.load_sources()
        assert len(registry.sources) == 1

    def test_add_source_derive_name(self, temp_registry: RegistryManager) -> None:
        """Test adding source with auto-derived name."""
        source = temp_registry.add_source("https://github.com/user/my-repo")
        assert source.name == "my-repo"

    def test_add_source_derive_name_git_suffix(self, temp_registry: RegistryManager) -> None:
        """Test name derivation removes .git suffix."""
        source = temp_registry.add_source("https://github.com/user/repo.git")
        assert source.name == "repo"

    def test_add_source_duplicate(self, temp_registry: RegistryManager) -> None:
        """Test adding duplicate source raises error."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        with pytest.raises(ValueError, match="already exists"):
            temp_registry.add_source("https://github.com/test/other", "test")

    def test_remove_source(self, temp_registry: RegistryManager) -> None:
        """Test removing a source."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        assert temp_registry.remove_source("test") is True
        assert temp_registry.remove_source("nonexistent") is False

    def test_get_source(self, temp_registry: RegistryManager) -> None:
        """Test getting a source by name."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        source = temp_registry.get_source("test")
        assert source is not None
        assert source.name == "test"

        assert temp_registry.get_source("nonexistent") is None

    def test_list_sources(self, temp_registry: RegistryManager) -> None:
        """Test listing sources."""
        temp_registry.add_source("https://github.com/test/repo1", "repo1")
        temp_registry.add_source("https://github.com/test/repo2", "repo2")
        sources = temp_registry.list_sources()
        assert len(sources) == 2

    def test_update_source_sync_time(self, temp_registry: RegistryManager) -> None:
        """Test updating source sync time."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.update_source_sync_time("test")
        source = temp_registry.get_source("test")
        assert source is not None
        assert source.last_sync is not None

    def test_add_installed(self, temp_registry: RegistryManager) -> None:
        """Test adding an installed item."""
        item = temp_registry.add_installed(
            source_name="source",
            item_type="agent",
            name="test",
            platform="claude",
            installed_path="/path/to/test.md",
            source_hash="abc123",
        )
        assert item.id == "source/agent/test"
        assert item.platform == "claude"

    def test_remove_installed(self, temp_registry: RegistryManager) -> None:
        """Test removing an installed item."""
        temp_registry.add_installed(
            source_name="source",
            item_type="agent",
            name="test",
            platform="claude",
            installed_path="/path/to/test.md",
            source_hash="abc123",
        )
        assert temp_registry.remove_installed("source/agent/test", "claude") is True
        assert temp_registry.remove_installed("nonexistent", "claude") is False

    def test_get_installed(self, temp_registry: RegistryManager) -> None:
        """Test getting installed items."""
        temp_registry.add_installed(
            source_name="source",
            item_type="agent",
            name="test",
            platform="claude",
            installed_path="/path/to/test.md",
            source_hash="abc123",
        )
        items = temp_registry.get_installed("source/agent/test")
        assert len(items) == 1

    def test_list_installed(self, temp_registry: RegistryManager) -> None:
        """Test listing installed items with filters."""
        temp_registry.add_installed(
            source_name="source1",
            item_type="agent",
            name="test1",
            platform="claude",
            installed_path="/path/to/test1.md",
            source_hash="abc123",
        )
        temp_registry.add_installed(
            source_name="source2",
            item_type="agent",
            name="test2",
            platform="vscode",
            installed_path="/path/to/test2.md",
            source_hash="def456",
        )

        all_items = temp_registry.list_installed()
        assert len(all_items) == 2

        source_items = temp_registry.list_installed(source="source1")
        assert len(source_items) == 1

        platform_items = temp_registry.list_installed(platform="claude")
        assert len(platform_items) == 1

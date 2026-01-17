"""Tests for registry module."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_installer.registry import (
    InstalledItem,
    MarketplaceManifest,
    MarketplaceMetadata,
    MarketplaceOwner,
    MarketplacePlugin,
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
        """Test adding source with auto-derived name includes owner/repo."""
        source = temp_registry.add_source("https://github.com/user/my-repo")
        assert source.name == "user/my-repo"

    def test_add_source_derive_name_git_suffix(self, temp_registry: RegistryManager) -> None:
        """Test name derivation removes .git suffix."""
        source = temp_registry.add_source("https://github.com/user/repo.git")
        assert source.name == "user/repo"

    def test_add_source_derive_name_different_orgs(self, temp_registry: RegistryManager) -> None:
        """Test adding sources with same repo name but different orgs."""
        source1 = temp_registry.add_source("https://github.com/anthropics/skills")
        source2 = temp_registry.add_source("https://github.com/openai/skills")
        assert source1.name == "anthropics/skills"
        assert source2.name == "openai/skills"

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

    def test_update_source_license(self, temp_registry: RegistryManager) -> None:
        """Test updating source license."""
        temp_registry.add_source("https://github.com/test/repo", "test-source")

        temp_registry.update_source_license("test-source", "MIT")

        source = temp_registry.get_source("test-source")
        assert source is not None
        assert source.license == "MIT"

    def test_update_source_license_not_found(self, temp_registry: RegistryManager) -> None:
        """Test updating license for non-existent source."""
        temp_registry.update_source_license("nonexistent", "MIT")

        source = temp_registry.get_source("nonexistent")
        assert source is None

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


class TestMarketplaceOwner:
    """Tests for MarketplaceOwner model."""

    def test_owner_with_email(self) -> None:
        """Test MarketplaceOwner with email."""
        owner = MarketplaceOwner(name="Test Author", email="test@example.com")
        assert owner.name == "Test Author"
        assert owner.email == "test@example.com"

    def test_owner_without_email(self) -> None:
        """Test MarketplaceOwner without email defaults to empty string."""
        owner = MarketplaceOwner(name="Test Author")
        assert owner.name == "Test Author"
        assert owner.email == ""


class TestMarketplaceMetadata:
    """Tests for MarketplaceMetadata model."""

    def test_metadata_defaults(self) -> None:
        """Test MarketplaceMetadata default values."""
        metadata = MarketplaceMetadata()
        assert metadata.description == ""
        assert metadata.version == "1.0.0"

    def test_metadata_with_values(self) -> None:
        """Test MarketplaceMetadata with custom values."""
        metadata = MarketplaceMetadata(description="Test marketplace", version="2.0.0")
        assert metadata.description == "Test marketplace"
        assert metadata.version == "2.0.0"


class TestMarketplacePlugin:
    """Tests for MarketplacePlugin model."""

    def test_plugin_minimal(self) -> None:
        """Test MarketplacePlugin with minimal fields."""
        plugin = MarketplacePlugin(name="test-plugin")
        assert plugin.name == "test-plugin"
        assert plugin.description == ""
        assert plugin.source == "./"
        assert plugin.strict is False
        assert plugin.skills == []

    def test_plugin_with_skills(self) -> None:
        """Test MarketplacePlugin with skills."""
        plugin = MarketplacePlugin(
            name="document-skills",
            description="Document processing",
            skills=["./skills/pdf", "./skills/docx"],
        )
        assert plugin.name == "document-skills"
        assert len(plugin.skills) == 2


class TestMarketplaceManifest:
    """Tests for MarketplaceManifest model."""

    def test_manifest_minimal(self) -> None:
        """Test MarketplaceManifest with minimal fields."""
        manifest = MarketplaceManifest(name="test-marketplace")
        assert manifest.name == "test-marketplace"
        assert manifest.owner is None
        assert manifest.metadata.description == ""
        assert manifest.plugins == []

    def test_manifest_full(self) -> None:
        """Test MarketplaceManifest with all fields."""
        manifest = MarketplaceManifest(
            name="test-marketplace",
            owner=MarketplaceOwner(name="Test Author", email="test@example.com"),
            metadata=MarketplaceMetadata(description="Test", version="1.0.0"),
            plugins=[MarketplacePlugin(name="test-plugin", skills=["./skills/test"])],
        )
        assert manifest.name == "test-marketplace"
        assert manifest.owner is not None
        assert manifest.owner.name == "Test Author"
        assert len(manifest.plugins) == 1

    def test_manifest_from_file(self, tmp_path: Path) -> None:
        """Test loading MarketplaceManifest from file."""
        manifest_data = {
            "name": "test-marketplace",
            "owner": {"name": "Test Author", "email": "test@example.com"},
            "metadata": {"description": "Test marketplace", "version": "1.0.0"},
            "plugins": [
                {"name": "test-plugin", "skills": ["./skills/pdf"]}
            ],
        }
        manifest_file = tmp_path / "marketplace.json"
        manifest_file.write_text(json.dumps(manifest_data))

        manifest = MarketplaceManifest.from_file(manifest_file)
        assert manifest.name == "test-marketplace"
        assert manifest.owner is not None
        assert manifest.owner.name == "Test Author"
        assert len(manifest.plugins) == 1

    def test_manifest_from_file_not_found(self, tmp_path: Path) -> None:
        """Test loading MarketplaceManifest from non-existent file."""
        manifest_file = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            MarketplaceManifest.from_file(manifest_file)

    def test_manifest_from_file_invalid_json(self, tmp_path: Path) -> None:
        """Test loading MarketplaceManifest from invalid JSON."""
        manifest_file = tmp_path / "invalid.json"
        manifest_file.write_text("{ invalid json }")
        with pytest.raises(json.JSONDecodeError):
            MarketplaceManifest.from_file(manifest_file)


class TestSourceMarketplace:
    """Tests for Source marketplace_enabled field."""

    def test_source_marketplace_default(self) -> None:
        """Test Source marketplace_enabled defaults to False."""
        source = Source(name="test", url="https://github.com/test/repo")
        assert source.marketplace_enabled is False

    def test_source_marketplace_enabled(self) -> None:
        """Test Source with marketplace_enabled set."""
        source = Source(
            name="skills",
            url="https://github.com/anthropics/skills",
            marketplace_enabled=True,
        )
        assert source.marketplace_enabled is True


class TestSourceAutoUpdate:
    """Tests for Source auto_update field."""

    def test_source_auto_update_default(self) -> None:
        """Test Source auto_update defaults to False."""
        source = Source(name="test", url="https://github.com/test/repo")
        assert source.auto_update is False

    def test_source_auto_update_enabled(self) -> None:
        """Test Source with auto_update set to True."""
        source = Source(
            name="skills",
            url="https://github.com/anthropics/skills",
            auto_update=True,
        )
        assert source.auto_update is True


class TestToggleSourceAutoUpdate:
    """Tests for RegistryManager.toggle_source_auto_update()."""

    def test_toggle_auto_update_enables(self, temp_registry: RegistryManager) -> None:
        """Test toggling auto_update from False to True."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        result = temp_registry.toggle_source_auto_update("test")
        assert result is True
        source = temp_registry.get_source("test")
        assert source is not None
        assert source.auto_update is True

    def test_toggle_auto_update_disables(self, temp_registry: RegistryManager) -> None:
        """Test toggling auto_update from True to False."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")  # Enable
        result = temp_registry.toggle_source_auto_update("test")  # Disable
        assert result is False
        source = temp_registry.get_source("test")
        assert source is not None
        assert source.auto_update is False

    def test_toggle_auto_update_nonexistent_source(self, temp_registry: RegistryManager) -> None:
        """Test toggling auto_update for non-existent source returns False."""
        result = temp_registry.toggle_source_auto_update("nonexistent")
        assert result is False

    def test_toggle_auto_update_persists(self, temp_registry: RegistryManager) -> None:
        """Test that auto_update state persists after reload."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")

        # Create new manager pointing to same directory
        new_manager = RegistryManager(registry_dir=temp_registry.registry_dir)
        source = new_manager.get_source("test")
        assert source is not None
        assert source.auto_update is True


class TestGetStaleAutoUpdateSources:
    """Tests for RegistryManager.get_stale_auto_update_sources()."""

    def test_stale_sources_never_synced(self, temp_registry: RegistryManager) -> None:
        """Test sources with auto_update but never synced are stale."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")

        stale = temp_registry.get_stale_auto_update_sources()
        assert len(stale) == 1
        assert stale[0].name == "test"

    def test_stale_sources_excludes_recently_synced(self, temp_registry: RegistryManager) -> None:
        """Test recently synced sources are not stale."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")
        temp_registry.update_source_sync_time("test")

        stale = temp_registry.get_stale_auto_update_sources()
        assert len(stale) == 0

    def test_stale_sources_excludes_auto_update_disabled(self, temp_registry: RegistryManager) -> None:
        """Test sources with auto_update disabled are not stale."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        # auto_update defaults to False

        stale = temp_registry.get_stale_auto_update_sources()
        assert len(stale) == 0

    def test_stale_sources_respects_max_age(self, temp_registry: RegistryManager) -> None:
        """Test stale detection respects max_age_hours parameter."""
        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")
        temp_registry.update_source_sync_time("test")

        # With 0 hours max age, source synced now should be stale
        stale = temp_registry.get_stale_auto_update_sources(max_age_hours=0)
        assert len(stale) == 1

    def test_stale_sources_old_sync(self, temp_registry: RegistryManager) -> None:
        """Test sources with old sync time are stale."""
        from datetime import timedelta

        temp_registry.add_source("https://github.com/test/repo", "test")
        temp_registry.toggle_source_auto_update("test")

        # Manually set last_sync to 48 hours ago
        registry = temp_registry.load_sources()
        for source in registry.sources:
            if source.name == "test":
                source.last_sync = datetime.now(timezone.utc) - timedelta(hours=48)
        temp_registry.save_sources(registry)

        stale = temp_registry.get_stale_auto_update_sources(max_age_hours=24)
        assert len(stale) == 1
        assert stale[0].name == "test"

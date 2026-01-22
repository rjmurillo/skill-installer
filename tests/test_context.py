"""Tests for context module."""

from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock
from skill_installer.context import AppContext, create_context


class TestAppContext:
    """Tests for AppContext dataclass."""

    def test_create_with_all_dependencies(self) -> None:
        """Test creating context with all dependencies."""
        registry = MagicMock()
        gitops = MagicMock()
        discovery = MagicMock()
        installer = MagicMock()
        filesystem = MagicMock()
        ctx = AppContext(
            registry=registry,
            gitops=gitops,
            discovery=discovery,
            installer=installer,
            filesystem=filesystem,
        )
        assert ctx.registry is registry
        assert ctx.gitops is gitops
        assert ctx.discovery is discovery
        assert ctx.installer is installer
        assert ctx.filesystem is filesystem

    def test_default_filesystem(self) -> None:
        """Test context creates default filesystem if not provided."""
        from skill_installer.filesystem import RealFileSystem

        registry = MagicMock()
        gitops = MagicMock()
        discovery = MagicMock()
        installer = MagicMock()
        ctx = AppContext(
            registry=registry,
            gitops=gitops,
            discovery=discovery,
            installer=installer,
        )
        assert isinstance(ctx.filesystem, RealFileSystem)


class TestCreateContext:
    """Tests for create_context factory function."""

    def test_create_context_default(self, temp_registry_dir: Path, temp_cache_dir: Path) -> None:
        """Test creating context with default parameters."""
        ctx = create_context(
            registry_dir=temp_registry_dir,
            cache_dir=temp_cache_dir,
        )
        assert ctx.registry is not None
        assert ctx.gitops is not None
        assert ctx.discovery is not None
        assert ctx.installer is not None
        assert ctx.filesystem is not None

    def test_create_context_wires_dependencies(
        self, temp_registry_dir: Path, temp_cache_dir: Path
    ) -> None:
        """Test create_context wires dependencies correctly."""
        ctx = create_context(
            registry_dir=temp_registry_dir,
            cache_dir=temp_cache_dir,
        )
        # Installer should use the same registry and gitops
        assert ctx.installer.registry is ctx.registry
        assert ctx.installer.gitops is ctx.gitops

    def test_create_context_respects_registry_dir(self, temp_registry_dir: Path) -> None:
        """Test create_context uses provided registry directory."""
        ctx = create_context(registry_dir=temp_registry_dir)
        assert ctx.registry.registry_dir == temp_registry_dir

    def test_create_context_respects_cache_dir(
        self, temp_registry_dir: Path, temp_cache_dir: Path
    ) -> None:
        """Test create_context uses provided cache directory."""
        ctx = create_context(
            registry_dir=temp_registry_dir,
            cache_dir=temp_cache_dir,
        )
        assert ctx.gitops.cache_dir == temp_cache_dir

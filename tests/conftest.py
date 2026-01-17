"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override home directory for testing."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def temp_registry_dir(tmp_path: Path) -> Path:
    """Create a temporary registry directory."""
    registry_dir = tmp_path / ".skill-installer"
    registry_dir.mkdir(parents=True)
    return registry_dir


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache_dir = tmp_path / ".skill-installer" / "cache"
    cache_dir.mkdir(parents=True)
    return cache_dir


# ============================================================================
# Platform-Specific Fixtures
# ============================================================================


@pytest.fixture
def claude_platform_dir(temp_home: Path) -> Path:
    """Create Claude platform directory structure."""
    claude_dir = temp_home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    return claude_dir


@pytest.fixture
def vscode_platform_dir(temp_home: Path) -> Path:
    """Create VS Code platform directory structure."""
    vscode_dir = temp_home / ".config" / "Code" / "User" / "prompts"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    return vscode_dir


@pytest.fixture
def copilot_platform_dir(temp_home: Path) -> Path:
    """Create Copilot platform directory structure."""
    copilot_dir = temp_home / ".copilot"
    copilot_dir.mkdir(parents=True, exist_ok=True)
    return copilot_dir


@pytest.fixture
def codex_platform_dir(temp_home: Path) -> Path:
    """Create Codex platform directory structure."""
    codex_dir = temp_home / ".config" / "opencode" / "skill"
    codex_dir.mkdir(parents=True, exist_ok=True)
    return codex_dir


# ============================================================================
# Mock FileSystem Fixture
# ============================================================================


@pytest.fixture
def mock_filesystem() -> MagicMock:
    """Create a mock FileSystem for testing.

    The mock tracks all filesystem operations without touching real files.
    """
    fs = MagicMock()
    fs.exists.return_value = False
    fs.is_dir.return_value = False
    fs.read_text.return_value = ""
    return fs


# ============================================================================
# Sample Content Fixtures
# ============================================================================


@pytest.fixture
def sample_claude_agent_content() -> str:
    """Sample Claude agent file content."""
    return """---
name: analyst
description: Research and investigation specialist
model: sonnet
---

# Analyst Agent

You are an analyst agent that investigates issues.

## Capabilities

- Research topics
- Gather evidence
- Provide analysis

Use Task(subagent_type="implementer", prompt="Write code") for implementation.
"""


@pytest.fixture
def sample_vscode_agent_content() -> str:
    """Sample VS Code agent file content."""
    return """---
name: analyst
description: Research and investigation specialist
model: claude-sonnet-4-5
tools:
  - read
  - edit
  - shell
  - search
---

# Analyst Agent

You are an analyst agent that investigates issues.

## Capabilities

- Research topics
- Gather evidence
- Provide analysis

Use #runSubagent("implementer", "Write code") for implementation.
"""


@pytest.fixture
def sample_copilot_agent_content() -> str:
    """Sample Copilot agent file content."""
    return """---
name: analyst
description: Research and investigation specialist
---

# Analyst Agent

You are an analyst agent that investigates issues.

## Capabilities

- Research topics
- Gather evidence
- Provide analysis
"""


@pytest.fixture
def sample_codex_agent_content() -> str:
    """Sample Codex agent file content."""
    return """---
name: analyst
description: Research and investigation specialist
model: o3
---

# Analyst Agent

You are an analyst agent that investigates issues.
"""


@pytest.fixture
def sample_skill_content() -> str:
    """Sample skill SKILL.md content."""
    return """---
name: github
description: GitHub operations skill
---

# GitHub Skill

Provides GitHub operations like creating PRs, issues, and comments.

## Commands

- `/pr-create`: Create a pull request
- `/issue-create`: Create an issue
"""


# ============================================================================
# App Context Fixtures
# ============================================================================


@pytest.fixture
def mock_app_context() -> MagicMock:
    """Create a complete mock AppContext for CLI testing."""
    from skill_installer.context import AppContext

    ctx = MagicMock(spec=AppContext)
    ctx.registry = MagicMock()
    ctx.gitops = MagicMock()
    ctx.discovery = MagicMock()
    ctx.installer = MagicMock()
    ctx.filesystem = MagicMock()
    return ctx


@pytest.fixture
def mock_source() -> Any:
    """Create a mock Source object."""
    from datetime import datetime, timezone

    source = MagicMock()
    source.name = "test-source"
    source.url = "https://github.com/test/repo"
    source.ref = "main"
    source.platforms = ["claude", "vscode"]
    source.added_at = datetime.now(timezone.utc)
    source.last_sync = datetime.now(timezone.utc)
    return source


@pytest.fixture
def mock_discovered_item() -> Any:
    """Create a mock DiscoveredItem."""
    item = MagicMock()
    item.name = "test-agent"
    item.item_type = "agent"
    item.description = "Test agent"
    item.platforms = ["claude"]
    item.path = Path("/fake/path/test-agent.md")
    return item


@pytest.fixture
def mock_installed_item() -> Any:
    """Create a mock InstalledItem."""
    item = MagicMock()
    item.id = "test-source/agent/test-agent"
    item.source = "test-source"
    item.item_type = "agent"
    item.name = "test-agent"
    item.platform = "claude"
    item.installed_path = "/fake/install/path"
    item.source_hash = "abc123"
    return item

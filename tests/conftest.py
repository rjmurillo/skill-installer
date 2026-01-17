"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_installer.discovery import DiscoveredItem
from skill_installer.gitops import GitOps
from skill_installer.install import Installer
from skill_installer.registry import RegistryManager


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

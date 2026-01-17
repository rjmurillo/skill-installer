# Claude Code Instructions

## Project Overview

Universal skill/agent installer for AI coding platforms (Claude Code, VS Code, Copilot CLI).

## Technology Stack

- Python 3.10+
- Typer (CLI framework)
- Rich (TUI, tables, progress)
- PyYAML (frontmatter parsing)
- GitPython (clone, fetch)
- Pydantic (config validation)

## Project Structure

```text
src/skill_installer/
    __init__.py          # Package init, version
    __main__.py          # Entry point
    cli.py               # Typer CLI commands
    registry.py          # Source/installed JSON management
    discovery.py         # Find content in repositories
    transform.py         # Cross-platform conversion
    install.py           # File operations, tracking
    tui.py               # Rich TUI components
    gitops.py            # Git clone/fetch
    platforms/
        __init__.py
        claude.py        # Claude Code paths/format
        vscode.py        # VS Code paths/format
        copilot.py       # Copilot CLI paths/format
tests/
    test_registry.py
    test_discovery.py
    test_transform.py
    test_install.py
```

## Code Standards

- Type hints on all functions
- Docstrings for public functions
- No nested code (max 2 levels)
- Cyclomatic complexity under 10
- 100% test coverage goal

## Running Tests

```bash
uv run pytest
uv run pytest --cov
```

## Key Modules

### registry.py

Manages `~/.skill-installer/sources.json` and `installed.json`.

### discovery.py

Finds agents, skills, commands in source repositories.

### transform.py

Converts between platform formats (frontmatter, syntax).

### platforms/

Platform-specific logic (paths, validation, format).

## Dependencies

See `pyproject.toml` for full list. Key ones:

- typer[all]: CLI with auto-completion
- rich: Beautiful terminal output
- pydantic: Config validation
- gitpython: Git operations

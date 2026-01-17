# Repository Guidelines

## Project Structure & Module Organization

```text
src/skill_installer/
    cli.py              # Typer CLI entry point
    registry.py         # JSON source/installed data management
    discovery.py        # Repository content discovery
    transform.py        # Cross-platform format conversion
    install.py          # File operations and tracking
    tui.py              # Textual TUI components
    gitops.py           # Git clone/fetch operations
    platforms/          # Platform-specific adapters
        claude.py       # Claude Code paths/format
        vscode.py       # VS Code paths/format
        copilot.py      # Copilot CLI paths/format
        codex.py        # Codex CLI paths/format
tests/
    test_*.py           # Unit tests (mirror source modules, 100% coverage required)
    scripts/            # TMUX-based TUI integration tests
```

## Build, Test, and Development Commands

```bash
uv run skill-installer interactive    # Launch TUI
uv run pytest                          # Run tests
uv run pytest --cov                    # Run tests with coverage report
uv run ruff check .                    # Lint code
uv run ruff format .                   # Format code
```

## Coding Style & Naming Conventions

- **Python**: 3.10+, 100-character line length
- **Type hints**: Required on all functions
- **Docstrings**: Required for public functions
- **Linting**: Ruff (pycodestyle, pyflakes, isort, flake8-bugbear, pyupgrade)
- **Data models**: Pydantic for config, dataclasses for results

## Testing Guidelines

- **Framework**: pytest with pytest-cov
- **Coverage**: 100% block coverage for non-interactive modules
- **Naming**: `test_<module>.py` mirrors `<module>.py`
- **TUI tests**: TMUX-based scripts in `tests/scripts/`

Run tests:
```bash
uv run pytest --cov
```

## Commit & Pull Request Guidelines

Use conventional commits with scope:

```text
feat(scope): add new feature
fix(scope): correct bug
docs(scope): documentation update
test: add or update tests
chore(scope): maintenance task
```

**Examples**: `feat(tui): add location selection view`, `fix(platforms): correct path resolution`

**PR requirements**:

- Descriptive title matching commit convention
- Link related issues
- All tests passing with coverage requirements met
- Ruff checks passing

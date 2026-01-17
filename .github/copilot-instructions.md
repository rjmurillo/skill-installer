# Copilot Instructions

## Project Overview

Universal skill/agent installer for AI coding platforms. Installs agents and skills from Git repositories to Claude Code, VS Code, and Copilot CLI.

## Technology Stack

- Python 3.10+ with type hints
- uv for package management
- Typer for CLI
- Rich for TUI
- Pydantic for validation
- GitPython for git operations

## Code Patterns

### Type Hints

All functions must have type hints:

```python
def install_item(
    self,
    item: DiscoveredItem,
    source_name: str,
    target_platform: str,
) -> InstallResult:
```

### Error Handling

Use specific exceptions and dataclasses for results:

```python
@dataclass
class InstallResult:
    success: bool
    item_id: str
    error: str | None = None
```

### Pydantic Models

Use Pydantic for configuration:

```python
class Source(BaseModel):
    name: str
    url: str
    ref: str = "main"
```

## Key Modules

- `cli.py`: Typer commands
- `registry.py`: JSON persistence
- `discovery.py`: Find content in repos
- `transform.py`: Platform format conversion
- `platforms/`: Platform-specific handlers

## Testing

Run with: `uv run pytest --cov`

## Platform Paths

- Claude: `~/.claude/`
- VS Code: `~/.config/Code/User/prompts/` (Linux)
- Copilot: `~/.copilot/`

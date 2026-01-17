# Skill Installer

Universal skill/agent installer for AI coding platforms. Manages sources (Git repositories) and installs content to multiple targets with automatic format transformation.

## Features

- **Multi-platform support**: Claude Code, VS Code, VS Code Insiders, Copilot CLI
- **Source management**: Add, remove, and sync Git repositories
- **Automatic transformation**: Convert between platform formats
- **Interactive TUI**: Browse and install with Rich-powered interface
- **Persistent registry**: Track installed items and sources

## Installation

```bash
# Recommended: Use uvx for isolated tool execution
uvx skill-installer

# Or install globally with uv
uv tool install skill-installer

# Or traditional pip
pip install skill-installer
```

## Quick Start

```bash
# Add a source repository
skill-installer source add https://github.com/rjmurillo/ai-agents

# Browse and install interactively
skill-installer install

# Or install directly
skill-installer install ai-agents/analyst --platform claude,vscode

# Check status
skill-installer status

# Sync all installed items
skill-installer sync
```

## Commands

### Source Management

```bash
skill-installer source add <url> [--ref <branch>] [--name <alias>]
skill-installer source remove <name>
skill-installer source list
skill-installer source update [<name>]
```

### Installation

```bash
skill-installer install                           # Interactive TUI
skill-installer install <source>/<item>           # Direct install
skill-installer install <source>/<item> --platform claude,vscode
```

### Status and Sync

```bash
skill-installer status                            # Show all installed
skill-installer sync                              # Update all from sources
skill-installer uninstall <source>/<item>
```

### Configuration

```bash
skill-installer config set default-platforms claude,vscode
skill-installer config show
```

## Supported Platforms

| Platform | Config Location | Agent Format | Skills Support |
|----------|-----------------|--------------|----------------|
| Claude Code | `~/.claude/` | `*.md` | Yes |
| VS Code | `~/.config/Code/User/prompts/` | `*.agent.md` | No |
| VS Code Insiders | `~/.config/Code - Insiders/User/prompts/` | `*.agent.md` | No |
| Copilot CLI | `~/.copilot/` | `*.agent.md` | No |

## Registry Files

The installer maintains two registry files in `~/.skill-installer/`:

- `sources.json`: Configured source repositories
- `installed.json`: Installed items and their metadata

## Development

```bash
# Clone the repository
git clone https://github.com/rjmurillo/skill-installer
cd skill-installer

# Install with uv
uv sync --extra dev

# Run tests
uv run pytest

# Run the CLI
uv run skill-installer --help
```

## License

MIT

# Skill Installer

Universal skill/agent installer for AI coding platforms. Manages sources (Git repositories) and installs content to multiple AI coding platform targets. Currently Visual Studio Code, Visual Studio Code Insiders, Copilot CLI, Claude Code, Codex, and Factory Droid are supported.

## Features

- **Multi-platform support**: Claude Code, VS Code, VS Code Insiders, Copilot CLI, Codex
- **Two scopes**: Install globally (user) or per-project for team sharing
- **Source management**: Add, remove, and sync Git repositories
- **Automatic transformation**: Convert between platform formats
- **Two interfaces**: Interactive TUI for browsing, CLI for scripting
- **Persistent registry**: Track installed items and sources

## Installation

```bash
# Run directly from GitHub (no install required)
uvx --from git+https://github.com/rjmurillo/skill-installer skill-installer interactive

# Or install globally with uv
uv tool install git+https://github.com/rjmurillo/skill-installer

# Or clone and install locally
git clone https://github.com/rjmurillo/skill-installer
cd skill-installer
uv tool install .
```

## Usage

Skill Installer provides two interfaces:

- **Interactive TUI**: Visual browser for discovering and managing skills
- **CLI**: Command-line interface for scripting and automation

### Quick Start

```bash
# Add a source repository
skill-installer source add <url>
skill-installer source add https://github.com/github/awesome-copilot

# Launch interactive TUI
skill-installer interactive

# Or use CLI commands directly
skill-installer install <source>/<type>/<name> --platform <platform>
skill-installer install awesome-copilot/agent/code-tour --platform copilot
skill-installer status
```

## Interactive TUI

The TUI provides a visual interface with three tabs: Discover, Installed, and Marketplaces.

```bash
skill-installer interactive
```

### Tabs

| Tab | Description |
|-----|-------------|
| **Discover** | Browse available skills and agents from all sources |
| **Installed** | View and manage installed items |
| **Marketplaces** | Manage source repositories |

### Key Bindings

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Switch between tabs |
| `j` / `k` or `↓` / `↑` | Navigate lists |
| `Enter` | Select item for details |
| `Space` | Toggle checkbox (batch operations) |
| `a` | Add new source (opens modal) |
| `r` | Refresh data |
| `i` | Install selected/checked items |
| `q` | Quit |

### Adding Sources in TUI

Press `a` from any tab to open the Add Source modal. Supported formats:

| Format | Example |
|--------|---------|
| `owner/repo` | `github/awesome-copilot` |
| SSH URL | `git@github.com:github/awesome-copilot.git` |
| HTTPS URL | `https://github.com/github/awesome-copilot` |

## CLI Commands

The CLI provides scriptable commands for automation and integration.

### Source Management

```bash
# Add a source repository
skill-installer source add <url> [--ref <branch>] [--name <alias>]

# List all sources
skill-installer source list

# Update sources (fetch latest)
skill-installer source update [<name>]

# Remove a source
skill-installer source remove <name>
```

### Installation

```bash
# Interactive item selection
skill-installer install

# Install specific item to all configured platforms
skill-installer install <source>/<type>/<name>
skill-installer install awesome-copilot/agent/code-tour

# Install to specific platforms
skill-installer install <source>/<type>/<name> --platform <platforms>
skill-installer install awesome-copilot/agent/code-tour --platform claude,vscode

# Install to project scope (for team sharing via repository)
skill-installer install <source>/<type>/<name> --scope project
skill-installer install awesome-copilot/agent/code-tour --scope project
```

## Installation Scopes

Skill Installer supports two installation scopes:

| Scope | Location | Use Case |
|-------|----------|----------|
| **user** (default) | `~/.claude/`, `~/.config/Code/...` | Personal tools available everywhere |
| **project** | `.claude/`, `.vscode/` in repo | Team-shared tools, committed to repository |

### User Scope

Installs to your home directory. Available in all projects. Not shared with collaborators.

```bash
skill-installer install <source>/<type>/<name>
skill-installer install awesome-copilot/agent/code-tour
```

### Project Scope

Installs to the current repository. Commit these files to share with collaborators. Run from within your project directory.

```bash
cd /path/to/your/project
skill-installer install <source>/<type>/<name> --scope project
skill-installer install awesome-copilot/agent/code-tour --scope project
```

Project scope creates:
- `.claude/commands/` for Claude Code commands
- `.vscode/prompts/` for VS Code agents
- `.github/prompts/` for Copilot CLI

### Status and Sync

```bash
# Show all installed items
skill-installer status

# Update all installed items from sources
skill-installer sync

# Remove an installed item
skill-installer uninstall <source>/<item>
```

### Configuration

```bash
# Set default target platforms
skill-installer config set default-platforms claude,vscode

# Show current configuration
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

# Set up git hooks (Bandit pre-commit, CodeQL pre-push)
git config core.hooksPath .githooks

# Run tests
uv run pytest

# Run the CLI
uv run skill-installer --help
```

### Security Scanning

This project uses layered security scanning:

| Layer | Tool | Trigger | Severity |
|-------|------|---------|----------|
| Pre-commit | Bandit | Every commit | High only |
| Pre-push | CodeQL | Before push | All warnings/errors |
| CI | Bandit, CodeQL, DevSkim | PR/push to main | All |

To run scans manually:

```bash
# Bandit (fast Python SAST)
bandit -c pyproject.toml -r src/

# CodeQL (comprehensive security)
gh codeql database create .codeql-db --language=python
gh codeql database analyze .codeql-db codeql/python-queries:codeql-suites/python-security-extended.qls
```

## License

MIT

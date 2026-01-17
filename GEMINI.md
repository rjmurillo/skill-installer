# Skill Installer - Project Context

> **IMPORTANT**: Comprehensive developer guidelines, project structure, testing strategies, and coding standards are strictly defined in **[AGENTS.md](AGENTS.md)**. Consult that file before making any changes.

## Project Overview

**Skill Installer** is a universal skill and agent installer designed for AI coding platforms. It acts as a package manager for AI skills/agents, enabling users to:
*   Manage source Git repositories.
*   Discover and browse available skills/agents.
*   Install content to multiple targets (Claude Code, VS Code, VS Code Insiders, Copilot CLI).
*   Automatically transform content formats between platforms.

**Key Technologies:**
*   **Language:** Python 3.10+
*   **CLI Framework:** Typer
*   **TUI Framework:** Textual & Rich
*   **Data Validation:** Pydantic
*   **Git Operations:** GitPython
*   **Build System:** Hatchling
*   **Dependency Management:** uv

## Quick Setup Prerequisites

While `AGENTS.md` details the build commands, ensure the following are available in the environment:
*   **Python 3.10** or higher
*   **uv** (Universal Python Package Installer) - Used for all dependency management and task execution.
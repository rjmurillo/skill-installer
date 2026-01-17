# Claude Code Instructions

> **Note**: Repository guidelines (project structure, coding standards, testing, commits) are documented in [AGENTS.md](AGENTS.md).

This document uses RFC 2119 keywords: MUST, MUST NOT, SHOULD, SHOULD NOT, MAY.

## Project-Specific Context

Universal skill/agent installer for AI coding platforms (Claude Code, VS Code, Copilot CLI).

**Key design principles**:
- Platform-agnostic core with platform-specific adapters in `platforms/`
- 100% test coverage requirement for non-interactive modules
- TMUX-based integration testing for TUI components (see AGENTS.md)

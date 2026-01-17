# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-17

### Added

- Initial release
- CLI with install, uninstall, list, and sync commands
- TUI with tabbed interface (Discover, Installed, Sources)
- Multi-platform support (Claude Code, VS Code, Copilot CLI, Codex)
- Registry management with source synchronization
- Skill discovery from GitHub repositories
- Platform-specific skill transformation
- **TUI Uninstall**: Uninstall items directly from the TUI with confirmation dialog
- **Open Homepage**: Open item homepage URLs in system default browser
- **Project-Scope Installation**: Install skills to project-local directories
  - Supports Claude (.claude/skills/), VS Code (.vscode/copilot-skills/),
    Copilot CLI (.github/copilot-skills/), and Codex (.codex/skills/)
  - Automatic project root detection via .git directory
- **Source Auto-Update**: Toggle automatic updates per source repository
  - Stale source detection for sources not synced in 24 hours
  - Persisted auto-update preferences in registry
- **ConfirmationScreen**: Modal dialog for destructive actions (y/n/escape)
- **LocationSelectionScreen**: Refactored to Textual ModalScreen pattern

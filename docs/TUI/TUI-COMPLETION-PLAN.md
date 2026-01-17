# TUI Completion Plan

## Value Statement

As a skill-installer user, I want a fully functional TUI with all advertised features working so that I can manage skills and agents without falling back to CLI commands.

## Target Version

v0.2.0

## Current State Analysis

### Test Results

- **174 tests passing** (100% pass rate)
- **43% overall code coverage**
- **21% TUI coverage** (expected for UI code with limited automated testing)

### Feature Audit

| Feature | Status | Location |
|---------|--------|----------|
| Tab navigation | [COMPLETE] | `SkillInstallerApp` bindings |
| Keyboard navigation (j/k) | [COMPLETE] | `ItemListView`, `SourceListView` |
| Search filtering | [COMPLETE] | `DiscoverPane`, `InstalledPane` |
| Platform filter dropdown | [COMPLETE] | `DiscoverPane` |
| Item detail popup | [COMPLETE] | `ItemDetailView` |
| Location selection popup | [COMPLETE] | `LocationSelectionView` |
| Install via 'i' key | [COMPLETE] | `action_install()` |
| Source detail popup | [COMPLETE] | `SourceDetailView` |
| Update source | [COMPLETE] | `_update_source()` |
| Remove source | [COMPLETE] | `_remove_source()` |
| **Space toggle in location selection** | [BLOCKED] | Line 1023-1030 |
| **Auto-update for sources** | [PENDING] | Line 1812-1813 |
| **Project-scope installation** | [PENDING] | Line 1852-1853 |
| **Uninstall from TUI** | [PENDING] | Line 1856-1857 |
| **Open homepage in browser** | [PENDING] | Line 1868 |

---

## Prerequisites

- Python 3.10+
- Textual framework understanding
- Familiarity with `skill_installer.install.Installer` API

---

## Milestone 1: Fix Location Selection Space Toggle

**Goal**: Enable platform checkbox toggling via Space key in `LocationSelectionView`.

**Root Cause Analysis**:

The `on_key` handler at line 1023-1030 calls `event.stop()` unconditionally when visible. This prevents the event from reaching the Textual binding system that maps `space` to `action_toggle_selection`.

```python
def on_key(self, event) -> None:
    """Handle key events and prevent bubbling to background widgets."""
    if not self.has_class("visible"):
        return
    event.stop()  # <-- Stops ALL events, including space
```

**Solution**: Process bound keys before stopping propagation, or handle space explicitly.

### Tasks

1. [ ] **Modify `on_key` handler to process space before stopping**
   - Acceptance: Space key toggles checkbox state when `LocationSelectionView` is visible
   - Files: `src/skill_installer/tui.py` lines 1023-1032
   - Approach: Check if key is space and call `action_toggle_selection()` directly, or use Textual's `self.run_action()` method

2. [ ] **Add unit test for space toggle behavior**
   - Acceptance: Test verifies checkbox state changes on simulated space key
   - Files: `tests/test_tui.py`
   - Approach: Create `TestLocationSelectionView` class with async Textual testing

3. [ ] **Add TMUX integration test for location selection flow**
   - Acceptance: Script demonstrates end-to-end location selection with space toggle
   - Files: `tests/scripts/test_location_selection.sh`

**Estimated Effort**: 2 hours

---

## Milestone 2: Implement Uninstall from TUI

**Goal**: Enable uninstalling installed items directly from the TUI detail view.

**Current State**: The `uninstall` option exists in `ItemDetailView` but shows "Uninstall feature not yet implemented" notification.

**Dependencies**:
- `Installer.uninstall_item()` already exists and works (tested in CLI)
- `InstalledItem` has all required metadata

### Tasks

1. [ ] **Implement `_uninstall_item` method in `SkillInstallerApp`**
   - Acceptance: Method calls `self.installer.uninstall_item()` and handles result
   - Files: `src/skill_installer/tui.py`
   - Approach: Mirror `_install_item()` pattern with error handling and notifications

2. [ ] **Wire up uninstall option in `on_item_detail_option_selected`**
   - Acceptance: Selecting "Uninstall" from detail view removes the item
   - Files: `src/skill_installer/tui.py` line 1854-1857
   - Approach: Replace TODO with call to `_uninstall_item()`

3. [ ] **Update UI state after uninstall**
   - Acceptance: Item status indicator changes from filled to empty after uninstall
   - Files: `src/skill_installer/tui.py`
   - Approach: Call `_load_data()` to refresh all lists

4. [ ] **Add confirmation dialog before uninstall**
   - Acceptance: User must confirm before destructive action
   - Files: `src/skill_installer/tui.py`
   - Approach: Use Textual's modal or notification with confirmation

5. [ ] **Add unit tests for uninstall flow**
   - Acceptance: Tests verify uninstall calls installer and updates registry
   - Files: `tests/test_tui.py`

**Estimated Effort**: 3 hours

---

## Milestone 3: Implement Open Homepage in Browser

**Goal**: Open item homepage URL in system default browser.

**Current State**: Shows URL in notification but does not open browser.

### Tasks

1. [ ] **Add `webbrowser` import and helper method**
   - Acceptance: `_open_url(url: str)` opens URL in default browser
   - Files: `src/skill_installer/tui.py`
   - Approach: Use Python's `webbrowser.open()` standard library

2. [ ] **Wire up homepage option in `on_item_detail_option_selected`**
   - Acceptance: Selecting "Open homepage" opens URL in browser
   - Files: `src/skill_installer/tui.py` line 1858-1870
   - Approach: Replace notification with `_open_url()` call

3. [ ] **Add fallback notification for headless environments**
   - Acceptance: If browser open fails, show URL in notification
   - Files: `src/skill_installer/tui.py`
   - Approach: Wrap `webbrowser.open()` in try/except, notify on failure

4. [ ] **Add unit test for URL opening**
   - Acceptance: Test verifies `webbrowser.open` is called with correct URL
   - Files: `tests/test_tui.py`
   - Approach: Mock `webbrowser.open` and verify call arguments

**Estimated Effort**: 1 hour

---

## Milestone 4: Implement Project-Scope Installation

**Goal**: Install items to project-local directories instead of user-global paths.

**Current State**: Option exists but shows "Project scope installation not yet implemented".

**Design Considerations**:

1. **Project detection**: Identify project root via `.git` directory or explicit path
2. **Platform-specific project paths**:
   - Claude: `<project>/.claude/` 
   - VS Code: `<project>/.vscode/`
   - Copilot: `<project>/.github/copilot/`
3. **Scope tracking**: Store `scope: "project"` in registry with project path

### Tasks

1. [ ] **Add `get_project_root()` utility function**
   - Acceptance: Returns nearest parent directory containing `.git` or `None`
   - Files: `src/skill_installer/install.py` or new `src/skill_installer/project.py`
   - Approach: Walk up directory tree from cwd

2. [ ] **Extend platform classes with `get_project_install_path()` method**
   - Acceptance: Each platform returns project-local path for items
   - Files: `src/skill_installer/platforms/*.py`
   - Approach: Add method that takes project_root parameter

3. [ ] **Add `scope` parameter to `Installer.install_item()`**
   - Acceptance: Method accepts `scope="user"` or `scope="project"`
   - Files: `src/skill_installer/install.py`
   - Approach: Use appropriate path based on scope

4. [ ] **Create `ProjectSelectionView` widget for project path selection**
   - Acceptance: Modal shows detected project and allows confirmation
   - Files: `src/skill_installer/tui.py`
   - Approach: Similar to `LocationSelectionView` but for project root

5. [ ] **Wire up project-scope option in `on_item_detail_option_selected`**
   - Acceptance: Selecting "Install for all collaborators" shows project selection
   - Files: `src/skill_installer/tui.py` line 1850-1853
   - Approach: Show `ProjectSelectionView` then install with scope="project"

6. [ ] **Add unit tests for project-scope installation**
   - Acceptance: Tests verify project path detection and installation
   - Files: `tests/test_install.py`, `tests/test_tui.py`

7. [ ] **Add TMUX integration test for project-scope flow**
   - Acceptance: Script demonstrates project-scope installation
   - Files: `tests/scripts/test_project_install.sh`

**Estimated Effort**: 6 hours

---

## Milestone 5: Implement Source Auto-Update

**Goal**: Enable automatic periodic updates for source repositories.

**Current State**: Option exists in source detail view but shows "Auto-update feature not yet implemented".

**Design Considerations**:

1. **Storage**: Add `auto_update: bool` field to `Source` model in registry
2. **Trigger**: Check on TUI startup or add background worker
3. **Frequency**: Default to daily, configurable via settings

### Tasks

1. [ ] **Add `auto_update` field to `Source` model**
   - Acceptance: Field defaults to `False`, persists in `sources.json`
   - Files: `src/skill_installer/registry.py`
   - Approach: Add field to `Source` Pydantic model

2. [ ] **Add `toggle_source_auto_update()` method to `RegistryManager`**
   - Acceptance: Method toggles auto_update flag for a source
   - Files: `src/skill_installer/registry.py`
   - Approach: Load, modify, save registry pattern

3. [ ] **Add auto-update check on TUI mount**
   - Acceptance: Sources with `auto_update=True` are updated if stale (>24h)
   - Files: `src/skill_installer/tui.py`
   - Approach: Add to `on_mount()` or create background worker

4. [ ] **Wire up auto-update toggle in `on_detail_option_selected`**
   - Acceptance: Toggling option updates registry and shows confirmation
   - Files: `src/skill_installer/tui.py` line 1810-1813
   - Approach: Call `toggle_source_auto_update()` and update detail view

5. [ ] **Update `SourceDetailView` to show auto-update status**
   - Acceptance: Option label shows "Enable auto-update" or "Disable auto-update"
   - Files: `src/skill_installer/tui.py`
   - Approach: Check source `auto_update` field when building options

6. [ ] **Add unit tests for auto-update functionality**
   - Acceptance: Tests verify toggle, persistence, and staleness check
   - Files: `tests/test_registry.py`, `tests/test_tui.py`

**Estimated Effort**: 4 hours

---

## Milestone 6: Version Management

**Goal**: Release v0.2.0 with all TUI features complete.

### Tasks

1. [ ] **Update version in `pyproject.toml`**
   - Acceptance: Version bumped to 0.2.0
   - Files: `pyproject.toml`

2. [ ] **Update CHANGELOG.md with new features**
   - Acceptance: All implemented features documented under v0.2.0
   - Files: `CHANGELOG.md`

3. [ ] **Run full test suite with coverage**
   - Acceptance: All tests pass, coverage meets targets
   - Command: `uv run pytest --cov`

4. [ ] **Run linting**
   - Acceptance: No linting errors
   - Command: `uv run ruff check .`

5. [ ] **Tag release**
   - Acceptance: Git tag `v0.2.0` created
   - Command: `git tag v0.2.0`

**Estimated Effort**: 1 hour

---

## Work Breakdown Summary

| Milestone | Tasks | Effort | Dependencies |
|-----------|-------|--------|--------------|
| M1: Fix Space Toggle | 3 | 2h | None |
| M2: Uninstall from TUI | 5 | 3h | None |
| M3: Open Homepage | 4 | 1h | None |
| M4: Project-Scope Install | 7 | 6h | M1 (location selection) |
| M5: Source Auto-Update | 6 | 4h | None |
| M6: Version Management | 5 | 1h | M1-M5 |

**Total Estimated Effort**: 17 hours

---

## Assumptions

1. Textual's event system allows manual action invocation via `run_action()`
2. `webbrowser.open()` works in terminal environments where TUI runs
3. Project root detection via `.git` is sufficient for all use cases
4. Auto-update frequency of 24 hours is acceptable default

## Open Questions

1. Should project-scope installation prompt for project path if not in a git repo?
2. Should auto-update run as a background worker or only on startup?
3. Should uninstall require confirmation for all items or only user-scope?

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Textual event handling changes between versions | High | Low | Pin Textual version, add integration tests |
| webbrowser fails in headless/SSH environments | Medium | Medium | Add fallback notification with URL |
| Project root detection false positives | Medium | Low | Allow manual path override in UI |
| Auto-update causes startup latency | Medium | Medium | Run updates asynchronously, add timeout |

---

## Implementation Order

Recommended sequence for incremental delivery:

1. **M1: Fix Space Toggle** - Unblocks location selection, critical bug
2. **M2: Uninstall from TUI** - High user value, straightforward implementation
3. **M3: Open Homepage** - Quick win, simple implementation
4. **M5: Source Auto-Update** - Independent feature, can parallelize
5. **M4: Project-Scope Install** - Most complex, benefits from other fixes
6. **M6: Version Management** - Final gate before release

---

## Test Strategy

### Unit Tests

Each milestone includes unit test tasks. Test files:

- `tests/test_tui.py` - Widget behavior tests
- `tests/test_install.py` - Installation logic tests
- `tests/test_registry.py` - Registry persistence tests

### Integration Tests

TMUX-based scripts for end-to-end validation:

- `tests/scripts/test_location_selection.sh` - M1 validation
- `tests/scripts/test_project_install.sh` - M4 validation

### Manual Testing Checklist

Before release, verify:

- [ ] Space toggles checkboxes in location selection
- [ ] Uninstall removes files and updates registry
- [ ] Homepage opens in browser (or shows URL on failure)
- [ ] Project-scope installs to correct directory
- [ ] Auto-update toggles and persists correctly
- [ ] All keyboard shortcuts work as documented

---

## Code Reference

### Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `tui.py` | TUI components | 1023-1030 (on_key), 1810-1873 (option handlers) |
| `install.py` | Installation logic | 137-180 (uninstall_item) |
| `registry.py` | Data persistence | 75-88 (Source model) |
| `platforms/*.py` | Platform paths | get_install_path methods |

### Existing Patterns to Follow

**Install pattern** (`_install_item` at line 1718-1745):
```python
def _install_item(self, item: DisplayItem, platforms: list[str] | None = None) -> None:
    if not self.installer:
        self.notify("Installer not configured", severity="error")
        return
    # ... installation logic with notifications
    self._load_data()  # Refresh UI
```

**Source operation pattern** (`_update_source` at line 1906-1922):
```python
def _update_source(self, source: DisplaySource) -> None:
    self._update_status(f"Updating {source.display_name}...")
    try:
        # ... operation logic
        self.notify(f"Updated {source.display_name}")
        self._load_data()
    except Exception as e:
        self.notify(f"Failed to update: {e}", severity="error")
```

---

## Handoff

This plan is ready for **critic** review. After approval, hand off to **implementer** for M1 (critical bug fix) first.

# DataTable Migration Plan

**Status:** Production-Ready Implementation Plan (Enriched v2.0)  
**Last Updated:** 2026-01-16  
**Research Validation:** ✅ COMPLETE - Analyst verified DataTable capabilities  
**Security Review:** ⚠️ CONDITIONAL APPROVAL - 2 critical fixes required  
**Estimated Effort:** 27 hours (3.4 working days) - UP FROM 16 hours

## 🎯 Enrichment Summary

This plan has been enriched with comprehensive research, security review, and implementation corrections by specialized agents:

**What Changed:**
- ✅ Added Phase 6.5: Unit Testing (4 hours, 20+ tests)
- ✅ Corrected DataTable API usage (`add_columns()`, `row_key` vs `cursor_row`)
- ✅ Added security requirements (terminal escape sanitization, Unicode fallback)
- ✅ Added state preservation logic with `_sync_checked_state_with_display()`
- ✅ Added debouncing (150ms) with race condition protection
- ✅ Enhanced all acceptance criteria to be measurable
- ✅ Updated estimates from 16 to 27 hours (69% increase justified)

**Agent Contributions:**
- 📊 **Analyst**: Validated DataTable performance (6,667 rows/sec, O(n) removal caveat)
- 🔍 **Critic**: Identified 5 critical gaps (state preservation, API errors, missing tests)
- 📋 **Planner**: Corrected implementation steps, added concrete code examples
- 🔒 **Security**: Found 2 CRITICAL issues (escape injection, Unicode fallback)

**Critical Blockers Before Deployment:**
- 🚨 CRITICAL-001: Terminal escape sequence injection (4 hours)
- 🚨 CRITICAL-002: Unicode fallback for non-UTF8 terminals (3 hours)

**Implementation Notes:**
- Security sanitization implemented in `src/skill_installer/tui/_utils.py`
- Tests in `tests/test_tui.py` (TestSanitizeTerminalText, TestGetTerminalIndicators)

---


## Problem Statement

The TUI takes 16-21 seconds to load due to excessive widget creation when mounting `ItemRow` widgets.

### Root Cause Analysis

Profiling revealed:

| Phase | Time | Notes |
|-------|------|-------|
| Imports + Context | ~0.6s | Acceptable |
| `load_all_data()` | ~1.0s | 501 items discovered |
| `ItemListView.set_items()` | ~3.0s | Creates 501 ItemRow widgets |
| Textual layout/CSS/render | ~12-17s | **Bottleneck** |
| **Total** | **~16-21s** | Unacceptable |

Each `ItemRow` creates 5 nested widgets:
```
ItemRow
└── Horizontal
    ├── Static (indicator)
    └── Vertical
        ├── Static (header)
        └── Static (description)
```

With 501 items → 2,505+ widgets → Textual's layout engine chokes.

### Solution

Replace custom `ItemListView` + `ItemRow` widgets with Textual's built-in `DataTable`, which uses **virtualization** (rendering only visible rows instead of all 501 items) to dramatically reduce widget count.

## Terminology

| Term | Definition |
|------|------------|
| **Virtualization** | Rendering technique that only creates UI elements for visible items |
| **DataTable** | Built-in Textual widget that displays tabular data with virtual scrolling |
| **DisplayItem** | Data class representing a skill with metadata (see Data Model below) |
| **Pane** | Top-level tab view in the TUI (Discover, Installed, Marketplaces) |
| **Source/Marketplace** | External skill repository (e.g., "awesome-prompts") |

### Data Model

```python
@dataclass
class DisplayItem:
    name: str                        # Skill name
    item_type: str                   # "agent", "skill", "prompt"
    description: str                 # Short description
    source_name: str                 # Marketplace name
    platforms: list[str]             # Supported platforms
    installed_platforms: list[str]   # Where currently installed
    raw_data: Any                    # Original DiscoveredItem
    source_url: str                  # Git URL of marketplace
    relative_path: str               # Path within marketplace repo

    @property
    def unique_id(self) -> str:
        """Unique identifier: source/type/name"""
        return f"{self.source_name}/{self.item_type}/{self.name}"
```

### Existing API Reference

Methods to preserve:
- `set_items(items: list[DisplayItem]) -> None`
- `get_checked_items() -> list[DisplayItem]`
- `clear_checked() -> None`

Messages emitted:
- `ItemSelected(item: DisplayItem)` - on Enter key
- `ItemToggled(item: DisplayItem, checked: bool)` - on Space key

## Goals

1. **Reduce startup time from ~16s to <3s**
2. Maintain all existing functionality:
   - Keyboard navigation (j/k, up/down, Enter, Space)
   - Visual indicators (installed/checked status)
   - Selection highlighting
   - Scrolling
3. Preserve existing API for `set_items()`, `get_checked_items()`, etc.
4. No breaking changes to pane or app layer

## Non-Goals

- Changing data loading logic
- Modifying the discovery/registry layer
- Redesigning the overall TUI architecture

## Design

### Repository Structure

```
skill-installer/
├── src/skill_installer/tui/
│   ├── app.py              # Main TUI application
│   ├── panes/
│   │   ├── discover.py     # Discover pane (all available skills)
│   │   └── installed.py    # Installed pane (installed skills)
│   ├── widgets/
│   │   └── item_list.py    # ItemListView/ItemRow (TO BE REPLACED)
│   └── styles.py           # CSS styling
└── tests/scripts/
    └── profile_tui_*.py    # Performance profiling tools
```

### Current Architecture

```
DiscoverPane
├── SearchInput
├── Select (platform filter)
├── ItemListView (VerticalScroll)
│   ├── ItemRow (Widget) [501 instances]
│   │   └── Horizontal → Static + Vertical → Static × 2
│   └── ...
└── ScrollIndicator
```

### Proposed Architecture

```
DiscoverPane
├── SearchInput
├── Select (platform filter)
├── ItemDataTable (DataTable)  ← Virtualized, renders ~20 visible rows
└── ScrollIndicator
```

### Component Changes

#### 1. New `ItemDataTable` Widget

Replace `ItemListView` with a wrapper around Textual's `DataTable`:

```python
class ItemDataTable(DataTable):
    """Virtualized item list using DataTable."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.items: list[DisplayItem] = []
        self._checked: set[str] = set()
        self.cursor_type = "row"
        self.zebra_stripes = True
    
    def set_items(self, items: list[DisplayItem]) -> None:
        """Replace all items (same API as ItemListView)."""
        self.clear()
        self.items = items
        for item in items:
            self._add_item_row(item)
    
    def _add_item_row(self, item: DisplayItem) -> None:
        """Add a single item as a table row."""
        indicator = self._get_indicator(item)
        name_source = f"{item.name} • {item.source_name}"
        status = f"[{', '.join(item.installed_platforms)}]" if item.installed_platforms else ""
        desc = (item.description or "No description")[:60]
        
        self.add_row(indicator, name_source, status, desc, key=item.unique_id)
    
    def _get_indicator(self, item: DisplayItem) -> str:
        if item.unique_id in self._checked:
            return "◉"  # checked
        elif item.installed_platforms:
            return "●"  # installed
        return "○"  # not installed
```

#### 2. Column Layout

| Column | Width | Content |
|--------|-------|---------|
| Indicator | 3 | ○/●/◉ (see legend) |
| Name • Source | flex (auto-expands) | `skill-name • marketplace` |
| Status | 20 | `[claude, copilot]` |
| Description | flex (truncated at 60 chars with ...) | Skill description |

**Indicator Symbols:**
- `○` Not installed
- `●` Installed
- `◉` Checked/selected for batch operation

#### 3. Event Mapping

| Old Event | New Implementation |
|-----------|-------------------|
| `ItemListView.ItemSelected` | `DataTable.RowSelected` → emit `ItemSelected` |
| `ItemListView.ItemToggled` | Override `action_toggle` → update row, emit `ItemToggled` |
| `action_cursor_up/down` | Built-in (DataTable handles) |
| `action_select` (Enter) | Built-in `RowSelected` message |

**Event Translation Example:**
```python
@on(DataTable.RowSelected)
def on_row_selected(self, event: DataTable.RowSelected) -> None:
    """Translate DataTable event to ItemSelected."""
    row_key = event.row_key
    if row_key is None:
        return
    item = next((i for i in self.items if i.unique_id == str(row_key.value)), None)
    if item:
        self.post_message(self.ItemSelected(item))
```
> **Note:** Uses `row_key` not `cursor_row`. See Correction 3 below for details.

#### 4. Files to Modify

| File | Change |
|------|--------|
| `src/skill_installer/tui/widgets/item_list.py` | Replace `ItemListView` with `ItemDataTable`, delete `ItemRow` |
| `src/skill_installer/tui/panes/discover.py` | Update imports, swap widget class |
| `src/skill_installer/tui/panes/installed.py` | Update imports, swap widget class |
| `src/skill_installer/tui/app.py` | Update event handlers if needed |
| `src/skill_installer/tui/styles.py` | Add DataTable styling |


## 🔒 Security Requirements [CRITICAL]

**Status:** 2 CRITICAL issues MUST be fixed before deployment (7 hours)

### CRITICAL-001: Terminal Escape Sequence Injection (CWE-150)

**Risk Level:** Critical  
**Impact:** Malicious skill metadata can inject ANSI escape codes to manipulate terminal UI, spoof system messages, or crash terminals  
**Effort:** 4 hours

**Attack Vector:**
```python
# Malicious skill name in marketplace
skill_name = "legitimate-skill\x1b[2J\x1b[H[SYSTEM] Installing malware..."
# Clears screen, positions cursor, displays fake system message
```

**Required Fix:**
```python
# In src/skill_installer/tui/_utils.py
import re

def sanitize_terminal_text(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for safe terminal rendering.
    
    Removes:
    - ANSI escape sequences (\x1b[...)
    - Control characters (except \n, \t)
    - Unicode directional overrides (RLO, LRO)
    - Non-printable characters
    """
    # Remove ANSI escape sequences
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    
    # Remove control characters except newline/tab
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
    
    # Remove Unicode directional overrides
    for override in ['\u202E', '\u202D', '\u200F', '\u200E']:
        text = text.replace(override, '')
    
    # Truncate to prevent DoS
    if len(text) > max_length:
        text = text[:max_length - 3] + "..."
    
    return text
```

**Integration Points:**
- Apply to `item.name`, `item.source_name`, `item.description` in `_add_item_row()`
- Add unit tests in `test_item_datatable_security.py`

---

### CRITICAL-002: Unicode Fallback for Non-UTF8 Terminals (CWE-20)

**Risk Level:** Critical  
**Impact:** Non-UTF8 terminals display � or boxes for ○●◉ indicators, users cannot distinguish checked/installed states  
**Effort:** 3 hours

**Failure Scenario:**
```
Windows Command Prompt (codepage 437):
  Expected: ● Installed
  Actual:   ? Installed  (corrupted display)
```

**Required Fix:**
```python
# In src/skill_installer/tui/_utils.py
import sys
import locale

def get_terminal_indicators() -> dict[str, str]:
    """
    Detect terminal UTF-8 support and return appropriate indicators.
    
    Returns:
        Dict with keys: "checked", "installed", "unchecked"
    """
    encoding = sys.stdout.encoding or locale.getpreferredencoding()
    supports_utf8 = encoding.lower() in ('utf-8', 'utf8')
    
    if supports_utf8:
        return {
            "checked": "◉",
            "installed": "●",
            "unchecked": "○"
        }
    else:
        return {
            "checked": "[x]",
            "installed": "[*]",
            "unchecked": "[ ]"
        }
```

**Integration Points:**
- Call in `ItemDataTable.__init__()` to set `self._indicators`
- Use `self._indicators["checked"]` instead of hardcoded "◉"
- Test in ASCII terminal environment

---

## ⚡ Implementation Corrections [CRITICAL]

The original plan contained **5 critical implementation errors** that would cause failures. These have been corrected below.

### Correction 1: Missing `add_columns()` Initialization

**Original (BROKEN):**
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    # Missing column setup - add_row() will fail!
```

**Corrected:**
```python
def on_mount(self) -> None:
    """Initialize table columns on mount."""
    # CRITICAL: Must call add_columns before adding rows
    self.add_columns(
        "",              # Indicator column
        "Name • Source",
        "Status",
        "Description"
    )
```

---

### Correction 2: Checked State Preservation Logic

**Original (LOSES STATE):**
```python
def set_items(self, items: list[DisplayItem]) -> None:
    self.clear()  # WRONG: Loses checked state!
    self.items = items
```

**Corrected:**
```python
def set_items(self, items: list[DisplayItem]) -> None:
    """Replace items while preserving checked state."""
    # CRITICAL: Copy checked state before clearing
    checked_ids = self._checked.copy()
    
    self.clear()
    self.items = items
    # ... bulk add rows ...
    
    # CRITICAL: Restore checked state
    self._checked = checked_ids
    self._sync_checked_state_with_display()
```

**New Method Required:**
```python
def _sync_checked_state_with_display(self) -> None:
    """Synchronize checked indicators with _checked set."""
    for idx, item in enumerate(self.items):
        if item.unique_id in self._checked:
            coord = Coordinate(idx, 0)
            if coord.row < self.row_count:
                self.update_cell_at(coord, self._indicators["checked"])
```

---

### Correction 3: Event Handler API Error

**Original (CRASHES):**
```python
def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    # WRONG: cursor_row doesn't exist!
    if event.cursor_row < len(self.items):
        item = self.items[event.cursor_row]
```

**Corrected:**
```python
def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
    # CORRECT: Use row_key, not cursor_row
    row_key = event.row_key
    
    item = next((item for item in self.items if item.unique_id == row_key), None)
    
    if item is not None:
        self.post_message(self.ItemSelected(item))
    else:
        self.log.warning(f"Row selected with unknown key: {row_key}")
```

---

### Correction 4: Race Condition Protection

**Original (VULNERABLE):**
```python
# No protection against concurrent filter + toggle operations
def action_toggle(self) -> None:
    # WRONG: Can be called while _execute_filter() is running
    item = self.items[row_idx]  # May reference stale data!
```

**Corrected:**
```python
class ItemDataTable(DataTable):
    def __init__(self):
        super().__init__()
        self._is_filtering = False  # Mutex flag
    
    def action_toggle(self) -> None:
        # CRITICAL: Check filtering flag
        if self._is_filtering:
            self.log.warning("Cannot toggle during filter operation")
            return
        
        # Safe to proceed...
    
    def _execute_filter(self) -> None:
        self._is_filtering = True
        try:
            # Perform filter + set_items
            pass
        finally:
            self._is_filtering = False
```

---

### Correction 5: Filter Performance (Use Bulk Operations)

**Original (SLOW):**
```python
# WRONG: Individual add_row() calls trigger O(n) refresh each time
for item in filtered_items:
    self.add_row(...)  # Slow! Analyst measured 71 rows/sec removal
```

**Corrected:**
```python
# CORRECT: Use bulk add_rows() for 6,667 rows/sec performance
self.clear()  # Fast O(1)
rows = [(indicator, name, status, desc) for item in filtered_items]
self.add_rows(rows)  # Single O(n) operation
```

---

## Implementation Steps

### Phase 0: Validation Spike (Est: 2 hours) ⚠️ GATE

**Goal:** Prove DataTable meets requirements BEFORE full implementation.

1. [ ] Create `tests/scripts/datatable_spike.py` with 50-item prototype
2. [ ] Verify Rich Text rendering in cells (colored indicators)
3. [ ] Test row selection/cursor events work
4. [ ] Test dynamic row add/remove performance
5. [ ] Measure render time vs. ItemListView baseline
6. [ ] Test keyboard navigation (j/k/up/down/Enter/Space)
7. [ ] Test multi-line cell content (description with path prefix)

**Decision Gate:** If spike shows >5s render time OR missing features, **STOP** and implement pagination instead.

**Acceptance Criteria:**
- 500 rows render in <1s
- Row selection emits events
- Cell content can include Rich markup (colors)
- j/k bindings work or can be overridden

### Phase 1: Core ItemDataTable (Est: 3 hours)

1. [ ] Create `ItemDataTable` class in `widgets/item_list.py`
   - Acceptance: Class compiles, can be instantiated, inherits DataTable
2. [ ] Implement `set_items()` with same signature as ItemListView
   - Acceptance: 501 items load without error
3. [ ] Implement `get_checked_items()` and `clear_checked()`
   - Acceptance: Returns correct items after toggle operations
4. [ ] Add column configuration (Indicator, Name, Status, Description)
   - Acceptance: Columns display with correct widths
5. [ ] Add indicator rendering logic (○/●/◉)
   - Acceptance: Installed items show ●, checked show ◉

### Phase 2: State Management (Est: 2 hours)

1. [ ] Preserve `_checked` set across `set_items()` calls
   - Acceptance: Check items, call set_items, verify checks preserved
2. [ ] Handle scroll position on filter changes
   - Acceptance: Cursor stays visible when list shrinks
3. [ ] Test state preservation with platform filter changes
   - Acceptance: Check 3 items, change filter, verify checked state

### Phase 3: Event Integration (Est: 2 hours)

1. [ ] Emit `ItemSelected` message on row selection (Enter)
   - Acceptance: `app.py` handler receives correct item
2. [ ] Implement toggle action for Space key
   - Acceptance: Space toggles indicator ○↔◉
3. [ ] Emit `ItemToggled` message with checked state
   - Acceptance: Status bar updates with checked count
4. [ ] Update row indicator when toggled (refresh cell)
   - Acceptance: Visual indicator changes immediately

### Phase 4: Pane Integration (Est: 2 hours)

1. [ ] Update `DiscoverPane` to use `ItemDataTable`
   - Acceptance: Discover tab renders item list
2. [ ] Update `InstalledPane` to use `ItemDataTable`
   - Acceptance: Installed tab renders item list
3. [ ] Verify event handlers in `app.py` still work
   - Acceptance: Enter opens detail view, Space toggles
4. [ ] Remove old `ItemRow` class from codebase
   - Acceptance: No references to ItemRow remain

### Phase 5: Filter Optimization (Est: 1.5 hours)

**Critical:** Search filtering calls `set_items()` on every keystroke.

1. [ ] Profile filter performance with 501 items
   - Acceptance: Filter operation <100ms
2. [ ] Consider row show/hide instead of clear/rebuild
   - Acceptance: No visible stutter during typing
3. [ ] Add debouncing to search input if needed (150ms)
   - Acceptance: Smooth typing experience

### Phase 6: Styling (Est: 1 hour)

1. [ ] Add DataTable CSS to `styles.py`
   - Acceptance: Table has borders, colors match theme
2. [ ] Match existing color scheme ($accent, $primary, etc.)
   - Acceptance: Selection highlight visible
3. [ ] Ensure focus/selection states are visible
   - Acceptance: Current row clearly highlighted
4. [ ] Test in various terminal sizes (80x24, 120x40)
   - Acceptance: Layout adapts without breaking


### Phase 6.5: Unit Testing ⚡ NEW PHASE (Est: 4 hours)

**CRITICAL:** Original plan only included manual testing. Unit tests are required for robust state management validation and regression prevention.

**Test Files to Create:**
1. `tests/unit/tui/widgets/test_item_datatable_state.py` - State management (1.5h)
2. `tests/unit/tui/widgets/test_item_datatable_events.py` - Event handling (1h)
3. `tests/unit/tui/widgets/test_item_datatable_filtering.py` - Filtering & race conditions (1h)
4. `tests/unit/tui/widgets/test_item_datatable_security.py` - Security sanitization (0.5h)

**Key Tests:**
- [ ] `test_checked_state_preserved_after_filter()` - Check items, filter, verify state
- [ ] `test_row_selected_emits_item_selected_message()` - Event emission with correct item
- [ ] `test_toggle_blocked_during_filtering()` - Race condition prevention
- [ ] `test_sanitize_removes_ansi_escapes()` - CRITICAL-001 validation
- [ ] `test_ascii_fallback_in_non_utf8_terminal()` - CRITICAL-002 validation
- [ ] `test_debounced_filter_executes_once()` - Debouncing validation
- [ ] `test_set_items_with_empty_list()` - Edge case handling

**Acceptance Criteria:**
- [ ] 20+ unit tests implemented across 4 test files
- [ ] All tests pass consistently (0 failures, 0 errors, 0 flakiness)
- [ ] Test execution time <10 seconds
- [ ] Coverage >85% line coverage for `ItemDataTable`
- [ ] Coverage >90% branch coverage for state management methods
- [ ] CI pipeline updated to run tests on every commit

### Phase 7: Testing & Validation (Est: 3 hours)

1. [ ] Run `profile_tui_startup.py` and record baseline
2. [ ] Run `profile_tui_interactive.sh` to measure startup time
   - Acceptance: Startup time <3s
3. [ ] Manual test all keyboard navigation
   - Acceptance: j/k/up/down/Enter/Space/Tab all work
4. [ ] Identify and update affected test scripts:
   - `tests/scripts/test_discover_tab.sh`
   - `tests/scripts/test_detail_view.sh`
   - `tests/scripts/test_navigation.sh`
5. [ ] Run updated test scripts
   - Acceptance: All tests pass

**Total Estimated Time: ~27 hours (3.4 working days)**

**Estimate Breakdown:**
- Phase 0: 2h (Validation Spike)
- Phase 1: 4h (Core ItemDataTable) - UP FROM 3h
- Phase 2: 3h (State Management) - UP FROM 2h
- Phase 3: 3h (Event Integration) - UP FROM 2h
- Phase 4: 2h (Pane Integration)
- Phase 5: 2.5h (Filter Optimization) - UP FROM 1.5h
- Phase 6: 1h (Styling)
- **Phase 6.5: 4h (Unit Testing) - NEW PHASE**
- Phase 7: 3.5h (Testing **Total Estimated Time: ~16 hours (2 working days)** Validation) - UP FROM 3h
- Buffer: 2h (10% contingency)

## Rollback Plan

If DataTable doesn't work as expected:

1. Keep old `ItemRow`/`ItemListView` in a separate file
2. Add feature flag to switch between implementations
3. Fallback: Implement pagination (show 50 items at a time)

### Rollback Triggers

Execute rollback if ANY condition is true:

1. Startup time remains >5s after optimization
2. Search filtering takes >200ms per keystroke
3. DataTable cannot render colored indicators
4. Keyboard navigation conflicts cannot be resolved
5. Multi-line cell content is unsupported and info density is lost

## Success Criteria

| Metric | Before | Target | Validation |
|--------|--------|--------|------------|
| Startup time | 16-21s | <3s | Run `profile_tui_interactive.sh` |
| Time to first paint | 10s+ | <2s | Measure from app launch |
| Widget count | 2500+ | ~50 | Check with Textual devtools |
| Search filter response | Unknown | <100ms | Profile filter operation |
| Keyboard navigation | Works | Works | Test j/k/up/down/Enter/Space |
| Toggle/select | Works | Works | Test Space toggles, Enter selects |
| Checked state preservation | N/A | Works | Check items, filter, verify preserved |

### Functional Acceptance Criteria

- [ ] All 501 items load in under 3 seconds
- [ ] Pressing `j` or Down arrow moves cursor to next row
- [ ] Pressing `k` or Up arrow moves cursor to previous row
- [ ] Pressing Space toggles indicator from ○ to ◉
- [ ] Pressing Enter selects item and opens detail view
- [ ] Checked items persist when filtering/searching
- [ ] Visual focus indicator clearly shows current row
- [ ] Status bar shows count of checked items

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| DataTable styling doesn't match | Low | Medium | Custom CSS, Rich markup in cells |
| DataTable doesn't support custom indicators | Medium | Low | Use Text/Rich objects in cells |
| Event handling differences | Medium | Medium | Wrapper class normalizes API |
| Tests need significant updates | Low | High | Update assertions, same test structure |
| Keyboard navigation conflicts | Medium | Medium | Override DataTable bindings if needed |
| Performance regression on filtering | High | Medium | Profile filter, add debouncing |
| Terminal resize breaks layout | Medium | Low | Test multiple sizes, responsive columns |
| Loss of visual fidelity (2-line display) | Medium | Medium | Test Rich multi-line cells or combine info |

## API Compatibility Matrix

| Method/Attribute | Signature Change | Behavior Change | Breaking |
|-----------------|------------------|-----------------|----------|
| `set_items(items)` | No | Yes (preserves checked state now) | No |
| `get_checked_items()` | No | No | No |
| `clear_checked()` | No | No | No |
| `selected_index` | **Removed** | Use DataTable cursor | Yes (internal) |
| `_rows` | **Removed** | Use DataTable internal storage | Yes (internal) |
| `ItemSelected` message | No | No | No |
| `ItemToggled` message | No | No | No |

## References

- [Textual DataTable docs](https://textual.textualize.io/widgets/data_table/)
- [DataTable source](https://github.com/Textualize/textual/blob/main/src/textual/widgets/_data_table.py)
- Profiling scripts: `tests/scripts/profile_tui_*.py`
- Current implementation: `src/skill_installer/tui/widgets/item_list.py`

---

## 📊 Change Summary (v2.0)

| Section | Status | Key Changes |
|---------|--------|-------------|
| **Header** | ✅ Added | Enrichment summary with agent contributions |
| **Security** | ✅ Added | 2 CRITICAL requirements (escape injection, Unicode fallback) |
| **Implementation Corrections** | ✅ Added | 5 critical API/logic fixes |
| **Phase 0** | ✅ Enhanced | Added security tests to validation spike |
| **Phase 1** | ✅ Enhanced | +1h for security implementations, add_columns() |
| **Phase 2** | ✅ Enhanced | +1h for robust state sync logic |
| **Phase 3** | ✅ Enhanced | +1h for correct event API usage (row_key) |
| **Phase 5** | ✅ Enhanced | +1h for debouncing + race condition protection |
| **Phase 6.5** | ⚡ NEW | +4h for unit testing (20+ tests, 4 files) |
| **Phase 7** | ✅ Enhanced | +0.5h for extended validation criteria |
| **Estimates** | ✅ Updated | 16h → 27h (69% increase, justified) |
| **Acceptance Criteria** | ✅ Enhanced | All criteria now measurable with specific targets |
| **Risks** | ✅ Enhanced | Added concrete mitigations for 5 new risks |

**Net Impact:** Implementation-ready plan with security hardening, robust state management, and comprehensive testing strategy.

---

## 📚 Implementation Reference

**Security Implementation:**
- `src/skill_installer/tui/_utils.py`: Contains `sanitize_terminal_text()` and `get_terminal_indicators()`
- CRITICAL-001 (terminal escape injection): Resolved in `sanitize_terminal_text()`
- CRITICAL-002 (Unicode fallback): Resolved in `get_terminal_indicators()`

**Test Coverage:**
- `tests/test_tui.py::TestSanitizeTerminalText`: 14 tests covering attack vectors
- `tests/test_tui.py::TestGetTerminalIndicators`: 6 tests covering encoding detection

**Widget Implementation:**
- `src/skill_installer/tui/widgets/item_list.py`: `ItemDataTable` class with DataTable virtualization

---

## ✅ Implementation Status

**Completed:**
- [x] DataTable migration in `item_list.py` (ItemDataTable class)
- [x] Security sanitization in `_utils.py` (CRITICAL-001 resolved)
- [x] Unicode fallback in `_utils.py` (CRITICAL-002 resolved)
- [x] State preservation with `_sync_checked_state_with_display()`
- [x] Race condition protection with `_is_filtering` flag
- [x] Unit tests for security functions (20+ tests)

**Validation Checklist:**
- [x] Follow corrected code patterns (add_columns, row_key, state preservation)
- [x] Security sanitization applied to all external data
- [x] Unit tests in place before integration testing
- [x] Debouncing with race condition protection implemented

---

## 🎓 Lessons Learned (For Future Migrations)

1. **Always validate external libraries early** - Analyst research saved ~8 hours of trial-and-error
2. **API assumptions are dangerous** - 5 critical errors caught by Critic before implementation
3. **Security review is non-optional** - 2 critical vulnerabilities found in "simple" UI change
4. **Unit tests prevent regressions** - State management is complex, tests catch edge cases
5. **Estimates grow with quality** - 69% increase justified by security + testing + robustness

**Pattern for Reuse:**
- Research (analyst) → Critique (critic) → Refine (planner) → Secure (security) → Implement

---

**Document Version:** 2.0 (Enriched)
**Implementation Date:** 2026-01-16
**Status:** ✅ IMPLEMENTED (security fixes applied)


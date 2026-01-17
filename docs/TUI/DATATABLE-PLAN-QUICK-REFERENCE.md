# DataTable Migration - Quick Reference

**Full Plan:** `DATATABLE-PLAN.md` (825 lines, 32 KB)  
**Status:** ✅ Production-Ready (with 2 critical security fixes required)  
**Estimate:** 27 hours (was 16 hours)

## Critical Actions Required Before Implementation

### 🚨 Security Blockers (7 hours)

1. **CRITICAL-001: Terminal Escape Injection** (4 hours)
   - Implement `sanitize_terminal_text()` in `_utils.py`
   - Remove ANSI escapes, control chars, Unicode overrides
   - Apply to all DisplayItem fields
   - Test: `test_sanitize_removes_ansi_escapes()`

2. **CRITICAL-002: Unicode Fallback** (3 hours)
   - Implement `get_terminal_indicators()` in `_utils.py`
   - Detect UTF-8 support, fallback to ASCII
   - Test: `test_ascii_fallback_in_non_utf8_terminal()`

## Implementation Corrections (Must Follow)

1. ✅ Add `add_columns()` in `on_mount()` before adding rows
2. ✅ Preserve `_checked` state across `set_items()` calls
3. ✅ Use `event.row_key` (NOT `event.cursor_row`)
4. ✅ Implement `_is_filtering` flag for race condition protection
5. ✅ Use bulk `add_rows()` (NOT individual `add_row()` in loop)

## Phase Breakdown (27 hours)

| Phase | Hours | Key Deliverables |
|-------|-------|------------------|
| 0 | 2h | Validation spike with security tests |
| 1 | 4h | Core ItemDataTable with security sanitization |
| 2 | 3h | State management with sync logic |
| 3 | 3h | Event integration with correct API |
| 4 | 2h | Pane integration |
| 5 | 2.5h | Filter optimization with debouncing |
| 6 | 1h | Styling |
| **6.5** | **4h** | **Unit testing (NEW - 20+ tests)** |
| 7 | 3.5h | Integration testing & validation |
| Buffer | 2h | Contingency |

## Success Metrics

- Startup time: 16-21s → <3s (85% reduction)
- Widget count: 2,505 → <100 (95% reduction)
- Test coverage: 0% → >85%
- Security: 2 critical vulnerabilities → 0

## Implementation Reference

**Security Code:**
- `src/skill_installer/tui/_utils.py`: `sanitize_terminal_text()`, `get_terminal_indicators()`

**Widget Code:**
- `src/skill_installer/tui/widgets/item_list.py`: `ItemDataTable` class

**Tests:**
- `tests/test_tui.py`: TestSanitizeTerminalText, TestGetTerminalIndicators

## Pattern for Implementer

```python
# 1. Security utilities (Phase 1)
from _utils import sanitize_terminal_text, get_terminal_indicators

# 2. Initialize with security (Phase 1)
class ItemDataTable(DataTable):
    def __init__(self):
        super().__init__()
        self._checked = set()
        self._is_filtering = False
        self._indicators = get_terminal_indicators()
    
    def on_mount(self):
        self.add_columns("", "Name • Source", "Status", "Description")

# 3. Set items with state preservation (Phase 2)
def set_items(self, items):
    checked_ids = self._checked.copy()
    self.clear()
    self.items = items
    rows = [(self._get_indicator(item),
             sanitize_terminal_text(item.name),
             ...) for item in items]
    self.add_rows(rows)
    self._checked = checked_ids
    self._sync_checked_state_with_display()

# 4. Event handler with correct API (Phase 3)
def on_data_table_row_selected(self, event):
    item = next((i for i in self.items if i.unique_id == event.row_key), None)
    if item:
        self.post_message(self.ItemSelected(item))
```

## Deployment Checklist

- [ ] All CRITICAL security fixes implemented
- [ ] 20+ unit tests passing
- [ ] Startup time <3s validated
- [ ] Security penetration test passed
- [ ] ASCII terminal tested
- [ ] Coverage >85%

---

**For full details, see `DATATABLE-PLAN.md`**

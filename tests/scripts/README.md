# TUI Integration Test Scripts

TMUX-based integration tests for the interactive TUI components.

## Prerequisites

- TMUX installed (`sudo apt install tmux` on Ubuntu/Debian)
- Project dependencies installed (`uv sync`)
- Running from project root directory

## Test Scripts

### test_discover_tab.sh

Tests the Discover tab functionality including:

- TUI launch and initialization
- Discover tab display and navigation
- Vim-style key bindings (j/k)
- Arrow key navigation
- Search input functionality
- Platform filter dropdown
- Item selection with Space key
- Item detail view with Enter key
- Tab switching between panes
- Quit functionality with 'q' key

**Usage:**

```bash
# Run from project root
./tests/scripts/test_discover_tab.sh

# View captured screens
ls -lh /tmp/skill-installer-test/
cat /tmp/skill-installer-test/01_initial_load.txt
```

**Expected Output:**

```
[INFO] Starting Discover tab tests
[INFO] Test 1: Launching interactive TUI
[PASS] TUI loaded successfully
[PASS] Discover tab visible
...
================================
All Discover tab tests passed!
================================
```

### test_detail_view.sh

Tests the Item Detail View functionality including:

- Opening detail view for installed items
- Opening detail view for uninstalled items
- Detail header components (title, name, source)
- Description and author metadata display
- Security warning message
- Install options (user scope, project scope)
- Uninstall option for installed items
- Back to list option
- Option navigation with Up/Down and j/k keys
- Selection indicator (>)
- Scrolling within detail view
- Closing detail view with Escape
- Footer navigation hints

**Usage:**

```bash
# Run from project root
./tests/scripts/test_detail_view.sh

# View captured screens
ls -lh /tmp/skill-installer-detail-test/
cat /tmp/skill-installer-detail-test/02_detail_installed_top.txt
cat /tmp/skill-installer-detail-test/08_install_options.txt
```

**Expected Output:**

```
[INFO] Starting Item Detail View tests
[INFO] Test 1: Launching interactive TUI
[PASS] TUI loaded successfully
[INFO] Test 2: Open detail view for installed item
[PASS] Detail view opened with title
[PASS] Source information shown
...
================================
All Detail View tests passed!
================================
```

### test_location_selection.sh

Tests the Location Selection View functionality including:

- Opening location selection from item detail
- Platform availability detection
- Display of available platforms with paths
- Keyboard navigation (Up/Down and j/k keys)
- Checkbox toggling with Space key
- Multiple platform selection
- Validation warning when no platforms selected
- Installation confirmation with Enter
- Cancellation with Escape key
- Return to Discover tab after cancel

**Usage:**

```bash
# Run from project root
./tests/scripts/test_location_selection.sh

# View captured screens
ls -lh /tmp/skill-installer-test/
cat /tmp/skill-installer-test/04-location-view.txt
cat /tmp/skill-installer-test/07-toggle-first.txt
```

**Expected Output:**

```
=========================================
Testing Location Selection View
=========================================

1. Starting TUI in TMUX session: skill-installer-location-test-12345
   ✓ TUI loaded successfully
2. Capturing initial Discover tab state
3. Navigating to first item in Discover list
   ✓ Item selected
4. Opening item detail view
   ✓ Detail view opened
5. Selecting 'Install for you (user scope)'
   ✓ Location selection view opened
   ✓ Claude Code platform detected
   ✓ Copilot CLI platform detected
...
=========================================
All Location Selection Tests PASSED ✓
=========================================
```

## Adding New Tests

Use this template for new test scripts:

```bash
#!/bin/bash
set -e

SESSION="skill-installer-test-$$"
OUTPUT_DIR="/tmp/skill-installer-test"

cleanup() {
    tmux kill-session -t "$SESSION" 2>/dev/null || true
}
trap cleanup EXIT

# Your test logic here
tmux new-session -d -s "$SESSION"
tmux send-keys -t "$SESSION" 'uv run skill-installer interactive' C-m
sleep 2

# Test interactions
tmux send-keys -t "$SESSION" 'j' 'k' 'Enter'

# Capture and verify
tmux capture-pane -t "$SESSION" -p > "$OUTPUT_DIR/output.txt"
grep -q "Expected Text" "$OUTPUT_DIR/output.txt" || exit 1

echo "Test passed"
```

## Troubleshooting

**TMUX session not cleaning up:**
```bash
# Kill all test sessions manually
tmux list-sessions | grep skill-installer-test | cut -d: -f1 | xargs -I {} tmux kill-session -t {}
```

**Screen captures not showing expected content:**
- Increase `LOAD_DELAY` and `KEYSTROKE_DELAY` in the script
- Check if TMUX window size matches expected layout
- Run `tmux attach -t skill-installer-test-<pid>` to view session live

**Tests fail intermittently:**
- Network issues may affect git operations
- Registry files may be in unexpected state
- Clean test environment: `rm -rf ~/.skill-installer-test/`

## Debug Mode

Run tests with manual TMUX attachment to observe behavior:

```bash
# In terminal 1: Start TMUX session
tmux new-session -s debug-tui
uv run skill-installer interactive

# In terminal 2: Monitor session
watch -n 1 'tmux capture-pane -t debug-tui -p'

# In terminal 1: Interact manually with TUI
# Test your workflows and verify output
```

## Performance Profiling

If the TUI is slow to start, use these scripts to identify bottlenecks.

### Quick Startup Timing

Measure how long the TUI takes to render:

```bash
./tests/scripts/profile_tui_interactive.sh
```

This launches the TUI in tmux and measures time until "Skill Installer" appears.

**Example output:**
```
TUI Interactive Startup Profiler
=================================

Waiting for TUI to render...
.......................

TUI rendered successfully!

=================================
STARTUP TIME: 12.5s
=================================

Status: 501 items available, 6 installed
```

### Component Profiling (No UI)

Profile imports, context creation, and data loading without launching the interactive UI:

```bash
uv run python tests/scripts/profile_tui_startup.py
```

**Example output:**
```
============================================================
PHASE 1: Imports
============================================================
  Import create_context: 0.04s
  Import SkillInstallerApp: 0.27s

============================================================
PHASE 2: Context Creation
============================================================
  create_context(): 0.30s

============================================================
PHASE 3: Data Loading
============================================================
  update_stale_sources(): 0.00s
  load_all_data(): 0.98s
    - 501 discovered items
    - 6 installed items
    - 8 sources

============================================================
PHASE 4: Widget Creation (simulation)
============================================================
  Create 501 ItemRow widgets: 0.02s
  Estimated total nested widgets: 2505
```

### Detailed Method Profiling

Run the full TUI with method-level timing instrumentation:

```bash
timeout 30 uv run python tests/scripts/profile_tui_detailed.py
# Press 'q' to quit once loaded
cat /tmp/tui_profile_detailed.log
```

This patches internal methods and logs timing data:

**Example output:**
```
============================================================
TIMING SUMMARY
============================================================
  DataManager.update_stale_sources: 0.00s (1 calls)
  DataManager.load_all_data: 0.98s (1 calls)
  ItemListView.set_items(501 items): 2.79s (1 calls)
  ItemListView.set_items(6 items): 0.03s (1 calls)
  ItemRow.compose: 507 calls

  Total app.run(): 16.29s
  Unaccounted (Textual layout/CSS/render): ~12.49s
============================================================
```

### Interpreting Results

| Metric | What It Means |
|--------|---------------|
| `load_all_data` | Time to discover items from all sources |
| `ItemListView.set_items` | Time to create and mount ItemRow widgets |
| `ItemRow.compose` count | Number of item widgets created |
| `Unaccounted` time | Textual's layout/CSS/render processing |

**Common bottlenecks:**

1. **High `load_all_data` time** → Too many sources or slow discovery
2. **High `set_items` time** → Too many widgets being mounted
3. **High unaccounted time** → Textual processing too many widgets

**Fixes:**

- Reduce widget count (virtualization/pagination)
- Simplify widget nesting (fewer child widgets per row)
- Lazy load data on demand

### Ad-hoc Profiling

For one-off profiling, patch methods directly:

```python
import time
from skill_installer.tui.data_manager import DataManager

original = DataManager.load_all_data
def timed(self):
    start = time.time()
    result = original(self)
    print(f"load_all_data: {time.time() - start:.2f}s")
    return result
DataManager.load_all_data = timed
```

Then run the TUI and observe timing in the terminal.

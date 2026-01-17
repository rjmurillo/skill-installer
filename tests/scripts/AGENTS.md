# How to Run the TUI Test Scripts

You are in `tests/scripts/`. These are shell-based integration tests for the TUI.

## Before You Do Anything

1. **Go to the project root first:**
   ```bash
   cd ../../
   ```

2. **Check tmux is installed:**
   ```bash
   which tmux
   ```
   If missing: `sudo apt install tmux`

3. **Sync dependencies:**
   ```bash
   uv sync
   ```

## How to Run a Test

From the **project root**, run any script like this:

```bash
./tests/scripts/test_discover_tab.sh
```

Do NOT cd into `tests/scripts/` and run `./test_discover_tab.sh`. That will break.

## The Test Scripts

| Script | What It Tests |
|--------|---------------|
| `test_discover_tab.sh` | Discover tab, navigation, search |
| `test_detail_view.sh` | Item detail view, install options |
| `test_location_selection.sh` | Platform selection checkboxes |
| `test_add_source.sh` | Adding marketplace sources |
| `test_batch_install.sh` | Installing multiple items |
| `test_navigation.sh` | Tab switching |
| `test_tui.sh` | Basic TUI launch |
| `test_tui_final.sh` | Final TUI verification |
| `test_tui_simple.sh` | Minimal TUI test |

## What Success Looks Like

```text
[PASS] TUI loaded successfully
[PASS] Discover tab visible
...
All tests passed!
```

## What Failure Looks Like

```text
[FAIL] TUI loaded successfully - Expected pattern 'Skill Installer' not found
```

## If Tests Fail

### Problem: "TUI failed to load"

The TUI didn't start in time. Try:

1. Check the TUI works manually:
   ```bash
   uv run skill-installer interactive
   ```
   Press `q` to quit.

2. If manual works but tests fail, the timing is too aggressive. Look for `LOAD_DELAY` or `sleep` values in the script and increase them.

### Problem: Stale tmux sessions

Kill all test sessions:
```bash
tmux list-sessions | grep skill-installer | cut -d: -f1 | xargs -I {} tmux kill-session -t {}
```

### Problem: Screen captures are empty

The tests capture what tmux sees. If empty:
- Increase sleep/delay values in the script
- Make sure terminal size is adequate (80x24 minimum)

## Debug Mode

Watch a test run live:

```bash
# Terminal 1: Run the test
./tests/scripts/test_discover_tab.sh

# Terminal 2: Watch the tmux session (find session name from test output)
tmux attach -t skill-installer-test-XXXXX
```

## Running All Tests

```bash
cd /home/richard/src/GitHub/rjmurillo/skill-installer
for script in ./tests/scripts/test_*.sh; do
  echo "=== $script ==="
  "$script" || echo "FAILED"
done
```

## TL;DR

```bash
cd /home/richard/src/GitHub/rjmurillo/skill-installer
uv sync
./tests/scripts/test_discover_tab.sh
```

That's it. Run from project root. Check tmux is installed. Read the output.

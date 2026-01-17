# Manual Testing Guide for Location Selection

Some TUI features cannot be fully automated with TMUX due to keyboard event handling limitations. This guide provides manual test procedures for those features.

## Prerequisites

```bash
# From project root
uv run skill-installer interactive
```

## Test Procedure: Location Selection Flow

### 1. Navigate to an Uninstalled Item

- Launch the interactive TUI
- Press `Tab` or arrow keys to focus on the item list
- Use `j`/`k` or `Up`/`Down` to find an item marked with `○` (not installed)
- Press `Enter` to open the detail view

**Expected**: Detail view opens showing item details

### 2. Select User-Scope Installation

- In the detail view, the first option should be "Install for you (user scope)"
- Press `Enter` to select this option

**Expected**: Location selection view appears with:
- Title: "Select installation locations"
- Subtitle with item name
- List of available platforms with checkboxes
- Footer: "Press SPACE to toggle, ENTER to install, ESC to cancel"

### 3. Test Platform Detection

**Expected platforms** (depending on your system):
- `[ ] Claude Code /home/user/.claude` (if Claude Code installed)
- `[ ] VS Code ~/.config/Code/User/prompts` (if VS Code installed)
- `[ ] VS Code Insiders ~/.config/Code - Insiders/User/prompts` (if VS Code Insiders installed)
- `[ ] Copilot CLI /home/user/.copilot/agents` (if Copilot CLI installed)

**Verify**:
- Only installed platforms appear
- Paths are correct for your system
- First platform is highlighted (selected)

### 4. Test Keyboard Navigation

**Test actions**:
- Press `j` or `Down` arrow
  - **Expected**: Selection moves to next platform
- Press `k` or `Up` arrow
  - **Expected**: Selection moves to previous platform
- Navigate to last platform and press `j`
  - **Expected**: Selection stays on last platform (no wrapping)
- Navigate to first platform and press `k`
  - **Expected**: Selection stays on first platform

### 5. Test Checkbox Toggling

**Test actions**:
- With first platform selected, press `Space`
  - **Expected**: Checkbox changes to `[X]`, text becomes bold
- Press `Space` again
  - **Expected**: Checkbox changes back to `[ ]`, text normal weight
- Navigate to second platform with `j`
- Press `Space`
  - **Expected**: Second checkbox toggles to `[X]`
- Both platforms should now be checked: `[X]`

### 6. Test Validation (No Platforms Selected)

**Setup**:
- Ensure all checkboxes are unchecked `[ ]`

**Test action**:
- Press `Enter`

**Expected**:
- Warning message appears: "⚠ Please select at least one location"
- Location view stays open
- No installation occurs

### 7. Test Installation with Selected Platforms

**Setup**:
- Check at least one platform (press `Space` to toggle to `[X]`)

**Test action**:
- Press `Enter`

**Expected**:
- Location view closes
- Returns to Discover tab
- Notification appears for each platform: "Installed {item} to {platform}"
- Item list refreshes
- Item is now marked with `●` (installed)
- Item shows platform tags for installed platforms

### 8. Test Cancellation

**Test action**:
- Select an uninstalled item and open location view (repeat steps 1-2)
- Check or uncheck any platforms
- Press `ESC`

**Expected**:
- Location view closes immediately
- Returns to Discover tab
- No installation occurs
- Item remains marked with `○` (not installed)

## Edge Cases to Test

### Multiple Platform Installation

1. Open location view for an uninstalled item
2. Check multiple platforms (e.g., Claude Code and VS Code)
3. Press `Enter`
4. **Expected**: Item installs to both platforms, shows success notification for each

### Platform Compatibility

1. Try to install a **skill** (only supported on Claude Code)
2. **Expected**: Only Claude Code appears in location selection
3. Try to install an **agent** (supported on all platforms)
4. **Expected**: All available platforms appear

### Already Installed Items

1. Select an item marked with `●` (installed)
2. Press `Enter` to open detail view
3. **Expected**:
   - First option is "Uninstall" (not "Install for you")
   - No location selection view appears

## Known TMUX Limitations

The following features work in manual testing but may not work reliably in TMUX automation:

1. **Space key toggle**: TMUX may intercept Space for copy mode
2. **ESC key closing**: TMUX may require `C-[` instead of ESC
3. **Modal focus**: Focus management differs between TMUX and native terminal

Always perform manual testing in a native terminal for final verification.

## Regression Testing Checklist

After code changes, verify:

- [ ] Location view opens from "Install for you" option
- [ ] Correct platforms detected (matches `platforms.py` logic)
- [ ] Platform paths match system conventions
- [ ] Navigation (j/k/arrows) works in both directions
- [ ] Space toggles checkboxes with visual feedback
- [ ] Validation prevents installation with no selection
- [ ] Enter installs to selected platforms only
- [ ] ESC cancels without installing
- [ ] Multiple platform selection works
- [ ] Notifications display for each platform
- [ ] Item status updates after installation

## Reporting Issues

If you find issues during manual testing:

1. Note the exact steps to reproduce
2. Capture screenshots if possible
3. Check `/tmp/skill-installer-test/` for TMUX test artifacts
4. Report at: https://github.com/rjmurillo/skill-installer/issues

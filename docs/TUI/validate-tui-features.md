# Prompt: Validate TUI Features and Update Implementation Plan

## Purpose

Systematically audit the TUI to determine what features are working and what remains to be implemented. Update the implementation plan at `TUI-COMPLETION-PLAN.md`.

## Instructions

Execute these steps in order:

### Step 1: Run Test Suite

Run the test suite and record results:

```bash
cd /home/richard/src/GitHub/rjmurillo/skill-installer
uv run pytest tests/ -v --tb=short 2>&1 | tail -50
```

Record: total tests, pass count, fail count, coverage percentage.

### Step 2: Identify TODO Items in Code

Search for unimplemented features:

```bash
grep -rn "TODO:\|FIXME:\|not yet implemented\|not implemented" src/skill_installer/
```

Document each TODO with file path and line number.

### Step 3: Launch Interactive TUI

Start the TUI in async mode:

```bash
uv run skill-installer interactive
```

### Step 4: Test Each Feature Category

Test these features and record pass/fail:

**Navigation**
- [ ] Tab switches between Discover/Installed/Marketplaces
- [ ] Arrow keys navigate item lists
- [ ] j/k keys navigate item lists
- [ ] Search input filters items

**Discover Tab**
- [ ] Items display with installed status indicators
- [ ] Platform filter dropdown works
- [ ] Enter key opens item detail view
- [ ] Space key toggles item selection
- [ ] 'i' key triggers installation

**Item Detail View**
- [ ] Shows name, source, description
- [ ] Shows license information
- [ ] Shows author if available
- [ ] "Install for you" option works
- [ ] "Install for all collaborators" option works
- [ ] "Uninstall" option works (for installed items)
- [ ] "Open homepage" option works
- [ ] Escape closes detail view

**Location Selection View**
- [ ] Opens when selecting "Install for you"
- [ ] Shows available platforms with paths
- [ ] Space key toggles platform checkboxes
- [ ] Enter key confirms and installs
- [ ] Escape cancels

**Installed Tab**
- [ ] Lists installed items
- [ ] Search filters installed items

**Marketplaces Tab**
- [ ] Lists configured sources
- [ ] Enter opens source detail view
- [ ] 'u' key updates source
- [ ] 'r' key removes source

**Source Detail View**
- [ ] "Browse plugins" filters Discover tab
- [ ] "Update marketplace" updates source
- [ ] "Enable auto-update" toggles setting
- [ ] "Remove marketplace" removes source

### Step 5: Document Findings

For each failed feature, identify:

1. Current behavior
2. Expected behavior
3. Root cause (if determinable from code inspection)
4. Relevant code location (file and line numbers)

### Step 6: Update Implementation Plan

Update `TUI-COMPLETION-PLAN.md` with:

1. Current date in header
2. Updated feature audit table with pass/fail status
3. Any new issues discovered
4. Revised effort estimates if scope changed
5. Updated milestone status ([COMPLETE], [IN PROGRESS], [PENDING], [BLOCKED])

### Step 7: Output Summary

Provide a summary in this format:

```markdown
## TUI Validation Summary

**Date**: YYYY-MM-DD
**Tests**: X/Y passing (Z% coverage)

### Feature Status

| Category | Working | Broken | Not Implemented |
|----------|---------|--------|-----------------|
| Navigation | N | N | N |
| Discover | N | N | N |
| Detail View | N | N | N |
| Location Selection | N | N | N |
| Installed | N | N | N |
| Marketplaces | N | N | N |

### Critical Issues

1. [Issue description] - [Location]

### Plan Updated

- File: TUI-COMPLETION-PLAN.md
- Changes: [Summary of updates]
```

## Key Files to Inspect

| File | Purpose |
|------|---------|
| `src/skill_installer/tui.py` | All TUI components |
| `src/skill_installer/install.py` | Installation logic |
| `src/skill_installer/registry.py` | Data persistence |
| `src/skill_installer/platforms/__init__.py` | Platform detection |

## Known Issue Patterns

When testing, watch for these patterns:

1. **Event bubbling**: `on_key` handlers calling `event.stop()` before bindings process
2. **Focus management**: Overlay views not receiving focus after display
3. **State refresh**: UI not updating after data changes
4. **Async timing**: Actions completing before UI updates

## Exit Criteria

Validation complete when:

- [ ] All feature categories tested
- [ ] All failures documented with root cause
- [ ] Implementation plan updated with current status
- [ ] Summary provided to user

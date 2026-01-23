# Test Coverage Analysis: Issue #6 - Marketplace Agents/Commands Discovery

## Quick Summary
Branch copilot/fix-installable-items-error adds discovery of agents and commands from marketplace manifests. Core functionality works (81% coverage on modified discovery code), but ONE failing test and critical coverage gaps remain for edge cases.

## Changes Implemented
1. MarketplacePlugin model extended: Added `agents: list[str]` and `commands: list[str]` fields
2. discover_from_marketplace() method extended: Loops over plugin.agents and plugin.commands, calls _parse_agent_file() with different parameters
3. Test fixture updated: marketplace_repo now includes agents and commands directories
4. New test assertions: Verify agents and commands are discovered (4 items instead of 2)

## Coverage Status
- discovery.py: 81% line coverage (up from 41%)
- test_discover_from_marketplace passes: agents and commands discovered correctly
- BLOCKER: test_discover_all_marketplace FAILS - expects 2 items, gets 4

## Critical Issues

### ISSUE 1: test_discover_all_marketplace Failure [BLOCKING]
**Test**: tests/test_discovery.py::TestMarketplaceDiscovery::test_discover_all_marketplace (line 388-396)
**Expected**: 2 items (skills only)
**Actual**: 4 items (2 skills + 1 agent + 1 command)
**Root Cause**: Test expectation incorrect - comment says "Should only find skills from marketplace" but code changed to discover agents/commands too
**Fix Required**: Update test assertion from `assert len(items) == 2` to `assert len(items) == 4`

### ISSUE 2: Agent Platform Assignment [HIGH RISK]
**Location**: discovery.py line 358-361
**Problem**: Agents/commands discovered via marketplace always get `platforms=["claude"]`
**Risk**: Agents in marketplace.json have no platform indicator. They default to Claude only, but should agents be platform-specific based on context?
**Question**: Should marketplace agents/commands inherit platform from plugin config or manifest?
**Impact**: User installs agent expecting VS Code compatibility but gets Claude-only
**Test Gap**: No test verifies platform assignment for marketplace agents/commands

### ISSUE 3: Missing File Path Validation [MEDIUM RISK]
**Location**: discovery.py line 131-139 (agents) and 140-150 (commands)
**Code**: `if agent_path.is_file(): ... if item:` pattern
**Gap**: No test for agent/command referenced in manifest but file doesn't exist at runtime
**Gap**: No test for when _parse_agent_file returns None (parsing error)
**Current Behavior**: Item silently skipped if missing/unparseable
**User Impact**: Agent listed in manifest doesn't appear without error message
**Test Gap**: Need test for missing agent/command file paths

### ISSUE 4: Relative Path Computation [MEDIUM RISK]
**Location**: discovery.py line 363-369 (in _parse_agent_file)
**Problem**: relative_path computed for agents/commands but may be empty string
**Evidence**: Line 365-369 catches ValueError and falls back to path.name
**Gap**: No test verifies relative_path is correctly computed for marketplace agents/commands
**Impact**: Item key might be just filename, not hierarchical path (breaks disambiguation)

## Code Path Coverage Analysis

### Happy Path (COVERED)
- Agent file exists, valid frontmatter with name field
  - Test: test_discover_from_marketplace ✓
- Command file exists, valid frontmatter with name field
  - Test: test_discover_from_marketplace ✓

### Edge Cases (GAPS)

| Edge Case | Tested? | Risk | Evidence |
|-----------|---------|------|----------|
| Agent file missing | NO | HIGH | Code calls is_file() but no test verifies behavior when false |
| Agent file not readable (permission denied) | NO | MEDIUM | Exception caught as `Exception` but test doesn't verify |
| Agent frontmatter invalid YAML | NO | MEDIUM | _parse_frontmatter returns {} but test doesn't verify agent is skipped |
| Agent frontmatter missing 'name' field | PARTIAL | MEDIUM | Code doesn't require_frontmatter for agents (only for commands), but tests don't verify name derivation |
| Command file missing 'name' in frontmatter | NO | HIGH | Commands use require_frontmatter=True but no test for this validation failure |
| Empty agents/commands lists in manifest | NO | LOW | Loops would just not iterate, but no explicit test |
| Path normalization issues (../, ./) | PARTIAL | MEDIUM | Code does lstrip("./") but doesn't handle ../ or complex paths |
| Relative path computation fails (ValueError) | NO | MEDIUM | Code catches ValueError but test doesn't exercise this path |

## Test Gap Details

### Gap 1: Missing File Handling
**Scenario**: Manifest references ./agents/nonexistent.md
**Current behavior**: Item not added (silently skipped)
**Test needed**:
```python
def test_discover_from_marketplace_missing_agent_file(discovery, tmp_path):
    # Create manifest with agent reference
    # Do NOT create the agent file
    # Assert no agent found (or no error thrown)
    items = discovery.discover_from_marketplace(tmp_path)
    agent_items = [i for i in items if i.item_type == "agent"]
    assert len(agent_items) == 0
```

### Gap 2: Command Without Required Frontmatter
**Scenario**: Command file exists but has no frontmatter or missing 'name' field
**Current behavior**: Command not added
**Test needed**:
```python
def test_discover_from_marketplace_command_invalid_frontmatter(discovery, tmp_path):
    # Create manifest with command reference
    # Create command file with no frontmatter
    # Assert no command found
    pass
```

### Gap 3: Agent Without Frontmatter (name derivation)
**Scenario**: Agent file exists but has no frontmatter
**Current behavior**: Name derived from filename (this is ALLOWED for agents, not commands)
**Test needed**:
```python
def test_discover_from_marketplace_agent_name_derivation(discovery, tmp_path):
    # Create agent file named "my-agent.md" with no frontmatter
    # Assert agent discovered with name="my-agent"
    pass
```

### Gap 4: Platform Assignment Verification
**Scenario**: Agent from marketplace
**Current behavior**: Always gets platforms=["claude"]
**Test needed**:
```python
def test_marketplace_agent_platform_assignment(discovery, marketplace_repo):
    items = discovery.discover_from_marketplace(marketplace_repo)
    agent = next(i for i in items if i.item_type == "agent")
    assert agent.platforms == ["claude"]  # OR should it be ["vscode", "copilot"]?
```

### Gap 5: Relative Path Computation
**Scenario**: Agent at ./agents/pdf-agent.md
**Current behavior**: relative_path set to "agents/pdf-agent.md"
**Test needed**:
```python
def test_marketplace_agent_relative_path(discovery, marketplace_repo):
    items = discovery.discover_from_marketplace(marketplace_repo)
    agent = next(i for i in items if i.item_type == "agent")
    assert agent.relative_path == "agents/pdf-agent.md"
    assert agent.item_key == "agents/pdf-agent.md"  # Verify item_key uses it
```

## _parse_agent_file() Parameters Analysis

### When called for agents (line 133-137)
```python
item = self._parse_agent_file(
    agent_path,
    "agent",
    repo_path=repo_path,
)
```
- require_frontmatter=False (default)
- Means: Agent can be discovered even without frontmatter (name derives from filename)
- Behavior: Matches auto-discovery of agents ✓

### When called for commands (line 143-148)
```python
item = self._parse_agent_file(
    command_path,
    "command",
    require_frontmatter=True,
    repo_path=repo_path,
)
```
- require_frontmatter=True
- Means: Command MUST have frontmatter with 'name' field
- Behavior: Commands are stricter than agents ✓

**Gap**: No test verifies command without frontmatter is rejected

## Platform Support Concern

**Current**: Agents/commands from marketplace get platforms=["claude"] (line 361)
**Issue**: Agents with .agent.md extension normally get ["vscode", "copilot"] (line 359)
**Question**: Should marketplace agents inherit platform from file extension or config?

**Evidence**:
- marketplace_repo fixture creates "agents/pdf-agent.md" (no .agent.md extension)
- discovery.py line 358: Extension check only matches .agent.md or .prompt.md
- marketplace agent gets platforms=["claude"] because it doesn't match extension patterns
- This may be by design (marketplace explicitly declares platform compatibility)

**Test Gap**: No test documents this intentional behavior or validates it's correct

## Cyclomatic Complexity Check

**Lines 130-150**: discover_from_marketplace marketplace agent/command discovery
- 2 nested loops + 2 if conditions = CC 5
- Well below max of 10 ✓

**Lines 320-381**: _parse_agent_file
- Multiple if branches, 1 try-except
- CC approximately 8 (acceptable) ✓

## Recommendations

1. **MUST FIX**: Update test_discover_all_marketplace to expect 4 items (agents and commands included)
2. **HIGH PRIORITY**: Add test for command file missing required frontmatter
3. **HIGH PRIORITY**: Add test for missing agent/command file (manifest reference doesn't exist)
4. **MEDIUM PRIORITY**: Add test verifying relative_path computation for marketplace agents/commands
5. **MEDIUM PRIORITY**: Add test documenting platform assignment for marketplace agents (should be ["claude"] or derived from extension?)
6. **MEDIUM PRIORITY**: Add test for agent name derivation when no frontmatter
7. **NICE-TO-HAVE**: Test for complex path normalization (../ handling)

## New Code Coverage
- Lines covered: 130-150 (agents/commands loops) ✓
- Lines NOT covered: 171-179 (auto-discovery path when marketplace disabled) - OK, different code path
- Frontmatter parsing: Covered ✓
- Platform filtering: Covered ✓

## Manual Testing Strategy

### Test Case 1: Marketplace with all item types
1. Create .claude-plugin/marketplace.json with agents and commands sections
2. Create actual agent and command files
3. Run discover_from_marketplace()
4. Verify: All 4 items discovered (2 skills + 1 agent + 1 command)

### Test Case 2: Missing agent file
1. Create manifest referencing ./agents/nonexistent.md
2. Run discover_from_marketplace()
3. Verify: No error, agent not included in results

### Test Case 3: Command with invalid frontmatter
1. Create commands/test.md with empty body (no frontmatter)
2. Add to manifest
3. Run discover_from_marketplace()
4. Verify: Command not discovered (silently skipped)

### Test Case 4: Platform compatibility
1. Install agent from marketplace
2. Filter by platform (vscode, claude)
3. Verify agent appears/disappears correctly

## Exit Criteria for QA Sign-Off
- [ ] test_discover_all_marketplace passes
- [ ] test_discover_from_marketplace passes
- [ ] New test for missing agent/command file
- [ ] New test for command invalid frontmatter
- [ ] discovery.py maintains 80%+ coverage
- [ ] All tests pass (29/29)

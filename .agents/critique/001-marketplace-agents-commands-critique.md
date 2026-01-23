# Plan Critique: Marketplace Discovery for Agents and Commands (Issue #6)

## Verdict

[FAIL] Plan implementation incomplete. Existing test failure must be resolved before merge.

## Summary

Changes add `agents` and `commands` fields to the MarketplacePlugin model and extend discovery logic to parse these item types. Test coverage added for new functionality. However, critical regression identified: existing test `test_discover_all_marketplace` fails because fixture was extended but test assertion was not updated to reflect expanded item count.

## Strengths

- Model extension follows existing pattern (agents/commands added as list fields with defaults)
- Discovery logic properly distinguishes between agents and commands via `require_frontmatter` parameter
- File existence checks prevent parsing missing files
- Test fixture creates proper directory structure with frontmatter
- Assertions verify both item types are discovered with correct names

## Critical Issues Found

[FAIL] **Test Regression: test_discover_all_marketplace**
- **Location**: tests/test_discovery.py line 394-396
- **Status**: FAILING
- **Problem**: Fixture now returns 4 items (2 skills + 1 agent + 1 command) but test assertion expects 2
- **Impact**: Cannot merge with failing test
- **Root Cause**: Fixture was extended with agent/command entries but existing test not updated
- **Required Fix**: Update assertion from `assert len(items) == 2` to `assert len(items) == 4` and remove or relax item_type check

Output from test run:
```
AssertionError: assert 4 == 2
 where 4 = len([DiscoveredItem(name='pdf', item_type='skill', ...),
                DiscoveredItem(name='docx', item_type='skill', ...),
                DiscoveredItem(name='pdf-agent', item_type='agent', ...),
                DiscoveredItem(name='pdf-process', item_type='command', ...)])
```

## Important Issues

### Edge Case: Platform Detection for Agents/Commands

**Location**: discovery.py lines 130-150

**Issue**: Agents and commands discovered from marketplace manifest default to `platforms=["claude"]` but file extension detection is skipped.

**Evidence**:
```python
# Lines 333-361 in _parse_agent_file
platforms = []
if path.name.endswith(".agent.md") or path.name.endswith(".prompt.md"):
    platforms = ["vscode", "copilot"]
elif path.suffix == ".md":
    platforms = ["claude"]  # <-- Always claude for plain .md files
```

**Concern**: Test fixture files are named `pdf-agent.md` and `pdf-process.md` (plain .md suffix, not .agent.md/.prompt.md). These are discovered as Claude-only items. Is this intentional?

**Questions**:
1. Should marketplace-specified agents/commands inherit platform info from marketplace.json?
2. Should `pdf-agent.md` with `.md` extension be treated as Claude-only or inherit from plugin metadata?
3. Are marketplace agents/commands always Claude-only, or should they support multi-platform like auto-discovered agents?

### Missing Frontmatter Validation Inconsistency

**Location**: discovery.py lines 140-150

**Issue**: Commands use `require_frontmatter=True` but agents do not.

**Evidence**:
```python
# Agents: no frontmatter requirement
item = self._parse_agent_file(agent_path, "agent", repo_path=repo_path)

# Commands: frontmatter required
item = self._parse_agent_file(command_path, "command", require_frontmatter=True, repo_path=repo_path)
```

**Concern**: Agent files without frontmatter will silently return None. Is this intentional? Should marketplace agents require frontmatter like commands do?

**Questions**:
1. What is the minimum viable agent? Frontmatter optional or required?
2. Should both agent and command require `name` in frontmatter for discovery?

## Minor Issues

### Test Fixture Data Inconsistency

**Location**: tests/test_discovery.py line 290

**Issue**: Docx skill description has indentation:
```markdown
  # DOCX Skill

Process Word documents.
```

The leading spaces before `# DOCX Skill` appear to be a typo (only docx has this, pdf doesn't).

**Impact**: Low - cosmetic, does not affect functionality
**Recommendation**: Fix indentation for consistency

### Relative Path Not Set for Marketplace Items

**Location**: discovery.py line 136

**Observation**: Agents and commands parsed via `_parse_agent_file` may not have `relative_path` set correctly.

**Evidence**: In `_parse_agent_file` (lines 364-369):
```python
relative_path = ""
if repo_path:
    try:
        relative_path = str(path.relative_to(repo_path))
    except ValueError:
        relative_path = path.name
```

The marketplace discovery **does pass** `repo_path`, so this should work. This is correct implementation.

**No action needed** - properly implemented.

## Questions for Implementation Team

1. **Platform Intent**: Clarify whether marketplace agents/commands should:
   - Always be Claude-only (current behavior via .md extension)?
   - Support multi-platform like VS Code agents (via .agent.md)?
   - Inherit platform info from marketplace manifest?

2. **Frontmatter Requirements**: Should agents require frontmatter like commands do?

3. **Item Type Coverage**: Is coverage for "agents" and "commands" complete, or are there other item types (prompts, workflows, etc.) that need addition to MarketplacePlugin?

## Acceptance Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| agents/commands fields added to MarketplacePlugin | [PASS] | registry.py lines 44-45 |
| discover_from_marketplace iterates agents | [PASS] | discovery.py lines 130-139 |
| discover_from_marketplace iterates commands | [PASS] | discovery.py lines 140-150 |
| Test fixtures created | [PASS] | tests/test_discovery.py lines 296-320 |
| Assertions verify discovery | [PARTIAL] | New test passes, existing test fails |
| **All tests pass** | [FAIL] | test_discover_all_marketplace fails |

## Recommendations

### Before Merge

1. **Fix test_discover_all_marketplace** (BLOCKING):
   - Update line 395: `assert len(items) == 4` (was `assert len(items) == 2`)
   - Update line 396: Remove or modify `assert all(i.item_type == "skill" for i in items)` since it now includes agents and commands
   - Verify the relaxed assertion still validates marketplace discovery behavior

2. **Clarify platform behavior**:
   - Add comment explaining why marketplace agents/commands default to Claude-only
   - If multi-platform support intended, update _parse_agent_file to check file extension

3. **Add missing edge case tests**:
   - Test marketplace with missing agent file (like existing test for missing skill dir)
   - Test marketplace agent without frontmatter
   - Test marketplace command without frontmatter (should return None with require_frontmatter=True)

### Desirable Improvements

4. **Fix test fixture formatting**:
   - Remove indentation from docx SKILL.md (line 290)

5. **Document platform behavior**:
   - Add docstring clarification in MarketplacePlugin about when agents/commands are used
   - Document platform assignment logic in _parse_agent_file

## Test Coverage Assessment

**Discovery module coverage increase**: 41% -> 81% (from test run)
- New paths covered: marketplace agent/command iteration
- Branch coverage improved for conditional file checks

**Missing coverage**:
- Marketplace with missing agent file (file doesn't exist check)
- Marketplace with missing command file
- Marketplace agents/commands with invalid/missing frontmatter

## Approval Conditions

| Condition | Status | Notes |
|-----------|--------|-------|
| Failing test fixed | [FAIL] | Must fix test_discover_all_marketplace |
| No regressions | [FAIL] | One existing test broken |
| Edge cases covered | [WARNING] | Missing tests for missing files |
| Implementation complete | [PASS] | All fields/logic added |
| Code follows conventions | [PASS] | Style, naming, structure consistent |

## Implementation Quality

### Code Style Compliance

**registry.py changes** (lines 44-45):
- Follows existing Pydantic patterns
- Field defaults use `Field(default_factory=list)` consistently
- Type hints correct: `list[str]`

**discovery.py changes** (lines 130-150):
- Consistent iteration pattern (same as skills loop)
- Path handling correct: `repo_path / path_str.lstrip("./")`
- Proper file existence check: `is_file()`
- Conditional logic clear and maintainable
- Names match item types correctly

**Test additions** (tests/test_discovery.py):
- Fixture setup follows existing patterns
- Directory creation proper: `mkdir(parents=True)`
- Frontmatter formatting correct with YAML
- Assertions verify names, counts, and types

### Analysis Notes

**Manual Integration Test Result**: PASS
- Created marketplace with agents and commands
- Both item types discovered correctly
- Frontmatter parsed, relative paths computed
- Platform defaults applied (claude for .md files)

**Cyclomatic Complexity**: Acceptable
- New loops are simple iteration (CC ~2 each)
- No nested branching complexity introduced

**Coverage Impact**: +40 percentage points (41% -> 81%)
- New discovery paths covered by test fixture
- Branch coverage for file existence checks

## Verdict Detail

**Cannot approve for merge** due to:
1. Failing test (test_discover_all_marketplace) - BLOCKING
2. Incomplete edge case coverage
3. Undocumented platform behavior assumptions

The implementation logic is sound and follows existing patterns. Code quality is good. The test regression is a simple oversight - the fixture was expanded correctly, but the existing test assertion was overlooked.

---

**Recommended Actions** (for implementer):

**Required (Blocking)**:
1. Fix test_discover_all_marketplace:
   - Line 395: Change `assert len(items) == 2` to `assert len(items) == 4`
   - Line 396: Change or remove the item_type assertion to allow mixed types
   - Example fix:
     ```python
     def test_discover_all_marketplace(self, discovery: Discovery, marketplace_repo: Path) -> None:
         """Test discover_all uses marketplace discovery when available."""
         items = discovery.discover_all(marketplace_repo, None)

         # Should find items from marketplace (not auto-discover)
         assert len(items) == 4
         names = [i.name for i in items]
         assert "pdf" in names
         assert "docx" in names
         assert "pdf-agent" in names
         assert "pdf-process" in names
     ```

**Strongly Recommended**:
2. Add edge case tests:
   - Test marketplace with missing agent file
   - Test marketplace with missing command file
   - Test agent/command without frontmatter (should these fail silently?)

3. Add documentation comments:
   - Clarify why marketplace items default to Claude platform
   - Document expected use of require_frontmatter for different item types

**Nice-to-have**:
4. Fix fixture formatting (docx indentation, line 290)

# Design Remediation Plan

## Executive Summary

This document analyzes the skill-installer codebase against the Software Hierarchy of Needs framework. The analysis identifies quality issues at each layer and proposes remediation strategies that allow patterns to emerge from enforced qualities.

## Analysis Framework

| Layer | Focus | Status |
|-------|-------|--------|
| Qualities | Cohesion, Coupling, DRY, Encapsulation, Testability | [WARNING] |
| Principles | Open-Closed, Separate Use from Creation | [WARNING] |
| Practices | Programming by Intention, CVA, Encapsulate Constructors | [FAIL] |
| Wisdom | Design to interfaces, favor delegation | [OK] |
| Patterns | Emerge from above | Blocked by lower layers |

## Layer 1: Qualities Assessment

### 1.1 Cohesion

| Module | Rating | Finding |
|--------|--------|---------|
| `registry.py` | HIGH | Single responsibility: manages registry data |
| `gitops.py` | HIGH | Single responsibility: git operations |
| `discovery.py` | MEDIUM | Mixed: discovery + parsing + filtering |
| `transform.py` | HIGH | Single responsibility: format transformation |
| `install.py` | MEDIUM | Mixed: installation + platform detection |
| `cli.py` | LOW | Orchestration mixed with UI feedback |
| `tui.py` | LOW | 1500+ lines, mixes widgets/screens/app/data |
| `platforms/*` | HIGH | Each platform focused on its paths/validation |

**Critical Issue: `tui.py` lacks cohesion**

The TUI module contains:
- Data types (`DisplayItem`, `DisplaySource`)
- UI widgets (12+ custom widgets)
- Modal screens (4+ screens)
- Tab panes (4 panes)
- Main application class
- Legacy console TUI class

**Remediation**: Split into focused modules:
```
src/skill_installer/tui/
    __init__.py          # Public exports
    models.py            # DisplayItem, DisplaySource
    widgets/
        __init__.py
        search.py        # SearchInput
        item_list.py     # ItemRow, ItemListView
        source_list.py   # SourceRow, SourceListView
        detail.py        # ItemDetailOption
    screens/
        __init__.py
        detail.py        # ItemDetailScreen
        location.py      # LocationSelectionScreen
        confirmation.py  # ConfirmationScreen
        add_source.py    # AddSourceScreen
    panes/
        __init__.py
        discover.py      # DiscoverPane
        installed.py     # InstalledPane
        marketplaces.py  # MarketplacesPane
        settings.py      # SettingsPane
    app.py               # SkillInstallerApp
    console.py           # TUI (legacy console)
```

### 1.2 Coupling

| Coupling Pattern | Modules | Severity |
|------------------|---------|----------|
| Concrete class dependencies | `cli.py` -> all modules | HIGH |
| Direct instantiation in commands | `cli.py` lines 73-74, 115-116 | HIGH |
| Platform handler tight coupling | `install.py` -> `platforms` | MEDIUM |
| TUI internal coupling | All widgets reference DisplayItem directly | MEDIUM |

**Critical Issue: `cli.py` creates and uses dependencies**

```python
# Line 73-74: Violates "Separate Use from Creation"
registry = RegistryManager()
gitops = GitOps()
```

Each command creates its own instances. No dependency injection.

**Remediation**: Introduce a context/container:
```python
@dataclass
class AppContext:
    registry: RegistryManager
    gitops: GitOps
    discovery: Discovery
    installer: Installer

def create_context() -> AppContext:
    """Factory for application dependencies."""
    registry = RegistryManager()
    gitops = GitOps()
    discovery = Discovery()
    installer = Installer(registry, gitops)
    return AppContext(registry, gitops, discovery, installer)
```

### 1.3 DRY Violations

| Location | Duplication | Count |
|----------|-------------|-------|
| Platform `validate_agent` | Frontmatter parsing repeated | 4 files |
| Platform `is_available` | Platform detection logic | 4 files |
| `ItemListView` / `SourceListView` | Identical cursor navigation | 2 classes |
| `cli.py` progress spinner | Same pattern in 5 commands | 5 locations |

**Critical Issue: Frontmatter parsing duplicated**

Each platform validates frontmatter independently:
- `claude.py:97-107`
- `vscode.py:92-103`
- `copilot.py:75-86`
- `codex.py:71-80`

**Remediation**: Extract common frontmatter parser:
```python
# In transform.py or new validation.py
def parse_frontmatter(content: str) -> tuple[dict, list[str]]:
    """Parse frontmatter, return (data, errors)."""
    ...

# Platforms use it:
def validate_agent(self, content: str) -> list[str]:
    fm, errors = parse_frontmatter(content)
    if errors:
        return errors
    # Platform-specific validation only
    if "name:" not in fm:
        errors.append("...")
    return errors
```

### 1.4 Encapsulation

| Issue | Location | Impact |
|-------|----------|--------|
| Public internal state | `ItemListView._rows`, `_checked_items` | Widget internals exposed |
| Mutable shared state | `tui.py` module-level `console` | Global state |
| Direct registry file access | `RegistryManager` exposes file paths | Implementation leak |

**Critical Issue: Widget internals exposed**

Test file `test_tui.py:437` directly accesses `_update_counter`:
```python
assert app.source_list._update_counter == 0
```

This couples tests to implementation details.

**Remediation**: Provide public interface for testing:
```python
class SourceListView:
    @property
    def refresh_count(self) -> int:
        """Number of times the list has been refreshed."""
        return self._update_counter
```

### 1.5 Testability Analysis

| Module | Testable | Issue |
|--------|----------|-------|
| `registry.py` | YES | Accepts `registry_dir` parameter |
| `gitops.py` | YES | Accepts `cache_dir` parameter |
| `discovery.py` | PARTIAL | No seams for filesystem |
| `transform.py` | YES | Pure functions |
| `install.py` | PARTIAL | Creates dependencies in constructor defaults |
| `cli.py` | YES | Accepts `_context` parameter for dependency injection |
| `tui.py` | PARTIAL | Async tests work but require App wrapper |
| `platforms/*` | PARTIAL | Filesystem and system checks |

**Remediation Complete: `cli.py` now testable**

All CLI commands accept `_context: AppContext | None` parameter:
```python
@source_app.command("add")
def source_add(
    ...,
    _context: AppContext | None = None,  # Testing seam
) -> None:
    ctx = _context or create_context()
```

Unit tests in `tests/test_cli.py` demonstrate injection of mock doubles.

## Layer 2: Principles Assessment

### 2.1 Open-Closed Principle

| Component | OCP Compliant | Issue |
|-----------|---------------|-------|
| Platforms | YES | Protocol interface defined |
| Discovery | NO | Hardcoded patterns for agent/skill/command |
| Transform | NO | Switch-based platform mapping |

**Critical Issue: No platform interface**

`platforms/__init__.py` uses a dict with concrete classes:
```python
PLATFORMS = {
    "claude": ClaudePlatform,
    "vscode": VSCodePlatform,
    ...
}
```

Adding a platform requires modifying this file.

**Remediation**: Define abstract protocol:
```python
from typing import Protocol

class Platform(Protocol):
    name: str
    agent_extension: str
    supports_skills: bool

    def get_install_path(self, item_type: str, name: str) -> Path: ...
    def validate_agent(self, content: str) -> list[str]: ...
    def is_available(self) -> bool: ...
```

### 2.2 Separate Use from Creation

| Location | Violation | Status |
|----------|-----------|--------|
| `cli.py` every command | Creates RegistryManager, GitOps | ✅ FIXED - Uses `_context` injection |
| `install.py:69-71` | Default construction in `__init__` | ✅ FIXED - Dependencies now required |
| `tui.py:438-444` | Creates all dependencies in command | ✅ FIXED - Uses AppContext |

All "Separate Use from Creation" violations have been remediated.

## Layer 3: Practices Assessment

### 3.1 Programming by Intention

**Current state**: Methods mix high-level intent with implementation details.

Example from `cli.py` `source_add`:
```python
def source_add(...):
    registry = RegistryManager()  # Setup
    gitops = GitOps()             # Setup
    platform_list = platforms.split(",") if platforms else ["claude", "vscode"]  # Parsing
    platform_list = [p.strip() for p in platform_list]  # Parsing
    try:
        source = registry.add_source(...)  # Business logic
        tui.show_success(...)              # UI
        with Progress(...):                # UI
            progress.add_task(...)         # UI
            gitops.clone_or_fetch(...)     # Business logic
        ...
```

**Remediation**: Sergeant method pattern:
```python
def source_add(...):
    """Add a source repository."""
    context = _get_context()
    platforms = _parse_platforms(platforms_arg)
    source = _register_source(context, url, name, ref, platforms)
    _sync_source(context, source)
    _extract_license(context, source)

def _register_source(ctx, url, name, ref, platforms) -> Source:
    """Register source in registry."""
    return ctx.registry.add_source(url, name, ref, platforms)
```

### 3.2 CVA (Commonality/Variability Analysis)

**Status**: ✅ COMPLETE

**Platforms Domain**:

| Commonality | Variability |
|-------------|-------------|
| Base directory | Path structure (claude: ~/.claude, vscode: ~/.config/Code) |
| Install path | Extension (.md vs .agent.md) |
| Validation algorithm | Required fields (name vs tools) |
| Availability check | Check method (dir exists vs app exists) |

**Implementation**: Created `BasePlatform` class with Template Method pattern:
- `validate_agent()` defines algorithm skeleton
- `get_required_fields()` specifies platform-specific requirements
- `get_field_error_message()` provides platform-specific messages

All 4 platforms now inherit from `BasePlatform`, eliminating duplicated validation structure.

**Item Types Domain**:

| Commonality | Variability |
|-------------|-------------|
| Name | From frontmatter or filename |
| Description | From frontmatter |
| Path | File or directory |
| Content retrieval | Single file vs SKILL.md in directory |

### 3.3 Encapsulate Constructors

**Status**: ✅ COMPLETE

All core classes now provide static factory methods:

- `RegistryManager.create(registry_dir)` / `RegistryManager.create_default()`
- `GitOps.create(cache_dir)` / `GitOps.create_default()`
- `Discovery.create()`
- `Installer.create(registry, gitops, transformer=None)`

The `create_context()` function uses these factories for all dependency construction.

## Layer 4: Wisdom Assessment

### 4.1 Design to Interfaces

**Status**: ✅ COMPLETE

Protocol definitions are now defined in `src/skill_installer/protocols.py`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SourceRepository(Protocol):
    """Protocol for git repository operations."""
    def clone_or_fetch(self, url: str, name: str, ref: str = "main") -> Path: ...
    def get_tree_hash(self, path: Path) -> str: ...
    def get_repo_path(self, source_name: str) -> Path: ...
    def remove_cached(self, name: str) -> bool: ...
    def is_cached(self, name: str) -> bool: ...
    def get_license(self, name: str) -> str | None: ...

@runtime_checkable
class ItemRegistry(Protocol):
    """Protocol for item registry operations."""
    def add_source(...) -> Source: ...
    def remove_source(name: str) -> bool: ...
    def get_source(name: str) -> Source | None: ...
    def list_sources() -> list[Source]: ...
    def add_installed(...) -> InstalledItem: ...
    def remove_installed(...) -> bool: ...
    def get_installed(...) -> list[InstalledItem]: ...
    def list_installed(...) -> list[InstalledItem]: ...

@runtime_checkable
class ItemDiscovery(Protocol):
    """Protocol for item discovery operations."""
    def discover_all(repo_path: Path, platform: str | None) -> list[DiscoveredItem]: ...
    def get_item_content(item: DiscoveredItem) -> str: ...
    def is_marketplace_repo(repo_path: Path) -> bool: ...

@runtime_checkable
class ItemInstaller(Protocol):
    """Protocol for item installation operations."""
    def install_item(...) -> InstallResult: ...
    def uninstall_item(...) -> list[InstallResult]: ...
    def check_update_needed(...) -> bool: ...
```

All concrete implementations satisfy these protocols structurally:
- `GitOps` satisfies `SourceRepository`
- `RegistryManager` satisfies `ItemRegistry`
- `Discovery` satisfies `ItemDiscovery`
- `Installer` satisfies `ItemInstaller`

The `AppContext` now types dependencies using protocol interfaces, enabling test doubles without inheritance.

### 4.2 Favor Delegation Over Inheritance

Current state is acceptable. Minimal inheritance used. Widgets extend Textual base classes appropriately.

### 4.3 Encapsulate Concept That Varies

**Status**: ✅ COMPLETE (Content Transformation)

**Concepts needing encapsulation**:

1. **Platform path resolution** - varies by OS and platform
2. **Content validation** - varies by platform (✅ uses Template Method in `BasePlatform`)
3. **Item discovery** - varies by repository structure
4. **Content transformation** - varies by source/target (✅ uses Strategy pattern)

**Content Transformation Implementation**:

The `TransformEngine` now uses the Strategy pattern to encapsulate platform-specific transformations:

```python
# Protocol in protocols.py
class TransformStrategy(Protocol):
    source_platform: str
    target_platform: str
    def transform_frontmatter(self, frontmatter: dict) -> dict: ...
    def transform_syntax(self, body: str) -> str: ...

# Concrete strategies in transform.py
class ClaudeToVSCodeStrategy(BaseTransformStrategy): ...
class VSCodeToClaudeStrategy(BaseTransformStrategy): ...
class IdentityStrategy(BaseTransformStrategy): ...
```

Benefits:
- Adding a new platform requires only creating a new strategy class
- Switch statement in `transform()` eliminated
- Each strategy encapsulates frontmatter and syntax transformations
- Custom strategies can be registered at runtime via `register_strategy()`

## Remediation Priority

### Phase 1: Foundation Fixes (Qualities)

| Task | Effort | Impact |
|------|--------|--------|
| Split `tui.py` into modules | HIGH | Cohesion, Maintainability |
| Extract frontmatter parsing | LOW | DRY |
| Add dependency injection seams | MEDIUM | Testability |
| Extract progress helper | LOW | DRY |

### Phase 2: Principle Enforcement

| Task | Effort | Impact |
|------|--------|--------|
| Create AppContext container | MEDIUM | Separate Use/Creation |
| Define Platform protocol | MEDIUM | Open-Closed |
| Refactor commands with sergeant methods | MEDIUM | Readability |

### Phase 3: Pattern Emergence

With qualities enforced, these patterns should emerge:

| Pattern | Where | Why | Status |
|---------|-------|-----|--------|
| Strategy | Transform engine | Encapsulate platform pair transformations | ✅ Complete |
| Strategy | Platform implementations | Encapsulate varying behavior | Pending |
| Factory | AppContext creation | Encapsulate construction | ✅ Complete |
| Template Method | Validation (parse -> validate -> collect errors) | Common algorithm, varying steps | ✅ Complete |
| Adapter | Transform engine | Adapt between formats | Superseded by Strategy |

## Testability Improvements

### Current Test Gaps

| Module | Coverage | Gap |
|--------|----------|-----|
| `tui.py` | PARTIAL | Integration tests only, unit tests blocked by coupling |
| `cli.py` | MEDIUM | Unit tests added via `_context` injection |
| `install.py` | HIGH | Good |
| `platforms/*` | MEDIUM | Filesystem mocking needed |

### Recommended Test Seams

```python
# install.py - make filesystem operations injectable
class Installer:
    def __init__(
        self,
        registry: RegistryManager | None = None,
        gitops: GitOps | None = None,
        transformer: TransformEngine | None = None,
        fs: FileSystem | None = None,  # New seam
    ):
        self.fs = fs or RealFileSystem()
```

### Hard-to-Test Indicators Found

1. **Static method calls**: `Path.home()` in platforms
2. **System calls**: `sys.platform` checks in platforms
3. **Global state**: `console = Console()` at module level
4. **Direct construction**: Dependencies created in methods

## Implementation Checklist

### Immediate (Sprint 1)

- [x] Create `tui/models.py` with DisplayItem, DisplaySource
- [x] Create `tui/widgets/` package structure
- [x] Extract SearchInput, ItemRow, ItemListView to widgets
- [x] Create `parse_frontmatter()` utility function
- [x] Add `refresh_count` property to `SourceListView` for encapsulation (1.4)
- [x] Add `_context` parameter to CLI commands for testing

### Short-term (Sprint 2)

- [x] Complete TUI module split
- [x] Define `Platform` protocol in `platforms/__init__.py`
- [x] Create `AppContext` container
- [x] Remove default construction from `Installer.__init__` (2.2)
- [x] Refactor `source_add` with sergeant method pattern
- [x] Add CLI unit tests using injected context

### Medium-term (Sprint 3)

- [x] Apply sergeant pattern to remaining commands
- [x] Extract `FileSystem` protocol for filesystem operations
- [x] Add platform-specific test fixtures
- [ ] Increase test coverage to 90%+ for all modules (currently 66%, TUI components are challenging to unit test)

## Metrics to Track

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| `tui.py` lines | N/A (split) | <300 per module | wc -l |
| DRY violations | 2 | 0 | Manual review |
| Test coverage | 66% | 90%+ | pytest --cov |
| Cyclomatic complexity | Unknown | <10 per function | radon cc |
| Coupling (afferent) | Reduced | Reduced | dependency analysis |

## Appendix: Code Smells Catalog

| Smell | Location | Severity | Status |
|-------|----------|----------|--------|
| God Class | `tui.py` | HIGH | ✅ Fixed (split into modules) |
| Feature Envy | `cli.py` accessing registry internals | MEDIUM | ✅ Fixed (uses AppContext) |
| Duplicated Code | Platform validation | MEDIUM | ✅ Fixed (BasePlatform) |
| Long Method | `_interactive_install` 60+ lines | MEDIUM | Pending |
| Data Class | `DisplayItem` with no behavior | LOW | By design |
| Primitive Obsession | Platform names as strings | LOW | Acceptable |

---

**Document Status**: Sprint 3 Complete
**Next Review**: After 90%+ coverage achieved
**Owner**: Architecture Team

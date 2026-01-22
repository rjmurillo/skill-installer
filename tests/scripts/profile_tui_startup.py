#!/usr/bin/env python3
"""Profile TUI startup to identify performance bottlenecks.

Run from project root:
    uv run python tests/scripts/profile_tui_startup.py

Outputs timing for each phase of TUI initialization without launching
the interactive UI.
"""

from __future__ import annotations

import time


def profile_imports() -> float:
    """Profile import times."""
    print("=" * 60)
    print("PHASE 1: Imports")
    print("=" * 60)

    start = time.time()
    from skill_installer.context import create_context  # noqa: F401

    elapsed = time.time() - start
    print(f"  Import create_context: {elapsed:.2f}s")

    start = time.time()
    from skill_installer.tui.app import SkillInstallerApp  # noqa: F401

    elapsed = time.time() - start
    print(f"  Import SkillInstallerApp: {elapsed:.2f}s")

    return time.time()


def profile_context_creation() -> tuple[float, object]:
    """Profile context/service creation."""
    print("\n" + "=" * 60)
    print("PHASE 2: Context Creation")
    print("=" * 60)

    from skill_installer.context import create_context

    start = time.time()
    ctx = create_context()
    elapsed = time.time() - start
    print(f"  create_context(): {elapsed:.2f}s")

    return time.time(), ctx


def profile_data_loading(ctx: object) -> float:
    """Profile data loading operations."""
    print("\n" + "=" * 60)
    print("PHASE 3: Data Loading")
    print("=" * 60)

    from skill_installer.tui.data_manager import DataManager

    dm = DataManager(
        registry_manager=ctx.registry,  # type: ignore[attr-defined]
        gitops=ctx.gitops,  # type: ignore[attr-defined]
        discovery=ctx.discovery,  # type: ignore[attr-defined]
    )

    start = time.time()
    dm.update_stale_sources()
    elapsed = time.time() - start
    print(f"  update_stale_sources(): {elapsed:.2f}s")

    start = time.time()
    discovered, installed, sources, status = dm.load_all_data()
    elapsed = time.time() - start
    print(f"  load_all_data(): {elapsed:.2f}s")
    print(f"    - {len(discovered)} discovered items")
    print(f"    - {len(installed)} installed items")
    print(f"    - {len(sources)} sources")

    return time.time()


def profile_widget_creation(ctx: object) -> float:
    """Profile widget/row creation (without mounting)."""
    print("\n" + "=" * 60)
    print("PHASE 4: Widget Creation (simulation)")
    print("=" * 60)

    from skill_installer.tui.data_manager import DataManager
    from skill_installer.tui.widgets.item_list import ItemDataTable

    dm = DataManager(
        registry_manager=ctx.registry,  # type: ignore[attr-defined]
        gitops=ctx.gitops,  # type: ignore[attr-defined]
        discovery=ctx.discovery,  # type: ignore[attr-defined]
    )
    discovered, _, _, _ = dm.load_all_data()

    # Simulate DataTable row creation (no widget per row, just data)
    start = time.time()
    table = ItemDataTable(id="test-table")
    # Prepare rows without mounting (since we're not in Textual context)
    rows = []
    for item in discovered:
        name_source = f"{item.name} • {item.source_name}"
        status = f"[{', '.join(item.installed_platforms)}]" if item.installed_platforms else ""
        desc = (item.description or "No description")[:60]
        rows.append(("○", name_source, status, desc))
    elapsed = time.time() - start
    print(f"  Prepare {len(rows)} DataTable rows: {elapsed:.2f}s")

    # DataTable uses virtualization - only visible rows are widgets
    visible_rows = 30  # Approximate visible rows in typical terminal
    widgets_per_visible_row = 1  # DataTable row is a single render unit
    total_widgets = visible_rows * widgets_per_visible_row
    print(f"  Estimated visible widgets: {total_widgets} (virtualized)")
    print(f"  [OLD: Would have been {len(rows) * 5} widgets with ItemRow]")

    return time.time()


def main() -> None:
    """Run all profiling phases."""
    print("\nTUI STARTUP PROFILER")
    print("=" * 60)

    overall_start = time.time()

    profile_imports()
    _, ctx = profile_context_creation()
    profile_data_loading(ctx)
    profile_widget_creation(ctx)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total profiling time: {time.time() - overall_start:.2f}s")
    print("\n  NOTE: This does NOT include Textual's layout/CSS/render time.")
    print("  The actual app.run() will take significantly longer due to")
    print("  Textual processing all widgets for layout and rendering.")
    print("\n  Use profile_tui_interactive.sh to measure full startup time.")


if __name__ == "__main__":
    main()

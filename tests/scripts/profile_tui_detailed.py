#!/usr/bin/env python3
"""Detailed TUI profiler that patches internal methods to measure timing.

Run from project root:
    timeout 30 uv run python tests/scripts/profile_tui_detailed.py

This script patches key TUI methods and runs the app, logging timing data.
Press 'q' to quit once the TUI loads, or it will timeout.

Output is written to /tmp/tui_profile_detailed.log
"""

from __future__ import annotations

import time

# Profiling data storage
PROFILE_LOG = "/tmp/tui_profile_detailed.log"
profile_data: dict[str, list[float]] = {}


def log(message: str) -> None:
    """Write to profile log."""
    with open(PROFILE_LOG, "a") as f:
        f.write(message + "\n")


def track_timing(name: str, elapsed: float) -> None:
    """Track timing for a method."""
    if name not in profile_data:
        profile_data[name] = []
    profile_data[name].append(elapsed)


def patch_methods() -> None:
    """Patch TUI methods to collect timing data."""
    from skill_installer.tui.data_manager import DataManager
    from skill_installer.tui.widgets.item_list import ItemDataTable

    # Patch DataManager.update_stale_sources
    original_update_stale = DataManager.update_stale_sources

    def timed_update_stale(self: DataManager) -> None:
        start = time.time()
        result = original_update_stale(self)
        track_timing("DataManager.update_stale_sources", time.time() - start)
        return result

    DataManager.update_stale_sources = timed_update_stale  # type: ignore[method-assign]

    # Patch DataManager.load_all_data
    original_load_all = DataManager.load_all_data

    def timed_load_all(self: DataManager) -> tuple:
        start = time.time()
        result = original_load_all(self)
        track_timing("DataManager.load_all_data", time.time() - start)
        return result

    DataManager.load_all_data = timed_load_all  # type: ignore[method-assign]

    # Patch ItemDataTable.set_items (DataTable-based, no per-row compose)
    original_set_items = ItemDataTable.set_items

    def timed_set_items(self: ItemDataTable, items: list) -> None:
        start = time.time()
        result = original_set_items(self, items)
        track_timing(f"ItemDataTable.set_items({len(items)} items)", time.time() - start)
        return result

    ItemDataTable.set_items = timed_set_items  # type: ignore[method-assign]


def main() -> None:
    """Run the profiled TUI."""
    # Clear log
    with open(PROFILE_LOG, "w") as f:
        f.write("TUI Detailed Profile\n")
        f.write("=" * 60 + "\n\n")

    log("Patching methods...")
    patch_methods()

    log("Creating context...")
    from skill_installer.context import create_context

    ctx = create_context()

    log("Creating app...")
    from skill_installer.tui.app import SkillInstallerApp

    app = SkillInstallerApp(
        registry_manager=ctx.registry,
        gitops=ctx.gitops,
        discovery=ctx.discovery,
        installer=ctx.installer,
    )

    log("Starting app.run()...\n")
    overall_start = time.time()

    try:
        app.run()
    except KeyboardInterrupt:
        pass

    overall_elapsed = time.time() - overall_start

    # Write summary
    log("\n" + "=" * 60)
    log("TIMING SUMMARY")
    log("=" * 60)

    for name, times in profile_data.items():
        total = sum(times)
        count = len(times)
        log(f"  {name}: {total:.2f}s ({count} calls)")

    log(f"\n  Total app.run(): {overall_elapsed:.2f}s")

    # Calculate unaccounted time
    accounted = sum(sum(times) for times in profile_data.values())
    unaccounted = overall_elapsed - accounted
    log(f"  Unaccounted (Textual layout/CSS/render): ~{unaccounted:.2f}s")

    log("\n" + "=" * 60)

    # Print to stdout
    print(f"\nProfile written to: {PROFILE_LOG}")
    print("\nQuick summary:")
    with open(PROFILE_LOG) as f:
        for line in f:
            if line.strip().startswith(("Total", "Unaccounted", "ItemDataTable", "DataManager")):
                print(line, end="")


if __name__ == "__main__":
    main()

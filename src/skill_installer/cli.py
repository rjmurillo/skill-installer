"""CLI commands using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    from skill_installer.context import AppContext
    from skill_installer.discovery import DiscoveredItem
    from skill_installer.registry import Source

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from skill_installer import __version__
from skill_installer.context import create_context
from skill_installer.gitops import GitOpsError
from skill_installer.tui import TUI, SkillInstallerApp

app = typer.Typer(
    name="skill-installer",
    help="Universal skill/agent installer for AI coding platforms",
    no_args_is_help=True,
)

source_app = typer.Typer(help="Manage source repositories")
config_app = typer.Typer(help="Configuration commands")

app.add_typer(source_app, name="source")
app.add_typer(config_app, name="config")

console = Console()
tui = TUI()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"skill-installer v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = False,
) -> None:
    """Universal skill/agent installer for AI coding platforms."""
    pass


# ============================================================================
# Source Commands
# ============================================================================


def _parse_platforms(platforms_arg: str | None) -> list[str]:
    """Parse comma-separated platform string into list."""
    if not platforms_arg:
        return ["claude", "vscode"]
    return [p.strip() for p in platforms_arg.split(",")]


def _register_source(
    ctx: AppContext, url: str, name: str | None, ref: str, platforms: list[str]
) -> Source:
    """Register source in registry."""
    source = ctx.registry.add_source(url, name, ref, platforms)
    tui.show_success(f"Added source '{source.name}'")
    return source


def _sync_source(ctx: AppContext, source: Source) -> None:
    """Clone or fetch source repository."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Cloning {source.name}...", total=None)
        ctx.gitops.clone_or_fetch(source.url, source.name, source.ref)
    ctx.registry.update_source_sync_time(source.name)


def _extract_license(ctx: AppContext, source: Source) -> None:
    """Extract and store license from source repository."""
    license_text = ctx.gitops.get_license(source.name)
    if license_text:
        ctx.registry.update_source_license(source.name, license_text)


@source_app.command("add")
def source_add(
    url: Annotated[str, typer.Argument(help="Repository URL")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Alias for the source")] = None,
    ref: Annotated[str, typer.Option("--ref", "-r", help="Branch or tag")] = "main",
    platforms: Annotated[
        str | None, typer.Option("--platforms", "-p", help="Target platforms (comma-separated)")
    ] = None,
    _context=None,
) -> None:
    """Add a source repository."""
    ctx = _context or create_context()
    platform_list = _parse_platforms(platforms)

    try:
        source = _register_source(ctx, url, name, ref, platform_list)
        _sync_source(ctx, source)
        _extract_license(ctx, source)
        tui.show_success(f"Cloned and synced '{source.name}'")
    except ValueError as e:
        tui.show_error(str(e))
        raise typer.Exit(1) from e
    except GitOpsError as e:
        tui.show_error(f"Git operation failed: {e}")
        raise typer.Exit(1) from e


@source_app.command("remove")
def source_remove(
    name: Annotated[str, typer.Argument(help="Source name")],
    _context=None,
) -> None:
    """Remove a source repository."""
    ctx = _context or create_context()

    if ctx.registry.remove_source(name):
        ctx.gitops.remove_cached(name)
        tui.show_success(f"Removed source '{name}'")
    else:
        tui.show_error(f"Source '{name}' not found")
        raise typer.Exit(1)


@source_app.command("list")
def source_list(
    _context=None,
) -> None:
    """List configured sources."""
    ctx = _context or create_context()
    sources = ctx.registry.list_sources()
    tui.show_sources(sources)


def _get_sources_to_update(ctx: AppContext, name: str | None) -> list[Source]:
    """Get list of sources to update.

    Args:
        ctx: Application context.
        name: Optional source name filter.

    Returns:
        List of sources to update.

    Raises:
        typer.Exit: If specified source not found.
    """
    sources = ctx.registry.list_sources()
    if not name:
        return sources
    filtered = [s for s in sources if s.name == name]
    if not filtered:
        tui.show_error(f"Source '{name}' not found")
        raise typer.Exit(1)
    return filtered


def _update_single_source(ctx: AppContext, source: Source) -> bool:
    """Update a single source repository.

    Args:
        ctx: Application context.
        source: Source to update.

    Returns:
        True if successful, False otherwise.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Updating {source.name}...", total=None)
            ctx.gitops.clone_or_fetch(source.url, source.name, source.ref)

        ctx.registry.update_source_sync_time(source.name)
        tui.show_success(f"Updated '{source.name}'")
        return True
    except GitOpsError as e:
        tui.show_error(f"Failed to update '{source.name}': {e}")
        return False


@source_app.command("update")
def source_update(
    name: Annotated[str | None, typer.Argument(help="Source name (all if not specified)")] = None,
    _context=None,
) -> None:
    """Update source repositories."""
    ctx = _context or create_context()
    sources = _get_sources_to_update(ctx, name)
    for source in sources:
        _update_single_source(ctx, source)


# ============================================================================
# Install Commands
# ============================================================================


def _parse_item_id(item: str) -> tuple[str, str | None, str]:
    """Parse item ID into components.

    Args:
        item: Item ID in format owner/repo/name or owner/repo/type/name.
              Source names contain slashes (e.g., rjmurillo/ai-agents).

    Returns:
        Tuple of (source_name, item_type, item_name).

    Raises:
        typer.Exit: If format is invalid.
    """
    parts = item.split("/")
    if len(parts) < 3:
        tui.show_error("Invalid item format. Use: owner/repo/name or owner/repo/type/name")
        raise typer.Exit(1)
    # Source name is always owner/repo (first two parts)
    source_name = f"{parts[0]}/{parts[1]}"
    item_name = parts[-1]
    # Type is present if we have 4 parts: owner/repo/type/name
    item_type = parts[2] if len(parts) == 4 else None
    return source_name, item_type, item_name


def _ensure_source_synced(ctx: AppContext, source: Source) -> Path:
    """Ensure source is synced and return repo path.

    Args:
        ctx: Application context.
        source: Source to sync.

    Returns:
        Path to repository.
    """
    repo_path = ctx.gitops.get_repo_path(source.name)
    if not repo_path.exists():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Syncing {source.name}...", total=None)
            ctx.gitops.clone_or_fetch(source.url, source.name, source.ref)
    return repo_path


def _find_item(
    ctx: AppContext,
    repo_path: Path,
    item_name: str,
    item_type: str | None,
    filter_platform: str | None,
) -> DiscoveredItem:
    """Find a discovered item matching criteria.

    Args:
        ctx: Application context.
        repo_path: Path to repository.
        item_name: Name of item to find.
        item_type: Optional type filter.
        filter_platform: Optional platform filter.

    Returns:
        Matching DiscoveredItem.

    Raises:
        typer.Exit: If no match found.
    """
    items = ctx.discovery.discover_all(repo_path, filter_platform)
    matches = [
        i for i in items if i.name == item_name and (item_type is None or i.item_type == item_type)
    ]
    if not matches:
        tui.show_error(f"Item '{item_name}' not found")
        raise typer.Exit(1)
    return matches[0]


def _install_to_platforms(
    ctx: AppContext,
    item: DiscoveredItem,
    source_name: str,
    target_platforms: list[str],
) -> None:
    """Install item to all target platforms.

    Args:
        ctx: Application context.
        item: Item to install.
        source_name: Source repository name.
        target_platforms: List of target platforms.
    """
    for target_platform in target_platforms:
        result = ctx.installer.install_item(item, source_name, target_platform)
        if result.success:
            tui.show_success(f"Installed {result.item_id} to {target_platform}")
        else:
            tui.show_error(f"Failed to install to {target_platform}: {result.error}")


@app.command()
def install(
    item: Annotated[str | None, typer.Argument(help="Item to install (source/type/name)")] = None,
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Target platforms (comma-separated)")
    ] = None,
    filter_platform: Annotated[
        str | None, typer.Option("--filter", "-f", help="Filter items by platform compatibility")
    ] = None,
    _context=None,
) -> None:
    """Install skills/agents from sources."""
    ctx = _context or create_context()
    platforms = _parse_platforms(platform)

    if not item:
        _interactive_install(ctx, platforms if platform else None, filter_platform)
        return

    source_name, item_type, item_name = _parse_item_id(item)
    source = ctx.registry.get_source(source_name)
    if not source:
        tui.show_error(f"Source '{source_name}' not found")
        raise typer.Exit(1)

    repo_path = _ensure_source_synced(ctx, source)
    discovered_item = _find_item(ctx, repo_path, item_name, item_type, filter_platform)
    target_platforms = platforms if platform else source.platforms
    _install_to_platforms(ctx, discovered_item, source_name, target_platforms)


def _interactive_install(
    ctx: AppContext,
    platforms: list[str] | None,
    filter_platform: str | None = None,
) -> None:
    """Interactive installation flow."""
    sources = ctx.registry.list_sources()
    if not sources:
        tui.show_warning("No sources configured. Add a source first.")
        tui.show_info("Run: skill-installer source add <url>")
        return

    # Select source
    source = tui.select_source(sources)
    if not source:
        return

    # Ensure source is synced
    repo_path = ctx.gitops.get_repo_path(source.name)
    if not repo_path.exists():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Syncing {source.name}...", total=None)
            ctx.gitops.clone_or_fetch(source.url, source.name, source.ref)

    # Discover items
    items = ctx.discovery.discover_all(repo_path, filter_platform)

    # Get installed items
    installed_items = ctx.registry.list_installed(source=source.name)
    installed_map: dict[str, list[str]] = {}
    for inst in installed_items:
        if inst.id not in installed_map:
            installed_map[inst.id] = []
        installed_map[inst.id].append(inst.platform)

    # Show items
    tui.show_items(items, installed_map, source.name)

    # Select item
    item = tui.select_item(items)
    if not item:
        return

    # Install to platforms
    target_platforms = platforms or source.platforms
    for target_platform in target_platforms:
        result = ctx.installer.install_item(item, source.name, target_platform)
        if result.success:
            tui.show_success(f"Installed {result.item_id} to {target_platform}")
        else:
            tui.show_error(f"Failed to install to {target_platform}: {result.error}")


@app.command()
def uninstall(
    item: Annotated[str, typer.Argument(help="Item to uninstall (source/type/name)")],
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Platform to uninstall from")
    ] = None,
    _context=None,
) -> None:
    """Uninstall a skill/agent."""
    ctx = _context or create_context()

    results = ctx.installer.uninstall_item(item, platform)

    if not results:
        tui.show_warning(f"Item '{item}' not found in installed items")
        return

    for result in results:
        if result.success:
            tui.show_success(f"Uninstalled {result.item_id} from {result.platform}")
        else:
            tui.show_error(f"Failed to uninstall from {result.platform}: {result.error}")


@app.command()
def status(
    _context=None,
) -> None:
    """Show installed items."""
    ctx = _context or create_context()
    items = ctx.registry.list_installed()
    tui.show_installed(items)


def _sync_all_sources(ctx: AppContext) -> None:
    """Sync all source repositories.

    Args:
        ctx: Application context.
    """
    for source in ctx.registry.list_sources():
        _update_single_source(ctx, source)


def _sync_installed_item(ctx: AppContext, item: any) -> None:
    """Check and update a single installed item.

    Args:
        ctx: Application context.
        item: Installed item to sync.
    """
    source = ctx.registry.get_source(item.source)
    if not source:
        tui.show_warning(f"Source '{item.source}' not found for {item.id}")
        return

    repo_path = ctx.gitops.get_repo_path(source.name)
    items = ctx.discovery.discover_all(repo_path, None)

    matches = [i for i in items if i.name == item.name and i.item_type == item.item_type]
    if not matches:
        tui.show_warning(f"Item {item.id} not found in source")
        return

    discovered = matches[0]
    if not ctx.installer.check_update_needed(discovered, source.name, item.platform):
        tui.show_info(f"{item.id} on {item.platform} is up to date")
        return

    result = ctx.installer.install_item(discovered, source.name, item.platform)
    if result.success:
        tui.show_success(f"Updated {item.id} on {item.platform}")
    else:
        tui.show_error(f"Failed to update {item.id}: {result.error}")


@app.command()
def sync(
    _context=None,
) -> None:
    """Sync all installed items from sources."""
    ctx = _context or create_context()
    _sync_all_sources(ctx)
    for item in ctx.registry.list_installed():
        _sync_installed_item(ctx, item)


# ============================================================================
# Config Commands
# ============================================================================


@config_app.command("show")
def config_show(
    _context=None,
) -> None:
    """Show current configuration."""
    ctx = _context or create_context()
    sources_registry = ctx.registry.load_sources()

    console.print("\n[bold]Configuration[/bold]")
    console.print(f"  Registry directory: {ctx.registry.registry_dir}")
    console.print(
        f"  Default platforms: {', '.join(sources_registry.defaults.get('targetPlatforms', []))}"
    )


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
    _context=None,
) -> None:
    """Set a configuration value."""
    ctx = _context or create_context()
    sources_registry = ctx.registry.load_sources()

    if key == "default-platforms":
        sources_registry.defaults["targetPlatforms"] = [p.strip() for p in value.split(",")]
        ctx.registry.save_sources(sources_registry)
        tui.show_success(f"Set {key} to {value}")
    else:
        tui.show_error(f"Unknown configuration key: {key}")
        raise typer.Exit(1)


# ============================================================================
# Interactive Mode
# ============================================================================


@app.command("interactive")
def interactive(
    _context=None,
) -> None:
    """Run in interactive TUI mode."""
    ctx = _context or create_context()

    tui_app = SkillInstallerApp(
        registry_manager=ctx.registry,
        gitops=ctx.gitops,
        discovery=ctx.discovery,
        installer=ctx.installer,
    )
    tui_app.run()


if __name__ == "__main__":
    app()

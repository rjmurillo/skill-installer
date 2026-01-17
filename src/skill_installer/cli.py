"""CLI commands using Typer."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from skill_installer import __version__
from skill_installer.discovery import Discovery
from skill_installer.gitops import GitOps, GitOpsError
from skill_installer.install import Installer
from skill_installer.registry import RegistryManager
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


@source_app.command("add")
def source_add(
    url: Annotated[str, typer.Argument(help="Repository URL")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Alias for the source")] = None,
    ref: Annotated[str, typer.Option("--ref", "-r", help="Branch or tag")] = "main",
    platforms: Annotated[
        str | None, typer.Option("--platforms", "-p", help="Target platforms (comma-separated)")
    ] = None,
) -> None:
    """Add a source repository."""
    registry = RegistryManager()
    gitops = GitOps()

    # Parse platforms
    platform_list = platforms.split(",") if platforms else ["claude", "vscode"]
    platform_list = [p.strip() for p in platform_list]

    try:
        source = registry.add_source(url, name, ref, platform_list)
        tui.show_success(f"Added source '{source.name}'")

        # Clone repository
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Cloning {source.name}...", total=None)
            gitops.clone_or_fetch(source.url, source.name, source.ref)

        registry.update_source_sync_time(source.name)
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
) -> None:
    """Remove a source repository."""
    registry = RegistryManager()
    gitops = GitOps()

    if registry.remove_source(name):
        gitops.remove_cached(name)
        tui.show_success(f"Removed source '{name}'")
    else:
        tui.show_error(f"Source '{name}' not found")
        raise typer.Exit(1)


@source_app.command("list")
def source_list() -> None:
    """List configured sources."""
    registry = RegistryManager()
    sources = registry.list_sources()
    tui.show_sources(sources)


@source_app.command("update")
def source_update(
    name: Annotated[str | None, typer.Argument(help="Source name (all if not specified)")] = None,
) -> None:
    """Update source repositories."""
    registry = RegistryManager()
    gitops = GitOps()

    sources = registry.list_sources()
    if name:
        sources = [s for s in sources if s.name == name]
        if not sources:
            tui.show_error(f"Source '{name}' not found")
            raise typer.Exit(1)

    for source in sources:
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Updating {source.name}...", total=None)
                gitops.clone_or_fetch(source.url, source.name, source.ref)

            registry.update_source_sync_time(source.name)
            tui.show_success(f"Updated '{source.name}'")
        except GitOpsError as e:
            tui.show_error(f"Failed to update '{source.name}': {e}")


# ============================================================================
# Install Commands
# ============================================================================


@app.command()
def install(
    item: Annotated[
        str | None, typer.Argument(help="Item to install (source/type/name)")
    ] = None,
    platform: Annotated[
        str | None, typer.Option("--platform", "-p", help="Target platforms (comma-separated)")
    ] = None,
) -> None:
    """Install skills/agents from sources."""
    registry = RegistryManager()
    gitops = GitOps()
    discovery = Discovery()
    installer = Installer(registry, gitops)

    # Parse platforms
    platforms = platform.split(",") if platform else None
    if platforms:
        platforms = [p.strip() for p in platforms]

    # Interactive mode if no item specified
    if not item:
        _interactive_install(registry, gitops, discovery, installer, platforms)
        return

    # Parse item ID (source/type/name or source/name)
    parts = item.split("/")
    if len(parts) < 2:
        tui.show_error("Invalid item format. Use: source/name or source/type/name")
        raise typer.Exit(1)

    source_name = parts[0]
    source = registry.get_source(source_name)
    if not source:
        tui.show_error(f"Source '{source_name}' not found")
        raise typer.Exit(1)

    # Ensure source is synced
    repo_path = gitops.get_repo_path(source_name)
    if not repo_path.exists():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Syncing {source_name}...", total=None)
            gitops.clone_or_fetch(source.url, source_name, source.ref)

    # Discover items
    items = discovery.discover_all(repo_path)

    # Find matching item
    item_name = parts[-1]
    item_type = parts[1] if len(parts) == 3 else None

    matches = [
        i for i in items
        if i.name == item_name and (item_type is None or i.item_type == item_type)
    ]

    if not matches:
        tui.show_error(f"Item '{item}' not found in source '{source_name}'")
        raise typer.Exit(1)

    discovered_item = matches[0]
    target_platforms = platforms or source.platforms

    for target_platform in target_platforms:
        result = installer.install_item(discovered_item, source_name, target_platform)
        if result.success:
            tui.show_success(f"Installed {result.item_id} to {target_platform}")
        else:
            tui.show_error(f"Failed to install to {target_platform}: {result.error}")


def _interactive_install(
    registry: RegistryManager,
    gitops: GitOps,
    discovery: Discovery,
    installer: Installer,
    platforms: list[str] | None,
) -> None:
    """Interactive installation flow."""
    sources = registry.list_sources()
    if not sources:
        tui.show_warning("No sources configured. Add a source first.")
        tui.show_info("Run: skill-installer source add <url>")
        return

    # Select source
    source = tui.select_source(sources)
    if not source:
        return

    # Ensure source is synced
    repo_path = gitops.get_repo_path(source.name)
    if not repo_path.exists():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Syncing {source.name}...", total=None)
            gitops.clone_or_fetch(source.url, source.name, source.ref)

    # Discover items
    items = discovery.discover_all(repo_path)

    # Get installed items
    installed_items = registry.list_installed(source=source.name)
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
        result = installer.install_item(item, source.name, target_platform)
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
) -> None:
    """Uninstall a skill/agent."""
    registry = RegistryManager()
    gitops = GitOps()
    installer = Installer(registry, gitops)

    results = installer.uninstall_item(item, platform)

    if not results:
        tui.show_warning(f"Item '{item}' not found in installed items")
        return

    for result in results:
        if result.success:
            tui.show_success(f"Uninstalled {result.item_id} from {result.platform}")
        else:
            tui.show_error(f"Failed to uninstall from {result.platform}: {result.error}")


@app.command()
def status() -> None:
    """Show installed items."""
    registry = RegistryManager()
    items = registry.list_installed()
    tui.show_installed(items)


@app.command()
def sync() -> None:
    """Sync all installed items from sources."""
    registry = RegistryManager()
    gitops = GitOps()
    discovery = Discovery()
    installer = Installer(registry, gitops)

    # Update all sources
    for source in registry.list_sources():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Updating {source.name}...", total=None)
                gitops.clone_or_fetch(source.url, source.name, source.ref)
            registry.update_source_sync_time(source.name)
        except GitOpsError as e:
            tui.show_error(f"Failed to update '{source.name}': {e}")
            continue

    # Check and update installed items
    for item in registry.list_installed():
        source = registry.get_source(item.source)
        if not source:
            tui.show_warning(f"Source '{item.source}' not found for {item.id}")
            continue

        repo_path = gitops.get_repo_path(source.name)
        items = discovery.discover_all(repo_path)

        # Find matching item
        matches = [i for i in items if i.name == item.name and i.item_type == item.item_type]
        if not matches:
            tui.show_warning(f"Item {item.id} not found in source")
            continue

        discovered = matches[0]
        if installer.check_update_needed(discovered, source.name, item.platform):
            result = installer.install_item(discovered, source.name, item.platform)
            if result.success:
                tui.show_success(f"Updated {item.id} on {item.platform}")
            else:
                tui.show_error(f"Failed to update {item.id}: {result.error}")
        else:
            tui.show_info(f"{item.id} on {item.platform} is up to date")


# ============================================================================
# Config Commands
# ============================================================================


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    registry = RegistryManager()
    sources_registry = registry.load_sources()

    console.print("\n[bold]Configuration[/bold]")
    console.print(f"  Registry directory: {registry.registry_dir}")
    console.print(f"  Default platforms: {', '.join(sources_registry.defaults.get('targetPlatforms', []))}")


@config_app.command("set")
def config_set(
    key: Annotated[str, typer.Argument(help="Configuration key")],
    value: Annotated[str, typer.Argument(help="Configuration value")],
) -> None:
    """Set a configuration value."""
    registry = RegistryManager()
    sources_registry = registry.load_sources()

    if key == "default-platforms":
        sources_registry.defaults["targetPlatforms"] = [p.strip() for p in value.split(",")]
        registry.save_sources(sources_registry)
        tui.show_success(f"Set {key} to {value}")
    else:
        tui.show_error(f"Unknown configuration key: {key}")
        raise typer.Exit(1)


# ============================================================================
# Interactive Mode
# ============================================================================


@app.command("interactive")
def interactive() -> None:
    """Run in interactive TUI mode."""
    registry = RegistryManager()
    gitops = GitOps()
    discovery = Discovery()
    installer = Installer(registry, gitops)

    tui_app = SkillInstallerApp(
        registry_manager=registry,
        gitops=gitops,
        discovery=discovery,
        installer=installer,
    )
    tui_app.run()


if __name__ == "__main__":
    app()

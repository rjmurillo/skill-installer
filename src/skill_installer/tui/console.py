"""Legacy TUI class for non-interactive CLI output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

if TYPE_CHECKING:
    from skill_installer.discovery import DiscoveredItem
    from skill_installer.registry import InstalledItem, Source


console = Console()


class TUI:
    """Text User Interface for skill-installer (non-interactive mode)."""

    def __init__(self) -> None:
        """Initialize TUI."""
        self.console = Console()

    def show_welcome(self) -> None:
        """Display welcome banner."""
        self.console.print(
            Panel(
                "[bold blue]Skill Installer[/bold blue] v0.1.0\n"
                "Universal skill/agent installer for AI coding platforms",
                title="Welcome",
                border_style="blue",
            )
        )

    def show_main_menu(self) -> str:
        """Display main menu and get selection.

        Returns:
            Selected option key.
        """
        self.console.print()
        self.console.print("[bold]Main Menu[/bold]")
        self.console.print("  [1] Add Source")
        self.console.print("  [2] Browse & Install")
        self.console.print("  [3] Status")
        self.console.print("  [4] Sync All")
        self.console.print("  [5] Settings")
        self.console.print("  [q] Quit")
        self.console.print()

        choice = Prompt.ask(
            "Select option",
            choices=["1", "2", "3", "4", "5", "q"],
            default="q",
        )
        return choice

    def prompt_source_url(self) -> str:
        """Prompt for source URL.

        Returns:
            Entered URL.
        """
        return Prompt.ask("Enter repository URL")

    def prompt_source_name(self, default: str) -> str:
        """Prompt for source name.

        Args:
            default: Default name derived from URL.

        Returns:
            Entered or default name.
        """
        return Prompt.ask("Source name", default=default)

    def prompt_source_ref(self) -> str:
        """Prompt for branch/tag reference.

        Returns:
            Entered reference.
        """
        return Prompt.ask("Branch/tag", default="main")

    def prompt_platforms(self) -> list[str]:
        """Prompt for target platforms.

        Returns:
            List of selected platforms.
        """
        platforms_str = Prompt.ask(
            "Target platforms (comma-separated)",
            default="claude,vscode",
        )
        return [p.strip() for p in platforms_str.split(",")]

    def confirm(self, message: str, default: bool = True) -> bool:
        """Show confirmation prompt.

        Args:
            message: Confirmation message.
            default: Default response.

        Returns:
            User's response.
        """
        return Confirm.ask(message, default=default)

    def show_sources(self, sources: list[Source]) -> None:
        """Display sources table.

        Args:
            sources: List of Source objects.
        """
        if not sources:
            self.console.print("[yellow]No sources configured[/yellow]")
            return

        table = Table(title="Configured Sources")
        table.add_column("Name", style="cyan")
        table.add_column("URL")
        table.add_column("Branch")
        table.add_column("Platforms")
        table.add_column("Last Sync")

        for source in sources:
            platforms = ", ".join(source.platforms)
            last_sync = source.last_sync.isoformat() if source.last_sync else "Never"
            table.add_row(
                source.name,
                source.url,
                source.ref,
                platforms,
                last_sync,
            )

        self.console.print(table)

    def show_items(
        self,
        items: list[DiscoveredItem],
        installed: dict[str, list[str]],
        source_name: str,
    ) -> None:
        """Display discovered items.

        Args:
            items: List of discovered items.
            installed: Dict mapping item IDs to installed platforms.
            source_name: Name of the source.
        """
        if not items:
            self.console.print(f"[yellow]No items found in {source_name}[/yellow]")
            return

        # Group by type
        agents = [i for i in items if i.item_type == "agent"]
        skills = [i for i in items if i.item_type == "skill"]
        commands = [i for i in items if i.item_type == "command"]

        self.console.print(f"\n[bold]Source: {source_name}[/bold]")

        for group_name, group_items in [
            ("AGENTS", agents),
            ("SKILLS", skills),
            ("COMMANDS", commands),
        ]:
            if group_items:
                self.console.print(f"\n[bold]{group_name}[/bold]")
                for item in group_items:
                    item_id = f"{source_name}/{item.item_type}/{item.name}"
                    platforms_installed = installed.get(item_id, [])

                    if platforms_installed:
                        status = f"[green]\u2713 {', '.join(platforms_installed)}[/green]"
                    else:
                        status = "[dim]\u25cb not installed[/dim]"

                    desc = f" - {item.description}" if item.description else ""
                    self.console.print(f"  {item.name}{desc} {status}")

    def show_installed(self, items: list[InstalledItem]) -> None:
        """Display installed items table.

        Args:
            items: List of installed items.
        """
        if not items:
            self.console.print("[yellow]No items installed[/yellow]")
            return

        table = Table(title="Installed Items")
        table.add_column("ID", style="cyan")
        table.add_column("Platform")
        table.add_column("Path")
        table.add_column("Installed")

        for item in items:
            table.add_row(
                item.id,
                item.platform,
                item.installed_path,
                item.installed_at.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)

    def show_success(self, message: str) -> None:
        """Show success message.

        Args:
            message: Success message.
        """
        self.console.print(f"[green]\u2713[/green] {message}")

    def show_error(self, message: str) -> None:
        """Show error message.

        Args:
            message: Error message.
        """
        self.console.print(f"[red]\u2717[/red] {message}")

    def show_warning(self, message: str) -> None:
        """Show warning message.

        Args:
            message: Warning message.
        """
        self.console.print(f"[yellow]![/yellow] {message}")

    def show_info(self, message: str) -> None:
        """Show info message.

        Args:
            message: Info message.
        """
        self.console.print(f"[blue]i[/blue] {message}")

    def select_item(self, items: list[DiscoveredItem]) -> DiscoveredItem | None:
        """Prompt user to select an item.

        Args:
            items: List of items to choose from.

        Returns:
            Selected item or None.
        """
        if not items:
            return None

        self.console.print("\nAvailable items:")
        for i, item in enumerate(items, 1):
            self.console.print(f"  [{i}] {item.name} ({item.item_type})")

        self.console.print("  [0] Cancel")

        choice = Prompt.ask("Select item", default="0")
        try:
            idx = int(choice)
        except ValueError:
            return None
        if 1 <= idx <= len(items):
            return items[idx - 1]
        return None

    def select_source(self, sources: list[Source]) -> Source | None:
        """Prompt user to select a source.

        Args:
            sources: List of sources to choose from.

        Returns:
            Selected source or None.
        """
        if not sources:
            return None

        self.console.print("\nAvailable sources:")
        for i, source in enumerate(sources, 1):
            self.console.print(f"  [{i}] {source.name} ({source.url})")

        self.console.print("  [0] Cancel")

        choice = Prompt.ask("Select source", default="0")
        try:
            idx = int(choice)
        except ValueError:
            return None
        if 1 <= idx <= len(sources):
            return sources[idx - 1]
        return None

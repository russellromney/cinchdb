"""Remote configuration management commands."""

import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

from cinchdb.cli.utils import get_config_with_data, validate_required_arg
from cinchdb.config import RemoteConfig

app = typer.Typer()
console = Console()


@app.command("add")
def add_remote(
    ctx: typer.Context,
    alias: Optional[str] = typer.Argument(None, help="Alias for the remote"),
    url: str = typer.Option(None, "--url", "-u", help="Remote API URL"),
    key: str = typer.Option(None, "--key", "-k", help="API key"),
):
    """Add a remote CinchDB instance configuration."""
    alias = validate_required_arg(alias, "alias", ctx)

    if not url:
        console.print("[red]❌ Error: --url is required[/red]")
        raise typer.Exit(1)

    if not key:
        console.print("[red]❌ Error: --key is required[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()

    # Check if alias already exists
    if alias in config_data.remotes:
        console.print(
            f"[yellow]⚠️  Remote '{alias}' already exists. Updating...[/yellow]"
        )

    # Add or update the remote
    config_data.remotes[alias] = RemoteConfig(url=url.rstrip("/"), key=key)
    config.save(config_data)

    console.print(f"[green]✓ Remote '{alias}' configured successfully[/green]")


@app.command("list")
def list_remotes():
    """List all configured remote instances."""
    config, config_data = get_config_with_data()

    if not config_data.remotes:
        console.print("[yellow]No remotes configured[/yellow]")
        return

    table = Table(title="Configured Remotes")
    table.add_column("Alias", style="cyan")
    table.add_column("URL", style="green")
    table.add_column("Active", style="yellow")

    for alias, remote in config_data.remotes.items():
        is_active = "✓" if alias == config_data.active_remote else ""
        table.add_row(alias, remote.url, is_active)

    console.print(table)


@app.command("remove")
def remove_remote(
    ctx: typer.Context,
    alias: Optional[str] = typer.Argument(None, help="Alias of the remote to remove"),
):
    """Remove a remote configuration."""
    alias = validate_required_arg(alias, "alias", ctx)

    config, config_data = get_config_with_data()

    if alias not in config_data.remotes:
        console.print(f"[red]❌ Remote '{alias}' not found[/red]")
        raise typer.Exit(1)

    # Remove the remote
    del config_data.remotes[alias]

    # If this was the active remote, clear it
    if config_data.active_remote == alias:
        config_data.active_remote = None

    config.save(config_data)
    console.print(f"[green]✓ Remote '{alias}' removed[/green]")


@app.command("use")
def use_remote(
    ctx: typer.Context,
    alias: Optional[str] = typer.Argument(None, help="Alias of the remote to use"),
):
    """Set the active remote instance."""
    alias = validate_required_arg(alias, "alias", ctx)

    config, config_data = get_config_with_data()

    if alias not in config_data.remotes:
        console.print(f"[red]❌ Remote '{alias}' not found[/red]")
        raise typer.Exit(1)

    config_data.active_remote = alias
    config.save(config_data)

    console.print(f"[green]✓ Now using remote '{alias}'[/green]")
    console.print(f"[dim]URL: {config_data.remotes[alias].url}[/dim]")


@app.command("clear")
def clear_remote():
    """Clear the active remote (switch back to local mode)."""
    config, config_data = get_config_with_data()

    if not config_data.active_remote:
        console.print("[yellow]No active remote set[/yellow]")
        return

    config_data.active_remote = None
    config.save(config_data)

    console.print("[green]✓ Cleared active remote. Now using local mode.[/green]")


@app.command("show")
def show_remote():
    """Show the currently active remote."""
    config, config_data = get_config_with_data()

    if not config_data.active_remote:
        console.print("[yellow]No active remote. Using local mode.[/yellow]")
        return

    alias = config_data.active_remote
    if alias not in config_data.remotes:
        console.print(
            f"[red]❌ Active remote '{alias}' not found in configuration[/red]"
        )
        return

    remote = config_data.remotes[alias]
    console.print(f"[green]Active remote:[/green] {alias}")
    console.print(f"[dim]URL: {remote.url}[/dim]")

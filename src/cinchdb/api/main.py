"""Main entry point for CinchDB API server."""

import uvicorn
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from cinchdb.api.auth import APIKeyManager
from cinchdb.core.path_utils import get_project_root


cli = typer.Typer(
    name="cinch-server",
    help="CinchDB API server",
    add_completion=False,
)
console = Console()


@cli.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-d", help="Project directory"
    ),
    create_key: bool = typer.Option(
        False, "--create-key", help="Create an API key on startup"
    ),
):
    """Start the CinchDB API server."""
    # Find project directory
    if project_dir:
        project_path = Path(project_dir)
    else:
        project_path = get_project_root(Path.cwd())

    if not project_path or not (project_path / ".cinchdb").exists():
        console.print("[red]❌ No CinchDB project found[/red]")
        console.print("[yellow]Run 'cinch init' to create a project[/yellow]")
        raise typer.Exit(1)

    console.print("[green]Starting CinchDB API server[/green]")
    console.print(f"Project: {project_path}")
    console.print(f"Host: {host}:{port}")

    # Create API key if requested
    if create_key:
        manager = APIKeyManager(project_path)
        api_key = manager.create_key("Initial API Key", permissions="write")
        console.print("\n[bold green]Created API key:[/bold green]")
        console.print(f"[yellow]Key: {api_key.key}[/yellow]")
        console.print(f"[yellow]Permissions: {api_key.permissions}[/yellow]")
        console.print("\n[bold]Save this key - it won't be shown again![/bold]\n")

    # Start server
    uvicorn.run(
        "cinchdb.api.app:app", host=host, port=port, reload=reload, log_level="info"
    )


@cli.command()
def create_key(
    name: str = typer.Argument(..., help="Name for the API key"),
    permissions: str = typer.Option(
        "read", "--permissions", "-p", help="Permissions (read/write)"
    ),
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-d", help="Project directory"
    ),
):
    """Create a new API key."""
    # Find project directory
    if project_dir:
        project_path = Path(project_dir)
    else:
        project_path = get_project_root(Path.cwd())

    if not project_path or not (project_path / ".cinchdb").exists():
        console.print("[red]❌ No CinchDB project found[/red]")
        raise typer.Exit(1)

    if permissions not in ["read", "write"]:
        console.print("[red]❌ Invalid permissions. Must be 'read' or 'write'[/red]")
        raise typer.Exit(1)

    manager = APIKeyManager(project_path)
    api_key = manager.create_key(name, permissions=permissions)

    console.print(f"[green]✅ Created API key '{name}'[/green]")
    console.print(f"[yellow]Key: {api_key.key}[/yellow]")
    console.print(f"[yellow]Permissions: {api_key.permissions}[/yellow]")
    console.print("\n[bold]Save this key - it won't be shown again![/bold]")


@cli.command()
def list_keys(
    project_dir: Optional[Path] = typer.Option(
        None, "--project-dir", "-d", help="Project directory"
    ),
):
    """List all API keys."""
    # Find project directory
    if project_dir:
        project_path = Path(project_dir)
    else:
        project_path = get_project_root(Path.cwd())

    if not project_path or not (project_path / ".cinchdb").exists():
        console.print("[red]❌ No CinchDB project found[/red]")
        raise typer.Exit(1)

    manager = APIKeyManager(project_path)
    keys = manager.list_keys()

    if not keys:
        console.print("[yellow]No API keys found[/yellow]")
        return

    console.print("\n[bold]API Keys:[/bold]")
    for key in keys:
        status = "[green]Active[/green]" if key.active else "[red]Revoked[/red]"
        branches = (
            f"Branches: {', '.join(key.branches)}" if key.branches else "All branches"
        )
        console.print(f"\n{key.name} - {status}")
        console.print(f"  Key: {key.key}")
        console.print(f"  Permissions: {key.permissions}")
        console.print(f"  {branches}")
        console.print(f"  Created: {key.created_at}")


if __name__ == "__main__":
    cli()

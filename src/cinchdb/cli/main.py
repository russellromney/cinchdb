"""Main CLI entry point for CinchDB."""

import typer
from typing import Optional
from pathlib import Path

# Import command groups
from cinchdb.cli.commands import (
    database,
    branch,
    tenant,
    table,
    column,
    view,
    codegen,
    remote,
)

app = typer.Typer(
    name="cinch",
    help="CinchDB - A Git-like SQLite database management system",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context):
    """
    CinchDB - A Git-like SQLite database management system
    """
    if ctx.invoked_subcommand is None:
        # No subcommand was invoked, show help
        print(ctx.get_help())
        raise typer.Exit(0)


# Add command groups
app.add_typer(database.app, name="db", help="Database management commands")
app.add_typer(branch.app, name="branch", help="Branch management commands")
app.add_typer(tenant.app, name="tenant", help="Tenant management commands")
app.add_typer(table.app, name="table", help="Table management commands")
app.add_typer(column.app, name="column", help="Column management commands")
app.add_typer(view.app, name="view", help="View management commands")
app.add_typer(codegen.app, name="codegen", help="Code generation commands")
app.add_typer(remote.app, name="remote", help="Remote instance management")


# Add query as direct command instead of subtyper
@app.command()
def query(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    format: Optional[str] = typer.Option(
        "table", "--format", "-f", help="Output format (table, json, csv)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Limit number of rows"
    ),
    local: bool = typer.Option(False, "--local", "-L", help="Force local connection"),
    remote: Optional[str] = typer.Option(
        None, "--remote", "-r", help="Use specific remote alias"
    ),
):
    """Execute a SQL query."""
    from cinchdb.cli.commands.query import execute_query

    execute_query(sql, tenant, format, limit, force_local=local, remote_alias=remote)


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        None, help="Directory to initialize project in (default: current directory)"
    ),
    database: Optional[str] = typer.Option(
        "main", "--database", "-d", help="Initial database name"
    ),
    branch: Optional[str] = typer.Option(
        "main", "--branch", "-b", help="Initial branch name"
    ),
):
    """Initialize a new CinchDB project."""
    from cinchdb.core.initializer import init_project

    project_path = path or Path.cwd()

    try:
        # Use the core initializer directly
        init_project(
            project_dir=project_path, database_name=database, branch_name=branch
        )
        typer.secho(
            f"✅ Initialized CinchDB project in {project_path}", fg=typer.colors.GREEN
        )
        typer.secho(f"   Database: {database}, Branch: {branch}", fg=typer.colors.CYAN)
    except FileExistsError:
        typer.secho(f"❌ Project already exists in {project_path}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def version():
    """Show CinchDB version."""
    from cinchdb import __version__

    typer.echo(f"CinchDB version {__version__}")


@app.command()
def status():
    """Show CinchDB status including configuration and environment variables."""
    from cinchdb.cli.utils import get_config_with_data, show_env_config
    from rich.console import Console

    console = Console()

    # Show project configuration
    try:
        config, config_data = get_config_with_data()

        console.print("\n[bold]CinchDB Status[/bold]")
        console.print(f"Project: {config.project_dir}")
        console.print(f"Active Database: {config_data.active_database}")
        console.print(f"Active Branch: {config_data.active_branch}")

        if config_data.active_remote:
            console.print(f"Active Remote: {config_data.active_remote}")
            if config_data.active_remote in config_data.remotes:
                remote = config_data.remotes[config_data.active_remote]
                console.print(f"  URL: {remote.url}")
                console.print(
                    f"  Key: ***{remote.key[-8:] if len(remote.key) > 8 else '*' * len(remote.key)}"
                )
        else:
            console.print("Active Remote: [dim]None (local mode)[/dim]")

        # Show environment variables
        show_env_config()

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

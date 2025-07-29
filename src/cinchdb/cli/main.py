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
):
    """Initialize a new CinchDB project."""
    from cinchdb.config import Config

    project_path = path or Path.cwd()

    try:
        config = Config(project_path)
        config.init_project()
        typer.secho(
            f"✅ Initialized CinchDB project in {project_path}", fg=typer.colors.GREEN
        )
    except FileExistsError:
        typer.secho(f"❌ Project already exists in {project_path}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def version():
    """Show CinchDB version."""
    from cinchdb import __version__

    typer.echo(f"CinchDB version {__version__}")


if __name__ == "__main__":
    app()

"""View management commands for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.managers.view import ViewModel
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.cli.utils import get_config_with_data, validate_required_arg

app = typer.Typer(help="View management commands", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command(name="list")
def list_views():
    """List all views in the current branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    view_mgr = ViewModel(config.project_dir, db_name, branch_name, "main")
    views = view_mgr.list_views()

    if not views:
        console.print("[yellow]No views found[/yellow]")
        return

    # Create a table
    table = RichTable(
        title=f"Views db={db_name} branch={branch_name}", title_justify="left"
    )
    table.add_column("Name", style="cyan")
    table.add_column("SQL Length", style="green")
    table.add_column("Created", style="yellow")

    for view in views:
        sql_length = len(view.sql_statement) if view.sql_statement else 0
        table.add_row(view.name, str(sql_length), "-")

    console.print(table)


@app.command()
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the view"),
    sql: Optional[str] = typer.Argument(None, help="SQL query for the view"),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Create a new view.

    Examples:
        cinch view create active_users "SELECT * FROM users WHERE is_active = 1"
        cinch view create user_stats "SELECT age, COUNT(*) as count FROM users GROUP BY age"
    """
    name = validate_required_arg(name, "name", ctx)
    sql = validate_required_arg(sql, "sql", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        view_mgr = ViewModel(config.project_dir, db_name, branch_name, "main")
        view_mgr.create_view(name, sql)
        console.print(f"[green]✅ Created view '{name}'[/green]")

        if apply:
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print("[green]✅ Applied changes to all tenants[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the view to update"),
    sql: Optional[str] = typer.Argument(None, help="New SQL query for the view"),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Update an existing view's SQL."""
    name = validate_required_arg(name, "name", ctx)
    sql = validate_required_arg(sql, "sql", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        view_mgr = ViewModel(config.project_dir, db_name, branch_name, "main")
        view_mgr.update_view(name, sql)
        console.print(f"[green]✅ Updated view '{name}'[/green]")

        if apply:
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print("[green]✅ Applied changes to all tenants[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the view to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Delete a view."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete view '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    try:
        view_mgr = ViewModel(config.project_dir, db_name, branch_name, "main")
        view_mgr.delete_view(name)
        console.print(f"[green]✅ Deleted view '{name}'[/green]")

        if apply:
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print("[green]✅ Applied changes to all tenants[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    ctx: typer.Context, name: Optional[str] = typer.Argument(None, help="View name")
):
    """Show detailed information about a view."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        view_mgr = ViewModel(config.project_dir, db_name, branch_name, "main")
        view = view_mgr.get_view(name)

        # Display info
        console.print(f"\n[bold]View: {view.name}[/bold]")
        console.print(f"Database: {db_name}")
        console.print(f"Branch: {branch_name}")
        console.print("Tenant: main")
        console.print("\n[bold]SQL:[/bold]")
        console.print(view.sql_statement)

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

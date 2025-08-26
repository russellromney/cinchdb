"""Database management commands for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.core.path_utils import list_databases
from cinchdb.cli.utils import (
    get_config_with_data,
    set_active_database,
    set_active_branch,
    validate_required_arg,
)
from cinchdb.utils.name_validator import validate_name, InvalidNameError

app = typer.Typer(help="Database management commands", invoke_without_command=True)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Database management commands."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(0)


@app.command(name="list")
def list_dbs():
    """List all databases in the project."""
    config, config_data = get_config_with_data()
    databases = list_databases(config.project_dir)

    if not databases:
        console.print("[yellow]No databases found[/yellow]")
        return

    # Create a table
    table = RichTable(title="Databases")
    table.add_column("Name", style="cyan")
    table.add_column("Active", style="green")
    table.add_column("Protected", style="yellow")

    current_db = config_data.active_database

    for db_name in databases:
        is_active = "✓" if db_name == current_db else ""
        is_protected = "✓" if db_name == "main" else ""
        table.add_row(db_name, is_active, is_protected)

    console.print(table)


@app.command()
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the database to create"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Database description"
    ),
    switch: bool = typer.Option(
        False, "--switch", "-s", help="Switch to the new database after creation"
    ),
):
    """Create a new database."""
    name = validate_required_arg(name, "name", ctx)

    # Validate database name
    try:
        validate_name(name, "database")
    except InvalidNameError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()

    # Use the ProjectInitializer to create the database properly
    from cinchdb.core.initializer import ProjectInitializer
    
    initializer = ProjectInitializer(config.project_dir)
    
    try:
        # Create database using initializer (lazy by default)
        initializer.init_database(name, description=description, lazy=True)
    except FileExistsError:
        console.print(f"[red]❌ Database '{name}' already exists[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✅ Created database '{name}'[/green]")

    if switch:
        set_active_database(config, name)
        console.print(f"[green]✅ Switched to database '{name}'[/green]")


@app.command()
def delete(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the database to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
):
    """Delete a database."""
    name = validate_required_arg(name, "name", ctx)
    if name == "main":
        console.print("[red]❌ Cannot delete the main database[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()
    
    # Check if database exists in metadata
    from cinchdb.infrastructure.metadata_db import MetadataDB
    
    with MetadataDB(config.project_dir) as metadata_db:
        db_info = metadata_db.get_database(name)
        if not db_info:
            console.print(f"[red]❌ Database '{name}' does not exist[/red]")
            raise typer.Exit(1)

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete database '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    # Delete the database from metadata and filesystem if materialized
    import shutil
    
    with MetadataDB(config.project_dir) as metadata_db:
        # Delete from metadata
        metadata_db.delete_database(db_info['id'])
    
    # Delete physical files if they exist
    db_path = config.project_dir / ".cinchdb" / "databases" / name
    if db_path.exists():
        shutil.rmtree(db_path)

    # If this was the active database, switch to main
    if config_data.active_database == name:
        set_active_database(config, "main")
        console.print("[yellow]Switched to main database[/yellow]")

    console.print(f"[green]✅ Deleted database '{name}'[/green]")


@app.command()
def info(
    name: Optional[str] = typer.Argument(None, help="Database name (default: current)"),
):
    """Show information about a database."""
    config, config_data = get_config_with_data()
    db_name = name or config_data.active_database

    # Check if database exists in metadata
    from cinchdb.infrastructure.metadata_db import MetadataDB
    
    with MetadataDB(config.project_dir) as metadata_db:
        db_info = metadata_db.get_database(db_name)
        if not db_info:
            console.print(f"[red]❌ Database '{db_name}' does not exist[/red]")
            raise typer.Exit(1)
        
        # Get branch info from metadata
        branches = metadata_db.list_branches(db_info['id'])
        branch_count = len(branches)

    # Get active branch
    active_branch = config_data.active_branch
    
    # Display info
    console.print(f"\n[bold]Database: {db_name}[/bold]")
    console.print(f"Status: {'Materialized' if db_info.get('materialized') else 'Lazy (not materialized)'}")
    console.print(f"Branches: {branch_count}")
    console.print(f"Active Branch: {active_branch}")
    console.print(f"Protected: {'Yes' if db_name == 'main' else 'No'}")
    
    # Show description if present
    if db_info.get('description'):
        console.print(f"Description: {db_info['description']}")

    # List branches
    if branch_count > 0:
        console.print("\n[bold]Branches:[/bold]")
        with MetadataDB(config.project_dir) as metadata_db:
            branches = metadata_db.list_branches(db_info['id'])
            for branch in sorted(branches, key=lambda x: x['name']):
                branch_name = branch['name']
                is_active = " (active)" if branch_name == active_branch else ""
                console.print(f"  - {branch_name}{is_active}")


@app.command()
def switch(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(
        None, help="Name of the database to switch to"
    ),
):
    """Switch to a different database."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()

    # Check if database exists in metadata
    from cinchdb.infrastructure.metadata_db import MetadataDB
    
    with MetadataDB(config.project_dir) as metadata_db:
        db_info = metadata_db.get_database(name)
        if not db_info:
            console.print(f"[red]❌ Database '{name}' does not exist[/red]")
            raise typer.Exit(1)

    # Switch
    set_active_database(config, name)
    set_active_branch(config, "main")  # Always switch to main branch

    console.print(f"[green]✅ Switched to database '{name}'[/green]")

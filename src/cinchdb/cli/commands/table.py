"""Table management commands for CinchDB CLI."""

import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.managers.table import TableManager
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column
from cinchdb.cli.utils import get_config_with_data

app = typer.Typer(help="Table management commands")
console = Console()


@app.command(name="list")
def list_tables(
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name")
):
    """List all tables in the current branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    table_mgr = TableManager(config.project_dir, db_name, branch_name, tenant)
    tables = table_mgr.list_tables()
    
    if not tables:
        console.print("[yellow]No tables found[/yellow]")
        return
    
    # Create a table
    table = RichTable(title=f"Tables in '{db_name}/{branch_name}'")
    table.add_column("Name", style="cyan")
    table.add_column("Columns", style="green")
    table.add_column("Created", style="yellow")
    
    for tbl in tables:
        # Count user-defined columns (exclude automatic ones)
        user_columns = len([c for c in tbl.columns if c.name not in ["id", "created_at", "updated_at"]])
        created = tbl.columns[0].name  # Placeholder - we don't track table creation time
        table.add_row(tbl.name, str(user_columns), "-")
    
    console.print(table)


@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the table"),
    columns: List[str] = typer.Argument(..., help="Column definitions (format: name:type[:nullable])"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    apply: bool = typer.Option(True, "--apply/--no-apply", help="Apply changes to all tenants")
):
    """Create a new table.
    
    Column format: name:type[:nullable]
    Types: TEXT, INTEGER, REAL, BLOB, NUMERIC
    
    Examples:
        cinch table create users name:TEXT email:TEXT:nullable age:INTEGER:nullable
        cinch table create posts title:TEXT content:TEXT published:INTEGER
    """
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    # Parse columns
    parsed_columns = []
    for col_def in columns:
        parts = col_def.split(":")
        if len(parts) < 2:
            console.print(f"[red]❌ Invalid column definition: '{col_def}'[/red]")
            console.print("[yellow]Format: name:type[:nullable][/yellow]")
            raise typer.Exit(1)
        
        col_name = parts[0]
        col_type = parts[1].upper()
        nullable = len(parts) > 2 and parts[2].lower() == "nullable"
        
        if col_type not in ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"]:
            console.print(f"[red]❌ Invalid type: '{col_type}'[/red]")
            console.print("[yellow]Valid types: TEXT, INTEGER, REAL, BLOB, NUMERIC[/yellow]")
            raise typer.Exit(1)
        
        parsed_columns.append(Column(name=col_name, type=col_type, nullable=nullable))
    
    try:
        table_mgr = TableManager(config.project_dir, db_name, branch_name, tenant)
        table = table_mgr.create_table(name, parsed_columns)
        console.print(f"[green]✅ Created table '{name}' with {len(parsed_columns)} columns[/green]")
        
        if apply and tenant == "main":
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print(f"[green]✅ Applied changes to all tenants[/green]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Name of the table to delete"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation"),
    apply: bool = typer.Option(True, "--apply/--no-apply", help="Apply changes to all tenants")
):
    """Delete a table."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete table '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        table_mgr = TableManager(config.project_dir, db_name, branch_name, tenant)
        table_mgr.delete_table(name)
        console.print(f"[green]✅ Deleted table '{name}'[/green]")
        
        if apply and tenant == "main":
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print(f"[green]✅ Applied changes to all tenants[/green]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def copy(
    source: str = typer.Argument(..., help="Source table name"),
    target: str = typer.Argument(..., help="Target table name"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    data: bool = typer.Option(True, "--data/--no-data", help="Copy data along with structure"),
    apply: bool = typer.Option(True, "--apply/--no-apply", help="Apply changes to all tenants")
):
    """Copy a table to a new table."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    try:
        table_mgr = TableManager(config.project_dir, db_name, branch_name, tenant)
        table = table_mgr.copy_table(source, target, copy_data=data)
        console.print(f"[green]✅ Copied table '{source}' to '{target}'[/green]")
        
        if apply and tenant == "main":
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print(f"[green]✅ Applied changes to all tenants[/green]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    name: str = typer.Argument(..., help="Table name"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name")
):
    """Show detailed information about a table."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch
    
    try:
        table_mgr = TableManager(config.project_dir, db_name, branch_name, tenant)
        table = table_mgr.get_table(name)
        
        # Display info
        console.print(f"\n[bold]Table: {table.name}[/bold]")
        console.print(f"Database: {db_name}")
        console.print(f"Branch: {branch_name}")
        console.print(f"Tenant: {tenant}")
        
        # Display columns
        console.print("\n[bold]Columns:[/bold]")
        col_table = RichTable()
        col_table.add_column("Name", style="cyan")
        col_table.add_column("Type", style="green")
        col_table.add_column("Nullable", style="yellow")
        col_table.add_column("Primary Key", style="red")
        col_table.add_column("Default", style="blue")
        
        for col in table.columns:
            nullable = "Yes" if col.nullable else "No"
            pk = "Yes" if col.primary_key else "No"
            default = col.default or "-"
            col_table.add_row(col.name, col.type, nullable, pk, default)
        
        console.print(col_table)
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
"""Index management commands for CinchDB CLI."""

import typer
from typing import List, Optional
from rich import print
from rich.table import Table
from rich.console import Console

from cinchdb.config import Config
from cinchdb.managers.index import IndexManager
from cinchdb.cli.utils import handle_cli_error

app = typer.Typer(help="Manage database indexes")
console = Console()


@app.command("create")
@handle_cli_error
def create_index(
    table: str = typer.Argument(..., help="Table name"),
    columns: List[str] = typer.Argument(..., help="Column names to index"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Index name"),
    unique: bool = typer.Option(False, "--unique", "-u", help="Create unique index"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Database name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name"),
):
    """Create an index on a table.
    
    Indexes are created at the branch level and apply to all tenants.
    
    Examples:
        cinch index create users email
        cinch index create orders user_id created_at --name idx_user_orders
        cinch index create products sku --unique
    """
    config = Config()
    project_config = config.load()
    
    # Use provided values or defaults
    database = database or project_config.active_database
    branch = branch or project_config.active_branch
    
    manager = IndexManager(config.base_dir, database, branch)
    
    try:
        index_name = manager.create_index(table, columns, name, unique)
        
        unique_text = "[green]UNIQUE[/green] " if unique else ""
        columns_text = ", ".join(columns)
        print(f"✓ Created {unique_text}index [bold cyan]{index_name}[/bold cyan] on {table}({columns_text})")
        
    except ValueError as e:
        print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("drop")
@handle_cli_error
def drop_index(
    name: str = typer.Argument(..., help="Index name"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Database name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name"),
):
    """Drop an index.
    
    Indexes are managed at the branch level.
    
    Example:
        cinch index drop idx_users_email
    """
    config = Config()
    project_config = config.load()
    
    # Use provided values or defaults
    database = database or project_config.active_database
    branch = branch or project_config.active_branch
    
    manager = IndexManager(config.base_dir, database, branch)
    
    try:
        manager.drop_index(name)
        print(f"✓ Dropped index [bold cyan]{name}[/bold cyan]")
    except ValueError as e:
        print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
@handle_cli_error
def list_indexes(
    table: Optional[str] = typer.Argument(None, help="Table name to filter indexes"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Database name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name"),
):
    """List indexes for a table or all tables.
    
    Indexes are managed at the branch level and apply to all tenants.
    
    Examples:
        cinch index list
        cinch index list users
    """
    config = Config()
    project_config = config.load()
    
    # Use provided values or defaults
    database = database or project_config.active_database
    branch = branch or project_config.active_branch
    
    manager = IndexManager(config.base_dir, database, branch)
    
    indexes = manager.list_indexes(table)
    
    if not indexes:
        if table:
            print(f"No indexes found for table [cyan]{table}[/cyan]")
        else:
            print("No indexes found")
        return
    
    # Create table for display
    table_obj = Table(title=f"Indexes{f' for {table}' if table else ''}")
    table_obj.add_column("Name", style="cyan")
    table_obj.add_column("Table", style="yellow")
    table_obj.add_column("Columns", style="green")
    table_obj.add_column("Unique", style="magenta")
    
    for idx in indexes:
        columns_str = ", ".join(idx["columns"])
        unique_str = "✓" if idx["unique"] else ""
        table_obj.add_row(
            idx["name"],
            idx["table"],
            columns_str,
            unique_str
        )
    
    console.print(table_obj)


@app.command("info")
@handle_cli_error
def index_info(
    name: str = typer.Argument(..., help="Index name"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Database name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name"),
):
    """Show detailed information about an index.
    
    Example:
        cinch index info idx_users_email
    """
    config = Config()
    project_config = config.load()
    
    # Use provided values or defaults
    database = database or project_config.active_database
    branch = branch or project_config.active_branch
    
    manager = IndexManager(config.base_dir, database, branch)
    
    try:
        info = manager.get_index_info(name)
        
        print(f"\nIndex: [bold cyan]{info['name']}[/bold cyan]")
        print(f"Table: [yellow]{info['table']}[/yellow]")
        print(f"Columns: [green]{', '.join(info['columns'])}[/green]")
        print(f"Unique: [magenta]{'Yes' if info['unique'] else 'No'}[/magenta]")
        print(f"Partial: [blue]{'Yes' if info.get('partial') else 'No'}[/blue]")
        
        if info.get('sql'):
            print("\nSQL Definition:")
            print(f"[dim]{info['sql']}[/dim]")
            
        if info.get('columns_info'):
            print("\nColumn Details:")
            for col in info['columns_info']:
                print(f"  - Position {col['position']}: {col['column_name']}")
                
    except ValueError as e:
        print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
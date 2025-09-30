"""Table management commands for CinchDB CLI."""

import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.managers.table import TableManager
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column, ForeignKeyRef
from cinchdb.cli.utils import get_config_with_data, validate_required_arg
from cinchdb.utils.type_utils import normalize_type

app = typer.Typer(help="Table management commands", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command(name="list")
def list_tables():
    """List all tables in the current branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    table_mgr = TableManager(ConnectionContext(project_root=config.project_dir, database=db_name, branch=branch_name))
    tables = table_mgr.list_tables()

    if not tables:
        console.print("[yellow]No tables found[/yellow]")
        return

    # Create a table
    table = RichTable(
        title=f"Tables db={db_name} branch={branch_name}", title_justify="left"
    )
    table.add_column("Name", style="cyan")
    table.add_column("Columns", style="green")
    table.add_column("Created", style="yellow")

    for tbl in tables:
        # Show total column count (including system columns: id, created_at, updated_at)
        total_columns = len(tbl.columns)
        table.add_row(tbl.name, str(total_columns), "-")

    console.print(table)


@app.command()
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the table"),
    columns: Optional[List[str]] = typer.Argument(
        None,
        help="Column definitions (format: name:type[:not_null][:fk=table[.column][:action]])",
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Create a new table.

    Column format: name:type[:not_null][:fk=table[.column][:action]]
    Types: TEXT, INTEGER, REAL, BLOB, NUMERIC, BOOLEAN
    Type aliases: int, bool, str, string, float, double, varchar, etc.
    FK Actions: CASCADE, SET NULL, RESTRICT, NO ACTION
    Note: Columns are nullable by default. Use :not_null to make them required.
    Note: Types are case-insensitive (text, TEXT, Text all work)

    Examples:
        cinch table create users name:text:not_null email:TEXT age:int
        cinch table create posts title:str:not_null content:TEXT active:bool author_id:TEXT:fk=users
        cinch table create comments content:TEXT post_id:TEXT:fk=posts.id:cascade
        cinch table create placeholder  # Creates table with only system columns
    """
    name = validate_required_arg(name, "name", ctx)
    # Allow empty columns list - table will have id, created_at, updated_at
    columns = columns or []
    if not columns:
        console.print("[yellow]Creating table with only system columns (id, created_at, updated_at)[/yellow]")
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    # Parse columns
    parsed_columns = []
    for col_def in columns:
        parts = col_def.split(":")
        if len(parts) < 2:
            console.print(f"[red]❌ Invalid column definition: '{col_def}'[/red]")
            console.print(
                "[yellow]Format: name:type[:nullable][:fk=table[.column][:action]][/yellow]"
            )
            raise typer.Exit(1)

        col_name = parts[0]
        try:
            col_type = normalize_type(parts[1])
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise typer.Exit(1)
        nullable = True  # Default to nullable (SQL standard)
        foreign_key = None

        # Parse additional parts
        for i in range(2, len(parts)):
            part = parts[i]
            if part.lower() == "nullable":
                nullable = True
            elif part.lower() in ["not_null", "notnull", "not_nullable"]:
                nullable = False
            elif part.startswith("fk="):
                # Parse foreign key definition
                fk_def = part[3:]  # Remove "fk=" prefix

                # Handle actions with spaces (e.g., "set null", "no action")
                # Check for known actions at the end
                fk_action = "RESTRICT"  # Default
                for action in ["cascade", "set null", "restrict", "no action"]:
                    if fk_def.lower().endswith("." + action):
                        fk_action = action.upper()
                        # Remove the action part from fk_def
                        fk_def = fk_def[: -len("." + action)]
                        break

                # Now split the remaining parts
                fk_parts = fk_def.split(".")

                if len(fk_parts) == 1:
                    # Just table name, column defaults to "id"
                    fk_table = fk_parts[0]
                    fk_column = "id"
                elif len(fk_parts) == 2:
                    # table.column format
                    fk_table = fk_parts[0]
                    fk_column = fk_parts[1]
                else:
                    console.print(
                        f"[red]❌ Invalid foreign key format: '{fk_def}'[/red]"
                    )
                    console.print("[yellow]Format: fk=table[.column][:action][/yellow]")
                    raise typer.Exit(1)

                foreign_key = ForeignKeyRef(
                    table=fk_table,
                    column=fk_column,
                    on_delete=fk_action,
                    on_update="RESTRICT",  # Default to RESTRICT for updates
                )

        # Type is already validated by normalize_type above
        parsed_columns.append(
            Column(
                name=col_name, type=col_type, nullable=nullable, foreign_key=foreign_key
            )
        )

    try:
        table_mgr = TableManager(ConnectionContext(project_root=config.project_dir, database=db_name, branch=branch_name))
        table_mgr.create_table(name, parsed_columns)
        console.print(
            f"[green]✅ Created table '{name}' with {len(parsed_columns)} columns[/green]"
        )

        # Changes are automatically applied to all tenants by the manager

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the table to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Delete a table."""
    name = validate_required_arg(name, "name", ctx)
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
        table_mgr = TableManager(ConnectionContext(project_root=config.project_dir, database=db_name, branch=branch_name))
        table_mgr.delete_table(name)
        console.print(f"[green]✅ Deleted table '{name}'[/green]")

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
def copy(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(None, help="Source table name"),
    target: Optional[str] = typer.Argument(None, help="Target table name"),
    data: bool = typer.Option(
        True, "--data/--no-data", help="Copy data along with structure"
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Copy a table to a new table."""
    source = validate_required_arg(source, "source", ctx)
    target = validate_required_arg(target, "target", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        table_mgr = TableManager(ConnectionContext(project_root=config.project_dir, database=db_name, branch=branch_name))
        table_mgr.copy_table(source, target, copy_data=data)
        console.print(f"[green]✅ Copied table '{source}' to '{target}'[/green]")

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
    ctx: typer.Context, name: Optional[str] = typer.Argument(None, help="Table name")
):
    """Show detailed information about a table."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        table_mgr = TableManager(ConnectionContext(project_root=config.project_dir, database=db_name, branch=branch_name))
        table = table_mgr.get_table(name)

        # Display info
        console.print(f"\n[bold]Table: {table.name}[/bold]")
        console.print(f"Database: {db_name}")
        console.print(f"Branch: {branch_name}")
        console.print("Tenant: main")

        # Display columns
        console.print("\n[bold]Columns:[/bold]")
        col_table = RichTable()
        col_table.add_column("Name", style="cyan")
        col_table.add_column("Type", style="green")
        col_table.add_column("Nullable", style="yellow")
        col_table.add_column("Unique", style="red")
        col_table.add_column("Default", style="blue")

        for col in table.columns:
            nullable = "Yes" if col.nullable else "No"
            unique = "Yes" if col.unique else "No"
            default = col.default or "-"
            col_table.add_row(col.name, col.type, nullable, unique, default)

        console.print(col_table)

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

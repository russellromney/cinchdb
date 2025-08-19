"""Column management commands for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.managers.column import ColumnManager
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column
from cinchdb.cli.utils import get_config_with_data, validate_required_arg

app = typer.Typer(help="Column management commands", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command(name="list")
def list_columns(
    ctx: typer.Context, table: Optional[str] = typer.Argument(None, help="Table name")
):
    """List all columns in a table."""
    table = validate_required_arg(table, "table", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")
        columns = column_mgr.list_columns(table)

        # Create a table
        col_table = RichTable(title=f"Columns in '{table}'")
        col_table.add_column("Name", style="cyan")
        col_table.add_column("Type", style="green")
        col_table.add_column("Nullable", style="yellow")
        col_table.add_column("Primary Key", style="red")
        col_table.add_column("Default", style="blue")

        for col in columns:
            nullable = "Yes" if col.nullable else "No"
            pk = "Yes" if col.primary_key else "No"
            default = col.default or "-"
            col_table.add_row(col.name, col.type, nullable, pk, default)

        console.print(col_table)

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def add(
    ctx: typer.Context,
    table: Optional[str] = typer.Argument(None, help="Table name"),
    name: Optional[str] = typer.Argument(None, help="Column name"),
    type: Optional[str] = typer.Argument(
        None, help="Column type (TEXT, INTEGER, REAL, BLOB, NUMERIC)"
    ),
    nullable: bool = typer.Option(
        True, "--nullable/--not-null", help="Allow NULL values"
    ),
    default: Optional[str] = typer.Option(
        None, "--default", "-d", help="Default value"
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Add a new column to a table."""
    table = validate_required_arg(table, "table", ctx)
    name = validate_required_arg(name, "name", ctx)
    type = validate_required_arg(type, "type", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    # Validate type
    type = type.upper()
    if type not in ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"]:
        console.print(f"[red]❌ Invalid type: '{type}'[/red]")
        console.print(
            "[yellow]Valid types: TEXT, INTEGER, REAL, BLOB, NUMERIC[/yellow]"
        )
        raise typer.Exit(1)

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")
        column = Column(name=name, type=type, nullable=nullable, default=default)
        column_mgr.add_column(table, column)

        console.print(f"[green]✅ Added column '{name}' to table '{table}'[/green]")

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
def drop(
    ctx: typer.Context,
    table: Optional[str] = typer.Argument(None, help="Table name"),
    name: Optional[str] = typer.Argument(None, help="Column name to drop"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Drop a column from a table."""
    table = validate_required_arg(table, "table", ctx)
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    # Confirmation
    if not force:
        confirm = typer.confirm(
            f"Are you sure you want to drop column '{name}' from table '{table}'?"
        )
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")
        column_mgr.drop_column(table, name)

        console.print(f"[green]✅ Dropped column '{name}' from table '{table}'[/green]")

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
def rename(
    ctx: typer.Context,
    table: Optional[str] = typer.Argument(None, help="Table name"),
    old_name: Optional[str] = typer.Argument(None, help="Current column name"),
    new_name: Optional[str] = typer.Argument(None, help="New column name"),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Rename a column in a table."""
    table = validate_required_arg(table, "table", ctx)
    old_name = validate_required_arg(old_name, "old_name", ctx)
    new_name = validate_required_arg(new_name, "new_name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")
        column_mgr.rename_column(table, old_name, new_name)

        console.print(
            f"[green]✅ Renamed column '{old_name}' to '{new_name}' in table '{table}'[/green]"
        )

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
    ctx: typer.Context,
    table: Optional[str] = typer.Argument(None, help="Table name"),
    name: Optional[str] = typer.Argument(None, help="Column name"),
):
    """Show detailed information about a column."""
    table = validate_required_arg(table, "table", ctx)
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")
        column = column_mgr.get_column_info(table, name)

        # Display info
        console.print(f"\n[bold]Column: {column.name}[/bold]")
        console.print(f"Table: {table}")
        console.print(f"Type: {column.type}")
        console.print(f"Nullable: {'Yes' if column.nullable else 'No'}")
        console.print(f"Primary Key: {'Yes' if column.primary_key else 'No'}")
        console.print(f"Unique: {'Yes' if column.unique else 'No'}")
        console.print(f"Default: {column.default or 'None'}")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command(name="alter-nullable")
def alter_nullable(
    ctx: typer.Context,
    table: Optional[str] = typer.Argument(None, help="Table name"),
    column: Optional[str] = typer.Argument(None, help="Column name"),
    nullable: bool = typer.Option(
        None, "--nullable/--not-nullable", help="Make column nullable or NOT NULL"
    ),
    fill_value: Optional[str] = typer.Option(
        None,
        "--fill-value",
        "-f",
        help="Value to use for NULL values when making NOT NULL",
    ),
    apply: bool = typer.Option(
        True, "--apply/--no-apply", help="Apply changes to all tenants"
    ),
):
    """Change the nullable constraint on a column."""
    table = validate_required_arg(table, "table", ctx)
    column = validate_required_arg(column, "column", ctx)

    # Validate nullable flag was provided
    if nullable is None:
        console.print(ctx.get_help())
        console.print(
            "\n[red]❌ Error: Must specify either --nullable or --not-nullable[/red]"
        )
        raise typer.Exit(1)

    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        column_mgr = ColumnManager(config.project_dir, db_name, branch_name, "main")

        # Check if column has NULLs when making NOT NULL
        if not nullable and fill_value is None:
            # Get column info to check current state
            col_info = column_mgr.get_column_info(table, column)
            if col_info.nullable:
                # Check for NULL values
                from cinchdb.core.connection import DatabaseConnection
                from cinchdb.core.path_utils import get_tenant_db_path

                db_path = get_tenant_db_path(
                    config.project_dir, db_name, branch_name, "main"
                )
                with DatabaseConnection(db_path) as conn:
                    cursor = conn.execute(
                        f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"
                    )
                    null_count = cursor.fetchone()[0]

                    if null_count > 0:
                        console.print(
                            f"[yellow]Column '{column}' has {null_count} NULL values.[/yellow]"
                        )
                        fill_value = typer.prompt("Provide a fill value")

        # Convert fill_value to appropriate type
        if fill_value is not None:
            # Try to interpret the value
            if fill_value.lower() == "null":
                fill_value = None
            elif fill_value.isdigit():
                fill_value = int(fill_value)
            elif fill_value.replace(".", "", 1).isdigit():
                fill_value = float(fill_value)
            # Otherwise keep as string

        column_mgr.alter_column_nullable(table, column, nullable, fill_value)

        if nullable:
            console.print(
                f"[green]✅ Made column '{column}' nullable in table '{table}'[/green]"
            )
        else:
            console.print(
                f"[green]✅ Made column '{column}' NOT NULL in table '{table}'[/green]"
            )

        if apply:
            # Apply to all tenants
            applier = ChangeApplier(config.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
            if applied > 0:
                console.print("[green]✅ Applied changes to all tenants[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

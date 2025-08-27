"""Data manipulation commands for CinchDB CLI."""

import typer
from typing import Optional
from rich.console import Console

from cinchdb.cli.utils import get_config_with_data

app = typer.Typer(help="Data manipulation commands", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def delete(
    table_name: str = typer.Argument(..., help="Name of table to delete from"),
    where: str = typer.Option(..., "--where", "-w", help="Filter conditions (e.g., 'status=inactive' or 'age__gt=65' or 'id__in=1,2,3')"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete records from a table based on filter criteria.
    
    Examples:
        cinch data delete users --where "status=inactive" 
        cinch data delete items --where "price__gt=100"
        cinch data delete logs --where "id__in=1,2,3,4,5"
    """
    from cinchdb.core.database import CinchDB
    
    config, config_data = get_config_with_data()
    
    # Parse conditions into filter dict
    try:
        filters = _parse_conditions(where)
    except ValueError as e:
        console.print(f"[red]❌ Invalid conditions format: {e}[/red]")
        raise typer.Exit(1)

    if not confirm:
        console.print(f"[yellow]⚠️  About to delete records from table '{table_name}' where: {where}[/yellow]")
        console.print(f"[yellow]   Tenant: {tenant}[/yellow]")
        confirm_delete = typer.confirm("Are you sure you want to proceed?")
        if not confirm_delete:
            console.print("Operation cancelled.")
            raise typer.Exit(0)

    try:
        db = CinchDB(config_data.active_database, tenant=tenant, project_dir=config.project_dir)
        
        console.print(f"[yellow]🗑️  Deleting records from '{table_name}'...[/yellow]")
        
        deleted_count = db.delete_where(table_name, **filters)
        
        if deleted_count > 0:
            console.print(f"[green]✅ Deleted {deleted_count} record(s) from '{table_name}'[/green]")
        else:
            console.print(f"[blue]ℹ️  No records matched the criteria in '{table_name}'[/blue]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    table_name: str = typer.Argument(..., help="Name of table to update"),
    set_data: str = typer.Option(..., "--set", "-s", help="Data to update (e.g., 'status=active,priority=high')"),
    where: str = typer.Option(..., "--where", "-w", help="Filter conditions (e.g., 'status=inactive' or 'age__gt=65')"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Update records in a table based on filter criteria.
    
    Examples:
        cinch data update users --set "status=active" --where "status=inactive"
        cinch data update items --set "price=99.99,category=sale" --where "price__gt=100"
    """
    from cinchdb.core.database import CinchDB
    
    config, config_data = get_config_with_data()
    
    # Parse conditions and data
    try:
        filters = _parse_conditions(where)
        update_data = _parse_set_data(set_data)
    except ValueError as e:
        console.print(f"[red]❌ Invalid format: {e}[/red]")
        raise typer.Exit(1)

    if not confirm:
        console.print(f"[yellow]⚠️  About to update records in table '{table_name}'[/yellow]")
        console.print(f"[yellow]   Set: {set_data}[/yellow]")
        console.print(f"[yellow]   Where: {where}[/yellow]")
        console.print(f"[yellow]   Tenant: {tenant}[/yellow]")
        confirm_update = typer.confirm("Are you sure you want to proceed?")
        if not confirm_update:
            console.print("Operation cancelled.")
            raise typer.Exit(0)

    try:
        db = CinchDB(config_data.active_database, tenant=tenant, project_dir=config.project_dir)
        
        console.print(f"[yellow]📝 Updating records in '{table_name}'...[/yellow]")
        
        updated_count = db.update_where(table_name, update_data, **filters)
        
        if updated_count > 0:
            console.print(f"[green]✅ Updated {updated_count} record(s) in '{table_name}'[/green]")
        else:
            console.print(f"[blue]ℹ️  No records matched the criteria in '{table_name}'[/blue]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def bulk_update(
    table_name: str = typer.Argument(..., help="Name of table to update"),
    data: str = typer.Option(..., "--data", "-d", help="JSON array of update objects with 'id' field"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Update multiple records in a table using JSON data.
    
    Examples:
        cinch data bulk-update users --data '[{"id":"123","name":"John"},{"id":"456","status":"active"}]'
        cinch data bulk-update items --data '[{"id":"1","price":99.99},{"id":"2","category":"sale"}]'
    """
    import json
    from cinchdb.core.database import CinchDB
    
    config, config_data = get_config_with_data()
    
    # Parse JSON data
    try:
        updates = json.loads(data)
        if not isinstance(updates, list):
            updates = [updates]
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ Invalid JSON format: {e}[/red]")
        raise typer.Exit(1)

    if not confirm:
        console.print(f"[yellow]⚠️  About to update {len(updates)} record(s) in table '{table_name}'[/yellow]")
        console.print(f"[yellow]   Tenant: {tenant}[/yellow]")
        console.print(f"[yellow]   Data preview: {json.dumps(updates[:3], indent=2)}{'...' if len(updates) > 3 else ''}[/yellow]")
        confirm_update = typer.confirm("Are you sure you want to proceed?")
        if not confirm_update:
            console.print("Operation cancelled.")
            raise typer.Exit(0)

    try:
        db = CinchDB(config_data.active_database, tenant=tenant, project_dir=config.project_dir)
        
        console.print(f"[yellow]📝 Updating {len(updates)} record(s) in '{table_name}'...[/yellow]")
        
        result = db.update(table_name, *updates)
        updated_count = len(updates)
        
        console.print(f"[green]✅ Updated {updated_count} record(s) in '{table_name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def bulk_delete(
    table_name: str = typer.Argument(..., help="Name of table to delete from"),
    ids: str = typer.Option(..., "--ids", "-i", help="Comma-separated list of IDs or JSON array"),
    tenant: Optional[str] = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """Delete multiple records from a table by IDs.
    
    Examples:
        cinch data bulk-delete users --ids "123,456,789"
        cinch data bulk-delete items --ids '["abc","def","ghi"]'
    """
    import json
    from cinchdb.core.database import CinchDB
    
    config, config_data = get_config_with_data()
    
    # Parse IDs - try JSON first, then comma-separated
    try:
        id_list = json.loads(ids)
        if not isinstance(id_list, list):
            id_list = [str(id_list)]
    except json.JSONDecodeError:
        # Try comma-separated format
        id_list = [id_str.strip() for id_str in ids.split(",") if id_str.strip()]

    if not id_list:
        console.print("[red]❌ No valid IDs provided[/red]")
        raise typer.Exit(1)

    if not confirm:
        console.print(f"[yellow]⚠️  About to delete {len(id_list)} record(s) from table '{table_name}'[/yellow]")
        console.print(f"[yellow]   Tenant: {tenant}[/yellow]")
        console.print(f"[yellow]   IDs: {id_list[:5]}{'...' if len(id_list) > 5 else ''}[/yellow]")
        confirm_delete = typer.confirm("Are you sure you want to proceed?")
        if not confirm_delete:
            console.print("Operation cancelled.")
            raise typer.Exit(0)

    try:
        db = CinchDB(config_data.active_database, tenant=tenant, project_dir=config.project_dir)
        
        console.print(f"[yellow]🗑️  Deleting {len(id_list)} record(s) from '{table_name}'...[/yellow]")
        
        deleted_count = db.delete(table_name, *id_list)
        
        console.print(f"[green]✅ Deleted {deleted_count} record(s) from '{table_name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


def _parse_conditions(conditions_str: str) -> dict:
    """Parse condition string into filter dictionary."""
    filters = {}
    
    # Split by commas but handle quotes
    parts = []
    current_part = ""
    in_quotes = False
    
    for char in conditions_str:
        if char == '"' and not in_quotes:
            in_quotes = True
            current_part += char
        elif char == '"' and in_quotes:
            in_quotes = False
            current_part += char
        elif char == ',' and not in_quotes:
            if current_part.strip():
                parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
    
    if current_part.strip():
        parts.append(current_part.strip())
    
    for part in parts:
        if '=' not in part:
            raise ValueError(f"Invalid condition format: '{part}'. Expected format: 'column=value' or 'column__operator=value'")
        
        key, value_str = part.split('=', 1)
        key = key.strip()
        value_str = value_str.strip()
        
        # Remove quotes if present
        if value_str.startswith('"') and value_str.endswith('"'):
            value_str = value_str[1:-1]
        
        # Handle special cases
        if '__in' in key:
            # Convert comma-separated values to list
            value = [v.strip() for v in value_str.split(',')]
            # Try to convert to numbers if possible
            try:
                value = [int(v) for v in value]
            except ValueError:
                try:
                    value = [float(v) for v in value]
                except ValueError:
                    pass  # Keep as strings
        else:
            # Try to convert to appropriate type
            value = _convert_value(value_str)
        
        filters[key] = value
    
    return filters


def _parse_set_data(set_str: str) -> dict:
    """Parse set string into update data dictionary."""
    data = {}
    
    # Split by commas but handle quotes (similar to conditions)
    parts = []
    current_part = ""
    in_quotes = False
    
    for char in set_str:
        if char == '"' and not in_quotes:
            in_quotes = True
            current_part += char
        elif char == '"' and in_quotes:
            in_quotes = False
            current_part += char
        elif char == ',' and not in_quotes:
            if current_part.strip():
                parts.append(current_part.strip())
            current_part = ""
        else:
            current_part += char
    
    if current_part.strip():
        parts.append(current_part.strip())
    
    for part in parts:
        if '=' not in part:
            raise ValueError(f"Invalid set format: '{part}'. Expected format: 'column=value'")
        
        key, value_str = part.split('=', 1)
        key = key.strip()
        value_str = value_str.strip()
        
        # Remove quotes if present
        if value_str.startswith('"') and value_str.endswith('"'):
            value_str = value_str[1:-1]
        
        data[key] = _convert_value(value_str)
    
    return data


def _convert_value(value_str: str):
    """Convert string value to appropriate Python type."""
    # Try integer
    try:
        return int(value_str)
    except ValueError:
        pass
    
    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # Try boolean
    if value_str.lower() in ('true', 'false'):
        return value_str.lower() == 'true'
    
    # Default to string
    return value_str
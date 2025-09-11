"""Tenant management commands for CinchDB CLI."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root
from cinchdb.managers.tenant import TenantManager
from cinchdb.cli.utils import get_config_with_data, validate_required_arg
from cinchdb.utils.name_validator import validate_name, InvalidNameError

app = typer.Typer(help="Tenant management commands", invoke_without_command=True)
console = Console()


@app.callback()
def callback(ctx: typer.Context):
    """Show help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


def get_config() -> Config:
    """Get config from current directory."""
    project_root = get_project_root(Path.cwd())
    if not project_root:
        console.print("[red]❌ Not in a CinchDB project directory[/red]")
        raise typer.Exit(1)
    return Config(project_root)


@app.command(name="list")
def list_tenants():
    """List all tenants in the current branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
    tenants = tenant_mgr.list_tenants()

    if not tenants:
        console.print("[yellow]No tenants found[/yellow]")
        return

    # Create a table
    table = RichTable(
        title=f"Tenants db={db_name} branch={branch_name}", title_justify="left"
    )
    table.add_column("Name", style="cyan")
    table.add_column("Protected", style="yellow")

    for tenant in tenants:
        is_protected = "✓" if tenant.is_main else ""
        table.add_row(tenant.name, is_protected)

    console.print(table)


@app.command()
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the tenant to create"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Tenant description"
    ),
    encrypt: bool = typer.Option(
        False, "--encrypt", help="Create encrypted tenant database"
    ),
    key: Optional[str] = typer.Option(
        None, "--key", help="Encryption key for encrypted tenant (required with --encrypt)"
    ),
):
    """Create a new tenant."""
    name = validate_required_arg(name, "name", ctx)

    # Validate encryption parameters
    if encrypt and not key:
        console.print("[red]❌ --key is required when using --encrypt[/red]")
        raise typer.Exit(1)
    
    if key and not encrypt:
        console.print("[red]❌ --encrypt is required when using --key[/red]")
        raise typer.Exit(1)

    # Validate tenant name
    try:
        validate_name(name, "tenant")
    except InvalidNameError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        tenant_mgr.create_tenant(name, description, encrypt=encrypt, encryption_key=key)
        
        if encrypt:
            console.print(f"[green]✅ Created encrypted tenant '{name}'[/green]")
            console.print("[yellow]Note: Keep your encryption key secure - losing it means losing your data[/yellow]")
        else:
            console.print(f"[green]✅ Created tenant '{name}'[/green]")
        console.print("[yellow]Note: Tenant has same schema as main tenant[/yellow]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the tenant to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
):
    """Delete a tenant."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    if name == "main":
        console.print("[red]❌ Cannot delete the main tenant[/red]")
        raise typer.Exit(1)

    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete tenant '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        tenant_mgr.delete_tenant(name)
        console.print(f"[green]✅ Deleted tenant '{name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def copy(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(None, help="Source tenant name"),
    target: Optional[str] = typer.Argument(None, help="Target tenant name"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Target tenant description"
    ),
):
    """Copy a tenant to a new tenant (including data)."""
    source = validate_required_arg(source, "source", ctx)
    target = validate_required_arg(target, "target", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        tenant_mgr.copy_tenant(source, target, description)
        console.print(f"[green]✅ Copied tenant '{source}' to '{target}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def rename(
    ctx: typer.Context,
    old_name: Optional[str] = typer.Argument(None, help="Current tenant name"),
    new_name: Optional[str] = typer.Argument(None, help="New tenant name"),
):
    """Rename a tenant."""
    old_name = validate_required_arg(old_name, "old_name", ctx)
    new_name = validate_required_arg(new_name, "new_name", ctx)

    # Validate new tenant name
    try:
        validate_name(new_name, "tenant")
    except InvalidNameError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    if old_name == "main":
        console.print("[red]❌ Cannot rename the main tenant[/red]")
        raise typer.Exit(1)

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        tenant_mgr.rename_tenant(old_name, new_name)
        console.print(f"[green]✅ Renamed tenant '{old_name}' to '{new_name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def vacuum(
    tenant_name: str = typer.Argument(..., help="Name of tenant to vacuum"),
):
    """Run VACUUM operation on a tenant to optimize storage and performance.
    
    VACUUM reclaims space from deleted records, defragments the database file,
    and can improve query performance. This is especially useful after
    deleting large amounts of data.
    
    Examples:
        cinch tenant vacuum main
        cinch tenant vacuum store_east
    """
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        
        console.print(f"[yellow]🔧 Starting VACUUM operation on tenant '{tenant_name}'...[/yellow]")
        
        result = tenant_mgr.vacuum_tenant(tenant_name)
        
        if result['success']:
            console.print("[green]✅ VACUUM completed successfully[/green]")
            console.print(f"  Tenant: {result['tenant']}")
            console.print(f"  Size before: {result['size_before']:,} bytes ({result['size_before'] / (1024*1024):.2f} MB)")
            console.print(f"  Size after: {result['size_after']:,} bytes ({result['size_after'] / (1024*1024):.2f} MB)")
            console.print(f"  Space reclaimed: {result['space_reclaimed']:,} bytes ({result['space_reclaimed_mb']} MB)")
            console.print(f"  Duration: {result['duration_seconds']} seconds")
            
            if result['space_reclaimed'] > 0:
                percent_saved = (result['space_reclaimed'] / result['size_before']) * 100
                console.print(f"  [green]💾 Saved {percent_saved:.1f}% of space[/green]")
            else:
                console.print("  [blue]ℹ️  No space to reclaim (database was already optimized)[/blue]")
        else:
            console.print(f"[red]❌ VACUUM failed: {result.get('error', 'Unknown error')}[/red]")
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command(name="rotate-key")
def rotate_key(
    tenant_name: str = typer.Argument(..., help="Name of the tenant to rotate encryption key for"),
):
    """Rotate encryption key for a tenant (requires plugged extension)."""
    validate_required_arg(tenant_name, "tenant name")
    
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = config_data.active_branch

    try:
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        
        console.print(f"[yellow]🔐 Rotating encryption key for tenant '{tenant_name}'...[/yellow]")
        
        new_key = tenant_mgr.rotate_tenant_key(tenant_name)
        
        console.print("[green]✅ Encryption key rotated successfully[/green]")
        console.print(f"  Tenant: {tenant_name}")
        console.print(f"  New key generated (version incremented)")
        console.print("[blue]ℹ️  Historical data remains accessible with previous key versions[/blue]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

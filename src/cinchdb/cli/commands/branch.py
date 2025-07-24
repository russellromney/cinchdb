"""Branch management commands for CinchDB CLI."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root
from cinchdb.managers.branch import BranchManager

app = typer.Typer(help="Branch management commands")
console = Console()


def get_config() -> Config:
    """Get config from current directory."""
    project_root = get_project_root(Path.cwd())
    if not project_root:
        console.print("[red]❌ Not in a CinchDB project directory[/red]")
        raise typer.Exit(1)
    return Config(project_root)


@app.command(name="list")
def list_branches():
    """List all branches in the current database."""
    config = get_config()
    db_name = config.get_active_database()
    
    branch_mgr = BranchManager(config.project_dir, db_name)
    branches = branch_mgr.list_branches()
    
    if not branches:
        console.print("[yellow]No branches found[/yellow]")
        return
    
    # Create a table
    table = RichTable(title=f"Branches in '{db_name}'")
    table.add_column("Name", style="cyan")
    table.add_column("Active", style="green")
    table.add_column("Parent", style="yellow")
    table.add_column("Protected", style="red")
    
    current_branch = config.get_active_branch()
    
    for branch in branches:
        is_active = "✓" if branch.name == current_branch else ""
        is_protected = "✓" if branch.name == "main" else ""
        parent = branch.parent or "-"
        table.add_row(branch.name, is_active, parent, is_protected)
    
    console.print(table)


@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the new branch"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Source branch (default: current)"),
    switch: bool = typer.Option(False, "--switch", help="Switch to the new branch after creation")
):
    """Create a new branch."""
    config = get_config()
    db_name = config.get_active_database()
    source_branch = source or config.get_active_branch()
    
    try:
        branch_mgr = BranchManager(config.project_dir, db_name)
        branch = branch_mgr.create_branch(source_branch, name)
        console.print(f"[green]✅ Created branch '{name}' from '{source_branch}'[/green]")
        
        if switch:
            branch_mgr.switch_branch(name)
            console.print(f"[green]✅ Switched to branch '{name}'[/green]")
            
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    name: str = typer.Argument(..., help="Name of the branch to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force deletion without confirmation")
):
    """Delete a branch."""
    config = get_config()
    db_name = config.get_active_database()
    
    if name == "main":
        console.print("[red]❌ Cannot delete the main branch[/red]")
        raise typer.Exit(1)
    
    # Confirmation
    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete branch '{name}'?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    try:
        branch_mgr = BranchManager(config.project_dir, db_name)
        branch_mgr.delete_branch(name)
        console.print(f"[green]✅ Deleted branch '{name}'[/green]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def switch(
    name: str = typer.Argument(..., help="Name of the branch to switch to")
):
    """Switch to a different branch."""
    config = get_config()
    db_name = config.get_active_database()
    
    try:
        branch_mgr = BranchManager(config.project_dir, db_name)
        branch_mgr.switch_branch(name)
        console.print(f"[green]✅ Switched to branch '{name}'[/green]")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    name: Optional[str] = typer.Argument(None, help="Branch name (default: current)")
):
    """Show information about a branch."""
    config = get_config()
    db_name = config.get_active_database()
    branch_name = name or config.get_active_branch()
    
    try:
        branch_mgr = BranchManager(config.project_dir, db_name)
        branches = branch_mgr.list_branches()
        
        branch = next((b for b in branches if b.name == branch_name), None)
        if not branch:
            console.print(f"[red]❌ Branch '{branch_name}' does not exist[/red]")
            raise typer.Exit(1)
        
        # Display info
        console.print(f"\n[bold]Branch: {branch.name}[/bold]")
        console.print(f"Database: {db_name}")
        console.print(f"Parent: {branch.parent or 'None'}")
        console.print(f"Created: {branch.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Protected: {'Yes' if branch.name == 'main' else 'No'}")
        
        # Count tenants
        from cinchdb.managers.tenant import TenantManager
        tenant_mgr = TenantManager(config.project_dir, db_name, branch_name)
        tenants = tenant_mgr.list_tenants()
        console.print(f"Tenants: {len(tenants)}")
        
        # Count changes
        from cinchdb.managers.change_tracker import ChangeTracker
        tracker = ChangeTracker(config.project_dir, db_name, branch_name)
        changes = tracker.get_changes()
        unapplied = tracker.get_unapplied_changes()
        console.print(f"Total Changes: {len(changes)}")
        console.print(f"Unapplied Changes: {len(unapplied)}")
        
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
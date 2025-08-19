"""Branch management commands for CinchDB CLI."""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root
from cinchdb.managers.branch import BranchManager
from cinchdb.cli.utils import (
    get_config_with_data,
    set_active_branch,
    validate_required_arg,
)
from cinchdb.utils.name_validator import validate_name, InvalidNameError

app = typer.Typer(help="Branch management commands", invoke_without_command=True)
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
def list_branches():
    """List all branches in the current database."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database

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

    current_branch = config_data.active_branch

    for branch in branches:
        is_active = "✓" if branch.name == current_branch else ""
        is_protected = "✓" if branch.name == "main" else ""
        parent = branch.parent_branch or "-"
        table.add_row(branch.name, is_active, parent, is_protected)

    console.print(table)


@app.command()
def create(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the new branch"),
    source: Optional[str] = typer.Option(
        None, "--source", "-s", help="Source branch (default: current)"
    ),
    switch: bool = typer.Option(
        False, "--switch", help="Switch to the new branch after creation"
    ),
):
    """Create a new branch."""
    name = validate_required_arg(name, "name", ctx)

    # Validate branch name
    try:
        validate_name(name, "branch")
    except InvalidNameError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    source_branch = source or config_data.active_branch

    try:
        branch_mgr = BranchManager(config.project_dir, db_name)
        branch_mgr.create_branch(source_branch, name)
        console.print(
            f"[green]✅ Created branch '{name}' from '{source_branch}'[/green]"
        )

        if switch:
            set_active_branch(config, name)
            console.print(f"[green]✅ Switched to branch '{name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the branch to delete"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force deletion without confirmation"
    ),
):
    """Delete a branch."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database

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
    ctx: typer.Context,
    name: Optional[str] = typer.Argument(None, help="Name of the branch to switch to"),
):
    """Switch to a different branch."""
    name = validate_required_arg(name, "name", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database

    try:
        BranchManager(config.project_dir, db_name)
        set_active_branch(config, name)
        console.print(f"[green]✅ Switched to branch '{name}'[/green]")

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    name: Optional[str] = typer.Argument(None, help="Branch name (default: current)"),
):
    """Show information about a branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = name or config_data.active_branch

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
        console.print(f"Parent: {branch.parent_branch or 'None'}")
        created_at = branch.metadata.get("created_at", "Unknown")
        if created_at != "Unknown":
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
        console.print(f"Created: {created_at}")
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


@app.command()
def merge(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(None, help="Source branch to merge from"),
    target: Optional[str] = typer.Option(
        None, "--target", "-t", help="Target branch (default: current)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force merge even with conflicts"
    ),
    preview: bool = typer.Option(
        False, "--preview", "-p", help="Show merge preview without executing"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show SQL statements that would be executed without applying them",
    ),
):
    """Merge changes from source branch into target branch."""
    source = validate_required_arg(source, "source", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    target_branch = target or config_data.active_branch

    from cinchdb.managers.merge_manager import MergeManager, MergeError

    try:
        merge_mgr = MergeManager(config.project_dir, db_name)

        if preview:
            # Show merge preview
            preview_result = merge_mgr.get_merge_preview(source, target_branch)

            if not preview_result["can_merge"]:
                console.print(f"[red]❌ Cannot merge: {preview_result['reason']}[/red]")
                if "conflicts" in preview_result:
                    console.print("[yellow]Conflicts:[/yellow]")
                    for conflict in preview_result["conflicts"]:
                        console.print(f"  • {conflict}")
                raise typer.Exit(1)

            console.print(f"\n[bold]Merge Preview: {source} → {target_branch}[/bold]")
            console.print(f"Merge Type: {preview_result['merge_type']}")
            console.print(f"Changes to merge: {preview_result['changes_to_merge']}")
            console.print(
                f"Target has changes: {preview_result.get('target_has_changes', False)}"
            )

            if preview_result["changes_by_type"]:
                console.print("\n[bold]Changes by type:[/bold]")
                for entity_type, changes in preview_result["changes_by_type"].items():
                    console.print(f"  {entity_type}: {len(changes)} changes")
                    for change in changes[:3]:  # Show first 3
                        console.print(
                            f"    • {change['operation']} {change['entity_name']}"
                        )
                    if len(changes) > 3:
                        console.print(f"    • ... and {len(changes) - 3} more")

            return

        # Handle dry-run
        if dry_run:
            result = merge_mgr.merge_branches(
                source, target_branch, force=force, dry_run=True
            )

            console.print(f"\n[bold]Dry Run: {source} → {target_branch}[/bold]")
            console.print(f"Merge Type: {result.get('merge_type', 'unknown')}")
            console.print(f"Changes to merge: {result.get('changes_to_merge', 0)}")

            if result.get("sql_statements"):
                console.print("\n[bold]SQL statements that would be executed:[/bold]")
                for stmt in result["sql_statements"]:
                    console.print(
                        f"\n[cyan]Change {stmt['change_id']} ({stmt['change_type']}): {stmt['entity_name']}[/cyan]"
                    )
                    if "step" in stmt:
                        console.print(f"  Step: {stmt['step']}")
                    console.print(f"  SQL: [yellow]{stmt['sql']}[/yellow]")
            else:
                console.print("\n[yellow]No SQL statements to execute[/yellow]")

            return

        # Perform actual merge
        result = merge_mgr.merge_branches(source, target_branch, force=force)

        if result["success"]:
            console.print(f"[green]✅ {result['message']}[/green]")
            console.print(f"Merge type: {result.get('merge_type', 'unknown')}")
        else:
            console.print(
                f"[red]❌ Merge failed: {result.get('message', 'Unknown error')}[/red]"
            )
            raise typer.Exit(1)

    except MergeError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def changes(
    name: Optional[str] = typer.Argument(None, help="Branch name (default: current)"),
    format: str = typer.Option(
        "table", "--format", "-f", help="Output format (table, json)"
    ),
):
    """List all changes in a branch."""
    config, config_data = get_config_with_data()
    db_name = config_data.active_database
    branch_name = name or config_data.active_branch

    try:
        from cinchdb.managers.change_tracker import ChangeTracker

        tracker = ChangeTracker(config.project_dir, db_name, branch_name)
        changes = tracker.get_changes()

        if not changes:
            console.print(
                f"[yellow]No changes found in branch '{branch_name}'[/yellow]"
            )
            return

        if format == "json":
            # JSON output
            import json

            changes_data = []
            for change in changes:
                change_dict = change.model_dump(mode="json")
                changes_data.append(change_dict)

            console.print(json.dumps(changes_data, indent=2, default=str))
        else:
            # Table output
            table = RichTable(title=f"Changes in '{branch_name}' branch")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Type", style="yellow")
            table.add_column("Entity", style="green")
            table.add_column("Entity Type", style="blue")
            table.add_column("Applied", style="magenta")
            table.add_column("Created", style="dim")

            for change in changes:
                created_at = (
                    change.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if change.created_at
                    else "Unknown"
                )
                applied_status = "✓" if change.applied else "✗"
                table.add_row(
                    change.id[:8] if change.id else "Unknown",
                    change.type.value
                    if hasattr(change.type, "value")
                    else str(change.type),
                    change.entity_name,
                    change.entity_type,
                    applied_status,
                    created_at,
                )

            console.print(table)

            # Summary
            total = len(changes)
            applied = sum(1 for c in changes if c.applied)
            unapplied = total - applied
            console.print(
                f"\n[bold]Total:[/bold] {total} changes ({applied} applied, {unapplied} unapplied)"
            )

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)


@app.command()
def merge_into_main(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(
        None, help="Source branch to merge into main"
    ),
    preview: bool = typer.Option(
        False, "--preview", "-p", help="Show merge preview without executing"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show SQL statements that would be executed without applying them",
    ),
):
    """Merge a branch into main branch (the primary way to get changes into main)."""
    source = validate_required_arg(source, "source", ctx)
    config, config_data = get_config_with_data()
    db_name = config_data.active_database

    from cinchdb.managers.merge_manager import MergeManager, MergeError

    try:
        merge_mgr = MergeManager(config.project_dir, db_name)

        if preview:
            # Show merge preview for main branch
            preview_result = merge_mgr.get_merge_preview(source, "main")

            if not preview_result["can_merge"]:
                console.print(
                    f"[red]❌ Cannot merge into main: {preview_result['reason']}[/red]"
                )
                if "conflicts" in preview_result:
                    console.print("[yellow]Conflicts:[/yellow]")
                    for conflict in preview_result["conflicts"]:
                        console.print(f"  • {conflict}")
                raise typer.Exit(1)

            console.print(f"\n[bold]Merge Preview: {source} → main[/bold]")
            console.print(f"Merge Type: {preview_result['merge_type']}")
            console.print(f"Changes to merge: {preview_result['changes_to_merge']}")

            if preview_result["changes_by_type"]:
                console.print("\n[bold]Changes to be merged:[/bold]")
                for entity_type, changes in preview_result["changes_by_type"].items():
                    console.print(f"  {entity_type}: {len(changes)} changes")
                    for change in changes:
                        console.print(
                            f"    • {change['operation']} {change['entity_name']}"
                        )

            return

        # Handle dry-run
        if dry_run:
            result = merge_mgr.merge_into_main(source, dry_run=True)

            console.print(f"\n[bold]Dry Run: {source} → main[/bold]")
            console.print(f"Merge Type: {result.get('merge_type', 'unknown')}")
            console.print(f"Changes to merge: {result.get('changes_to_merge', 0)}")

            if result.get("sql_statements"):
                console.print("\n[bold]SQL statements that would be executed:[/bold]")
                for stmt in result["sql_statements"]:
                    console.print(
                        f"\n[cyan]Change {stmt['change_id']} ({stmt['change_type']}): {stmt['entity_name']}[/cyan]"
                    )
                    if "step" in stmt:
                        console.print(f"  Step: {stmt['step']}")
                    console.print(f"  SQL: [yellow]{stmt['sql']}[/yellow]")
            else:
                console.print("\n[yellow]No SQL statements to execute[/yellow]")

            return

        # Perform merge into main
        result = merge_mgr.merge_into_main(source)

        if result["success"]:
            console.print(f"[green]✅ {result['message']}[/green]")
            console.print("[green]Main branch has been updated![/green]")
        else:
            console.print(
                f"[red]❌ Merge into main failed: {result.get('message', 'Unknown error')}[/red]"
            )
            raise typer.Exit(1)

    except MergeError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        raise typer.Exit(1)

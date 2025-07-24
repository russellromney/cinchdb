"""Codegen CLI commands."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable
from typing import Optional

from ..utils import get_config_with_data
from ...managers import CodegenManager

console = Console()

app = typer.Typer(
    help="Generate models from database schemas",
    invoke_without_command=True
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Generate models from database schemas."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def languages():
    """List available code generation languages."""
    try:
        config, config_data = get_config_with_data()
        
        # Create manager to get supported languages
        manager = CodegenManager(
            project_root=config.project_dir,
            database=config_data.active_database,
            branch=config_data.active_branch,
            tenant="main"
        )
        
        supported = manager.get_supported_languages()
        
        table = RichTable(title="Supported Languages")
        table.add_column("Language", style="cyan")
        table.add_column("Status", style="green")
        
        for lang in supported:
            status = "Available" if lang == "python" else "Coming Soon"
            table.add_row(lang, status)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    language: str = typer.Argument(..., help="Target language (python, typescript)"),
    output_dir: str = typer.Argument(..., help="Output directory for generated models"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Database name (defaults to active)"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch name (defaults to active)"),
    tenant: str = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    include_tables: bool = typer.Option(True, "--tables/--no-tables", help="Include table models"),
    include_views: bool = typer.Option(True, "--views/--no-views", help="Include view models"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files")
):
    """Generate model files for the specified language."""
    try:
        config, config_data = get_config_with_data()
        
        # Use provided values or defaults from config
        db_name = database or config_data.active_database
        branch_name = branch or config_data.active_branch
        
        # Create output directory path
        output_path = Path(output_dir).resolve()
        
        # Check if output directory exists and has files
        if output_path.exists() and any(output_path.iterdir()) and not force:
            console.print(f"[yellow]⚠️  Output directory '{output_path}' already contains files.[/yellow]")
            console.print("Use --force to overwrite existing files.")
            raise typer.Exit(1)
        
        # Create manager
        manager = CodegenManager(
            project_root=config.project_dir,
            database=db_name,
            branch=branch_name,
            tenant=tenant
        )
        
        # Validate language
        supported = manager.get_supported_languages()
        if language not in supported:
            console.print(f"[red]❌ Language '{language}' not supported.[/red]")
            console.print(f"Available languages: {', '.join(supported)}")
            raise typer.Exit(1)
        
        # Show what will be generated
        console.print(f"[blue]🔧 Generating {language} models...[/blue]")
        console.print(f"Database: {db_name}")
        console.print(f"Branch: {branch_name}")
        console.print(f"Tenant: {tenant}")
        console.print(f"Output: {output_path}")
        console.print(f"Include tables: {include_tables}")
        console.print(f"Include views: {include_views}")
        console.print()
        
        # Generate models
        results = manager.generate_models(
            language=language,
            output_dir=output_path,
            include_tables=include_tables,
            include_views=include_views
        )
        
        # Display results
        console.print(f"[green]✅ Generated {len(results['files_generated'])} files[/green]")
        
        if results["tables_processed"]:
            console.print(f"Tables processed: {', '.join(results['tables_processed'])}")
        
        if results["views_processed"]:
            console.print(f"Views processed: {', '.join(results['views_processed'])}")
        
        console.print(f"Output directory: {results['output_dir']}")
        
        # Show generated files
        if results["files_generated"]:
            table = RichTable(title="Generated Files")
            table.add_column("File", style="cyan")
            
            for filename in results["files_generated"]:
                table.add_row(filename)
            
            console.print(table)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
"""Codegen CLI commands."""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table as RichTable
from typing import Optional

from ..utils import get_config_with_data, get_config_dict, validate_required_arg
from ..handlers import CodegenHandler

console = Console()

app = typer.Typer(
    help="Generate models from database schemas", invoke_without_command=True
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
        config_dict = get_config_dict()

        # Create handler to get supported languages
        handler = CodegenHandler(config_dict)
        supported = handler.get_supported_languages(project_root=config.project_dir)

        table = RichTable(title="Supported Languages")
        table.add_column("Language", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Source", style="blue")

        for lang in supported:
            status = "Available" if lang == "python" else "Coming Soon"
            source = "Remote API" if handler.is_remote else "Local"
            table.add_row(lang, status, source)

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    ctx: typer.Context,
    language: Optional[str] = typer.Argument(
        None, help="Target language (python, typescript)"
    ),
    output_dir: Optional[str] = typer.Argument(
        None, help="Output directory for generated models"
    ),
    database: Optional[str] = typer.Option(
        None, "--database", "-d", help="Database name (defaults to active)"
    ),
    branch: Optional[str] = typer.Option(
        None, "--branch", "-b", help="Branch name (defaults to active)"
    ),
    tenant: str = typer.Option("main", "--tenant", "-t", help="Tenant name"),
    include_tables: bool = typer.Option(
        True, "--tables/--no-tables", help="Include table models"
    ),
    include_views: bool = typer.Option(
        True, "--views/--no-views", help="Include view models"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
    api_url: Optional[str] = typer.Option(
        None, "--api-url", help="API URL for remote generation"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="API key for remote generation"
    ),
    local: bool = typer.Option(
        False, "--local", help="Force local generation even if API configured"
    ),
):
    """Generate model files for the specified language."""
    language = validate_required_arg(language, "language", ctx)
    output_dir = validate_required_arg(output_dir, "output_dir", ctx)
    try:
        config, config_data = get_config_with_data()
        config_dict = get_config_dict()

        # Use provided values or defaults from config
        db_name = database or config_data.active_database
        branch_name = branch or config_data.active_branch

        # Create output directory path
        output_path = Path(output_dir).resolve()

        # Check if output directory exists and has files
        if output_path.exists() and any(output_path.iterdir()) and not force:
            console.print(
                f"[yellow]⚠️  Output directory '{output_path}' already contains files.[/yellow]"
            )
            console.print("Use --force to overwrite existing files.")
            raise typer.Exit(1)

        # Create handler with API options
        handler = CodegenHandler(
            config_data=config_dict, api_url=api_url, api_key=api_key, force_local=local
        )

        # Validate language
        supported = handler.get_supported_languages(project_root=config.project_dir)
        if language not in supported:
            console.print(f"[red]❌ Language '{language}' not supported.[/red]")
            console.print(f"Available languages: {', '.join(supported)}")
            raise typer.Exit(1)

        # Show what will be generated
        source = "Remote API" if handler.is_remote else "Local"
        console.print(f"[blue]🔧 Generating {language} models via {source}...[/blue]")
        console.print(f"Database: {db_name}")
        console.print(f"Branch: {branch_name}")
        console.print(f"Tenant: {tenant}")
        console.print(f"Output: {output_path}")
        console.print(f"Include tables: {include_tables}")
        console.print(f"Include views: {include_views}")
        if handler.is_remote:
            console.print(f"API URL: {handler.api_url}")
        console.print()

        # Generate models
        results = handler.generate_models(
            language=language,
            output_dir=output_path,
            database=db_name,
            branch=branch_name,
            tenant=tenant,
            include_tables=include_tables,
            include_views=include_views,
            project_root=config.project_dir,
        )

        # Display results
        console.print(
            f"[green]✅ Generated {len(results['files_generated'])} files[/green]"
        )

        if results.get("tables_processed"):
            console.print(f"Tables processed: {', '.join(results['tables_processed'])}")

        if results.get("views_processed"):
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

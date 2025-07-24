"""Main CLI entry point for CinchDB."""

import typer
from typing import Optional
from pathlib import Path

app = typer.Typer(
    name="cinch",
    help="CinchDB - A Git-like SQLite database management system",
    add_completion=False,
)


@app.command()
def init(
    path: Optional[Path] = typer.Argument(None, help="Directory to initialize project in (default: current directory)")
):
    """Initialize a new CinchDB project."""
    from cinchdb.config import Config
    
    project_path = path or Path.cwd()
    
    try:
        config = Config(project_path)
        config.init_project()
        typer.secho(f"✅ Initialized CinchDB project in {project_path}", fg=typer.colors.GREEN)
    except FileExistsError:
        typer.secho(f"❌ Project already exists in {project_path}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def version():
    """Show CinchDB version."""
    from cinchdb import __version__
    typer.echo(f"CinchDB version {__version__}")


if __name__ == "__main__":
    app()
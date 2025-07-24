"""Utility functions for CLI commands."""

import typer
from pathlib import Path
from rich.console import Console

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root

console = Console()


def get_config_with_data():
    """Get config and load data from current directory.
    
    Returns:
        tuple: (config, config_data)
    """
    project_root = get_project_root(Path.cwd())
    if not project_root:
        console.print("[red]❌ Not in a CinchDB project directory[/red]")
        raise typer.Exit(1)
    
    config = Config(project_root)
    try:
        config_data = config.load()
    except FileNotFoundError:
        console.print("[red]❌ Config file not found. Run 'cinch init' first.[/red]")
        raise typer.Exit(1)
    
    return config, config_data


def set_active_database(config: Config, database: str):
    """Set the active database in config."""
    config_data = config.load()
    config_data.active_database = database
    config.save(config_data)


def set_active_branch(config: Config, branch: str):
    """Set the active branch in config."""
    config_data = config.load()
    config_data.active_branch = branch
    config.save(config_data)
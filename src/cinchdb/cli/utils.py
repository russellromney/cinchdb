"""Utility functions for CLI commands."""

import typer
from pathlib import Path
from typing import Optional
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


def get_config_dict():
    """Get config data as dictionary, including API configuration if present.

    Returns:
        dict: Configuration data
    """
    config, config_data = get_config_with_data()

    # Convert config_data to dict-like structure for handlers
    config_dict = {
        "active_database": getattr(config_data, "active_database", None),
        "active_branch": getattr(config_data, "active_branch", "main"),
        "project_root": config.project_dir,
    }

    # Add API configuration if present in raw config
    if hasattr(config_data, "api") and config_data.api:
        config_dict["api"] = {
            "url": getattr(config_data.api, "url", None),
            "key": getattr(config_data.api, "key", None),
        }

    return config_dict


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


def validate_required_arg(
    value: Optional[str], arg_name: str, ctx: typer.Context
) -> str:
    """Validate a required argument and show help if missing.

    Args:
        value: The argument value
        arg_name: Name of the argument (for error message)
        ctx: Typer context

    Returns:
        The validated value

    Raises:
        typer.Exit: If value is None
    """
    if value is None:
        console.print(ctx.get_help())
        console.print(f"\n[red]❌ Error: Missing argument '{arg_name.upper()}'.[/red]")
        raise typer.Exit(1)
    return value

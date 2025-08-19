"""Utility functions for CLI commands."""

import os
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root
from cinchdb.core.database import CinchDB

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


def get_cinchdb_instance(
    database: Optional[str] = None,
    branch: Optional[str] = None,
    tenant: str = "main",
    force_local: bool = False,
    remote_alias: Optional[str] = None,
) -> CinchDB:
    """Get a CinchDB instance configured for local or remote access.

    Args:
        database: Database name (uses active database if None)
        branch: Branch name (uses active branch if None)
        tenant: Tenant name (default: main)
        force_local: Force local connection even if remote is configured
        remote_alias: Use specific remote alias (overrides active remote)

    Returns:
        CinchDB instance

    Raises:
        typer.Exit: If configuration is invalid
    """
    config, config_data = get_config_with_data()

    # Use provided or active database/branch
    database = database or config_data.active_database
    branch = branch or config_data.active_branch

    # Determine if we should use remote connection
    use_remote = False
    remote_config = None

    if not force_local:
        if remote_alias:
            # Use specific remote alias
            if remote_alias not in config_data.remotes:
                console.print(f"[red]❌ Remote '{remote_alias}' not found[/red]")
                raise typer.Exit(1)
            remote_config = config_data.remotes[remote_alias]
            use_remote = True
        elif config_data.active_remote:
            # Use active remote
            if config_data.active_remote not in config_data.remotes:
                console.print(
                    f"[red]❌ Active remote '{config_data.active_remote}' not found[/red]"
                )
                raise typer.Exit(1)
            remote_config = config_data.remotes[config_data.active_remote]
            use_remote = True

    if use_remote and remote_config:
        # Create remote connection
        return CinchDB(
            database=database,
            branch=branch,
            tenant=tenant,
            api_url=remote_config.url,
            api_key=remote_config.key,
        )
    else:
        # Create local connection
        return CinchDB(
            database=database,
            branch=branch,
            tenant=tenant,
            project_dir=config.project_dir,
        )


def show_env_config():
    """Display active environment variable configuration."""
    env_vars = {
        "CINCHDB_PROJECT_DIR": os.environ.get("CINCHDB_PROJECT_DIR"),
        "CINCHDB_DATABASE": os.environ.get("CINCHDB_DATABASE"),
        "CINCHDB_BRANCH": os.environ.get("CINCHDB_BRANCH"),
        "CINCHDB_REMOTE_URL": os.environ.get("CINCHDB_REMOTE_URL"),
        "CINCHDB_API_KEY": "***" if "CINCHDB_API_KEY" in os.environ else None,
    }

    active = {k: v for k, v in env_vars.items() if v}
    if active:
        console.print("\n[yellow]Active environment variables:[/yellow]")
        for key, value in active.items():
            console.print(f"  {key}={value}")
    else:
        console.print("\n[dim]No CinchDB environment variables set[/dim]")

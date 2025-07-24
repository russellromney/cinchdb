"""Maintenance mode utilities for CinchDB."""

from pathlib import Path
import json
from typing import Dict, Any, Optional

from cinchdb.core.path_utils import get_branch_path


class MaintenanceError(Exception):
    """Exception raised when operation blocked by maintenance mode."""

    pass


def is_branch_in_maintenance(project_root: Path, database: str, branch: str) -> bool:
    """Check if a branch is in maintenance mode.

    Args:
        project_root: Path to project root
        database: Database name
        branch: Branch name

    Returns:
        True if in maintenance mode, False otherwise
    """
    branch_path = get_branch_path(project_root, database, branch)
    maintenance_file = branch_path / ".maintenance_mode"
    return maintenance_file.exists()


def get_maintenance_info(
    project_root: Path, database: str, branch: str
) -> Optional[Dict[str, Any]]:
    """Get maintenance mode information if active.

    Args:
        project_root: Path to project root
        database: Database name
        branch: Branch name

    Returns:
        Maintenance info dict or None if not in maintenance
    """
    branch_path = get_branch_path(project_root, database, branch)
    maintenance_file = branch_path / ".maintenance_mode"

    if maintenance_file.exists():
        with open(maintenance_file, "r") as f:
            return json.load(f)

    return None


def check_maintenance_mode(project_root: Path, database: str, branch: str) -> None:
    """Check maintenance mode and raise error if active.

    Args:
        project_root: Path to project root
        database: Database name
        branch: Branch name

    Raises:
        MaintenanceError: If branch is in maintenance mode
    """
    if is_branch_in_maintenance(project_root, database, branch):
        info = get_maintenance_info(project_root, database, branch)
        reason = (
            info.get("reason", "Maintenance in progress")
            if info
            else "Maintenance in progress"
        )
        raise MaintenanceError(f"Branch '{branch}' is in maintenance mode: {reason}")

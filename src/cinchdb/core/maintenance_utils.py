"""Maintenance utilities for CinchDB operations."""

from pathlib import Path
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db


class MaintenanceError(Exception):
    """Exception raised when operation blocked by maintenance mode."""
    pass


def check_maintenance_mode(project_root: Path, database: str, branch: str = None) -> None:
    """Check if database or branch is in maintenance mode and raise error if so.
    
    Args:
        project_root: Path to project root
        database: Database name  
        branch: Branch name (optional)
        
    Raises:
        MaintenanceError: If database or branch is in maintenance mode
    """
    try:
        metadata_db = get_metadata_db(project_root)
        
        # Check database-level maintenance
        if metadata_db.is_database_in_maintenance(database):
            info = metadata_db.get_maintenance_info(database)
            reason = info.get("reason", "Database maintenance in progress") if info else "Database maintenance in progress"
            raise MaintenanceError(f"Database '{database}' is in maintenance mode: {reason}")
        
        # Check branch-level maintenance if branch specified
        if branch and metadata_db.is_branch_in_maintenance(database, branch):
            info = metadata_db.get_maintenance_info(database, branch)
            reason = info.get("reason", "Branch maintenance in progress") if info else "Branch maintenance in progress"
            raise MaintenanceError(f"Branch '{database}/{branch}' is in maintenance mode: {reason}")
            
    except MaintenanceError:
        raise  # Re-raise maintenance errors
    except Exception:
        # If we can't check maintenance status, allow the operation to proceed
        # This prevents maintenance check failures from blocking normal operations
        pass
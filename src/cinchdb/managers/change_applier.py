"""Change application logic for CinchDB."""

from pathlib import Path
import logging

from cinchdb.models import Change, ChangeType
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path

logger = logging.getLogger(__name__)


class ChangeApplier:
    """Applies tracked changes to tenants."""
    
    def __init__(self, project_root: Path, database: str, branch: str):
        """Initialize change applier.
        
        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.change_tracker = ChangeTracker(project_root, database, branch)
        self.tenant_manager = TenantManager(project_root, database, branch)
    
    def apply_change(self, change_id: str) -> None:
        """Apply a single change to all tenants in the branch.
        
        Args:
            change_id: ID of the change to apply
            
        Raises:
            ValueError: If change not found
            Exception: If SQL execution fails
        """
        # Get the change
        changes = self.change_tracker.get_changes()
        change = None
        for c in changes:
            if c.id == change_id:
                change = c
                break
        
        if not change:
            raise ValueError(f"Change with ID '{change_id}' not found")
        
        if change.applied:
            logger.info(f"Change {change_id} already applied")
            return
        
        # Apply to all tenants
        tenants = self.tenant_manager.list_tenants()
        for tenant in tenants:
            self._apply_change_to_tenant(change, tenant.name)
        
        # Mark as applied
        self.change_tracker.mark_change_applied(change_id)
        logger.info(f"Applied change {change_id} to {len(tenants)} tenants")
    
    def apply_all_unapplied(self) -> int:
        """Apply all unapplied changes to all tenants.
        
        Returns:
            Number of changes applied
        """
        unapplied = self.change_tracker.get_unapplied_changes()
        applied_count = 0
        
        for change in unapplied:
            try:
                self.apply_change(change.id)
                applied_count += 1
            except Exception as e:
                logger.error(f"Failed to apply change {change.id}: {e}")
                # Stop on first error to maintain consistency
                raise
        
        return applied_count
    
    def apply_changes_since(self, change_id: str) -> int:
        """Apply all changes after a specific change.
        
        Args:
            change_id: ID of change to start after
            
        Returns:
            Number of changes applied
        """
        changes = self.change_tracker.get_changes_since(change_id)
        applied_count = 0
        
        for change in changes:
            if not change.applied:
                self.apply_change(change.id)
                applied_count += 1
        
        return applied_count
    
    
    def _apply_change_to_tenant(self, change: Change, tenant_name: str) -> None:
        """Apply a change to a specific tenant.
        
        Args:
            change: Change to apply
            tenant_name: Name of tenant
            
        Raises:
            Exception: If SQL execution fails
        """
        db_path = get_tenant_db_path(self.project_root, self.database, self.branch, tenant_name)
        
        with DatabaseConnection(db_path) as conn:
            try:
                # Check if this is a complex operation with multiple statements
                if change.details and "statements" in change.details:
                    # Execute multiple statements in sequence within a transaction
                    conn.execute("BEGIN")
                    for step_name, sql in change.details["statements"]:
                        conn.execute(sql)
                    conn.execute("COMMIT")
                elif change.type == ChangeType.UPDATE_VIEW:
                    # For view updates, first drop the existing view if it exists
                    view_name = change.entity_name
                    conn.execute(f"DROP VIEW IF EXISTS {view_name}")
                    conn.execute(change.sql)
                    conn.commit()
                elif change.type == ChangeType.CREATE_TABLE and change.details and change.details.get("copy_sql"):
                    # For table copy operations, create table and copy data
                    conn.execute(change.sql)  # CREATE TABLE
                    conn.execute(change.details["copy_sql"])  # INSERT data
                    conn.commit()
                else:
                    # Regular single statement execution
                    conn.execute(change.sql)
                    conn.commit()
                logger.debug(f"Applied {change.type} to tenant '{tenant_name}'")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to apply change to tenant '{tenant_name}': {e}")
                raise
    
    def validate_change(self, change: Change) -> bool:
        """Validate that a change can be applied.
        
        Args:
            change: Change to validate
            
        Returns:
            True if change is valid
        """
        # Basic validation
        if not change.sql:
            return False
        
        # Validate based on change type
        if change.type == ChangeType.ADD_COLUMN:
            # Ensure table name is provided in details
            if not change.details or "table" not in change.details:
                return False
        
        # Could add more validation here (e.g., check table exists for ADD_COLUMN)
        return True
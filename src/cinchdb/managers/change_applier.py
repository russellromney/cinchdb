"""Change application logic for CinchDB."""

from pathlib import Path
import logging
import shutil
from typing import List
from datetime import datetime

from cinchdb.models import Change, ChangeType, Tenant
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path, get_branch_path

logger = logging.getLogger(__name__)


class ChangeError(Exception):
    """Exception raised when change application fails."""

    pass


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

        # Import here to avoid circular imports
        from cinchdb.managers.branch import BranchManager

        self.branch_manager = BranchManager(project_root, database)

    def _get_change_by_id(self, change_id: str) -> Change:
        """Get a change by its ID.

        Args:
            change_id: ID of the change

        Returns:
            Change object

        Raises:
            ValueError: If change not found
        """
        changes = self.change_tracker.get_changes()
        for change in changes:
            if change.id == change_id:
                return change
        raise ValueError(f"Change with ID '{change_id}' not found")

    def apply_change(self, change_id: str) -> None:
        """Apply a single change to all tenants atomically with snapshot-based rollback.

        Args:
            change_id: ID of the change to apply

        Raises:
            ValueError: If change not found
            ChangeError: If change application fails
        """
        # Get the change
        try:
            change = self._get_change_by_id(change_id)
        except ValueError:
            raise

        if change.applied:
            logger.info(f"Change {change_id} already applied")
            return

        backup_dir = self._get_backup_dir(change.id)
        tenants = self.tenant_manager.list_tenants()

        if not tenants:
            # No tenants, just mark as applied
            self.change_tracker.mark_change_applied(change_id)
            return

        logger.info(f"Applying change {change_id} to {len(tenants)} tenants...")

        try:
            # Phase 1: Create snapshots
            logger.info("Creating database snapshots...")
            self._create_snapshots(tenants, backup_dir)

            # Phase 2: Enter maintenance mode to block writes
            logger.info("Entering maintenance mode for schema update...")
            self._enter_maintenance_mode()

            try:
                # Track which tenants we've applied to
                applied_tenants = []

                for tenant in tenants:
                    try:
                        self._apply_change_to_tenant(change, tenant.name)
                        applied_tenants.append(tenant.name)
                    except Exception as e:
                        logger.error(
                            f"Failed to apply change to tenant '{tenant.name}': {e}"
                        )
                        raise ChangeError(
                            f"Change application failed on tenant '{tenant.name}': {e}"
                        )

                # Phase 3: Mark as applied
                self.change_tracker.mark_change_applied(change_id)

                # Exit maintenance mode before cleanup
                self._exit_maintenance_mode()
                logger.info("Exited maintenance mode")

                # Cleanup snapshots
                self._cleanup_snapshots(backup_dir)

                logger.info(
                    f"Schema update complete. Applied change {change_id} to {len(tenants)} tenants"
                )

            except Exception:
                # Always exit maintenance mode on error
                self._exit_maintenance_mode()
                raise

        except Exception as e:
            # Rollback all tenants
            logger.error(f"Change {change_id} failed: {e}")
            logger.info("Rolling back all tenants to snapshot...")

            # Restore all tenants from snapshots
            self._restore_all_snapshots(tenants, backup_dir)

            # Clean up backup directory
            self._cleanup_snapshots(backup_dir)

            logger.info("Rollback complete. All tenants restored to pre-change state")

            # Re-raise as ChangeError
            if not isinstance(e, ChangeError):
                raise ChangeError(f"Failed to apply change {change_id}: {e}")
            raise

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
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )

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
                elif (
                    change.type == ChangeType.CREATE_TABLE
                    and change.details
                    and change.details.get("copy_sql")
                ):
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

    def _get_backup_dir(self, change_id: str) -> Path:
        """Get path for change backup directory.

        Args:
            change_id: ID of the change

        Returns:
            Path to backup directory
        """
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        return branch_path / ".change_backups" / change_id

    def _create_tenant_snapshot(self, tenant_name: str, backup_dir: Path) -> None:
        """Create snapshot of a tenant database.

        Args:
            tenant_name: Name of tenant
            backup_dir: Directory to store backup
        """
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        backup_path = backup_dir / f"{tenant_name}.db"

        # Copy main database file
        if db_path.exists():
            shutil.copy2(db_path, backup_path)

        # Copy WAL file if exists
        wal_path = Path(str(db_path) + "-wal")
        if wal_path.exists():
            shutil.copy2(wal_path, backup_dir / f"{tenant_name}.db-wal")

        # Copy SHM file if exists
        shm_path = Path(str(db_path) + "-shm")
        if shm_path.exists():
            shutil.copy2(shm_path, backup_dir / f"{tenant_name}.db-shm")

    def _restore_tenant_snapshot(self, tenant_name: str, backup_dir: Path) -> None:
        """Restore tenant database from snapshot.

        Args:
            tenant_name: Name of tenant
            backup_dir: Directory containing backup
        """
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        backup_path = backup_dir / f"{tenant_name}.db"

        # Restore main database file
        if backup_path.exists():
            shutil.copy2(backup_path, db_path)

        # Restore WAL file
        wal_backup = backup_dir / f"{tenant_name}.db-wal"
        wal_path = Path(str(db_path) + "-wal")
        if wal_backup.exists():
            shutil.copy2(wal_backup, wal_path)
        elif wal_path.exists():
            # Remove WAL if it wasn't in backup
            wal_path.unlink()

        # Restore SHM file
        shm_backup = backup_dir / f"{tenant_name}.db-shm"
        shm_path = Path(str(db_path) + "-shm")
        if shm_backup.exists():
            shutil.copy2(shm_backup, shm_path)
        elif shm_path.exists():
            # Remove SHM if it wasn't in backup
            shm_path.unlink()

    def _create_snapshots(self, tenants: List[Tenant], backup_dir: Path) -> None:
        """Create snapshots of all tenant databases.

        Args:
            tenants: List of tenants
            backup_dir: Directory to store backups
        """
        backup_dir.mkdir(parents=True, exist_ok=True)

        for tenant in tenants:
            self._create_tenant_snapshot(tenant.name, backup_dir)

    def _restore_all_snapshots(self, tenants: List[Tenant], backup_dir: Path) -> None:
        """Restore all tenants from snapshots.

        Args:
            tenants: List of tenants
            backup_dir: Directory containing backups
        """
        for tenant in tenants:
            try:
                self._restore_tenant_snapshot(tenant.name, backup_dir)
            except Exception as e:
                # Log but continue restoring other tenants
                logger.error(f"Failed to restore tenant {tenant.name}: {e}")

    def _cleanup_snapshots(self, backup_dir: Path) -> None:
        """Remove backup directory and all snapshots.

        Args:
            backup_dir: Directory to remove
        """
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)

    def _enter_maintenance_mode(self) -> None:
        """Enter maintenance mode to block writes during schema changes."""
        # Create a maintenance mode file that all connections can check
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        maintenance_file = branch_path / ".maintenance_mode"

        with open(maintenance_file, "w") as f:
            import json

            json.dump(
                {
                    "active": True,
                    "reason": "Schema update in progress",
                    "started_at": datetime.now().isoformat(),
                },
                f,
            )

        # Give time for any in-flight writes to complete
        # Can be disabled for tests via environment variable
        import time
        import os

        if os.getenv("CINCHDB_SKIP_MAINTENANCE_DELAY") != "1":
            time.sleep(0.25)  # A quarter second should be enough

    def _exit_maintenance_mode(self) -> None:
        """Exit maintenance mode to allow writes again."""
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        maintenance_file = branch_path / ".maintenance_mode"

        if maintenance_file.exists():
            maintenance_file.unlink()

    def is_in_maintenance_mode(self) -> bool:
        """Check if branch is in maintenance mode.

        Returns:
            True if in maintenance mode, False otherwise
        """
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        maintenance_file = branch_path / ".maintenance_mode"
        return maintenance_file.exists()

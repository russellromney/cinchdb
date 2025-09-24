"""Change tracking for CinchDB using metadata.db."""

from typing import List
from datetime import datetime, timezone

from cinchdb.models import Change
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db


class ChangeTracker:
    """Tracks schema changes within a branch using metadata.db."""

    def __init__(self, project_root, database: str, branch: str):
        """Initialize change tracker.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
        """
        self.project_root = project_root
        self.database = database
        self.branch = branch
        self.metadata_db = get_metadata_db(project_root)

        # Database and branch must already exist
        db_info = self.metadata_db.get_database(self.database)
        if not db_info:
            raise ValueError(f"Database '{self.database}' does not exist. Cannot track changes for non-existent database.")
        self.database_id = db_info["id"]

        branch_info = self.metadata_db.get_branch(self.database_id, self.branch)
        if not branch_info:
            raise ValueError(f"Branch '{self.branch}' does not exist in database '{self.database}'. Cannot track changes for non-existent branch.")
        self.branch_id = branch_info["id"]

    def get_changes(self) -> List[Change]:
        """Get all changes for the branch.

        Returns:
            List of Change objects
        """
        changes_data = self.metadata_db.get_branch_changes(branch_id=self.branch_id)

        changes = []
        for data in changes_data:
            # Ensure details is a dict or None (not the string 'null')
            details = data.get("details")
            if details is None or details == "null":
                details = {}
            elif isinstance(details, str):
                import json
                try:
                    details = json.loads(details)
                except:
                    details = {}

            change = Change(
                id=data["id"],
                type=data["type"],
                entity_type=data["entity_type"],
                entity_name=data["entity_name"],
                details=details,
                sql=data.get("sql"),
                branch=self.branch,
                applied=data.get("applied", False),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
                updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            )
            changes.append(change)

        return changes

    def add_change(self, change: Change) -> Change:
        """Add a new change to the branch.

        Args:
            change: Change object to add

        Returns:
            The added Change object with ID and timestamp
        """
        # Ensure change has required fields
        if not change.id:
            import uuid
            change.id = str(uuid.uuid4())

        if not change.created_at:
            change.created_at = datetime.now(timezone.utc)

        # Check if change already exists
        existing = self.metadata_db.get_change(change.id)
        if not existing:
            # Create new change - use the correct parameter names
            self.metadata_db.create_change(
                change_id=change.id,
                database_id=self.database_id,
                origin_branch_id=self.branch_id,
                origin_branch_name=self.branch,
                change_type=change.type,
                entity_type=change.entity_type,
                entity_name=change.entity_name,
                details=change.details,
                sql=change.sql,
            )

        # Link change to branch if not already linked
        existing_branch_changes = self.metadata_db.get_branch_changes(branch_id=self.branch_id)
        if not any(c["id"] == change.id for c in existing_branch_changes):
            applied_order = len(existing_branch_changes)
            self.metadata_db.link_change_to_branch(
                branch_id=self.branch_id,
                branch_name=self.branch,
                change_id=change.id,
                applied=change.applied,
                applied_order=applied_order,
            )

        return change

    def get_unapplied_changes(self) -> List[Change]:
        """Get all unapplied changes.

        Returns:
            List of unapplied Change objects
        """
        changes = self.get_changes()
        return [c for c in changes if not c.applied]

    def mark_change_applied(self, change_id: str) -> None:
        """Mark a change as applied.

        Args:
            change_id: ID of change to mark as applied
        """
        self.metadata_db.mark_change_applied(self.branch, change_id, branch_id=self.branch_id)

    def get_changes_since(self, change_id: str) -> List[Change]:
        """Get all changes after a specific change.

        Args:
            change_id: ID of change to start after

        Returns:
            List of Change objects after the specified change
        """
        changes = self.get_changes()

        # Find the index of the specified change
        start_index = None
        for i, change in enumerate(changes):
            if change.id == change_id:
                start_index = i + 1
                break

        if start_index is None:
            return []

        return changes[start_index:]

    def clear_changes(self) -> None:
        """Clear all changes from the branch."""
        self.metadata_db.clear_branch_changes(branch_id=self.branch_id)

    def has_change_id(self, change_id: str) -> bool:
        """Check if a change ID exists.

        Args:
            change_id: ID to check

        Returns:
            True if change exists
        """
        changes = self.get_changes()
        return any(c.id == change_id for c in changes)

    def remove_change(self, change_id: str) -> bool:
        """Remove a change from the branch.

        Args:
            change_id: ID of change to remove

        Returns:
            True if change was removed, False if not found
        """
        # Check if change is linked to this branch
        changes = self.get_changes()
        found = any(c.id == change_id for c in changes)

        if found:
            self.metadata_db.unlink_change_from_branch(self.branch_id, change_id)
            return True

        return False
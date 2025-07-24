"""Change tracking for CinchDB."""

import json
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from cinchdb.models import Change
from cinchdb.core.path_utils import get_branch_path


class ChangeTracker:
    """Tracks schema changes within a branch."""

    def __init__(self, project_root: Path, database: str, branch: str):
        """Initialize change tracker.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.branch_path = get_branch_path(self.project_root, database, branch)
        self.changes_file = self.branch_path / "changes.json"

    def get_changes(self) -> List[Change]:
        """Get all changes for the branch.

        Returns:
            List of Change objects
        """
        if not self.changes_file.exists():
            return []

        with open(self.changes_file, "r") as f:
            changes_data = json.load(f)

        changes = []
        for data in changes_data:
            # Convert string dates back to datetime
            if data.get("created_at"):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if data.get("updated_at"):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

            change = Change(**data)
            changes.append(change)

        return changes

    def add_change(self, change: Change) -> Change:
        """Add a new change to the branch.

        Args:
            change: Change object to add

        Returns:
            The added Change object with ID and timestamp
        """
        # Get existing changes
        changes = self.get_changes()

        # Ensure change has required fields
        if not change.id:
            import uuid

            change.id = str(uuid.uuid4())

        if not change.created_at:
            change.created_at = datetime.now(timezone.utc)

        # Add to list
        changes.append(change)

        # Save
        self._save_changes(changes)

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
        changes = self.get_changes()

        for change in changes:
            if change.id == change_id:
                change.applied = True
                change.updated_at = datetime.now(timezone.utc)
                break

        self._save_changes(changes)

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
        self._save_changes([])

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
        changes = self.get_changes()

        # Find and remove the change
        for i, change in enumerate(changes):
            if change.id == change_id:
                changes.pop(i)
                self._save_changes(changes)
                return True

        return False

    def _save_changes(self, changes: List[Change]) -> None:
        """Save changes to disk.

        Args:
            changes: List of Change objects to save
        """
        # Convert to JSON-serializable format
        changes_data = []
        for change in changes:
            # model_dump with mode='json' handles datetime serialization
            data = change.model_dump(mode="json")
            changes_data.append(data)

        # Save to file
        with open(self.changes_file, "w") as f:
            json.dump(changes_data, f, indent=2)

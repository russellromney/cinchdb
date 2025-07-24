"""Change comparison and divergence detection for CinchDB branches."""

from pathlib import Path
from typing import List, Tuple, Optional
from cinchdb.models import Change
from cinchdb.managers.change_tracker import ChangeTracker


class ChangeComparator:
    """Compares changes between branches to detect divergence and conflicts."""

    def __init__(self, project_root: Path, database_name: str):
        """Initialize the change comparator.

        Args:
            project_root: Path to the project root
            database_name: Name of the database
        """
        self.project_root = Path(project_root)
        self.database_name = database_name

    def get_branch_changes(self, branch_name: str) -> List[Change]:
        """Get all changes for a branch.

        Args:
            branch_name: Name of the branch

        Returns:
            List of changes in the branch
        """
        tracker = ChangeTracker(self.project_root, self.database_name, branch_name)
        return tracker.get_changes()

    def find_common_ancestor(
        self, source_branch: str, target_branch: str
    ) -> Optional[str]:
        """Find the common ancestor change between two branches.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            ID of the common ancestor change, or None if no common ancestor
        """
        source_changes = self.get_branch_changes(source_branch)
        target_changes = self.get_branch_changes(target_branch)

        # Convert to sets of change IDs for efficient lookup
        source_ids = {change.id for change in source_changes}
        target_ids = {change.id for change in target_changes}

        # Find common changes
        common_ids = source_ids & target_ids

        # Find the latest common change (highest timestamp)
        common_changes = [c for c in source_changes if c.id in common_ids]
        if not common_changes:
            return None

        return max(common_changes, key=lambda c: c.created_at).id

    def get_divergent_changes(
        self, source_branch: str, target_branch: str
    ) -> Tuple[List[Change], List[Change]]:
        """Get changes that diverge between two branches.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            Tuple of (source_only_changes, target_only_changes)
        """
        source_changes = self.get_branch_changes(source_branch)
        target_changes = self.get_branch_changes(target_branch)

        # Convert to sets of change IDs
        source_ids = {change.id for change in source_changes}
        target_ids = {change.id for change in target_changes}

        # Find changes unique to each branch
        source_only_ids = source_ids - target_ids
        target_only_ids = target_ids - source_ids

        # Get the actual change objects
        source_only = [c for c in source_changes if c.id in source_only_ids]
        target_only = [c for c in target_changes if c.id in target_only_ids]

        # Sort by timestamp for consistent ordering
        source_only.sort(key=lambda c: c.created_at)
        target_only.sort(key=lambda c: c.created_at)

        return source_only, target_only

    def can_fast_forward_merge(self, source_branch: str, target_branch: str) -> bool:
        """Check if source can be fast-forward merged into target.

        A fast-forward merge is possible when target branch has no changes
        that source doesn't have (target is ancestor of source).

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            True if fast-forward merge is possible
        """
        source_only, target_only = self.get_divergent_changes(
            source_branch, target_branch
        )

        # Fast-forward is possible if target has no unique changes
        return len(target_only) == 0 and len(source_only) > 0

    def detect_conflicts(self, source_branch: str, target_branch: str) -> List[str]:
        """Detect potential conflicts between two branches.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            List of conflict descriptions
        """
        source_only, target_only = self.get_divergent_changes(
            source_branch, target_branch
        )

        conflicts = []

        # Check for same table/column operations
        source_entities = set()
        target_entities = set()

        for change in source_only:
            if change.entity_type == "table":
                source_entities.add(f"table:{change.entity_name}")
            elif change.entity_type == "column":
                # Extract table name from SQL for column operations
                table_name = self._extract_table_from_column_sql(change.sql)
                if table_name:
                    source_entities.add(f"column:{table_name}.{change.entity_name}")

        for change in target_only:
            if change.entity_type == "table":
                target_entities.add(f"table:{change.entity_name}")
            elif change.entity_type == "column":
                table_name = self._extract_table_from_column_sql(change.sql)
                if table_name:
                    target_entities.add(f"column:{table_name}.{change.entity_name}")

        # Find overlapping entities
        overlapping = source_entities & target_entities
        if overlapping:
            conflicts.extend(
                [f"Both branches modified {entity}" for entity in overlapping]
            )

        return conflicts

    def _extract_table_from_column_sql(self, sql: str) -> Optional[str]:
        """Extract table name from column SQL statement.

        Args:
            sql: SQL statement for column operation

        Returns:
            Table name if found, None otherwise
        """
        # Simple extraction for common patterns
        # ALTER TABLE table_name ADD COLUMN ...
        # ALTER TABLE table_name DROP COLUMN ...
        # ALTER TABLE table_name RENAME COLUMN ...

        sql_upper = sql.upper().strip()
        if sql_upper.startswith("ALTER TABLE"):
            parts = sql.split()
            if len(parts) >= 3:
                return parts[2]  # table_name is the third part

        return None

    def get_merge_order(self, changes: List[Change]) -> List[Change]:
        """Get changes in the correct order for merging.

        Args:
            changes: List of changes to order

        Returns:
            Changes ordered by timestamp for safe merging
        """
        # Sort by timestamp to maintain chronological order
        return sorted(changes, key=lambda c: c.created_at)

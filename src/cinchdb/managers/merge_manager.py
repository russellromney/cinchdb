"""Branch merging functionality for CinchDB."""

from pathlib import Path
from typing import List, Dict, Any
from cinchdb.models import Change, ChangeType
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.managers.change_comparator import ChangeComparator
from cinchdb.managers.branch import BranchManager
from cinchdb.core.path_utils import list_tenants


class MergeError(Exception):
    """Exception raised when merge operations fail."""

    pass


class MergeManager:
    """Manages merging operations between branches."""

    def __init__(self, project_root: Path, database_name: str):
        """Initialize the merge manager.

        Args:
            project_root: Path to the project root
            database_name: Name of the database
        """
        self.project_root = Path(project_root)
        self.database_name = database_name
        self.comparator = ChangeComparator(project_root, database_name)
        self.branch_manager = BranchManager(project_root, database_name)

    def can_merge(self, source_branch: str, target_branch: str) -> Dict[str, Any]:
        """Check if source branch can be merged into target branch.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            Dictionary with merge status and details
        """
        # Check if branches exist
        if not self.branch_manager.branch_exists(source_branch):
            return {
                "can_merge": False,
                "reason": f"Source branch '{source_branch}' does not exist",
            }

        if not self.branch_manager.branch_exists(target_branch):
            return {
                "can_merge": False,
                "reason": f"Target branch '{target_branch}' does not exist",
            }

        # Check for conflicts
        conflicts = self.comparator.detect_conflicts(source_branch, target_branch)
        if conflicts:
            return {
                "can_merge": False,
                "reason": "Merge conflicts detected",
                "conflicts": conflicts,
            }

        # Check if there are changes to merge
        source_only, target_only = self.comparator.get_divergent_changes(
            source_branch, target_branch
        )
        if not source_only:
            return {
                "can_merge": False,
                "reason": "No changes to merge from source branch",
            }

        # Check merge type
        is_fast_forward = self.comparator.can_fast_forward_merge(
            source_branch, target_branch
        )

        return {
            "can_merge": True,
            "merge_type": "fast_forward" if is_fast_forward else "three_way",
            "changes_to_merge": len(source_only),
            "target_changes": len(target_only),
        }

    def _merge_branches_internal(
        self,
        source_branch: str,
        target_branch: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Internal merge method without main branch protection.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch
            force: If True, attempt merge even with conflicts
            dry_run: If True, return SQL statements without executing

        Returns:
            Dictionary with merge result details

        Raises:
            MergeError: If merge cannot be completed
        """
        # Check if merge is possible
        merge_check = self.can_merge(source_branch, target_branch)
        if not merge_check["can_merge"]:
            if not force:
                raise MergeError(f"Cannot merge: {merge_check['reason']}")
            elif "conflicts" in merge_check:
                raise MergeError(
                    f"Cannot force merge due to conflicts: {', '.join(merge_check['conflicts'])}"
                )

        # Get changes to merge
        source_only, _ = self.comparator.get_divergent_changes(
            source_branch, target_branch
        )
        if not source_only:
            return {
                "success": True,
                "message": "No changes to merge",
                "changes_merged": 0,
            }

        # Order changes for safe merging
        ordered_changes = self.comparator.get_merge_order(source_only)

        if dry_run:
            # Collect SQL statements that would be executed
            sql_statements = self._collect_sql_statements(
                ordered_changes, target_branch
            )
            return {
                "success": True,
                "dry_run": True,
                "message": f"Dry run: would merge {len(ordered_changes)} changes from '{source_branch}' to '{target_branch}'",
                "changes_to_merge": len(ordered_changes),
                "merge_type": merge_check.get("merge_type", "unknown"),
                "sql_statements": sql_statements,
            }

        try:
            # Apply changes to target branch atomically
            self._apply_changes_to_branch(ordered_changes, target_branch)

            return {
                "success": True,
                "message": f"Successfully merged {len(ordered_changes)} changes from '{source_branch}' to '{target_branch}'",
                "changes_merged": len(ordered_changes),
                "merge_type": merge_check.get("merge_type", "unknown"),
            }

        except Exception as e:
            raise MergeError(f"Merge failed during application: {str(e)}")

    def merge_branches(
        self,
        source_branch: str,
        target_branch: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Merge source branch into target branch.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch
            force: If True, attempt merge even with conflicts
            dry_run: If True, return SQL statements without executing

        Returns:
            Dictionary with merge result details

        Raises:
            MergeError: If merge cannot be completed
        """
        # Protect main branch from direct changes
        if target_branch == "main":
            raise MergeError(
                "Cannot merge directly into main branch. Main branch is protected."
            )

        # Use internal method for actual merge
        return self._merge_branches_internal(
            source_branch, target_branch, force, dry_run
        )

    def _apply_changes_to_branch(
        self, changes: List[Change], target_branch: str
    ) -> None:
        """Apply changes to target branch atomically.

        Args:
            changes: List of changes to apply
            target_branch: Name of the target branch

        Raises:
            MergeError: If changes cannot be applied
        """
        target_tracker = ChangeTracker(
            self.project_root, self.database_name, target_branch
        )
        target_applier = ChangeApplier(
            self.project_root, self.database_name, target_branch
        )

        # Get all tenants for the target branch
        list_tenants(self.project_root, self.database_name, target_branch)

        applied_changes = []

        try:
            for change in changes:
                # Create a copy of the change for the target branch, marking as unapplied
                # so it gets executed in the target branch's database
                change_copy = change.model_copy()
                change_copy.applied = False

                # Add change to target branch history
                target_tracker.add_change(change_copy)
                applied_changes.append(change_copy.id)

                # Apply change to all tenants in target branch
                target_applier.apply_change(change_copy.id)

        except Exception as e:
            # Rollback: remove changes that were added but not fully applied
            for change_id in applied_changes:
                try:
                    # Note: This is a simplified rollback - in production you'd want
                    # more sophisticated transaction handling
                    target_tracker.remove_change(change_id) if hasattr(
                        target_tracker, "remove_change"
                    ) else None
                except Exception:
                    pass  # Best effort rollback

            raise MergeError(f"Failed to apply changes: {str(e)}")

    def _collect_sql_statements(
        self, changes: List[Change], target_branch: str
    ) -> List[Dict[str, Any]]:
        """Collect SQL statements that would be executed for the given changes.

        Args:
            changes: List of changes to collect SQL for
            target_branch: Name of the target branch

        Returns:
            List of dictionaries with SQL statement information
        """
        sql_statements = []

        for change in changes:
            # Determine what SQL would be executed
            if change.details and "statements" in change.details:
                # Multiple statements in a transaction
                for step_name, sql in change.details["statements"]:
                    sql_statements.append(
                        {
                            "change_id": change.id,
                            "change_type": change.type.value
                            if hasattr(change.type, "value")
                            else change.type,
                            "entity_name": change.entity_name,
                            "step": step_name,
                            "sql": sql,
                        }
                    )
            elif change.type == ChangeType.UPDATE_VIEW:
                # View update requires DROP and CREATE
                sql_statements.append(
                    {
                        "change_id": change.id,
                        "change_type": change.type.value
                        if hasattr(change.type, "value")
                        else change.type,
                        "entity_name": change.entity_name,
                        "step": "drop_existing",
                        "sql": f"DROP VIEW IF EXISTS {change.entity_name}",
                    }
                )
                sql_statements.append(
                    {
                        "change_id": change.id,
                        "change_type": change.type.value
                        if hasattr(change.type, "value")
                        else change.type,
                        "entity_name": change.entity_name,
                        "step": "create_view",
                        "sql": change.sql,
                    }
                )
            elif (
                change.type == ChangeType.CREATE_TABLE
                and change.details
                and change.details.get("copy_sql")
            ):
                # Table copy operation
                sql_statements.append(
                    {
                        "change_id": change.id,
                        "change_type": change.type.value
                        if hasattr(change.type, "value")
                        else change.type,
                        "entity_name": change.entity_name,
                        "step": "create_table",
                        "sql": change.sql,
                    }
                )
                sql_statements.append(
                    {
                        "change_id": change.id,
                        "change_type": change.type.value
                        if hasattr(change.type, "value")
                        else change.type,
                        "entity_name": change.entity_name,
                        "step": "copy_data",
                        "sql": change.details["copy_sql"],
                    }
                )
            else:
                # Regular single statement
                sql_statements.append(
                    {
                        "change_id": change.id,
                        "change_type": change.type.value
                        if hasattr(change.type, "value")
                        else change.type,
                        "entity_name": change.entity_name,
                        "sql": change.sql,
                    }
                )

        return sql_statements

    def merge_into_main(
        self, source_branch: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Merge a branch into main branch with additional validation.

        This is the primary way to get changes into main branch.

        Args:
            source_branch: Name of the source branch to merge
            dry_run: If True, return SQL statements without executing

        Returns:
            Dictionary with merge result details

        Raises:
            MergeError: If merge cannot be completed
        """
        if source_branch == "main":
            raise MergeError("Cannot merge main branch into itself")

        # Additional validation for main branch merges
        merge_check = self.can_merge(source_branch, "main")
        if not merge_check["can_merge"]:
            raise MergeError(f"Cannot merge into main: {merge_check['reason']}")

        # Ensure source branch has all changes from main (is up to date)
        main_only, source_only = self.comparator.get_divergent_changes(
            "main", source_branch
        )
        if main_only:
            raise MergeError(
                f"Source branch '{source_branch}' is not up to date with main. "
                f"Pull latest changes from main first."
            )

        # Perform the merge (bypass protection for official merge into main)
        return self._merge_branches_internal(source_branch, "main", dry_run=dry_run)

    def get_merge_preview(
        self, source_branch: str, target_branch: str
    ) -> Dict[str, Any]:
        """Get a preview of what would happen during a merge.

        Args:
            source_branch: Name of the source branch
            target_branch: Name of the target branch

        Returns:
            Dictionary with merge preview details
        """
        merge_check = self.can_merge(source_branch, target_branch)

        if not merge_check["can_merge"]:
            return {
                "can_merge": False,
                "reason": merge_check["reason"],
                "conflicts": merge_check.get("conflicts", []),
            }

        source_only, target_only = self.comparator.get_divergent_changes(
            source_branch, target_branch
        )

        # Categorize changes by type
        changes_by_type = {}
        for change in source_only:
            entity_type = change.entity_type
            if entity_type not in changes_by_type:
                changes_by_type[entity_type] = []
            changes_by_type[entity_type].append(
                {
                    "id": change.id,
                    "entity_name": change.entity_name,
                    "operation": change.type,
                    "timestamp": change.created_at.isoformat(),
                }
            )

        return {
            "can_merge": True,
            "merge_type": merge_check.get("merge_type", "unknown"),
            "changes_to_merge": len(source_only),
            "target_has_changes": len(target_only) > 0,
            "changes_by_type": changes_by_type,
            "common_ancestor": self.comparator.find_common_ancestor(
                source_branch, target_branch
            ),
        }

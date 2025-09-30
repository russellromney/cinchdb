"""Tests for MergeManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.core.initializer import init_project
from cinchdb.managers.merge_manager import MergeManager, MergeError
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.base import ConnectionContext
from cinchdb.models import Change, ChangeType


class TestMergeManager:
    """Test the MergeManager class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Initialize project with main database and branch
        init_project(project_path)

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_can_merge_nonexistent_source(self, temp_project):
        """Test merge check with nonexistent source branch."""
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        result = merge_mgr.can_merge("nonexistent", "main")

        assert not result["can_merge"]
        assert "does not exist" in result["reason"]

    def test_can_merge_nonexistent_target(self, temp_project):
        """Test merge check with nonexistent target branch."""
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        result = merge_mgr.can_merge("main", "nonexistent")

        assert not result["can_merge"]
        assert "does not exist" in result["reason"]

    def test_can_merge_no_changes(self, temp_project):
        """Test merge check when source has no changes to merge."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.can_merge("feature", "main")

        assert not result["can_merge"]
        assert "No changes to merge" in result["reason"]

    def test_can_merge_with_changes(self, temp_project):
        """Test merge check when merge is possible."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Add change to feature branch
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.can_merge("feature", "main")

        assert result["can_merge"]
        assert result["merge_type"] == "fast_forward"
        assert result["changes_to_merge"] == 1
        assert result["target_changes"] == 0

    def test_can_merge_with_conflicts(self, temp_project):
        """Test merge check when conflicts exist."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature1")
        branch_mgr.create_branch("main", "feature2")

        # Add conflicting changes
        tracker1 = ChangeTracker(temp_project, "main", "feature1")
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature1",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)",
        )
        tracker1.add_change(change1)

        tracker2 = ChangeTracker(temp_project, "main", "feature2")
        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature2",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT)",
        )
        tracker2.add_change(change2)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.can_merge("feature1", "feature2")

        assert not result["can_merge"]
        assert "conflicts detected" in result["reason"]
        assert "conflicts" in result

    def test_merge_branches_success(self, temp_project):
        """Test successful branch merge."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")
        branch_mgr.create_branch("main", "target")

        # Add change to feature branch
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_branches("feature", "target")

        assert result["success"]
        assert result["changes_merged"] == 1
        assert "Successfully merged" in result["message"]

        # Verify change was copied to target
        target_tracker = ChangeTracker(temp_project, "main", "target")
        target_changes = target_tracker.get_changes()
        assert len(target_changes) == 1
        assert target_changes[0].entity_name == "users"

    def test_merge_branches_into_main_blocked(self, temp_project):
        """Test that merging into main branch is blocked."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Add change to feature
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        with pytest.raises(MergeError) as exc_info:
            merge_mgr.merge_branches("feature", "main")

        assert "protected" in str(exc_info.value)

    def test_merge_branches_with_conflicts_fails(self, temp_project):
        """Test merge fails when conflicts exist."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature1")
        branch_mgr.create_branch("main", "feature2")

        # Add conflicting changes
        tracker1 = ChangeTracker(temp_project, "main", "feature1")
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature1",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)",
        )
        tracker1.add_change(change1)

        tracker2 = ChangeTracker(temp_project, "main", "feature2")
        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature2",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT)",
        )
        tracker2.add_change(change2)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        with pytest.raises(MergeError) as exc_info:
            merge_mgr.merge_branches("feature1", "feature2")

        assert "Cannot merge" in str(exc_info.value)

    def test_merge_into_main_success(self, temp_project):
        """Test successful merge into main branch."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Add change to feature
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_into_main("feature")

        assert result["success"]
        assert result["changes_merged"] == 1

        # Verify change was merged into main
        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_changes = main_tracker.get_changes()
        assert len(main_changes) == 1
        assert main_changes[0].entity_name == "users"

    def test_merge_into_main_self_fails(self, temp_project):
        """Test merging main into itself fails."""
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        with pytest.raises(MergeError) as exc_info:
            merge_mgr.merge_into_main("main")

        assert "into itself" in str(exc_info.value)

    def test_merge_into_main_not_up_to_date(self, temp_project):
        """Test merge into main fails when source is not up to date."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        # Add change to main first
        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="base",
            branch="main",
            sql="CREATE TABLE base (id TEXT PRIMARY KEY)",
        )
        main_tracker.add_change(main_change)

        # Create feature branch (won't have main's new change)
        branch_mgr.create_branch("main", "feature")

        # Add another change to main after branch creation
        new_main_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="new_table",
            branch="main",
            sql="CREATE TABLE new_table (id TEXT PRIMARY KEY)",
        )
        main_tracker.add_change(new_main_change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        with pytest.raises(MergeError) as exc_info:
            merge_mgr.merge_into_main("feature")

        assert "No changes to merge" in str(exc_info.value)

    def test_get_merge_preview(self, temp_project):
        """Test getting merge preview."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Add changes to feature
        tracker = ChangeTracker(temp_project, "main", "feature")
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change1)

        change2 = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name="email",
            branch="feature",
            sql="ALTER TABLE users ADD COLUMN email TEXT",
        )
        tracker.add_change(change2)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        preview = merge_mgr.get_merge_preview("feature", "main")

        assert preview["can_merge"]
        assert preview["merge_type"] == "fast_forward"
        assert preview["changes_to_merge"] == 2
        assert not preview["target_has_changes"]

        # Check changes by type
        assert "table" in preview["changes_by_type"]
        assert "column" in preview["changes_by_type"]
        assert len(preview["changes_by_type"]["table"]) == 1
        assert len(preview["changes_by_type"]["column"]) == 1

    def test_get_merge_preview_cannot_merge(self, temp_project):
        """Test merge preview when merge is not possible."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # No changes in feature branch
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        preview = merge_mgr.get_merge_preview("feature", "main")

        assert not preview["can_merge"]
        assert "No changes to merge" in preview["reason"]

    def test_merge_branches_dry_run(self, temp_project):
        """Test dry-run merge returns SQL statements without applying."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")
        branch_mgr.create_branch("main", "target")

        # Add changes to feature branch
        tracker = ChangeTracker(temp_project, "main", "feature")

        # Add a table
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)",
        )
        tracker.add_change(change1)

        # Add a column
        change2 = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name="email",
            branch="feature",
            sql="ALTER TABLE users ADD COLUMN email TEXT",
            details={"table": "users"},
        )
        tracker.add_change(change2)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_branches("feature", "target", dry_run=True)

        assert result["success"]
        assert result["dry_run"] is True
        assert "Dry run" in result["message"]
        assert result["changes_to_merge"] == 2
        assert "sql_statements" in result
        assert len(result["sql_statements"]) == 2

        # Check SQL statement structure
        stmt1 = result["sql_statements"][0]
        assert stmt1["change_id"] == change1.id
        assert stmt1["change_type"] == "create_table"
        assert stmt1["entity_name"] == "users"
        assert stmt1["sql"] == "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)"

        stmt2 = result["sql_statements"][1]
        assert stmt2["change_id"] == change2.id
        assert stmt2["change_type"] == "add_column"
        assert stmt2["entity_name"] == "email"
        assert stmt2["sql"] == "ALTER TABLE users ADD COLUMN email TEXT"

        # Verify no changes were actually applied to target
        target_tracker = ChangeTracker(temp_project, "main", "target")
        target_changes = target_tracker.get_changes()
        assert len(target_changes) == 0

    def test_merge_into_main_dry_run(self, temp_project):
        """Test dry-run merge into main returns SQL statements without applying."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Add a view change to feature
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.UPDATE_VIEW,
            entity_type="view",
            entity_name="user_stats",
            branch="feature",
            sql="CREATE VIEW user_stats AS SELECT COUNT(*) as total FROM users",
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_into_main("feature", dry_run=True)

        assert result["success"]
        assert result["dry_run"] is True
        assert "sql_statements" in result

        # View updates produce two statements: DROP and CREATE
        assert len(result["sql_statements"]) == 2

        stmt1 = result["sql_statements"][0]
        assert stmt1["step"] == "drop_existing"
        assert stmt1["sql"] == "DROP VIEW IF EXISTS user_stats"

        stmt2 = result["sql_statements"][1]
        assert stmt2["step"] == "create_view"
        assert (
            stmt2["sql"]
            == "CREATE VIEW user_stats AS SELECT COUNT(*) as total FROM users"
        )

        # Verify no changes were applied to main
        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_changes = main_tracker.get_changes()
        assert len(main_changes) == 0

    def test_merge_branches_dry_run_complex_changes(self, temp_project):
        """Test dry-run with complex changes including table copy."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")
        branch_mgr.create_branch("main", "target")

        # Add complex change with copy SQL
        tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users_backup",
            branch="feature",
            sql="CREATE TABLE users_backup (id TEXT PRIMARY KEY, name TEXT)",
            details={"copy_sql": "INSERT INTO users_backup SELECT * FROM users"},
        )
        tracker.add_change(change)

        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_branches("feature", "target", dry_run=True)

        assert result["success"]
        assert len(result["sql_statements"]) == 2

        # Table copy produces two statements
        stmt1 = result["sql_statements"][0]
        assert stmt1["step"] == "create_table"
        assert "CREATE TABLE users_backup" in stmt1["sql"]

        stmt2 = result["sql_statements"][1]
        assert stmt2["step"] == "copy_data"
        assert "INSERT INTO users_backup" in stmt2["sql"]

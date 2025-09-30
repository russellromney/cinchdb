"""Integration tests for branch creation with change tracking."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.models import Column, Change, ChangeType


class TestBranchChangeIntegration:
    """Test that branch creation properly copies changes."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        init_project(project_dir)
        yield project_dir
        shutil.rmtree(temp)

    def test_new_branch_inherits_changes(self, temp_project):
        """Test that a new branch inherits all changes from its parent."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        table_mgr.create_table(
            "users",
            [
                Column(name="user_id", type="TEXT", nullable=False),
                Column(name="email", type="TEXT", nullable=False),
            ]
        )

        # Get changes in main
        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_changes = main_tracker.get_changes()
        assert len(main_changes) > 0  # Should have CREATE TABLE change

        # Create feature branch
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Feature branch should have all main's changes
        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        feature_changes = feature_tracker.get_changes()

        # Should have same number of changes
        assert len(feature_changes) == len(main_changes)

        # Should be the same change IDs
        main_ids = {c.id for c in main_changes}
        feature_ids = {c.id for c in feature_changes}
        assert main_ids == feature_ids

    def test_branch_after_merge_has_all_changes(self, temp_project):
        """Test that branching after a merge includes merged changes."""
        # Create feature1 branch and add a table
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature1")
        table_mgr1 = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature1", tenant="main"))
        table_mgr1.create_table(
            "products",
            [Column(name="name", type="TEXT", nullable=False)]
        )

        # Merge feature1 to main
        from cinchdb.managers.merge_manager import MergeManager
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_branches("feature1", "main")
        assert result["success"]

        # Create feature2 from updated main
        branch_mgr.create_branch("main", "feature2")

        # feature2 should have the products table change
        feature2_tracker = ChangeTracker(temp_project, "main", "feature2")
        feature2_changes = feature2_tracker.get_changes()

        # Should have the CREATE TABLE products change
        table_changes = [c for c in feature2_changes if c.entity_name == "products"]
        assert len(table_changes) > 0
        assert table_changes[0].type == ChangeType.CREATE_TABLE

    def test_divergent_branches_track_correctly(self, temp_project):
        """Test that divergent branches correctly track their changes."""
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

        # Create two feature branches from main
        branch_mgr.create_branch("main", "feature_a")
        branch_mgr.create_branch("main", "feature_b")

        # Add different tables to each branch
        table_mgr_a = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature_a", tenant="main"))
        table_mgr_a.create_table(
            "table_a",
            [Column(name="item_id", type="INTEGER", nullable=False)]
        )

        table_mgr_b = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature_b", tenant="main"))
        table_mgr_b.create_table(
            "table_b",
            [Column(name="item_id", type="INTEGER", nullable=False)]
        )

        # Get changes from each branch
        tracker_a = ChangeTracker(temp_project, "main", "feature_a")
        tracker_b = ChangeTracker(temp_project, "main", "feature_b")

        changes_a = tracker_a.get_changes()
        changes_b = tracker_b.get_changes()

        # Find new changes in each branch
        table_a_changes = [c for c in changes_a if c.entity_name == "table_a"]
        table_b_changes = [c for c in changes_b if c.entity_name == "table_b"]

        # feature_a should have table_a but not table_b
        assert len(table_a_changes) == 1
        assert not any(c.entity_name == "table_b" for c in changes_a)

        # feature_b should have table_b but not table_a
        assert len(table_b_changes) == 1
        assert not any(c.entity_name == "table_a" for c in changes_b)

    def test_applied_status_preserved_on_copy(self, temp_project):
        """Test that applied status is preserved when copying changes."""
        # Create table in main branch
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        table_mgr.create_table(
            "users",
            [Column(name="user_id", type="TEXT", nullable=False)]
        )

        # Mark changes as applied
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        for change in changes:
            tracker.mark_change_applied(change.id)

        # Verify they're applied in main
        main_changes = tracker.get_changes()
        assert all(c.applied for c in main_changes)

        # Create new branch
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Changes should still be marked as applied in new branch
        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        feature_changes = feature_tracker.get_changes()
        assert all(c.applied for c in feature_changes)

    def test_change_order_preserved_on_copy(self, temp_project):
        """Test that change order is preserved when creating branches."""
        # Create multiple tables in main branch
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))

        tables = ["users", "products", "orders", "reviews"]
        for table_name in tables:
            table_mgr.create_table(
                table_name,
                [Column(name="item_id", type="INTEGER", nullable=False)]
            )

        # Get main changes
        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_changes = main_tracker.get_changes()

        # Create new branch
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")

        # Get feature changes
        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        feature_changes = feature_tracker.get_changes()

        # Order should be preserved
        assert len(feature_changes) == len(main_changes)
        for i, (main_change, feature_change) in enumerate(zip(main_changes, feature_changes)):
            assert main_change.id == feature_change.id
            assert main_change.entity_name == feature_change.entity_name
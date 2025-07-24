"""Tests for ChangeComparator."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.config import Config
from cinchdb.managers.change_comparator import ChangeComparator
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.branch import BranchManager
from cinchdb.models import Change, ChangeType


class TestChangeComparator:
    """Test the ChangeComparator class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Initialize project with main database and branch
        config = Config(project_path)
        config.init_project()

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_get_branch_changes(self, temp_project):
        """Test getting changes for a branch."""
        comparator = ChangeComparator(temp_project, "main")

        # Initially no changes
        changes = comparator.get_branch_changes("main")
        assert len(changes) == 0

        # Add a change
        tracker = ChangeTracker(temp_project, "main", "main")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change)

        # Should now have one change
        changes = comparator.get_branch_changes("main")
        assert len(changes) == 1
        assert changes[0].entity_name == "users"

    def test_find_common_ancestor_no_common(self, temp_project):
        """Test finding common ancestor when branches have no common changes."""
        # Create two branches with different changes
        branch_mgr = BranchManager(temp_project, "main")
        branch_mgr.create_branch("main", "feature1")
        branch_mgr.create_branch("main", "feature2")

        # Add different changes to each branch
        tracker1 = ChangeTracker(temp_project, "main", "feature1")
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="feature1",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
        )
        tracker1.add_change(change1)

        tracker2 = ChangeTracker(temp_project, "main", "feature2")
        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="posts",
            branch="feature2",
            sql="CREATE TABLE posts (id TEXT PRIMARY KEY)",
        )
        tracker2.add_change(change2)

        comparator = ChangeComparator(temp_project, "main")
        ancestor = comparator.find_common_ancestor("feature1", "feature2")
        assert ancestor is None

    def test_find_common_ancestor_with_common(self, temp_project):
        """Test finding common ancestor when branches have common changes."""
        branch_mgr = BranchManager(temp_project, "main")

        # Add common change to both branches
        main_tracker = ChangeTracker(temp_project, "main", "main")
        common_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="base",
            branch="main",
            sql="CREATE TABLE base (id TEXT PRIMARY KEY)",
        )
        main_tracker.add_change(common_change)

        # Create feature branch
        branch_mgr.create_branch("main", "feature")

        # Add the same common change to feature branch (simulating shared history)
        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        feature_tracker.add_change(common_change)

        # Add unique change to feature
        feature_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="feature_table",
            branch="feature",
            sql="CREATE TABLE feature_table (id TEXT PRIMARY KEY)",
        )
        feature_tracker.add_change(feature_change)

        comparator = ChangeComparator(temp_project, "main")
        ancestor = comparator.find_common_ancestor("main", "feature")
        assert ancestor == common_change.id

    def test_get_divergent_changes(self, temp_project):
        """Test getting divergent changes between branches."""
        branch_mgr = BranchManager(temp_project, "main")
        branch_mgr.create_branch("main", "feature")

        # Add common change to both branches
        common_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="base",
            branch="main",
            sql="CREATE TABLE base (id TEXT PRIMARY KEY)",
        )

        main_tracker = ChangeTracker(temp_project, "main", "main")
        main_tracker.add_change(common_change)

        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        feature_tracker.add_change(common_change)  # Same change in both branches

        # Add unique change to main
        main_unique = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="main_table",
            branch="main",
            sql="CREATE TABLE main_table (id TEXT PRIMARY KEY)",
        )
        main_tracker.add_change(main_unique)

        # Add unique change to feature
        feature_unique = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="feature_table",
            branch="feature",
            sql="CREATE TABLE feature_table (id TEXT PRIMARY KEY)",
        )
        feature_tracker.add_change(feature_unique)

        comparator = ChangeComparator(temp_project, "main")
        main_only, feature_only = comparator.get_divergent_changes("main", "feature")

        assert len(main_only) == 1
        assert main_only[0].entity_name == "main_table"

        assert len(feature_only) == 1
        assert feature_only[0].entity_name == "feature_table"

    def test_can_fast_forward_merge(self, temp_project):
        """Test fast-forward merge detection."""
        branch_mgr = BranchManager(temp_project, "main")
        branch_mgr.create_branch("main", "feature")

        # Add change only to feature branch (fast-forward scenario)
        feature_tracker = ChangeTracker(temp_project, "main", "feature")
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="new_table",
            branch="feature",
            sql="CREATE TABLE new_table (id TEXT PRIMARY KEY)",
        )
        feature_tracker.add_change(change)

        comparator = ChangeComparator(temp_project, "main")

        # Feature -> main should be fast-forward
        assert comparator.can_fast_forward_merge("feature", "main")

        # Main -> feature should not be fast-forward (no changes to merge)
        assert not comparator.can_fast_forward_merge("main", "feature")

    def test_detect_conflicts(self, temp_project):
        """Test conflict detection between branches."""
        branch_mgr = BranchManager(temp_project, "main")
        branch_mgr.create_branch("main", "feature1")
        branch_mgr.create_branch("main", "feature2")

        # Add conflicting table changes
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

        comparator = ChangeComparator(temp_project, "main")
        conflicts = comparator.detect_conflicts("feature1", "feature2")

        assert len(conflicts) == 1
        assert "table:users" in conflicts[0]

    def test_get_merge_order(self, temp_project):
        """Test getting changes in correct merge order."""
        branch_mgr = BranchManager(temp_project, "main")
        branch_mgr.create_branch("main", "feature")

        tracker = ChangeTracker(temp_project, "main", "feature")

        # Add changes with different timestamps
        import time

        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="first",
            branch="feature",
            sql="CREATE TABLE first (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change1)

        time.sleep(0.001)  # Ensure different timestamps

        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="second",
            branch="feature",
            sql="CREATE TABLE second (id TEXT PRIMARY KEY)",
        )
        tracker.add_change(change2)

        comparator = ChangeComparator(temp_project, "main")
        ordered = comparator.get_merge_order(
            [change2, change1]
        )  # Pass in reverse order

        # Should be ordered by timestamp
        assert ordered[0].entity_name == "first"
        assert ordered[1].entity_name == "second"

    def test_extract_table_from_column_sql(self, temp_project):
        """Test extracting table name from column SQL."""
        comparator = ChangeComparator(temp_project, "main")

        # Test ADD COLUMN
        sql = "ALTER TABLE users ADD COLUMN email TEXT"
        table = comparator._extract_table_from_column_sql(sql)
        assert table == "users"

        # Test DROP COLUMN
        sql = "ALTER TABLE posts DROP COLUMN content"
        table = comparator._extract_table_from_column_sql(sql)
        assert table == "posts"

        # Test RENAME COLUMN
        sql = "ALTER TABLE accounts RENAME COLUMN old_name TO new_name"
        table = comparator._extract_table_from_column_sql(sql)
        assert table == "accounts"

        # Test non-ALTER TABLE statement
        sql = "CREATE TABLE test (id TEXT PRIMARY KEY)"
        table = comparator._extract_table_from_column_sql(sql)
        assert table is None

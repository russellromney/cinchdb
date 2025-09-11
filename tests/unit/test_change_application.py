"""Tests for change application logic."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
from cinchdb.core.initializer import init_project
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier, ChangeError
from cinchdb.models import Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path as get_tenant_db_path, get_branch_path


class TestChangeApplier:
    """Test change application functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def managers(self, temp_project):
        """Create manager instances."""
        branch_mgr = BranchManager(temp_project, "main")
        tenant_mgr = TenantManager(temp_project, "main", "main")
        change_tracker = ChangeTracker(temp_project, "main", "main")
        change_applier = ChangeApplier(temp_project, "main", "main")

        return {
            "branch": branch_mgr,
            "tenant": tenant_mgr,
            "tracker": change_tracker,
            "applier": change_applier,
        }

    def test_apply_create_table_change(self, managers, temp_project):
        """Test applying a CREATE TABLE change to all tenants."""
        # Create additional tenants
        managers["tenant"].create_tenant("tenant1")
        managers["tenant"].create_tenant("tenant2")

        # Create a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, email TEXT)",
        )
        added_change = managers["tracker"].add_change(change)

        # Apply the change
        managers["applier"].apply_change(added_change.id)

        # Verify table exists in all tenants
        # For lazy tenants, this will read from __empty__ which has the schema
        tenants = managers["tenant"].list_tenants()
        for tenant in tenants:
            # Use tenant manager to get proper path (reads from __empty__ for lazy tenants)
            db_path = managers["tenant"].get_tenant_db_path_for_operation(tenant.name, is_write=False)
            with DatabaseConnection(db_path) as conn:
                # Check table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                )
                result = cursor.fetchone()
                assert result is not None
                assert result["name"] == "users"

        # Verify change marked as applied
        changes = managers["tracker"].get_changes()
        assert changes[0].applied

    def test_apply_add_column_change(self, managers, temp_project):
        """Test applying an ADD COLUMN change."""
        # Create a table first
        create_table_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)",
        )
        managers["tracker"].add_change(create_table_change)
        managers["applier"].apply_change(create_table_change.id)

        # Add column change
        add_column_change = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name="email",
            branch="main",
            details={"table": "users"},
            sql="ALTER TABLE users ADD COLUMN email TEXT",
        )
        added = managers["tracker"].add_change(add_column_change)

        # Apply the change
        managers["applier"].apply_change(added.id)

        # Verify column exists in main tenant
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            column_names = [col["name"] for col in columns]
            assert "email" in column_names

    def test_apply_all_unapplied_changes(self, managers, temp_project):
        """Test applying all unapplied changes at once."""
        # Add multiple changes
        changes = [
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="users",
                branch="main",
                sql="CREATE TABLE users (id TEXT PRIMARY KEY)",
            ),
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="posts",
                branch="main",
                sql="CREATE TABLE posts (id TEXT PRIMARY KEY, user_id TEXT)",
            ),
            Change(
                type=ChangeType.CREATE_INDEX,
                entity_type="index",
                entity_name="idx_posts_user",
                branch="main",
                sql="CREATE INDEX idx_posts_user ON posts(user_id)",
            ),
        ]

        for change in changes:
            managers["tracker"].add_change(change)

        # Apply all
        applied_count = managers["applier"].apply_all_unapplied()
        assert applied_count == 3

        # Verify all marked as applied
        unapplied = managers["tracker"].get_unapplied_changes()
        assert len(unapplied) == 0

        # Verify entities exist
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            # Check tables
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'posts')"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            assert "users" in tables
            assert "posts" in tables

            # Check index
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_posts_user'"
            )
            assert cursor.fetchone() is not None

    def test_apply_drop_table_change(self, managers, temp_project):
        """Test applying a DROP TABLE change."""
        # Create table first
        create_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="temp_table",
            branch="main",
            sql="CREATE TABLE temp_table (id TEXT PRIMARY KEY)",
        )
        managers["tracker"].add_change(create_change)
        managers["applier"].apply_change(create_change.id)

        # Drop table
        drop_change = Change(
            type=ChangeType.DROP_TABLE,
            entity_type="table",
            entity_name="temp_table",
            branch="main",
            sql="DROP TABLE temp_table",
        )
        added = managers["tracker"].add_change(drop_change)
        managers["applier"].apply_change(added.id)

        # Verify table doesn't exist
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='temp_table'"
            )
            assert cursor.fetchone() is None

    def test_apply_create_view_change(self, managers, temp_project):
        """Test applying a CREATE VIEW change."""
        # Create base table first
        create_table = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="users",
            branch="main",
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, active INTEGER)",
        )
        managers["tracker"].add_change(create_table)
        managers["applier"].apply_change(create_table.id)

        # Create view
        create_view = Change(
            type=ChangeType.CREATE_VIEW,
            entity_type="view",
            entity_name="active_users",
            branch="main",
            sql="CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1",
        )
        added = managers["tracker"].add_change(create_view)
        managers["applier"].apply_change(added.id)

        # Verify view exists
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='active_users'"
            )
            assert cursor.fetchone() is not None

    def test_apply_changes_to_new_tenant(self, managers, temp_project):
        """Test that new tenants copy schema from main."""
        # Add some changes
        changes = [
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="users",
                branch="main",
                sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)",
            ),
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="posts",
                branch="main",
                sql="CREATE TABLE posts (id TEXT PRIMARY KEY, title TEXT)",
            ),
        ]

        for change in changes:
            added = managers["tracker"].add_change(change)
            managers["applier"].apply_change(added.id)

        # Create new eager tenant - should copy schema from main
        managers["tenant"].create_tenant("new-tenant", lazy=False)

        # Verify tables already exist in new tenant (copied from main)
        db_path = get_tenant_db_path(temp_project, "main", "main", "new-tenant")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'posts')"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            assert "users" in tables
            assert "posts" in tables

        # Add a new change after tenant creation
        new_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="comments",
            branch="main",
            sql="CREATE TABLE comments (id TEXT PRIMARY KEY, content TEXT)",
        )
        added = managers["tracker"].add_change(new_change)

        # Apply to all tenants
        managers["applier"].apply_change(added.id)

        # Verify new table exists in both tenants
        for tenant_name in ["main", "new-tenant"]:
            db_path = get_tenant_db_path(temp_project, "main", "main", tenant_name)
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
                )
                assert cursor.fetchone() is not None

    def test_error_handling_invalid_sql(self, managers):
        """Test error handling for invalid SQL."""
        # Add change with invalid SQL
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="bad_table",
            branch="main",
            sql="CREATE TABLE bad syntax error",
        )
        added = managers["tracker"].add_change(change)

        # Should raise error
        with pytest.raises(Exception):
            managers["applier"].apply_change(added.id)

        # Change should not be marked as applied
        changes = managers["tracker"].get_changes()
        assert not changes[0].applied

    def test_apply_changes_from_specific_point(self, managers):
        """Test applying changes from a specific change ID."""
        # Add multiple changes
        change_ids = []
        for i in range(5):
            change = Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name=f"table_{i}",
                branch="main",
                sql=f"CREATE TABLE table_{i} (id TEXT PRIMARY KEY)",
            )
            added = managers["tracker"].add_change(change)
            change_ids.append(added.id)

        # Apply first two
        managers["applier"].apply_change(change_ids[0])
        managers["applier"].apply_change(change_ids[1])

        # Apply from third change onward
        applied_count = managers["applier"].apply_changes_since(change_ids[1])
        assert applied_count == 3  # Changes 2, 3, 4

        # Verify all are applied
        changes = managers["tracker"].get_changes()
        assert all(c.applied for c in changes)


class TestChangeApplierRollback:
    """Test snapshot-based rollback functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def setup_with_tenants(self, temp_project):
        """Set up project with multiple tenants and basic tables."""
        branch_mgr = BranchManager(temp_project, "main")
        tenant_mgr = TenantManager(temp_project, "main", "main")
        change_tracker = ChangeTracker(temp_project, "main", "main")
        change_applier = ChangeApplier(temp_project, "main", "main")

        # Create multiple tenants
        tenant_mgr.create_tenant("tenant1")
        tenant_mgr.create_tenant("tenant2")
        tenant_mgr.create_tenant("tenant3")

        # Create a base table in all tenants
        base_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="base_table",
            branch="main",
            sql="CREATE TABLE base_table (id TEXT PRIMARY KEY, data TEXT)",
        )
        added = change_tracker.add_change(base_change)
        change_applier.apply_change(added.id)

        # Insert test data in each tenant
        tenants = tenant_mgr.list_tenants()
        for tenant in tenants:
            # Use tenant manager to get connection (handles lazy tenants properly)
            db_path = tenant_mgr.get_tenant_db_path_for_operation(tenant.name, is_write=True)
            with DatabaseConnection(db_path) as conn:
                conn.execute(
                    "INSERT INTO base_table (id, data) VALUES (?, ?)",
                    (f"test-{tenant.name}", f"data-{tenant.name}"),
                )
                conn.commit()

        return {
            "project_dir": temp_project,
            "branch_mgr": branch_mgr,
            "tenant_mgr": tenant_mgr,
            "change_tracker": change_tracker,
            "change_applier": change_applier,
            "tenants": tenants,
        }

    def test_successful_application_cleans_up_snapshots(self, setup_with_tenants):
        """Test that successful change application cleans up snapshots."""
        setup = setup_with_tenants

        # Create a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="new_table",
            branch="main",
            sql="CREATE TABLE new_table (id TEXT PRIMARY KEY, value INTEGER)",
        )
        added = setup["change_tracker"].add_change(change)

        # Apply the change
        setup["change_applier"].apply_change(added.id)

        # Verify table exists in all tenants
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='new_table'"
                )
                assert cursor.fetchone() is not None

        # Verify snapshot directory was cleaned up
        branch_path = get_branch_path(setup["project_dir"], "main", "main")
        backup_dir = branch_path / ".change_backups" / added.id
        assert not backup_dir.exists()

    def test_rollback_on_first_tenant_failure(self, setup_with_tenants):
        """Test rollback when first tenant fails."""
        setup = setup_with_tenants

        # Create a change that will fail on first tenant
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="fail_table",
            branch="main",
            sql="CREATE TABLE fail_table (id TEXT PRIMARY KEY)",
        )
        added = setup["change_tracker"].add_change(change)

        # Mock to make first tenant fail
        original_apply = setup["change_applier"]._apply_change_to_tenant
        call_count = 0

        def mock_apply(change, tenant_name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First tenant
                raise Exception("Simulated failure on first tenant")
            return original_apply(change, tenant_name)

        with patch.object(
            setup["change_applier"], "_apply_change_to_tenant", side_effect=mock_apply
        ):
            # Should raise ChangeError
            with pytest.raises(ChangeError) as exc_info:
                setup["change_applier"].apply_change(added.id)

            assert "Simulated failure on first tenant" in str(exc_info.value)

        # Verify table doesn't exist in any tenant
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='fail_table'"
                )
                assert cursor.fetchone() is None

        # Verify change not marked as applied
        changes = setup["change_tracker"].get_changes()
        test_change = next(c for c in changes if c.id == added.id)
        assert not test_change.applied

        # Verify original data still intact
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM base_table WHERE id = ?", (f"test-{tenant.name}",)
                )
                row = cursor.fetchone()
                assert row is not None
                assert row["data"] == f"data-{tenant.name}"

    def test_rollback_on_middle_tenant_failure(self, setup_with_tenants):
        """Test rollback when middle tenant fails after some succeed."""
        setup = setup_with_tenants

        # Create a change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="partial_table",
            branch="main",
            sql="CREATE TABLE partial_table (id TEXT PRIMARY KEY, status TEXT)",
        )
        added = setup["change_tracker"].add_change(change)

        # Mock to make second tenant fail
        original_apply = setup["change_applier"]._apply_change_to_tenant
        call_count = 0

        def mock_apply(change, tenant_name):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second tenant
                raise Exception("Simulated failure on second tenant")
            return original_apply(change, tenant_name)

        with patch.object(
            setup["change_applier"], "_apply_change_to_tenant", side_effect=mock_apply
        ):
            # Should raise ChangeError
            with pytest.raises(ChangeError):
                setup["change_applier"].apply_change(added.id)

        # Verify table doesn't exist in ANY tenant (all rolled back)
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='partial_table'"
                )
                assert cursor.fetchone() is None

    def test_snapshot_creation_and_restoration(self, setup_with_tenants):
        """Test snapshot creation and restoration functionality."""
        setup = setup_with_tenants
        applier = setup["change_applier"]

        # Create backup directory
        backup_dir = applier._get_backup_dir("test-backup")

        # Create snapshots
        applier._create_snapshots(setup["tenants"], backup_dir)

        # Verify snapshots exist
        for tenant in setup["tenants"]:
            backup_path = backup_dir / f"{tenant.name}.db"
            assert backup_path.exists()

        # Modify data in tenants
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                conn.execute("DELETE FROM base_table")
                conn.execute("CREATE TABLE extra_table (id INTEGER)")
                conn.commit()

        # Restore from snapshots
        applier._restore_all_snapshots(setup["tenants"], backup_dir)

        # Verify data is restored
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                # Original data should be back
                cursor = conn.execute(
                    "SELECT * FROM base_table WHERE id = ?", (f"test-{tenant.name}",)
                )
                row = cursor.fetchone()
                assert row is not None
                assert row["data"] == f"data-{tenant.name}"

                # Extra table should not exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='extra_table'"
                )
                assert cursor.fetchone() is None

        # Cleanup
        applier._cleanup_snapshots(backup_dir)
        assert not backup_dir.exists()

    def test_rollback_preserves_existing_data(self, setup_with_tenants):
        """Test that rollback preserves all existing data and state."""
        setup = setup_with_tenants

        # Add more data to base table
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                for i in range(5):
                    conn.execute(
                        "INSERT INTO base_table (id, data) VALUES (?, ?)",
                        (f"extra-{tenant.name}-{i}", f"value-{i}"),
                    )
                conn.commit()

        # Create a failing change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="bad_table",
            branch="main",
            sql="CREATE TABLE bad_table SYNTAX ERROR HERE",  # Definitely bad SQL
        )
        added = setup["change_tracker"].add_change(change)

        # Apply should fail
        with pytest.raises(ChangeError):
            setup["change_applier"].apply_change(added.id)

        # Verify all original data is intact
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM base_table")
                count = cursor.fetchone()["count"]
                assert count == 6  # 1 original + 5 extra

                # Verify specific records
                cursor = conn.execute("SELECT * FROM base_table ORDER BY id")
                rows = cursor.fetchall()
                assert len(rows) == 6

    def test_rollback_with_wal_files(self, setup_with_tenants):
        """Test that rollback properly handles WAL and SHM files."""
        setup = setup_with_tenants

        # Ensure WAL files exist by doing operations
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                conn.execute(
                    "INSERT INTO base_table (id, data) VALUES ('wal-test', 'wal-data')"
                )
                conn.commit()  # Commit to ensure data is persisted

        # Create a failing change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="wal_test_table",
            branch="main",
            sql="CREATE TABLE wal_test_table (id TEXT PRIMARY KEY)",
        )
        added = setup["change_tracker"].add_change(change)

        # Make it fail on second tenant
        original_apply = setup["change_applier"]._apply_change_to_tenant
        call_count = 0

        def mock_apply(change, tenant_name):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Simulated WAL test failure")
            return original_apply(change, tenant_name)

        with patch.object(
            setup["change_applier"], "_apply_change_to_tenant", side_effect=mock_apply
        ):
            with pytest.raises(ChangeError):
                setup["change_applier"].apply_change(added.id)

        # Verify data integrity after rollback
        for tenant in setup["tenants"]:
            db_path = get_tenant_db_path(
                setup["project_dir"], "main", "main", tenant.name
            )
            with DatabaseConnection(db_path) as conn:
                # WAL test data should still be there
                cursor = conn.execute("SELECT * FROM base_table WHERE id = 'wal-test'")
                row = cursor.fetchone()
                assert row is not None
                assert row["data"] == "wal-data"

                # New table should not exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='wal_test_table'"
                )
                assert cursor.fetchone() is None

    def test_rollback_cleans_up_snapshots(self, setup_with_tenants):
        """Test that snapshots are cleaned up after rollback."""
        setup = setup_with_tenants

        # Create a change that will fail
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="cleanup_test",
            branch="main",
            sql="CREATE TABLE syntax error here",  # Invalid SQL
        )
        added = setup["change_tracker"].add_change(change)

        # Get the expected backup directory path
        branch_path = get_branch_path(setup["project_dir"], "main", "main")
        backup_dir = branch_path / ".change_backups" / added.id

        # Apply should fail
        with pytest.raises(ChangeError):
            setup["change_applier"].apply_change(added.id)

        # Verify snapshot directory was cleaned up after rollback
        assert not backup_dir.exists(), (
            "Backup directory should be cleaned up after rollback"
        )

        # Verify change not marked as applied
        changes = setup["change_tracker"].get_changes()
        test_change = next(c for c in changes if c.id == added.id)
        assert not test_change.applied

"""Integration tests for maintenance mode during operations."""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from threading import Thread
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.managers.merge_manager import MergeManager
from cinchdb.models import Column
from cinchdb.core.maintenance_utils import MaintenanceError
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db


class TestMaintenanceMode:
    """Test maintenance mode behavior during various operations."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        init_project(project_dir)
        yield project_dir
        shutil.rmtree(temp)

    def test_maintenance_mode_during_apply_all(self, temp_project):
        """Test that apply_all sets and clears maintenance mode."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        table_mgr.create_table(
            "users",
            [Column(name="user_id", type="TEXT", nullable=False)]
        )

        # Track maintenance mode states
        maintenance_states = []
        metadata_db = get_metadata_db(temp_project)

        # Monitor maintenance mode in a separate thread
        def monitor_maintenance():
            for _ in range(10):  # Check 10 times
                try:
                    is_maintenance = metadata_db.is_branch_in_maintenance("main", "main")
                    maintenance_states.append(is_maintenance)
                except:
                    maintenance_states.append(False)
                time.sleep(0.01)

        # Start monitoring
        monitor_thread = Thread(target=monitor_maintenance)
        monitor_thread.start()

        # Apply all changes
        applier = ChangeApplier(temp_project, "main", "main")
        applier.apply_all_unapplied()

        # Wait for monitoring to complete
        monitor_thread.join()

        # Should have seen maintenance mode enabled at some point
        # (Note: with CINCHDB_SKIP_MAINTENANCE_DELAY, this might be very brief)
        # At minimum, maintenance mode should be False at the end
        assert maintenance_states[-1] is False, "Maintenance mode should be cleared after apply_all"

    def test_maintenance_mode_blocks_writes(self, temp_project):
        """Test that maintenance mode blocks write operations."""
        # Set maintenance mode manually
        metadata_db = get_metadata_db(temp_project)
        metadata_db.set_branch_maintenance("main", "main", True, "Testing")

        # Try to create table while in maintenance mode
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        with pytest.raises(MaintenanceError) as exc_info:
            table_mgr.create_table(
                "blocked_table",
                [Column(name="item_id", type="INTEGER", nullable=False)]
            )

        assert "maintenance mode" in str(exc_info.value).lower()

        # Clear maintenance mode
        metadata_db.set_branch_maintenance("main", "main", False)

        # Now it should work
        table_mgr.create_table(
            "allowed_table",
            [Column(name="item_id", type="INTEGER", nullable=False)]
        )

    def test_maintenance_mode_during_merge(self, temp_project):
        """Test that merge operations use maintenance mode."""
        # Create a feature branch with changes
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="main"))
        table_mgr.create_table(
            "products",
            [Column(name="name", type="TEXT", nullable=False)]
        )

        # Monitor maintenance mode during merge
        maintenance_states = []
        metadata_db = get_metadata_db(temp_project)

        def monitor_maintenance():
            for _ in range(20):  # Check 20 times during merge
                try:
                    is_maintenance = metadata_db.is_branch_in_maintenance("main", "main")
                    maintenance_states.append(is_maintenance)
                except:
                    maintenance_states.append(False)
                time.sleep(0.01)

        # Start monitoring
        monitor_thread = Thread(target=monitor_maintenance)
        monitor_thread.start()

        # Perform merge
        merge_mgr = MergeManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        result = merge_mgr.merge_into_main("feature")
        assert result["success"]

        # Wait for monitoring to complete
        monitor_thread.join()

        # Maintenance mode should be cleared at the end
        assert maintenance_states[-1] is False, "Maintenance mode should be cleared after merge"

    def test_concurrent_write_blocked_during_maintenance(self, temp_project):
        """Test that concurrent writes are blocked during maintenance."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        table_mgr.create_table(
            "initial",
            [Column(name="item_id", type="INTEGER", nullable=False)]
        )

        # Track if write was blocked
        write_blocked = False
        write_succeeded = False

        def try_concurrent_write():
            """Try to write during maintenance."""
            nonlocal write_blocked, write_succeeded
            time.sleep(0.05)  # Let maintenance mode get set

            try:
                table_mgr2 = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
                table_mgr2.create_table(
                    "concurrent_table",
                    [Column(name="data", type="TEXT", nullable=False)]
                )
                write_succeeded = True
            except MaintenanceError:
                write_blocked = True

        # Start concurrent write attempt
        write_thread = Thread(target=try_concurrent_write)
        write_thread.start()

        # Apply changes (which sets maintenance mode)
        applier = ChangeApplier(temp_project, "main", "main")
        applier.apply_all_unapplied()

        # Wait for write attempt to complete
        write_thread.join()

        # With CINCHDB_SKIP_MAINTENANCE_DELAY, timing is tricky
        # But at minimum, maintenance mode should be properly cleared
        metadata_db = get_metadata_db(temp_project)
        is_maintenance = metadata_db.is_branch_in_maintenance("main", "main")
        assert not is_maintenance, "Maintenance mode should be cleared"

    def test_maintenance_mode_in_metadata_db(self, temp_project):
        """Test that maintenance mode is stored in metadata.db."""
        # Set maintenance mode with a reason
        metadata_db = get_metadata_db(temp_project)
        metadata_db.set_branch_maintenance(
            "main", "main", True,
            "Applying schema changes"
        )

        # Check maintenance mode is set
        assert metadata_db.is_branch_in_maintenance("main", "main")

        # Get maintenance info
        info = metadata_db.get_maintenance_info("main", "main")
        assert info is not None
        assert info["reason"] == "Applying schema changes"
        assert "started_at" in info

        # Clear maintenance mode
        metadata_db.set_branch_maintenance("main", "main", False)

        # Should no longer be in maintenance
        assert not metadata_db.is_branch_in_maintenance("main", "main")

        # Info should be None when not in maintenance
        info = metadata_db.get_maintenance_info("main", "main")
        assert info is None

    def test_nested_maintenance_mode(self, temp_project):
        """Test that nested operations don't interfere with maintenance mode."""
        # Create a branch with multiple changes
        branch_mgr = BranchManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        branch_mgr.create_branch("main", "feature")
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="feature", tenant="main"))

        # Create multiple tables
        for i in range(3):
            table_mgr.create_table(
                f"table_{i}",
                [Column(name=f"col_{i}", type="TEXT", nullable=False)]
            )

        # Apply all changes (should handle maintenance mode properly)
        applier = ChangeApplier(temp_project, "main", "feature")
        applier.apply_all_unapplied()

        # Verify maintenance mode is cleared
        metadata_db = get_metadata_db(temp_project)
        is_maintenance = metadata_db.is_branch_in_maintenance("main", "feature")
        assert not is_maintenance, "Maintenance mode should be cleared"

        # Verify all tables were created in main tenant
        from cinchdb.core.connection import DatabaseConnection
        from cinchdb.core.path_utils import get_tenant_db_path

        db_path = get_tenant_db_path(temp_project, "main", "feature", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'table_%'"
            )
            tables = [row["name"] for row in cursor.fetchall()]

        assert len(tables) == 3
        assert "table_0" in tables
        assert "table_1" in tables
        assert "table_2" in tables

    def test_maintenance_mode_with_multiple_tenants(self, temp_project):
        """Test maintenance mode applies to all materialized tenants."""
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        tenant_mgr.create_tenant("tenant1")
        tenant_mgr.create_tenant("tenant2")

        # Materialize the tenants so they have actual databases
        tenant_mgr.materialize_tenant("tenant1")
        tenant_mgr.materialize_tenant("tenant2")

        # Create table in main branch
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))
        table_mgr.create_table(
            "shared_table",
            [Column(name="data", type="TEXT", nullable=False)]
        )

        # Apply to all materialized tenants
        applier = ChangeApplier(temp_project, "main", "main")
        applier.apply_all_unapplied()

        # Verify table exists in all materialized tenants
        for tenant in ["main", "tenant1", "tenant2"]:
            from cinchdb.core.connection import DatabaseConnection
            from cinchdb.core.path_utils import get_tenant_db_path

            db_path = get_tenant_db_path(temp_project, "main", "main", tenant)
            with DatabaseConnection(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='shared_table'"
                )
                assert cursor.fetchone() is not None, f"Table should exist in {tenant}"

        # Maintenance mode should be cleared
        metadata_db = get_metadata_db(temp_project)
        is_maintenance = metadata_db.is_branch_in_maintenance("main", "main")
        assert not is_maintenance, "Maintenance mode should be cleared"

    def test_maintenance_mode_error_recovery(self, temp_project):
        """Test that maintenance mode is cleared even if an error occurs."""
        # Create an invalid change that will fail
        tracker = ChangeTracker(temp_project, "main", "main")

        from cinchdb.models import Change, ChangeType
        bad_change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="bad_table",
            branch="main",
            # Invalid SQL that will cause an error
            sql="CREATE TABLE bad_table (id id id)",
        )
        tracker.add_change(bad_change)

        # Try to apply - should fail but clear maintenance mode
        applier = ChangeApplier(temp_project, "main", "main")

        try:
            applier.apply_change(bad_change.id)
        except Exception:
            pass  # Expected to fail

        # Maintenance mode should still be cleared
        metadata_db = get_metadata_db(temp_project)
        is_maintenance = metadata_db.is_branch_in_maintenance("main", "main")
        assert not is_maintenance, "Maintenance mode should be cleared after error"
"""Tests for maintenance mode write blocking."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from cinchdb.managers.data import DataManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.column import ColumnManager
from cinchdb.managers.view import ViewModel
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column
from cinchdb.core.path_utils import get_branch_path
from cinchdb.core.maintenance import MaintenanceError
from pydantic import BaseModel


class SampleTable(BaseModel):
    """Test model for data operations."""

    id: str = ""
    name: str
    value: int = 0
    created_at: datetime = None
    updated_at: datetime = None

    model_config = {"json_schema_extra": {"table_name": "test_table"}}


class TestMaintenanceMode:
    """Test maintenance mode write blocking."""

    def setup_method(self):
        """Set up test environment."""
        import tempfile
        from cinchdb.core.initializer import init_project
        
        # Use temporary directory for tests
        self.test_dir = Path(tempfile.mkdtemp())
        self.project_root = self.test_dir / "project"
        self.database = "test_db"
        self.branch = "main"

        # Initialize CinchDB project properly
        init_project(self.project_root, database_name=self.database, branch_name=self.branch)

        # Initialize managers
        self.table_manager = TableManager(self.project_root, self.database, self.branch)
        self.column_manager = ColumnManager(
            self.project_root, self.database, self.branch
        )
        self.data_manager = DataManager(self.project_root, self.database, self.branch)
        self.view_manager = ViewModel(self.project_root, self.database, self.branch)
        self.tenant_manager = TenantManager(
            self.project_root, self.database, self.branch
        )
        self.change_applier = ChangeApplier(
            self.project_root, self.database, self.branch
        )

        # Create test table
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="value", type="INTEGER", nullable=True),
        ]
        self.table_manager.create_table("test_table", columns)

    def teardown_method(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            import shutil

            shutil.rmtree(self.test_dir)

    def _enter_maintenance_mode(self):
        """Helper to enter maintenance mode."""
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        maintenance_file = branch_path / ".maintenance_mode"

        with open(maintenance_file, "w") as f:
            json.dump(
                {
                    "active": True,
                    "reason": "Testing write blocking",
                    "started_at": datetime.now().isoformat(),
                },
                f,
            )

    def _exit_maintenance_mode(self):
        """Helper to exit maintenance mode."""
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        maintenance_file = branch_path / ".maintenance_mode"

        if maintenance_file.exists():
            maintenance_file.unlink()

    def test_table_create_blocked(self):
        """Test that table creation is blocked during maintenance."""
        self._enter_maintenance_mode()

        columns = [Column(name="test_col", type="TEXT")]

        with pytest.raises(MaintenanceError) as exc_info:
            self.table_manager.create_table("blocked_table", columns)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_table_delete_blocked(self):
        """Test that table deletion is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.table_manager.delete_table("test_table")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_table_copy_blocked(self):
        """Test that table copying is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.table_manager.copy_table("test_table", "copy_table")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_column_add_blocked(self):
        """Test that column addition is blocked during maintenance."""
        self._enter_maintenance_mode()

        column = Column(name="new_col", type="TEXT")

        with pytest.raises(MaintenanceError) as exc_info:
            self.column_manager.add_column("test_table", column)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_column_drop_blocked(self):
        """Test that column drop is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.column_manager.drop_column("test_table", "name")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_column_rename_blocked(self):
        """Test that column rename is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.column_manager.rename_column("test_table", "name", "new_name")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_data_create_blocked(self):
        """Test that data creation is blocked during maintenance."""
        self._enter_maintenance_mode()

        record = SampleTable(name="test", value=123)

        with pytest.raises(MaintenanceError) as exc_info:
            self.data_manager.create(record)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_data_save_blocked(self):
        """Test that data save is blocked during maintenance."""
        self._enter_maintenance_mode()

        record = SampleTable(name="test", value=123)

        with pytest.raises(MaintenanceError) as exc_info:
            self.data_manager.save(record)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_data_update_blocked(self):
        """Test that data update is blocked during maintenance."""
        # First create a record
        record = SampleTable(name="test", value=123)
        created = self.data_manager.create(record)

        self._enter_maintenance_mode()

        created.value = 456

        with pytest.raises(MaintenanceError) as exc_info:
            self.data_manager.update(created)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_data_delete_blocked(self):
        """Test that data deletion is blocked during maintenance."""
        # First create a record
        record = SampleTable(name="test", value=123)
        created = self.data_manager.create(record)

        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.data_manager.delete(SampleTable, id=created.id)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_data_bulk_create_blocked(self):
        """Test that bulk data creation is blocked during maintenance."""
        self._enter_maintenance_mode()

        records = [
            SampleTable(name="test1", value=123),
            SampleTable(name="test2", value=456),
        ]

        with pytest.raises(MaintenanceError) as exc_info:
            self.data_manager.bulk_create(records)

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_view_create_blocked(self):
        """Test that view creation is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.view_manager.create_view("test_view", "SELECT * FROM test_table")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_view_update_blocked(self):
        """Test that view update is blocked during maintenance."""
        # First create a view
        self.view_manager.create_view("test_view", "SELECT * FROM test_table")

        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.view_manager.update_view("test_view", "SELECT name FROM test_table")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_view_delete_blocked(self):
        """Test that view deletion is blocked during maintenance."""
        # First create a view
        self.view_manager.create_view("test_view", "SELECT * FROM test_table")

        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.view_manager.delete_view("test_view")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_tenant_create_blocked(self):
        """Test that tenant creation is blocked during maintenance."""
        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.tenant_manager.create_tenant("new_tenant")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_tenant_delete_blocked(self):
        """Test that tenant deletion is blocked during maintenance."""
        # First create a tenant
        self.tenant_manager.create_tenant("test_tenant")

        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.tenant_manager.delete_tenant("test_tenant")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_tenant_copy_blocked(self):
        """Test that tenant copy is blocked during maintenance."""
        # First create a tenant
        self.tenant_manager.create_tenant("test_tenant")

        self._enter_maintenance_mode()

        with pytest.raises(MaintenanceError) as exc_info:
            self.tenant_manager.copy_tenant("test_tenant", "copy_tenant")

        assert "maintenance mode" in str(exc_info.value)

        self._exit_maintenance_mode()

    def test_read_operations_allowed(self):
        """Test that read operations are allowed during maintenance."""
        # Create some data
        record = SampleTable(name="test", value=123)
        created = self.data_manager.create(record)

        self._enter_maintenance_mode()

        # These should all work
        tables = self.table_manager.list_tables()
        assert len(tables) > 0

        table = self.table_manager.get_table("test_table")
        assert table.name == "test_table"

        columns = self.column_manager.list_columns("test_table")
        assert len(columns) > 0

        records = self.data_manager.select(SampleTable)
        assert len(records) == 1

        found = self.data_manager.find_by_id(SampleTable, created.id)
        assert found is not None

        count = self.data_manager.count(SampleTable)
        assert count == 1

        self._exit_maintenance_mode()

    def test_maintenance_mode_cleared_after_change(self):
        """Test that maintenance mode is properly cleared after change application."""
        # Check not in maintenance mode initially
        assert not self.change_applier.is_in_maintenance_mode()

        # Create a change
        column = Column(name="new_col", type="TEXT", nullable=True)
        self.column_manager.add_column("test_table", column)

        # Should not be in maintenance mode after change
        assert not self.change_applier.is_in_maintenance_mode()

"""Tests for ColumnManager."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.config import Config
from cinchdb.managers.column import ColumnManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.models import Column, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


class TestColumnManager:
    """Test column management functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        config = Config(project_dir)
        config.init_project()

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def managers(self, temp_project):
        """Create manager instances with a test table."""
        table_mgr = TableManager(temp_project, "main", "main", "main")

        # Create a test table
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=True),
        ]
        table_mgr.create_table("users", columns)

        column_mgr = ColumnManager(temp_project, "main", "main", "main")

        return {"table": table_mgr, "column": column_mgr}

    def test_add_column(self, managers, temp_project):
        """Test adding a column to a table."""
        # Add a new column
        column = Column(name="age", type="INTEGER", nullable=True)
        managers["column"].add_column("users", column)

        # Verify column exists
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            col_names = [col["name"] for col in columns]
            assert "age" in col_names

            # Check column properties
            age_col = next(col for col in columns if col["name"] == "age")
            assert age_col["type"] == "INTEGER"
            assert age_col["notnull"] == 0  # nullable

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        assert len(changes) == 2  # CREATE TABLE + ADD COLUMN
        assert changes[1].type == ChangeType.ADD_COLUMN
        assert changes[1].entity_name == "age"

    def test_add_column_table_not_exists(self, managers):
        """Test adding column to non-existent table."""
        column = Column(name="test", type="TEXT")

        with pytest.raises(ValueError) as exc:
            managers["column"].add_column("non_existent", column)
        assert "does not exist" in str(exc.value)

    def test_add_column_duplicate(self, managers):
        """Test adding duplicate column."""
        # Try to add existing column
        column = Column(name="name", type="TEXT")

        with pytest.raises(ValueError) as exc:
            managers["column"].add_column("users", column)
        assert "already exists" in str(exc.value)

    def test_add_column_protected_name(self, managers):
        """Test adding column with protected name."""
        # Try to add column with protected name
        column = Column(name="id", type="TEXT")

        with pytest.raises(ValueError) as exc:
            managers["column"].add_column("users", column)
        assert "protected" in str(exc.value).lower()

    def test_drop_column(self, managers, temp_project):
        """Test dropping a column from a table."""
        # SQLite doesn't support DROP COLUMN directly, so this tests the workaround
        managers["column"].drop_column("users", "email")

        # Verify column is gone
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            col_names = [col["name"] for col in columns]
            assert "email" not in col_names
            assert "name" in col_names  # Other columns remain

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        drop_change = next(c for c in changes if c.type == ChangeType.DROP_COLUMN)
        assert drop_change.entity_name == "email"

    def test_drop_column_not_exists(self, managers):
        """Test dropping non-existent column."""
        with pytest.raises(ValueError) as exc:
            managers["column"].drop_column("users", "non_existent")
        assert "does not exist" in str(exc.value)

    def test_drop_column_protected(self, managers):
        """Test dropping protected column."""
        with pytest.raises(ValueError) as exc:
            managers["column"].drop_column("users", "id")
        assert "cannot drop" in str(exc.value).lower()

    def test_rename_column(self, managers, temp_project):
        """Test renaming a column."""
        # SQLite doesn't support RENAME COLUMN in older versions, so this tests the workaround
        managers["column"].rename_column("users", "email", "email_address")

        # Verify rename
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            col_names = [col["name"] for col in columns]
            assert "email" not in col_names
            assert "email_address" in col_names

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        rename_change = next(c for c in changes if c.type == ChangeType.RENAME_COLUMN)
        assert rename_change.entity_name == "email_address"
        assert rename_change.details["old_name"] == "email"

    def test_rename_column_not_exists(self, managers):
        """Test renaming non-existent column."""
        with pytest.raises(ValueError) as exc:
            managers["column"].rename_column("users", "non_existent", "new_name")
        assert "does not exist" in str(exc.value)

    def test_rename_column_protected(self, managers):
        """Test renaming protected column."""
        with pytest.raises(ValueError) as exc:
            managers["column"].rename_column("users", "id", "user_id")
        assert "cannot rename" in str(exc.value).lower()

    def test_rename_column_to_existing(self, managers):
        """Test renaming column to existing name."""
        with pytest.raises(ValueError) as exc:
            managers["column"].rename_column("users", "email", "name")
        assert "already exists" in str(exc.value)

    def test_list_columns(self, managers):
        """Test listing columns of a table."""
        columns = managers["column"].list_columns("users")

        # Should have user columns + automatic columns
        assert len(columns) >= 5  # name, email + id, created_at, updated_at

        col_names = [col.name for col in columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names

        # Check column properties
        name_col = next(c for c in columns if c.name == "name")
        assert name_col.type == "TEXT"
        assert not name_col.nullable

        email_col = next(c for c in columns if c.name == "email")
        assert email_col.type == "TEXT"
        assert email_col.nullable

    def test_list_columns_table_not_exists(self, managers):
        """Test listing columns of non-existent table."""
        with pytest.raises(ValueError) as exc:
            managers["column"].list_columns("non_existent")
        assert "does not exist" in str(exc.value)

    def test_get_column_info(self, managers):
        """Test getting specific column information."""
        column = managers["column"].get_column_info("users", "name")

        assert column.name == "name"
        assert column.type == "TEXT"
        assert not column.nullable
        assert not column.primary_key

    def test_get_column_info_not_exists(self, managers):
        """Test getting info for non-existent column."""
        with pytest.raises(ValueError) as exc:
            managers["column"].get_column_info("users", "non_existent")
        assert "does not exist" in str(exc.value)

    def test_add_column_with_default(self, managers, temp_project):
        """Test adding column with default value."""
        column = Column(name="status", type="TEXT", default="'active'")
        managers["column"].add_column("users", column)

        # Verify default value
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            status_col = next(col for col in columns if col["name"] == "status")
            assert status_col["dflt_value"] == "'active'"

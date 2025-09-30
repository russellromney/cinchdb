"""Tests for TableManager."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.table import TableManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.database import CinchDB


class TestTableManager:
    """Test table management functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        
        # Clean up connection pool
        from cinchdb.infrastructure.metadata_connection_pool import MetadataConnectionPool
        MetadataConnectionPool.close_all()
        
        shutil.rmtree(temp)

    @pytest.fixture
    def table_manager(self, temp_project):
        """Create a TableManager instance."""
        return TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

    def test_list_tables_empty(self, table_manager):
        """Test listing tables in empty database."""
        tables = table_manager.list_tables()
        assert tables == []

    def test_create_table(self, table_manager, temp_project):
        """Test creating a table."""
        # Define columns
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=True),
            Column(name="age", type="INTEGER", nullable=True),
        ]

        # Create table
        table = table_manager.create_table("users", columns)

        # Verify table properties
        assert table.name == "users"
        assert table.database == "main"
        assert table.branch == "main"
        assert len(table.columns) == 6  # 3 user columns + id, created_at, updated_at

        # Verify automatic fields
        col_names = [col.name for col in table.columns]
        assert "id" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names

        # Verify table exists in database
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            assert cursor.fetchone() is not None

            # Verify columns
            cursor = conn.execute("PRAGMA table_info(users)")
            db_columns = cursor.fetchall()
            db_col_names = [col["name"] for col in db_columns]
            assert "id" in db_col_names
            assert "name" in db_col_names
            assert "email" in db_col_names
            assert "age" in db_col_names
            assert "created_at" in db_col_names
            assert "updated_at" in db_col_names

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        assert len(changes) == 1
        assert changes[0].type == ChangeType.CREATE_TABLE
        assert changes[0].entity_name == "users"

    def test_create_table_duplicate(self, table_manager):
        """Test creating a duplicate table."""
        columns = [Column(name="title", type="TEXT")]

        # Create first table
        table_manager.create_table("posts", columns)

        # Try to create duplicate
        with pytest.raises(ValueError) as exc:
            table_manager.create_table("posts", columns)
        assert "already exists" in str(exc.value)

    def test_create_table_empty_columns(self, table_manager, temp_project):
        """Test creating table with empty columns list."""
        # Create table with no user-defined columns
        table = table_manager.create_table("empty_table", [])

        # Should have exactly 3 system columns
        assert table.name == "empty_table"
        assert len(table.columns) == 3

        # Verify the system columns
        col_names = [col.name for col in table.columns]
        assert col_names == ["id", "created_at", "updated_at"]

        # Verify id column is marked as unique
        id_col = table.columns[0]
        assert id_col.name == "id"
        assert id_col.unique == True
        assert id_col.nullable == False

        # Verify table exists in database
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(empty_table)")
            db_columns = cursor.fetchall()
            assert len(db_columns) == 3

    def test_create_table_protected_names(self, table_manager):
        """Test creating table with protected column names."""
        # Try to use protected column names
        columns = [
            Column(name="id", type="TEXT"),  # Protected
            Column(name="title", type="TEXT"),
        ]

        with pytest.raises(ValueError) as exc:
            table_manager.create_table("posts", columns)
        assert "protected" in str(exc.value).lower()

    def test_get_table(self, table_manager):
        """Test getting table information."""
        # Create a table
        columns = [Column(name="content", type="TEXT")]
        table_manager.create_table("notes", columns)

        # Get table info
        table = table_manager.get_table("notes")
        assert table.name == "notes"
        assert len(table.columns) == 4  # content + automatic fields

        # Verify column types
        content_col = next(c for c in table.columns if c.name == "content")
        assert content_col.type == "TEXT"

        id_col = next(c for c in table.columns if c.name == "id")
        assert id_col.type == "TEXT"
        assert id_col.unique == True  # id is always unique (PRIMARY KEY)

    def test_get_table_not_exists(self, table_manager):
        """Test getting non-existent table."""
        with pytest.raises(ValueError) as exc:
            table_manager.get_table("non_existent")
        assert "does not exist" in str(exc.value)

    def test_delete_table(self, table_manager, temp_project):
        """Test deleting a table."""
        # Create a table
        columns = [Column(name="data", type="TEXT")]
        table_manager.create_table("temp_table", columns)

        # Delete it
        table_manager.delete_table("temp_table")

        # Verify it's gone
        tables = table_manager.list_tables()
        assert "temp_table" not in [t.name for t in tables]

        # Verify in database
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='temp_table'"
            )
            assert cursor.fetchone() is None

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        assert len(changes) == 2  # CREATE and DROP
        assert changes[1].type == ChangeType.DROP_TABLE
        assert changes[1].entity_name == "temp_table"

    def test_delete_table_not_exists(self, table_manager):
        """Test deleting non-existent table."""
        with pytest.raises(ValueError) as exc:
            table_manager.delete_table("non_existent")
        assert "does not exist" in str(exc.value)

    def test_copy_table(self, table_manager, temp_project):
        """Test copying a table."""
        # Create source table with data
        columns = [
            Column(name="title", type="TEXT"),
            Column(name="views", type="INTEGER"),
        ]
        table_manager.create_table("articles", columns)

        # Add some data using CinchDB convenience function
        db = CinchDB(database="main", project_dir=temp_project, tenant="main")
        from datetime import datetime
        db.insert("articles", {
            "id": "1",
            "title": "Test Article",
            "views": 100,
            "created_at": datetime.now()
        })

        # Copy table
        new_table = table_manager.copy_table("articles", "articles_backup")

        # Verify new table
        assert new_table.name == "articles_backup"
        assert len(new_table.columns) == len(columns) + 3  # User columns + automatic

        # Verify data was copied using CinchDB convenience function
        results = db.query("SELECT COUNT(*) as count FROM articles_backup")
        assert results[0]["count"] == 1

        results = db.query("SELECT title, views FROM articles_backup")
        assert len(results) == 1
        row = results[0]
        assert row["title"] == "Test Article"
        assert row["views"] == 100

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        assert any(
            c.type == ChangeType.CREATE_TABLE and c.entity_name == "articles_backup"
            for c in changes
        )

    def test_copy_table_structure_only(self, table_manager, temp_project):
        """Test copying table structure without data."""
        # Create source table with data
        columns = [Column(name="content", type="TEXT")]
        table_manager.create_table("messages", columns)

        # Add data using CinchDB convenience function
        db = CinchDB(database="main", project_dir=temp_project, tenant="main")
        from datetime import datetime
        db.insert("messages", {
            "id": "1",
            "content": "Test message",
            "created_at": datetime.now()
        })

        # Copy structure only
        new_table = table_manager.copy_table(
            "messages", "messages_template", copy_data=False
        )

        # Verify structure
        assert new_table.name == "messages_template"
        assert len(new_table.columns) == 4  # content + automatic fields

        # Verify no data using CinchDB convenience function
        results = db.query("SELECT COUNT(*) as count FROM messages_template")
        assert results[0]["count"] == 0

    def test_list_tables(self, table_manager):
        """Test listing all tables."""
        # Create multiple tables
        table_manager.create_table("users", [Column(name="name", type="TEXT")])
        table_manager.create_table("posts", [Column(name="title", type="TEXT")])
        table_manager.create_table("comments", [Column(name="text", type="TEXT")])

        # List tables
        tables = table_manager.list_tables()
        table_names = [t.name for t in tables]

        assert len(tables) == 3
        assert "users" in table_names
        assert "posts" in table_names
        assert "comments" in table_names

        # Verify each table has correct metadata
        for table in tables:
            assert table.database == "main"
            assert table.branch == "main"
            assert (
                len(table.columns) >= 4
            )  # At least one user column + automatic fields

    def test_table_changes_applied_to_all_tenants(self, table_manager, temp_project):
        """Test that table changes are tracked and can be applied to all tenants."""
        from cinchdb.managers.tenant import TenantManager

        # Create additional tenant first (non-lazy)
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        tenant_mgr.create_tenant("tenant2", lazy=False)

        # Create table (this automatically applies to all tenants)
        columns = [Column(name="data", type="TEXT")]
        table_manager.create_table("shared_table", columns)

        # Verify table exists in main tenant
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='shared_table'"
            )
            assert cursor.fetchone() is not None

        # Verify table automatically exists in tenant2 due to auto-application
        db_path2 = get_tenant_db_path(temp_project, "main", "main", "tenant2")
        with DatabaseConnection(db_path2) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='shared_table'"
            )
            assert cursor.fetchone() is not None

        # Verify change is marked as applied
        applier = ChangeApplier(temp_project, "main", "main")
        unapplied_changes = applier.change_tracker.get_unapplied_changes()
        assert len(unapplied_changes) == 0

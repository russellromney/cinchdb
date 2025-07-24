"""Tests for TableManager."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.config import Config
from cinchdb.managers.table import TableManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


class TestTableManager:
    """Test table management functionality."""
    
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
    def table_manager(self, temp_project):
        """Create a TableManager instance."""
        return TableManager(temp_project, "main", "main", "main")
    
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
            Column(name="age", type="INTEGER", nullable=True)
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
    
    def test_create_table_protected_names(self, table_manager):
        """Test creating table with protected column names."""
        # Try to use protected column names
        columns = [
            Column(name="id", type="TEXT"),  # Protected
            Column(name="title", type="TEXT")
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
        assert id_col.primary_key
    
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
            Column(name="views", type="INTEGER")
        ]
        table_manager.create_table("articles", columns)
        
        # Add some data
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO articles (id, title, views, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("1", "Test Article", 100)
            )
            conn.commit()
        
        # Copy table
        new_table = table_manager.copy_table("articles", "articles_backup")
        
        # Verify new table
        assert new_table.name == "articles_backup"
        assert len(new_table.columns) == len(columns) + 3  # User columns + automatic
        
        # Verify data was copied
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM articles_backup")
            assert cursor.fetchone()["count"] == 1
            
            cursor = conn.execute("SELECT title, views FROM articles_backup")
            row = cursor.fetchone()
            assert row["title"] == "Test Article"
            assert row["views"] == 100
        
        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        assert any(c.type == ChangeType.CREATE_TABLE and c.entity_name == "articles_backup" for c in changes)
    
    def test_copy_table_structure_only(self, table_manager, temp_project):
        """Test copying table structure without data."""
        # Create source table with data
        columns = [Column(name="content", type="TEXT")]
        table_manager.create_table("messages", columns)
        
        # Add data
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO messages (id, content, created_at) VALUES (?, ?, datetime('now'))",
                ("1", "Test message")
            )
            conn.commit()
        
        # Copy structure only
        new_table = table_manager.copy_table("messages", "messages_template", copy_data=False)
        
        # Verify structure
        assert new_table.name == "messages_template"
        assert len(new_table.columns) == 4  # content + automatic fields
        
        # Verify no data
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM messages_template")
            assert cursor.fetchone()["count"] == 0
    
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
            assert len(table.columns) >= 4  # At least one user column + automatic fields
    
    def test_table_changes_applied_to_all_tenants(self, table_manager, temp_project):
        """Test that table changes are tracked and can be applied to all tenants."""
        from cinchdb.managers.tenant import TenantManager
        
        # Create additional tenant first
        tenant_mgr = TenantManager(temp_project, "main", "main")
        tenant_mgr.create_tenant("tenant2")
        
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
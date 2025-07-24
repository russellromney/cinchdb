"""Tests for change application logic."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.config import Config
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


class TestChangeApplier:
    """Test change application functionality."""
    
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
        """Create manager instances."""
        branch_mgr = BranchManager(temp_project, "main")
        tenant_mgr = TenantManager(temp_project, "main", "main")
        change_tracker = ChangeTracker(temp_project, "main", "main")
        change_applier = ChangeApplier(temp_project, "main", "main")
        
        return {
            "branch": branch_mgr,
            "tenant": tenant_mgr,
            "tracker": change_tracker,
            "applier": change_applier
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
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, email TEXT)"
        )
        added_change = managers["tracker"].add_change(change)
        
        # Apply the change
        managers["applier"].apply_change(added_change.id)
        
        # Verify table exists in all tenants
        tenants = managers["tenant"].list_tenants()
        for tenant in tenants:
            db_path = get_tenant_db_path(temp_project, "main", "main", tenant.name)
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
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)"
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
            sql="ALTER TABLE users ADD COLUMN email TEXT"
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
                sql="CREATE TABLE users (id TEXT PRIMARY KEY)"
            ),
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="posts",
                branch="main",
                sql="CREATE TABLE posts (id TEXT PRIMARY KEY, user_id TEXT)"
            ),
            Change(
                type=ChangeType.CREATE_INDEX,
                entity_type="index",
                entity_name="idx_posts_user",
                branch="main",
                sql="CREATE INDEX idx_posts_user ON posts(user_id)"
            )
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
            sql="CREATE TABLE temp_table (id TEXT PRIMARY KEY)"
        )
        managers["tracker"].add_change(create_change)
        managers["applier"].apply_change(create_change.id)
        
        # Drop table
        drop_change = Change(
            type=ChangeType.DROP_TABLE,
            entity_type="table",
            entity_name="temp_table",
            branch="main",
            sql="DROP TABLE temp_table"
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
            sql="CREATE TABLE users (id TEXT PRIMARY KEY, active INTEGER)"
        )
        managers["tracker"].add_change(create_table)
        managers["applier"].apply_change(create_table.id)
        
        # Create view
        create_view = Change(
            type=ChangeType.CREATE_VIEW,
            entity_type="view",
            entity_name="active_users",
            branch="main",
            sql="CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1"
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
                sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT)"
            ),
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="posts",
                branch="main",
                sql="CREATE TABLE posts (id TEXT PRIMARY KEY, title TEXT)"
            )
        ]
        
        for change in changes:
            added = managers["tracker"].add_change(change)
            managers["applier"].apply_change(added.id)
        
        # Create new tenant - should copy schema from main
        managers["tenant"].create_tenant("new_tenant")
        
        # Verify tables already exist in new tenant (copied from main)
        db_path = get_tenant_db_path(temp_project, "main", "main", "new_tenant")
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
            sql="CREATE TABLE comments (id TEXT PRIMARY KEY, content TEXT)"
        )
        added = managers["tracker"].add_change(new_change)
        
        # Apply to all tenants
        managers["applier"].apply_change(added.id)
        
        # Verify new table exists in both tenants
        for tenant_name in ["main", "new_tenant"]:
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
            sql="CREATE TABLE bad syntax error"
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
                sql=f"CREATE TABLE table_{i} (id TEXT PRIMARY KEY)"
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
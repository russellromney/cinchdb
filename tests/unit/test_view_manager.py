"""Tests for ViewModel."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.view import ViewModel
from cinchdb.managers.table import TableManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.models import Column, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.database import CinchDB


class TestViewModel:
    """Test view management functionality."""

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
        """Create managers for testing."""
        table_mgr = TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))

        # Create test tables
        table_mgr.create_table(
            "users",
            [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="email", type="TEXT", nullable=True),
                Column(name="active", type="INTEGER", default="1"),
            ],
        )

        table_mgr.create_table(
            "posts",
            [
                Column(name="title", type="TEXT", nullable=False),
                Column(name="user_id", type="TEXT", nullable=False),
                Column(name="published", type="INTEGER", default="0"),
            ],
        )

        view_mgr = ViewModel(ConnectionContext(project_root=temp_project, database="main", branch="main", tenant="main"))

        return {"table": table_mgr, "view": view_mgr}

    def test_create_view(self, managers, temp_project):
        """Test creating a view."""
        sql = "SELECT * FROM users WHERE active = 1"
        view = managers["view"].create_view("active_users", sql)

        assert view.name == "active_users"
        assert view.database == "main"
        assert view.branch == "main"
        assert view.sql_statement == sql

        # Verify view exists in database
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='active_users'"
            )
            assert cursor.fetchone() is not None

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        view_change = next(c for c in changes if c.type == ChangeType.CREATE_VIEW)
        assert view_change.entity_name == "active_users"

    def test_create_view_duplicate(self, managers):
        """Test creating duplicate view."""
        sql = "SELECT * FROM users"
        managers["view"].create_view("all_users", sql)

        with pytest.raises(ValueError) as exc:
            managers["view"].create_view("all_users", sql)
        assert "already exists" in str(exc.value)

    def test_create_view_complex(self, managers, temp_project):
        """Test creating a complex view with joins."""
        sql = """
        SELECT 
            u.name as user_name,
            u.email,
            COUNT(p.id) as post_count
        FROM users u
        LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.id, u.name, u.email
        """

        view = managers["view"].create_view("user_stats", sql)
        assert view.name == "user_stats"

        # Verify view works using CinchDB convenience functions
        db = CinchDB(database="main", project_dir=temp_project, tenant="main")
        from datetime import datetime

        # Insert test data
        db.insert("users", {
            "id": "1",
            "name": "John",
            "email": "john@example.com",
            "created_at": datetime.now()
        })
        db.insert("posts", {
            "id": "1",
            "title": "Post 1",
            "user_id": "1",
            "created_at": datetime.now()
        })
        db.insert("posts", {
            "id": "2",
            "title": "Post 2",
            "user_id": "1",
            "created_at": datetime.now()
        })

        # Query the view
        results = db.query("SELECT * FROM user_stats")
        assert len(results) == 1
        row = results[0]
        assert row["user_name"] == "John"
        assert row["post_count"] == 2

    def test_update_view(self, managers, temp_project):
        """Test updating a view SQL."""
        # Create initial view
        managers["view"].create_view(
            "published_posts", "SELECT * FROM posts WHERE published = 1"
        )

        # Update it
        new_sql = "SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC"
        managers["view"].update_view("published_posts", new_sql)

        # Verify update
        view = managers["view"].get_view("published_posts")
        assert view.sql_statement == new_sql

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        update_change = next(c for c in changes if c.type == ChangeType.UPDATE_VIEW)
        assert update_change.entity_name == "published_posts"

    def test_update_view_not_exists(self, managers):
        """Test updating non-existent view."""
        with pytest.raises(ValueError) as exc:
            managers["view"].update_view("non_existent", "SELECT * FROM users")
        assert "does not exist" in str(exc.value)

    def test_delete_view(self, managers, temp_project):
        """Test deleting a view."""
        # Create a view
        managers["view"].create_view("temp_view", "SELECT * FROM users LIMIT 10")

        # Delete it
        managers["view"].delete_view("temp_view")

        # Verify it's gone
        views = managers["view"].list_views()
        assert "temp_view" not in [v.name for v in views]

        # Verify in database
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='temp_view'"
            )
            assert cursor.fetchone() is None

        # Verify change was tracked
        tracker = ChangeTracker(temp_project, "main", "main")
        changes = tracker.get_changes()
        drop_change = next(c for c in changes if c.type == ChangeType.DROP_VIEW)
        assert drop_change.entity_name == "temp_view"

    def test_delete_view_not_exists(self, managers):
        """Test deleting non-existent view."""
        with pytest.raises(ValueError) as exc:
            managers["view"].delete_view("non_existent")
        assert "does not exist" in str(exc.value)

    def test_list_views(self, managers):
        """Test listing all views."""
        # Create multiple views
        managers["view"].create_view("view1", "SELECT * FROM users")
        managers["view"].create_view("view2", "SELECT * FROM posts")
        managers["view"].create_view("view3", "SELECT id, name FROM users")

        views = managers["view"].list_views()
        view_names = [v.name for v in views]

        assert len(views) == 3
        assert "view1" in view_names
        assert "view2" in view_names
        assert "view3" in view_names

        # Check view properties
        for view in views:
            assert view.database == "main"
            assert view.branch == "main"
            assert view.sql_statement is not None

    def test_get_view(self, managers):
        """Test getting specific view information."""
        sql = "SELECT name, email FROM users WHERE active = 1"
        managers["view"].create_view("active_users", sql)

        view = managers["view"].get_view("active_users")
        assert view.name == "active_users"
        assert view.sql_statement == sql
        assert view.database == "main"
        assert view.branch == "main"

    def test_get_view_not_exists(self, managers):
        """Test getting non-existent view."""
        with pytest.raises(ValueError) as exc:
            managers["view"].get_view("non_existent")
        assert "does not exist" in str(exc.value)

    def test_view_with_parameters(self, managers):
        """Test creating view with parameterized SQL."""
        # Views can reference other views
        managers["view"].create_view(
            "recent_users",
            "SELECT * FROM users WHERE created_at > date('now', '-30 days')",
        )

        managers["view"].create_view(
            "recent_active_users", "SELECT * FROM recent_users WHERE active = 1"
        )

        views = managers["view"].list_views()
        assert len(views) == 2

    def test_view_changes_applied_to_all_tenants(self, managers, temp_project):
        """Test that view changes are tracked for multi-tenant application."""
        from cinchdb.managers.tenant import TenantManager
        from cinchdb.managers.change_applier import ChangeApplier

        # Create additional tenant (non-lazy)
        tenant_mgr = TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))
        tenant_mgr.create_tenant("tenant2", lazy=False)

        # Create view (this automatically applies to all tenants)
        managers["view"].create_view("user_summary", "SELECT id, name FROM users")

        # Verify view exists in main tenant
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='user_summary'"
            )
            assert cursor.fetchone() is not None

        # Verify view automatically exists in tenant2 due to auto-application
        db_path2 = get_tenant_db_path(temp_project, "main", "main", "tenant2")
        with DatabaseConnection(db_path2) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='user_summary'"
            )
            assert cursor.fetchone() is not None

        # Verify change is marked as applied
        applier = ChangeApplier(temp_project, "main", "main")
        unapplied_changes = applier.change_tracker.get_unapplied_changes()
        assert len(unapplied_changes) == 0

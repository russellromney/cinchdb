"""Tests for CinchDB convenience methods that wrap manager functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from cinchdb.core.database import CinchDB
from cinchdb.models import Column, Tenant, Branch, View


class TestCinchDBConvenienceMethods:
    """Test convenience methods on CinchDB class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())
        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        # Create .cinchdb directory to make it a valid project
        cinchdb_dir = project_dir / ".cinchdb"
        cinchdb_dir.mkdir()

        yield project_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def db(self, temp_project):
        """Create a CinchDB instance for testing."""
        return CinchDB(
            database="test_db",
            branch="main",
            tenant="main",
            project_dir=temp_project
        )

    def test_convenience_methods_use_private_managers(self, db):
        """Test that convenience methods delegate to private managers."""
        # Test that _managers property exists and provides typed access
        assert hasattr(db, '_managers')

        # Test that _managers provides access to all manager types
        managers = db._managers
        assert hasattr(managers, 'tenants')
        assert hasattr(managers, 'branches')
        assert hasattr(managers, 'merge')
        assert hasattr(managers, 'indexes')
        assert hasattr(managers, 'columns')
        assert hasattr(managers, 'views')
        assert hasattr(managers, 'data')
        assert hasattr(managers, 'tables')

    def test_tenant_convenience_methods(self, db):
        """Test tenant convenience methods."""
        # Mock the private manager
        mock_tenant_manager = Mock()
        db._tenant_manager = mock_tenant_manager

        # Test list_tenants
        mock_tenant_manager.list_tenants.return_value = [
            Tenant(name="tenant1", database="test_db", branch="main"),
            Tenant(name="tenant2", database="test_db", branch="main")
        ]

        tenants = db.list_tenants()
        assert len(tenants) == 2
        mock_tenant_manager.list_tenants.assert_called_once_with(include_system=False)

        # Test list_tenants with system tenants
        db.list_tenants(include_system=True)
        mock_tenant_manager.list_tenants.assert_called_with(include_system=True)

        # Test create_tenant
        mock_tenant = Tenant(name="new_tenant", database="test_db", branch="main")
        mock_tenant_manager.create_tenant.return_value = mock_tenant

        result = db.create_tenant("new_tenant")
        assert result == mock_tenant
        mock_tenant_manager.create_tenant.assert_called_once_with("new_tenant", lazy=True)

        # Test create_tenant with copy_from
        mock_tenant_manager.copy_tenant.return_value = mock_tenant
        db.create_tenant("copied_tenant", copy_from="template")
        mock_tenant_manager.copy_tenant.assert_called_once_with("template", "copied_tenant")

        # Test delete_tenant
        db.delete_tenant("old_tenant")
        mock_tenant_manager.delete_tenant.assert_called_once_with("old_tenant")

        # Test create_tenant with lazy parameter
        db.create_tenant("lazy_tenant", lazy=False)
        mock_tenant_manager.create_tenant.assert_called_with("lazy_tenant", lazy=False)

        # Test copy_tenant
        db.copy_tenant("source", "target")
        mock_tenant_manager.copy_tenant.assert_called_with("source", "target")

        # Test rename_tenant
        db.rename_tenant("old_name", "new_name")
        mock_tenant_manager.rename_tenant.assert_called_once_with("old_name", "new_name")

    def test_branch_convenience_methods(self, db):
        """Test branch convenience methods."""
        # Mock the private manager
        mock_branch_manager = Mock()
        db._branch_manager = mock_branch_manager

        # Test list_branches
        mock_branches = [
            Branch(name="main", database="test_db"),
            Branch(name="feature", database="test_db")
        ]
        mock_branch_manager.list_branches.return_value = mock_branches

        branches = db.list_branches()
        assert len(branches) == 2
        mock_branch_manager.list_branches.assert_called_once()

        # Test create_branch
        mock_branch = Branch(name="new_branch", database="test_db")
        mock_branch_manager.create_branch.return_value = mock_branch

        result = db.create_branch("new_branch")
        assert result == mock_branch
        mock_branch_manager.create_branch.assert_called_once_with("main", "new_branch")

        # Test create_branch with custom source
        db.create_branch("feature_branch", source_branch="develop")
        mock_branch_manager.create_branch.assert_called_with("develop", "feature_branch")

        # Test delete_branch
        db.delete_branch("old_branch")
        mock_branch_manager.delete_branch.assert_called_once_with("old_branch")

    def test_merge_convenience_methods(self, db):
        """Test merge convenience methods."""
        # Mock the private manager
        mock_merge_manager = Mock()
        db._merge_manager = mock_merge_manager

        # Test can_merge
        mock_merge_manager.can_merge.return_value = {"can_merge": True, "conflicts": []}

        result = db.can_merge("feature", "main")
        assert result["can_merge"] is True
        mock_merge_manager.can_merge.assert_called_once_with("feature", "main")

        # Test merge_branches
        mock_merge_manager.merge_branches.return_value = {"changes_applied": 5}

        result = db.merge_branches("feature")
        assert result["changes_applied"] == 5
        mock_merge_manager.merge_branches.assert_called_once_with("feature", "main")

        # Test merge_branches with custom target
        db.merge_branches("hotfix", "develop")
        mock_merge_manager.merge_branches.assert_called_with("hotfix", "develop")

        # Test merge_into_main
        mock_merge_manager.merge_into_main.return_value = {"changes_applied": 3, "conflicts": []}

        result = db.merge_into_main("feature")
        assert result["changes_applied"] == 3
        mock_merge_manager.merge_into_main.assert_called_once_with("feature", force=False, dry_run=False)

        # Test merge_into_main with options
        db.merge_into_main("hotfix", force=True, dry_run=True)
        mock_merge_manager.merge_into_main.assert_called_with("hotfix", force=True, dry_run=True)

    def test_index_convenience_methods(self, db):
        """Test index convenience methods."""
        # Mock the private manager
        mock_index_manager = Mock()
        db._index_manager = mock_index_manager

        # Test list_indexes
        mock_indexes = [{"name": "idx_users_email", "table": "users"}]
        mock_index_manager.list_indexes.return_value = mock_indexes

        indexes = db.list_indexes()
        assert len(indexes) == 1
        mock_index_manager.list_indexes.assert_called_once_with(None)

        # Test list_indexes with table filter
        db.list_indexes("users")
        mock_index_manager.list_indexes.assert_called_with("users")

        # Test drop_index
        db.drop_index("old_index")
        mock_index_manager.drop_index.assert_called_once_with("old_index", True)

        # Test drop_index with if_exists=False
        db.drop_index("strict_index", if_exists=False)
        mock_index_manager.drop_index.assert_called_with("strict_index", False)

        # Test get_index_info
        mock_info = {"name": "idx_test", "columns": ["col1"], "unique": False}
        mock_index_manager.get_index_info.return_value = mock_info

        info = db.get_index_info("idx_test")
        assert info == mock_info
        mock_index_manager.get_index_info.assert_called_once_with("idx_test")

    def test_column_convenience_methods(self, db):
        """Test column convenience methods."""
        # Mock the private manager
        mock_column_manager = Mock()
        db._column_manager = mock_column_manager

        # Test add_column
        column = Column(name="new_col", type="TEXT")
        db.add_column("users", column)
        mock_column_manager.add_column.assert_called_once_with("users", column)

        # Test drop_column
        db.drop_column("users", "old_col")
        mock_column_manager.drop_column.assert_called_once_with("users", "old_col")

        # Test rename_column
        db.rename_column("users", "old_name", "new_name")
        mock_column_manager.rename_column.assert_called_once_with("users", "old_name", "new_name")

        # Test alter_column_nullable
        db.alter_column_nullable("users", "phone", True)
        mock_column_manager.alter_column_nullable.assert_called_once_with("users", "phone", True, None)

        # Test alter_column_nullable with fill_value
        db.alter_column_nullable("users", "active", False, fill_value="true")
        mock_column_manager.alter_column_nullable.assert_called_with("users", "active", False, "true")

    def test_view_convenience_methods(self, db):
        """Test view convenience methods."""
        # Mock the private manager
        mock_view_manager = Mock()
        db._view_manager = mock_view_manager

        # Test create_view
        mock_view = View(
            name="test_view",
            database="test_db",
            branch="main",
            sql_statement="SELECT * FROM users"
        )
        mock_view_manager.create_view.return_value = mock_view

        result = db.create_view("test_view", "SELECT * FROM users")
        assert result == mock_view
        mock_view_manager.create_view.assert_called_once_with("test_view", "SELECT * FROM users")

        # Test list_views
        mock_views = [mock_view]
        mock_view_manager.list_views.return_value = mock_views

        views = db.list_views()
        assert len(views) == 1
        mock_view_manager.list_views.assert_called_once()

        # Test update_view
        updated_view = View(
            name="test_view",
            database="test_db",
            branch="main",
            sql_statement="SELECT * FROM users WHERE active = true"
        )
        mock_view_manager.update_view.return_value = updated_view

        result = db.update_view("test_view", "SELECT * FROM users WHERE active = true")
        assert result == updated_view
        mock_view_manager.update_view.assert_called_once_with("test_view", "SELECT * FROM users WHERE active = true", None)

        # Test update_view with description
        db.update_view("test_view", "SELECT * FROM users", "User view")
        mock_view_manager.update_view.assert_called_with("test_view", "SELECT * FROM users", "User view")

        # Test drop_view
        db.drop_view("old_view")
        mock_view_manager.delete_view.assert_called_once_with("old_view")

    def test_data_convenience_methods(self, db):
        """Test data convenience methods."""
        # Mock the private manager
        mock_data_manager = Mock()
        db._data_manager = mock_data_manager

        # Create a mock model class
        class MockUser:
            pass

        # Test select
        mock_users = [MockUser(), MockUser()]
        mock_data_manager.select.return_value = mock_users

        users = db.select(MockUser)
        assert len(users) == 2
        mock_data_manager.select.assert_called_once_with(MockUser, limit=None, offset=None)

        # Test select with filters
        db.select(MockUser, limit=10, offset=5, active=True)
        mock_data_manager.select.assert_called_with(MockUser, limit=10, offset=5, active=True)

        # Test find_by_id
        mock_user = MockUser()
        mock_data_manager.find_by_id.return_value = mock_user

        user = db.find_by_id(MockUser, "user-123")
        assert user == mock_user
        mock_data_manager.find_by_id.assert_called_once_with(MockUser, "user-123")

    def test_remote_connections_raise_not_implemented(self):
        """Test that convenience methods raise NotImplementedError for remote connections."""
        # Create a remote connection
        remote_db = CinchDB(
            database="test_db",
            api_url="https://api.example.com",
            api_key="test-key"
        )

        # Test that convenience methods raise NotImplementedError
        with pytest.raises(NotImplementedError, match="Remote tenant listing not implemented"):
            remote_db.list_tenants()

        with pytest.raises(NotImplementedError, match="Remote tenant creation not implemented"):
            remote_db.create_tenant("test")

        with pytest.raises(NotImplementedError, match="Remote branch listing not implemented"):
            remote_db.list_branches()

        with pytest.raises(NotImplementedError, match="Remote merge checking not implemented"):
            remote_db.can_merge("a", "b")

    def test_convenience_methods_preserve_existing_functionality(self, db):
        """Test that convenience methods don't break existing functionality."""
        # Test that existing methods still work
        assert hasattr(db, 'query')
        assert hasattr(db, 'insert')
        assert hasattr(db, 'update')
        assert hasattr(db, 'delete')
        assert hasattr(db, 'create_table')
        assert hasattr(db, 'create_index')

        # Test that private managers are still accessible internally via _managers
        assert hasattr(db, '_managers')
        managers = db._managers
        assert hasattr(managers, 'tenants')
        assert hasattr(managers, 'branches')
        assert hasattr(managers, 'merge')

    def test_manager_properties_are_private(self, db):
        """Test that manager properties are now private and not in public API."""
        # Test that old public properties don't exist
        assert not hasattr(db, 'tenants')
        assert not hasattr(db, 'branches')
        assert not hasattr(db, 'merge')
        assert not hasattr(db, 'indexes')
        assert not hasattr(db, 'columns')
        assert not hasattr(db, 'views')
        assert not hasattr(db, 'data')
        assert not hasattr(db, 'tables')  # Added tables check

        # Test that private properties are accessible via _managers
        assert hasattr(db, '_managers')
        managers = db._managers
        assert hasattr(managers, 'tenants')
        assert hasattr(managers, 'branches')
        assert hasattr(managers, 'merge')
        assert hasattr(managers, 'indexes')
        assert hasattr(managers, 'columns')
        assert hasattr(managers, 'views')
        assert hasattr(managers, 'data')
        assert hasattr(managers, 'tables')

    def test_table_convenience_methods(self, db):
        """Test table convenience methods."""
        # Mock the private manager
        mock_table_manager = Mock()
        db._table_manager = mock_table_manager

        # Test list_tables
        from cinchdb.models import Table, Column
        mock_tables = [
            Table(name="users", database="test_db", branch="main", columns=[]),
            Table(name="posts", database="test_db", branch="main", columns=[])
        ]
        mock_table_manager.list_tables.return_value = mock_tables

        tables = db.list_tables()
        assert len(tables) == 2
        mock_table_manager.list_tables.assert_called_once()

        # Test get_table
        mock_table = Table(
            name="users",
            database="test_db",
            branch="main",
            columns=[Column(name="id", type="TEXT")]
        )
        mock_table_manager.get_table.return_value = mock_table

        table = db.get_table("users")
        assert table == mock_table
        mock_table_manager.get_table.assert_called_once_with("users")

        # Test drop_table
        db.drop_table("old_table")
        mock_table_manager.delete_table.assert_called_once_with("old_table")

        # Test copy_table
        db.copy_table("source", "target")
        mock_table_manager.copy_table.assert_called_once_with("source", "target", True)

        # Test copy_table without data
        db.copy_table("source2", "target2", copy_data=False)
        mock_table_manager.copy_table.assert_called_with("source2", "target2", False)

    def test_table_methods_raise_not_implemented_for_remote(self):
        """Test that table methods raise NotImplementedError for remote connections."""
        # Create a remote connection
        remote_db = CinchDB(
            database="test_db",
            api_url="https://api.example.com",
            api_key="test-key"
        )

        # Test that table methods raise NotImplementedError
        with pytest.raises(NotImplementedError, match="Remote table listing not implemented"):
            remote_db.list_tables()

        with pytest.raises(NotImplementedError, match="Remote table details not implemented"):
            remote_db.get_table("users")

        with pytest.raises(NotImplementedError, match="Remote table dropping not implemented"):
            remote_db.drop_table("users")

        with pytest.raises(NotImplementedError, match="Remote table copying not implemented"):
            remote_db.copy_table("source", "target")


if __name__ == "__main__":
    pytest.main([__file__])
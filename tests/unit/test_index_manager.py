"""Tests for the IndexManager class."""

import pytest
from pathlib import Path
import tempfile
import shutil

from cinchdb.managers.index import IndexManager
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.table import TableManager
from cinchdb.models import Column
from cinchdb.core.initializer import ProjectInitializer


class TestIndexManager:
    """Test IndexManager functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing."""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")

        table_manager = TableManager(ConnectionContext(project_root=project_dir, database="testdb", branch="main", tenant="main"))
        table_manager.create_table(
            "users",
            [
                Column(name="email", type="TEXT", nullable=False),
                Column(name="username", type="TEXT", nullable=False),
                Column(name="age", type="INTEGER"),
                Column(name="last_login", type="TEXT"),
            ]
        )
        
        yield project_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_create_simple_index(self, temp_project):
        """Test creating a simple index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create index
        index_name = manager.create_index("users", ["email"])
        
        assert index_name == "idx_users_email"
        
        # Verify index exists
        indexes = manager.list_indexes("users")
        assert len(indexes) == 1
        assert indexes[0]["name"] == index_name
        assert indexes[0]["columns"] == ["email"]
        assert indexes[0]["unique"] is False

    def test_create_unique_index(self, temp_project):
        """Test creating a unique index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create unique index
        index_name = manager.create_index("users", ["username"], unique=True)
        
        assert index_name == "uniq_users_username"
        
        # Verify index
        indexes = manager.list_indexes("users")
        assert len(indexes) == 1
        assert indexes[0]["unique"] is True

    def test_create_compound_index(self, temp_project):
        """Test creating a compound index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create compound index
        index_name = manager.create_index("users", ["username", "email"])
        
        assert index_name == "idx_users_username_email"
        
        # Verify index
        indexes = manager.list_indexes("users")
        assert len(indexes) == 1
        assert indexes[0]["columns"] == ["username", "email"]

    def test_create_named_index(self, temp_project):
        """Test creating a named index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create named index
        custom_name = "idx_user_lookup"
        index_name = manager.create_index("users", ["email"], name=custom_name)
        
        assert index_name == custom_name
        
        # Verify index
        indexes = manager.list_indexes("users")
        assert len(indexes) == 1
        assert indexes[0]["name"] == custom_name

    def test_drop_index(self, temp_project):
        """Test dropping an index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create and drop index
        index_name = manager.create_index("users", ["email"])
        manager.drop_index(index_name)
        
        # Verify index is gone
        indexes = manager.list_indexes("users")
        assert len(indexes) == 0

    def test_list_all_indexes(self, temp_project):
        """Test listing all indexes."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        table_manager = TableManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create another table
        table_manager.create_table(
            "products",
            [
                Column(name="sku", type="TEXT"),
                Column(name="price", type="REAL"),
            ]
        )
        
        # Create indexes on both tables
        manager.create_index("users", ["email"])
        manager.create_index("users", ["username"], unique=True)
        manager.create_index("products", ["sku"])
        
        # List all indexes
        all_indexes = manager.list_indexes()
        assert len(all_indexes) == 3
        
        # List indexes for specific table
        user_indexes = manager.list_indexes("users")
        assert len(user_indexes) == 2
        
        product_indexes = manager.list_indexes("products")
        assert len(product_indexes) == 1

    def test_get_index_info(self, temp_project):
        """Test getting detailed index information."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create index
        index_name = manager.create_index("users", ["email", "username"], unique=True)
        
        # Get info
        info = manager.get_index_info(index_name)
        
        assert info["name"] == index_name
        assert info["table"] == "users"
        assert info["columns"] == ["email", "username"]
        assert info["unique"] is True
        assert info["sql"] is not None
        assert len(info["columns_info"]) == 2

    def test_create_index_nonexistent_table(self, temp_project):
        """Test creating an index on a non-existent table."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        with pytest.raises(ValueError, match="Table 'nonexistent' does not exist"):
            manager.create_index("nonexistent", ["column"])

    def test_create_index_nonexistent_column(self, temp_project):
        """Test creating an index on a non-existent column."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        with pytest.raises(ValueError, match="do not exist in table"):
            manager.create_index("users", ["nonexistent"])

    def test_drop_nonexistent_index(self, temp_project):
        """Test dropping a non-existent index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # With if_exists=True (default), should not raise
        manager.drop_index("nonexistent")
        
        # With if_exists=False, should raise
        with pytest.raises(ValueError, match="does not exist"):
            manager.drop_index("nonexistent", if_exists=False)

    def test_get_info_nonexistent_index(self, temp_project):
        """Test getting info for a non-existent index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        with pytest.raises(ValueError, match="does not exist"):
            manager.get_index_info("nonexistent")

    def test_create_duplicate_index(self, temp_project):
        """Test creating a duplicate index."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        # Create index
        index_name = manager.create_index("users", ["email"], name="test_index")
        
        # Try to create again with if_not_exists=True (default)
        same_name = manager.create_index("users", ["email"], name="test_index")
        assert same_name == index_name
        
        # Try to create again with if_not_exists=False
        with pytest.raises(ValueError, match="already exists"):
            manager.create_index("users", ["email"], name="test_index", if_not_exists=False)

    def test_empty_column_list(self, temp_project):
        """Test creating an index with an empty column list."""
        manager = IndexManager(ConnectionContext(project_root=temp_project, database="testdb", branch="main", tenant="main"))
        
        with pytest.raises(ValueError, match="At least one column"):
            manager.create_index("users", [])
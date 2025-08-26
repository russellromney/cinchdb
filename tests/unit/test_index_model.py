"""Tests for the Index model and enhanced table creation with indexes."""

import pytest
from pathlib import Path
import tempfile
import shutil

from cinchdb.models import Column, Index
from cinchdb.managers.table import TableManager
from cinchdb.core.database import CinchDB


class TestIndexModel:
    """Test the Index pydantic model."""
    
    def test_index_creation_with_columns(self):
        """Test creating an Index with columns."""
        index = Index(columns=["email"])
        assert index.columns == ["email"]
        assert index.name is None
        assert index.unique is False
    
    def test_index_creation_with_all_fields(self):
        """Test creating an Index with all fields."""
        index = Index(columns=["name", "email"], name="user_lookup", unique=True)
        assert index.columns == ["name", "email"]
        assert index.name == "user_lookup"
        assert index.unique is True
    
    def test_index_validation_empty_columns(self):
        """Test that Index validates empty columns list."""
        index = Index(columns=[])
        assert index.columns == []  # Model allows empty, validation happens in manager
    
    def test_index_validation_forbids_extra_fields(self):
        """Test that Index model forbids extra fields."""
        with pytest.raises(ValueError, match="Extra inputs are not permitted"):
            Index(columns=["email"], extra_field="not_allowed")


class TestTableCreationWithIndexes:
    """Test enhanced table creation with indexes."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir)
        
        # Initialize project properly
        from cinchdb.core.initializer import init_project
        init_project(project_dir, database_name="test_db", branch_name="main")
        
        yield project_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def table_manager(self, temp_project):
        """Create a TableManager for testing."""
        return TableManager(temp_project, "test_db", "main", "main")
    
    def test_create_table_with_single_index(self, table_manager):
        """Test creating a table with a single index."""
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False)
        ]
        indexes = [Index(columns=["email"], unique=True)]
        
        table = table_manager.create_table("users", columns, indexes)
        
        assert table.name == "users"
        assert len(table.columns) == 5  # id, created_at, updated_at + user columns
        
        # Verify index was created
        from cinchdb.managers.index import IndexManager
        index_manager = IndexManager(table_manager.project_root, "test_db", "main")
        created_indexes = index_manager.list_indexes("users")
        
        assert len(created_indexes) == 1
        assert created_indexes[0]["name"] == "uniq_users_email"
        assert created_indexes[0]["columns"] == ["email"]
        assert created_indexes[0]["unique"] is True
    
    def test_create_table_with_multiple_indexes(self, table_manager):
        """Test creating a table with multiple indexes."""
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False),
            Column(name="age", type="INTEGER", nullable=True),
            Column(name="city", type="TEXT", nullable=True)
        ]
        indexes = [
            Index(columns=["email"], unique=True),
            Index(columns=["name"]),
            Index(columns=["city", "age"], name="location_age_idx")
        ]
        
        table = table_manager.create_table("users", columns, indexes)
        
        # Verify all indexes were created
        from cinchdb.managers.index import IndexManager
        index_manager = IndexManager(table_manager.project_root, "test_db", "main")
        created_indexes = index_manager.list_indexes("users")
        
        assert len(created_indexes) == 3
        
        # Check each index
        index_names = {idx["name"] for idx in created_indexes}
        assert "uniq_users_email" in index_names
        assert "idx_users_name" in index_names
        assert "location_age_idx" in index_names
        
        # Verify specific properties
        for idx in created_indexes:
            if idx["name"] == "uniq_users_email":
                assert idx["unique"] is True
                assert idx["columns"] == ["email"]
            elif idx["name"] == "idx_users_name":
                assert idx["unique"] is False
                assert idx["columns"] == ["name"]
            elif idx["name"] == "location_age_idx":
                assert idx["unique"] is False
                assert idx["columns"] == ["city", "age"]
    
    def test_create_table_without_indexes(self, table_manager):
        """Test that creating table without indexes still works."""
        columns = [Column(name="name", type="TEXT", nullable=False)]
        
        table = table_manager.create_table("simple", columns)
        
        assert table.name == "simple"
        
        # Verify no indexes were created (beyond any SQLite auto-creates)
        from cinchdb.managers.index import IndexManager
        index_manager = IndexManager(table_manager.project_root, "test_db", "main")
        created_indexes = index_manager.list_indexes("simple")
        
        # Should only have SQLite's automatic rowid index, if any
        user_indexes = [idx for idx in created_indexes if not idx["name"].startswith("sqlite_")]
        assert len(user_indexes) == 0
    
    def test_create_table_indexes_none_parameter(self, table_manager):
        """Test that passing indexes=None works the same as omitting it."""
        columns = [Column(name="name", type="TEXT", nullable=False)]
        
        table = table_manager.create_table("simple", columns, indexes=None)
        
        assert table.name == "simple"
        
        # Should behave same as not passing indexes parameter
        from cinchdb.managers.index import IndexManager
        index_manager = IndexManager(table_manager.project_root, "test_db", "main")
        created_indexes = index_manager.list_indexes("simple")
        
        user_indexes = [idx for idx in created_indexes if not idx["name"].startswith("sqlite_")]
        assert len(user_indexes) == 0


class TestCinchDBIndexIntegration:
    """Test Index model integration with CinchDB class."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir)
        
        # Initialize project properly
        from cinchdb.core.initializer import init_project
        init_project(project_dir, database_name="test_db", branch_name="main")
        
        yield project_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def db(self, temp_project):
        """Create a CinchDB instance for testing."""
        return CinchDB(project_dir=str(temp_project), database="test_db")
    
    def test_cinchdb_create_index_uses_index_model_internally(self, db):
        """Test that CinchDB.create_index uses Index model for validation."""
        # Create a simple table first
        db.tables.create_table("test_table", [Column(name="name", type="TEXT")])
        
        # Create index - this should internally use Index model for validation
        index_name = db.create_index("test_table", ["name"], unique=True)
        
        assert index_name == "uniq_test_table_name"
        
        # Verify index exists
        indexes = db.indexes.list_indexes("test_table")
        assert len(indexes) == 1
        assert indexes[0]["name"] == "uniq_test_table_name"
    
    def test_enhanced_table_creation_with_cinchdb(self, db):
        """Test enhanced table creation through CinchDB instance."""
        table = db.tables.create_table(
            "products",
            columns=[
                Column(name="name", type="TEXT", nullable=False),
                Column(name="price", type="REAL", nullable=False),
                Column(name="category", type="TEXT", nullable=True)
            ],
            indexes=[
                Index(columns=["name"], unique=True),
                Index(columns=["category"]),
                Index(columns=["category", "price"], name="category_price_idx")
            ]
        )
        
        assert table.name == "products"
        
        # Verify indexes were created
        indexes = db.indexes.list_indexes("products")
        assert len(indexes) == 3
        
        index_names = {idx["name"] for idx in indexes}
        assert "uniq_products_name" in index_names
        assert "idx_products_category" in index_names
        assert "category_price_idx" in index_names
    
    def test_backward_compatibility_still_works(self, db):
        """Test that old API continues to work alongside new API."""
        # Create table the new way with indexes
        db.tables.create_table(
            "new_table",
            columns=[Column(name="data", type="TEXT")],
            indexes=[Index(columns=["data"])]
        )
        
        # Create table the old way
        db.tables.create_table("old_table", [Column(name="info", type="TEXT")])
        
        # Add index the old way
        old_index = db.create_index("old_table", ["info"], unique=True)
        
        # Verify both approaches work
        new_indexes = db.indexes.list_indexes("new_table")
        old_indexes = db.indexes.list_indexes("old_table")
        
        assert len(new_indexes) == 1
        assert len(old_indexes) == 1
        assert old_index == "uniq_old_table_info"


class TestIndexModelValidation:
    """Test Index model validation through actual usage."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_dir = Path(temp_dir)
        
        # Initialize project properly
        from cinchdb.core.initializer import init_project
        init_project(project_dir, database_name="test_db", branch_name="main")
        
        yield project_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def table_manager(self, temp_project):
        """Create a TableManager for testing."""
        return TableManager(temp_project, "test_db", "main", "main")
    
    def test_index_validation_through_table_creation(self, table_manager):
        """Test that Index model validation works through table creation."""
        columns = [Column(name="name", type="TEXT")]
        
        # Create table first
        table_manager.create_table("test", columns)
        
        # Test invalid column names in indexes
        with pytest.raises(ValueError, match="do not exist in table"):
            invalid_indexes = [Index(columns=["nonexistent_column"])]
            table_manager.create_table("test2", columns, invalid_indexes)
    
    def test_index_validation_through_cinchdb_create_index(self, table_manager):
        """Test that Index validation works through CinchDB.create_index method."""
        # Create table first
        table_manager.create_table("test", [Column(name="name", type="TEXT")])
        
        # Use CinchDB to create index - should validate through Index model
        db = CinchDB(project_dir=str(table_manager.project_root), database="test_db")
        
        # Valid case
        index_name = db.create_index("test", ["name"])
        assert index_name == "idx_test_name"
        
        # Invalid case - nonexistent column should be caught by Index model validation
        with pytest.raises(ValueError, match="do not exist in table"):
            db.create_index("test", ["nonexistent"])
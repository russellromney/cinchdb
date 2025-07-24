"""Tests for DataManager - CRUD operations on table data."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from cinchdb.config import Config
from cinchdb.managers.data import DataManager
from cinchdb.managers.table import TableManager
from cinchdb.models import Column


# Test model for CRUD operations
class UserModel(BaseModel):
    """Test model representing a user table."""
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"table_name": "users"}
    )
    
    id: Optional[str] = Field(default=None, description="id field")
    created_at: Optional[datetime] = Field(default=None, description="created_at field")
    updated_at: Optional[datetime] = Field(default=None, description="updated_at field")
    name: str = Field(description="name field")
    email: str = Field(description="email field")  
    age: int = Field(description="age field")


class TestDataManager:
    """Test suite for DataManager CRUD operations."""
    
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
    def data_manager(self, temp_project):
        """Create a DataManager instance with test table."""
        project_root = temp_project
        database = "main"
        branch = "main"
        tenant = "main"
        
        # Create table manager and test table
        table_manager = TableManager(project_root, database, branch, tenant)
        
        # Create users table
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False),
            Column(name="age", type="INTEGER", nullable=False)
        ]
        table_manager.create_table("users", columns)
        
        # Create and return data manager
        return DataManager(project_root, database, branch, tenant)
    
    def test_create_record(self, data_manager):
        """Test creating a new record."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        created_user = data_manager.create(user)
        
        assert created_user.id is not None
        assert created_user.created_at is not None
        assert created_user.updated_at is not None
        assert created_user.name == "John Doe"
        assert created_user.email == "john@example.com"
        assert created_user.age == 30
    
    def test_create_duplicate_id_fails(self, data_manager):
        """Test that creating a record with existing ID fails."""
        user1 = UserModel(id="test-id", name="John", email="john@example.com", age=30)
        user2 = UserModel(id="test-id", name="Jane", email="jane@example.com", age=25)
        
        data_manager.create(user1)
        
        with pytest.raises(ValueError, match="Record with ID test-id already exists"):
            data_manager.create(user2)
    
    def test_find_by_id(self, data_manager):
        """Test finding a record by ID."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        created_user = data_manager.create(user)
        
        found_user = data_manager.find_by_id(UserModel, created_user.id)
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.name == "John Doe"
        
        # Test non-existent ID
        not_found = data_manager.find_by_id(UserModel, "non-existent")
        assert not_found is None
    
    def test_select_all(self, data_manager):
        """Test selecting all records."""
        # Create test users
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(name="Jane", email="jane@example.com", age=25),
            UserModel(name="Bob", email="bob@example.com", age=35)
        ]
        
        for user in users:
            data_manager.create(user)
        
        # Select all
        all_users = data_manager.select(UserModel)
        assert len(all_users) == 3
        
        names = [user.name for user in all_users]
        assert "John" in names
        assert "Jane" in names
        assert "Bob" in names
    
    def test_select_with_filters(self, data_manager):
        """Test selecting records with filters."""
        # Create test users
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(name="Jane", email="jane@example.com", age=25),
            UserModel(name="Bob", email="bob@example.com", age=35)
        ]
        
        for user in users:
            data_manager.create(user)
        
        # Filter by exact match
        johns = data_manager.select(UserModel, name="John")
        assert len(johns) == 1
        assert johns[0].name == "John"
        
        # Filter by age with operator
        older_users = data_manager.select(UserModel, age__gte=30)
        assert len(older_users) == 2
        ages = [user.age for user in older_users]
        assert 30 in ages
        assert 35 in ages
    
    def test_select_with_operators(self, data_manager):
        """Test various filter operators."""
        # Create test users
        users = [
            UserModel(name="Alice", email="alice@example.com", age=20),
            UserModel(name="Bob", email="bob@example.com", age=25),
            UserModel(name="Charlie", email="charlie@example.com", age=30),
            UserModel(name="David", email="david@example.com", age=35)
        ]
        
        for user in users:
            data_manager.create(user)
        
        # Test gte (greater than or equal)
        gte_results = data_manager.select(UserModel, age__gte=25)
        assert len(gte_results) == 3
        
        # Test lte (less than or equal)
        lte_results = data_manager.select(UserModel, age__lte=25)
        assert len(lte_results) == 2
        
        # Test gt (greater than)
        gt_results = data_manager.select(UserModel, age__gt=25)
        assert len(gt_results) == 2
        
        # Test lt (less than)
        lt_results = data_manager.select(UserModel, age__lt=30)
        assert len(lt_results) == 2
        
        # Test like
        like_results = data_manager.select(UserModel, name__like="A%")
        assert len(like_results) == 1
        assert like_results[0].name == "Alice"
        
        # Test in
        in_results = data_manager.select(UserModel, age__in=[20, 30])
        assert len(in_results) == 2
        ages = [user.age for user in in_results]
        assert 20 in ages
        assert 30 in ages
    
    def test_select_with_limit_offset(self, data_manager):
        """Test selecting with limit and offset."""
        # Create test users
        for i in range(10):
            user = UserModel(name=f"User{i}", email=f"user{i}@example.com", age=20 + i)
            data_manager.create(user)
        
        # Test limit
        limited = data_manager.select(UserModel, limit=5)
        assert len(limited) == 5
        
        # Test offset
        offset_results = data_manager.select(UserModel, limit=3, offset=2)
        assert len(offset_results) == 3
    
    def test_update_record(self, data_manager):
        """Test updating an existing record."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        created_user = data_manager.create(user)
        
        # Update the user
        created_user.name = "John Smith"
        created_user.age = 31
        updated_user = data_manager.update(created_user)
        
        assert updated_user.name == "John Smith"
        assert updated_user.age == 31
        assert updated_user.id == created_user.id
        assert updated_user.created_at == created_user.created_at
        assert updated_user.updated_at > created_user.updated_at
    
    def test_update_nonexistent_record_fails(self, data_manager):
        """Test that updating a non-existent record fails."""
        user = UserModel(id="non-existent", name="John", email="john@example.com", age=30)
        
        with pytest.raises(ValueError, match="Record with ID non-existent not found"):
            data_manager.update(user)
    
    def test_update_without_id_fails(self, data_manager):
        """Test that updating a record without ID fails."""
        user = UserModel(name="John", email="john@example.com", age=30)
        
        with pytest.raises(ValueError, match="Cannot update record without ID"):
            data_manager.update(user)
    
    def test_save_upsert_create(self, data_manager):
        """Test save operation creates new record when it doesn't exist."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        saved_user = data_manager.save(user)
        
        assert saved_user.id is not None
        assert saved_user.created_at is not None
        assert saved_user.updated_at is not None
    
    def test_save_upsert_update(self, data_manager):
        """Test save operation updates existing record."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        created_user = data_manager.create(user)
        
        # Modify and save
        created_user.name = "John Smith"
        saved_user = data_manager.save(created_user)
        
        assert saved_user.id == created_user.id
        assert saved_user.name == "John Smith"
        assert saved_user.updated_at > created_user.updated_at
    
    def test_delete_by_filters(self, data_manager):
        """Test deleting records by filters."""
        # Create test users
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(name="Jane", email="jane@example.com", age=25),
            UserModel(name="Bob", email="bob@example.com", age=35)
        ]
        
        for user in users:
            data_manager.create(user)
        
        # Delete by filter
        deleted_count = data_manager.delete(UserModel, name="John")
        assert deleted_count == 1
        
        # Verify deletion
        remaining = data_manager.select(UserModel)
        assert len(remaining) == 2
        names = [user.name for user in remaining]
        assert "John" not in names
    
    def test_delete_by_id(self, data_manager):
        """Test deleting a record by ID."""
        user = UserModel(name="John Doe", email="john@example.com", age=30)
        created_user = data_manager.create(user)
        
        # Delete by ID
        deleted = data_manager.delete_by_id(UserModel, created_user.id)
        assert deleted is True
        
        # Verify deletion
        found = data_manager.find_by_id(UserModel, created_user.id)
        assert found is None
        
        # Test deleting non-existent ID
        not_deleted = data_manager.delete_by_id(UserModel, "non-existent")
        assert not_deleted is False
    
    def test_delete_without_filters_fails(self, data_manager):
        """Test that delete without filters fails for safety."""
        with pytest.raises(ValueError, match="Delete requires at least one filter"):
            data_manager.delete(UserModel)
    
    def test_bulk_create(self, data_manager):
        """Test creating multiple records in a single transaction."""
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(name="Jane", email="jane@example.com", age=25),
            UserModel(name="Bob", email="bob@example.com", age=35)
        ]
        
        created_users = data_manager.bulk_create(users)
        
        assert len(created_users) == 3
        for user in created_users:
            assert user.id is not None
            assert user.created_at is not None
            assert user.updated_at is not None
        
        # Verify all were created
        all_users = data_manager.select(UserModel)
        assert len(all_users) == 3
    
    def test_bulk_create_empty_list(self, data_manager):
        """Test bulk create with empty list."""
        result = data_manager.bulk_create([])
        assert result == []
    
    def test_count(self, data_manager):
        """Test counting records."""
        # Initially no records
        assert data_manager.count(UserModel) == 0
        
        # Create test users
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(name="Jane", email="jane@example.com", age=25),
            UserModel(name="Bob", email="bob@example.com", age=35)
        ]
        
        for user in users:
            data_manager.create(user)
        
        # Count all
        assert data_manager.count(UserModel) == 3
        
        # Count with filters
        assert data_manager.count(UserModel, age__gte=30) == 2
        assert data_manager.count(UserModel, name="John") == 1
    
    def test_table_name_extraction(self, data_manager):
        """Test table name extraction from model class."""
        table_name = data_manager._get_table_name(UserModel)
        assert table_name == "users"
    
    def test_invalid_operator_fails(self, data_manager):
        """Test that invalid filter operators fail."""
        user = UserModel(name="John", email="john@example.com", age=30)
        data_manager.create(user)
        
        with pytest.raises(ValueError, match="Unsupported operator: invalid"):
            data_manager.select(UserModel, age__invalid=30)
    
    def test_where_clause_building(self, data_manager):
        """Test WHERE clause building logic."""
        # Test empty filters
        where, params = data_manager._build_where_clause({})
        assert where == ""
        assert params == {}
        
        # Test exact match
        where, params = data_manager._build_where_clause({"name": "John"})
        assert where == "name = :name"
        assert params == {"name": "John"}
        
        # Test multiple filters
        where, params = data_manager._build_where_clause({"name": "John", "age": 30})
        assert "name = :name" in where
        assert "age = :age" in where
        assert " AND " in where
        assert params == {"name": "John", "age": 30}
        
        # Test operator
        where, params = data_manager._build_where_clause({"age__gte": 30})
        assert where == "age >= :age_gte"
        assert params == {"age_gte": 30}
        
        # Test IN operator
        where, params = data_manager._build_where_clause({"age__in": [20, 30]})
        assert where == "age IN (:age_in_0, :age_in_1)"
        assert params == {"age_in_0": 20, "age_in_1": 30}
    
    def test_transaction_rollback_on_error(self, data_manager):
        """Test that transactions are rolled back on errors."""
        # This test verifies error handling in bulk operations
        users = [
            UserModel(name="John", email="john@example.com", age=30),
            UserModel(id="duplicate", name="Jane", email="jane@example.com", age=25),
            UserModel(id="duplicate", name="Bob", email="bob@example.com", age=35)  # Duplicate ID
        ]
        
        with pytest.raises(Exception):  # Should fail on duplicate ID
            data_manager.bulk_create(users)
        
        # Verify no records were created due to rollback
        all_users = data_manager.select(UserModel)
        assert len(all_users) == 0
"""Tests for enhanced codegen with CRUD operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.config import Config
from cinchdb.managers.table import TableManager
from cinchdb.managers.codegen import CodegenManager
from cinchdb.models import Column


class TestCodegenEnhanced:
    """Test suite for enhanced codegen with CRUD operations."""
    
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
    def codegen_manager(self, temp_project):
        """Create a CodegenManager instance with test table."""
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
        
        # Create and return codegen manager
        return CodegenManager(project_root, database, branch, tenant)
    
    def test_enhanced_model_generation(self, temp_project, codegen_manager):
        """Test that enhanced models are generated with CRUD methods."""
        output_dir = temp_project / "generated_models"
        
        result = codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        assert "users.py" in result["files_generated"]
        assert "users" in result["tables_processed"]
        
        # Read generated model file
        users_file = output_dir / "users.py"
        assert users_file.exists()
        
        content = users_file.read_text()
        
        # Check for enhanced imports
        assert "from cinchdb.managers.data import DataManager" in content
        assert "from typing import Optional, List, ClassVar" in content
        
        # Check for class variable
        assert "_data_manager: ClassVar[Optional[DataManager]] = None" in content
        
        # Check for CRUD methods
        assert "def set_connection(" in content
        assert "def select(" in content
        assert "def find_by_id(" in content
        assert "def create(" in content
        assert "def bulk_create(" in content
        assert "def count(" in content
        assert "def delete_records(" in content
        assert "def save(self)" in content
        assert "def update(self)" in content
        assert "def delete(self)" in content
        
        # Check method implementations
        assert "return cls._get_data_manager().select(cls" in content
        assert "return cls._get_data_manager().find_by_id(cls" in content
        assert "return cls._get_data_manager().create(instance)" in content
    
    def test_generated_model_functionality(self, temp_project, codegen_manager):
        """Test that generated models work with DataManager."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Import the generated model dynamically
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            from users import Users
            
            # Set connection
            Users.set_connection(
                temp_project, "main", "main", "main"
            )
            
            # Test create operation
            user = Users.create(name="John Doe", email="john@example.com", age=30)
            assert user.id is not None
            assert user.name == "John Doe"
            assert user.email == "john@example.com"
            assert user.age == 30
            assert user.created_at is not None
            assert user.updated_at is not None
            
            # Test find_by_id
            found_user = Users.find_by_id(user.id)
            assert found_user is not None
            assert found_user.id == user.id
            assert found_user.name == "John Doe"
            
            # Test select
            all_users = Users.select()
            assert len(all_users) == 1
            assert all_users[0].id == user.id
            
            # Test select with filters
            johns = Users.select(name="John Doe")
            assert len(johns) == 1
            
            adults = Users.select(age__gte=18)
            assert len(adults) == 1
            
            # Test count
            assert Users.count() == 1
            assert Users.count(name="John Doe") == 1
            
            # Test save (update)
            user.name = "John Smith"
            updated_user = user.save()
            assert updated_user.name == "John Smith"
            assert updated_user.id == user.id
            
            # Test update
            user.age = 31
            updated_user = user.update()
            assert updated_user.age == 31
            
            # Test bulk_create
            new_users = [
                {"name": "Jane Doe", "email": "jane@example.com", "age": 25},
                {"name": "Bob Smith", "email": "bob@example.com", "age": 35}
            ]
            created_users = Users.bulk_create(new_users)
            assert len(created_users) == 2
            assert Users.count() == 3
            
            # Test delete_records
            deleted_count = Users.delete_records(name="Jane Doe")
            assert deleted_count == 1
            assert Users.count() == 2
            
            # Test instance delete
            deleted = user.delete()
            assert deleted is True
            assert Users.count() == 1
            
        finally:
            # Clean up sys.path
            sys.path.remove(str(output_dir))
    
    def test_model_without_connection_fails(self, temp_project, codegen_manager):
        """Test that models fail gracefully without connection."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Import the generated model dynamically
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            from users import Users
            
            # Reset the data manager to None to simulate fresh import without connection
            Users._data_manager = None
            
            # Don't set connection - should fail
            with pytest.raises(RuntimeError, match="Model not initialized"):
                Users.select()
            
            with pytest.raises(RuntimeError, match="Model not initialized"):
                Users.find_by_id("test-id")
            
            with pytest.raises(RuntimeError, match="Model not initialized"):
                Users.create(name="Test", email="test@example.com", age=25)
                
        finally:
            # Clean up sys.path
            sys.path.remove(str(output_dir))
    
    def test_table_name_extraction(self, temp_project, codegen_manager):
        """Test that table name is correctly extracted from model config."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Read generated model file
        users_file = output_dir / "users.py"
        content = users_file.read_text()
        
        # Check that table name is in json_schema_extra
        assert 'json_schema_extra={"table_name": "users"}' in content
    
    def test_model_class_methods_return_types(self, temp_project, codegen_manager):
        """Test that class methods have correct return type annotations."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Read generated model file
        users_file = output_dir / "users.py"
        content = users_file.read_text()
        
        # Check return type annotations
        assert "-> List['Users']:" in content  # select method
        assert "-> Optional['Users']:" in content  # find_by_id method
        assert "-> 'Users':" in content  # create method
        assert "def save(self) -> 'Users':" in content  # save method
        assert "def update(self) -> 'Users':" in content  # update method
        assert "def delete(self) -> bool:" in content  # delete method
    
    def test_init_file_generation(self, temp_project):
        """Test that __init__.py is generated correctly."""
        # Create table manager directly for this test
        table_manager = TableManager(temp_project, "main", "main", "main")
        
        # Create another table for testing
        columns = [
            Column(name="title", type="TEXT", nullable=False),
            Column(name="content", type="TEXT", nullable=True)
        ]
        table_manager.create_table("posts", columns)
        
        # Create codegen manager
        codegen_manager = CodegenManager(temp_project, "main", "main", "main")
        
        output_dir = temp_project / "generated_models"
        
        # Generate models
        result = codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        assert "__init__.py" in result["files_generated"]
        
        # Read __init__.py
        init_file = output_dir / "__init__.py"
        assert init_file.exists()
        
        content = init_file.read_text()
        
        # Check imports - should include both users and posts
        # Note: users table is from the fixture, posts is from this test
        assert "from .posts import Posts" in content
        
        # Check __all__ export - should include Posts (users might not be present in this specific test)
        assert '"Posts"' in content
    
    def test_field_generation_with_types(self, temp_project):
        """Test that fields are generated with correct types."""
        # Create table manager and table with various column types
        table_manager = TableManager(temp_project, "main", "main", "main")
        
        columns = [
            Column(name="text_field", type="TEXT", nullable=True),
            Column(name="int_field", type="INTEGER", nullable=False),
            Column(name="real_field", type="REAL", nullable=True),
            Column(name="blob_field", type="BLOB", nullable=True)
        ]
        table_manager.create_table("test_types", columns)
        
        # Create codegen manager
        codegen_manager = CodegenManager(temp_project, "main", "main", "main")
        
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Read generated model file
        test_types_file = output_dir / "test_types.py"
        content = test_types_file.read_text()
        
        # Check field types
        assert "text_field: Optional[str]" in content
        assert "int_field: int" in content
        assert "real_field: Optional[float]" in content
        assert "blob_field: Optional[bytes]" in content
        
        # Check that created_at and updated_at have datetime type
        assert "created_at: Optional[datetime]" in content
        assert "updated_at: Optional[datetime]" in content
    
    def test_error_handling_in_generated_methods(self, temp_project, codegen_manager):
        """Test error handling in generated model methods."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Import the generated model dynamically
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            from users import Users
            
            # Set connection
            Users.set_connection(
                temp_project, "main", "main", "main"
            )
            
            # Test delete without ID fails
            user = Users(name="Test", email="test@example.com", age=25)
            # user.id is None at this point
            
            # This should be handled by the delete method checking for ID
            with pytest.raises(ValueError, match="Cannot delete record without ID"):
                user.delete()
                
        finally:
            # Clean up sys.path
            sys.path.remove(str(output_dir))
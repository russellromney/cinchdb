"""Tests for enhanced codegen with CRUD operations."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.config import Config
from cinchdb.managers.table import TableManager
from cinchdb.managers.codegen import CodegenManager
from cinchdb.models import Column
from cinchdb.core.database import CinchDB


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
        
        # Check enhanced model structure with CinchModels container pattern
        assert "from pydantic import BaseModel" in content
        assert "from typing import Optional" in content
        assert "from datetime import datetime" in content
        assert "from cinchdb.managers.data import DataManager" in content
        
        # Should NOT have set_connection method (replaced by CinchModels container)
        assert "def set_connection(" not in content
        
        # Should HAVE CRUD methods, but they use container-managed data manager
        assert "def select(" in content
        assert "def find_by_id(" in content
        assert "def create(" in content
        assert "def bulk_create(" in content
        assert "def count(" in content
        assert "def delete_records(" in content
        assert "def save(self)" in content
        assert "def update(self)" in content
        assert "def delete(self)" in content
        
        # Check that methods rely on container-managed data manager
        assert "_data_manager: ClassVar[Optional[DataManager]] = None" in content
        assert "def _get_data_manager(cls) -> DataManager:" in content
        assert "Model not initialized. Access models through CinchModels container." in content
        
        # Check that CinchModels container was generated
        assert "cinch_models.py" in result["files_generated"]
        cinch_models_file = output_dir / "cinch_models.py"
        assert cinch_models_file.exists()
        
        # Check __init__.py has create_models function
        init_file = output_dir / "__init__.py"
        init_content = init_file.read_text()
        assert "def create_models(" in init_content
    
    def test_generated_model_functionality(self, temp_project, codegen_manager):
        """Test that generated models have the expected structure and error handling."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Import the generated models using the new unified approach
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            # Import the generated models directly
            import users
            
            # Test that model has the expected structure
            assert hasattr(users.Users, '_data_manager')
            assert hasattr(users.Users, 'select')
            assert hasattr(users.Users, 'create')
            assert hasattr(users.Users, 'find_by_id')
            
            # Test that methods require proper initialization
            with pytest.raises(RuntimeError, match="Model not initialized"):
                users.Users.select()
                
            with pytest.raises(RuntimeError, match="Model not initialized"):
                users.Users.create(name="Test", email="test@example.com", age=25)
            
            # Test that CinchModels container was generated
            import cinch_models
            assert hasattr(cinch_models, 'CinchModels')
            
            # Test basic instantiation (doesn't require database operations)
            db = CinchDB(database="main", branch="main", tenant="main", project_dir=temp_project)
            container = cinch_models.CinchModels(db)
            assert container is not None
            
        finally:
            # Clean up sys.path
            sys.path.remove(str(output_dir))
    
    def test_model_without_connection_fails(self, temp_project, codegen_manager):
        """Test that models fail gracefully without proper connection."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Import the generated model dynamically
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            # Import the generated models directly
            import users
            
            # Test that models require proper initialization via container
            # This is already covered by test_generated_model_functionality
            assert users.Users._data_manager is None
            
            with pytest.raises(RuntimeError, match="Model not initialized"):
                users.Users.select()
                
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
        
        # Check that table name is in model_config
        assert '"table_name": "users"' in content
    
    def test_model_class_methods_return_types(self, temp_project, codegen_manager):
        """Test that CinchModels container provides the correct interface."""
        output_dir = temp_project / "generated_models"
        
        # Generate models
        codegen_manager.generate_models(
            "python", output_dir, include_tables=True, include_views=False
        )
        
        # Check that CinchModels container was generated
        cinch_models_file = output_dir / "cinch_models.py"
        assert cinch_models_file.exists()
        
        content = cinch_models_file.read_text()
        
        # Check that the CinchModels class provides the unified interface
        assert "class CinchModels:" in content
        assert "def __getattr__(" in content
        assert "def with_tenant(" in content
    
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
        
        # Import the generated models using the new unified approach
        import sys
        sys.path.insert(0, str(output_dir))
        
        try:
            # Import the generated models directly
            import users
            
            # Test delete without ID fails
            user = users.Users(name="Test", email="test@example.com", age=25)
            # user.id is None at this point
            
            # This should be handled by the delete method checking for ID
            with pytest.raises(ValueError, match="Cannot delete record without ID"):
                user.delete()
                
        finally:
            # Clean up sys.path
            sys.path.remove(str(output_dir))
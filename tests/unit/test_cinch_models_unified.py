"""Tests for CinchModels unified container functionality."""

import pytest
import tempfile
import shutil
import sys
from pathlib import Path

from cinchdb.config import Config
from cinchdb.core.database import CinchDB
from cinchdb.managers import TableManager, CodegenManager
from cinchdb.models import Column


class TestCinchModelsUnified:
    """Test CinchModels container functionality."""
    
    @pytest.fixture
    def temp_project(self):
        """Create temporary test project."""
        temp = tempfile.mkdtemp()
        project_root = Path(temp)
        
        # Initialize project
        config = Config(project_root)
        config.init_project()
        
        yield project_root
        
        # Cleanup
        shutil.rmtree(temp)
    
    @pytest.fixture
    def project_with_tables(self, temp_project):
        """Create project with test tables."""
        # Create some test tables
        table_manager = TableManager(temp_project, "main", "main", "main")
        
        # Create users table
        users_columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False, unique=True),
            Column(name="age", type="INTEGER", nullable=True)
        ]
        table_manager.create_table("users", users_columns)
        
        # Create products table
        products_columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="price", type="REAL", nullable=False),
            Column(name="category", type="TEXT", nullable=True)
        ]
        table_manager.create_table("products", products_columns)
        
        return temp_project
    
    @pytest.fixture
    def generated_models_dir(self, project_with_tables):
        """Generate models and return the output directory."""
        output_dir = project_with_tables / "generated_models"
        
        # Generate models
        codegen_manager = CodegenManager(project_with_tables, "main", "main", "main")
        codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=True,
            include_views=False
        )
        
        return output_dir
    
    def test_cinch_models_creation(self, project_with_tables, generated_models_dir):
        """Test CinchModels container creation."""
        # Add generated models to path
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            # Import generated modules
            from generated_models import create_models
            
            # Create CinchDB connection
            db = CinchDB(
                database="main",
                branch="main", 
                tenant="main",
                project_dir=project_with_tables
            )
            
            # Create models container
            models = create_models(db)
            
            # Test basic properties
            assert models._connection is db
            assert models._model_registry is not None
            assert len(models._model_registry) == 2  # Users and Products
            assert "Users" in models._model_registry
            assert "Products" in models._model_registry
            
        finally:
            # Clean up path
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_cinch_models_invalid_connection(self, generated_models_dir):
        """Test CinchModels with invalid connection type."""
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            from generated_models import create_models
            
            # Test with invalid connection type
            with pytest.raises(TypeError, match="CinchModels requires a CinchDB connection instance"):
                create_models("not a connection")
                
        finally:
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_model_access_and_initialization(self, project_with_tables, generated_models_dir):
        """Test accessing models through container."""
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            from generated_models import create_models
            
            db = CinchDB(
                database="main",
                branch="main", 
                tenant="main",
                project_dir=project_with_tables
            )
            
            models = create_models(db)
            
            # Access model (should initialize it)
            Users = models.Users
            assert Users is not None
            assert hasattr(Users, '_data_manager')
            assert Users._data_manager is not None
            
            # Access same model again (should return cached)
            Users2 = models.Users
            assert Users is Users2
            
            # Access different model
            Products = models.Products
            assert Products is not None
            assert Products is not Users
            
        finally:
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_model_not_found(self, project_with_tables, generated_models_dir):
        """Test accessing non-existent model."""
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            from generated_models import create_models
            
            db = CinchDB(
                database="main",
                branch="main", 
                tenant="main",
                project_dir=project_with_tables
            )
            
            models = create_models(db)
            
            # Try to access non-existent model
            with pytest.raises(AttributeError, match="Model 'NonExistent' not found"):
                models.NonExistent
                
        finally:
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_with_tenant_functionality(self, project_with_tables, generated_models_dir):
        """Test with_tenant method."""
        # First create a second tenant
        from cinchdb.managers.tenant import TenantManager
        tenant_manager = TenantManager(project_with_tables, "main", "main")
        tenant_manager.create_tenant("customer1")
        
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            from generated_models import create_models
            
            db = CinchDB(
                database="main",
                branch="main", 
                tenant="main",
                project_dir=project_with_tables
            )
            
            models = create_models(db)
            
            # Create tenant-specific models
            customer_models = models.with_tenant("customer1")
            
            # Should be different instance
            assert customer_models is not models
            assert customer_models._connection is db  # Same connection
            assert customer_models._tenant_override == "customer1"
            assert models._tenant_override is None
            
            # Should have same model registry
            assert customer_models._model_registry is models._model_registry
            
        finally:
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_model_crud_operations(self, project_with_tables, generated_models_dir):
        """Test basic CRUD operations through models."""
        sys.path.insert(0, str(generated_models_dir.parent))
        
        try:
            from generated_models import create_models
            
            db = CinchDB(
                database="main",
                branch="main", 
                tenant="main",
                project_dir=project_with_tables
            )
            
            models = create_models(db)
            
            # Test creating a user
            user = models.Users.create(name="Alice", email="alice@example.com", age=25)
            assert user.name == "Alice"
            assert user.email == "alice@example.com"
            assert user.age == 25
            assert user.id is not None
            
            # Test selecting users
            users = models.Users.select()
            assert len(users) == 1
            assert users[0].name == "Alice"
            
            # Test finding by ID
            found_user = models.Users.find_by_id(user.id)
            assert found_user is not None
            assert found_user.name == "Alice"
            
            # Test counting
            count = models.Users.count()
            assert count == 1
            
        finally:
            sys.path.remove(str(generated_models_dir.parent))
    
    def test_generated_model_structure(self, generated_models_dir):
        """Test the structure of generated models."""
        # Check CinchModels file exists and has correct content
        cinch_models_file = generated_models_dir / "cinch_models.py"
        assert cinch_models_file.exists()
        
        content = cinch_models_file.read_text()
        assert "class CinchModels:" in content
        assert "def __init__(self, connection: CinchDB):" in content
        assert "def __getattr__(self, name: str):" in content
        assert "def with_tenant(self, tenant: str)" in content
        
        # Check __init__.py has factory function
        init_file = generated_models_dir / "__init__.py"
        assert init_file.exists()
        
        init_content = init_file.read_text()
        assert "from .cinch_models import CinchModels" in init_content
        assert "def create_models(connection) -> CinchModels:" in init_content
        assert "_MODEL_REGISTRY = {" in init_content
        assert "'Users': Users," in init_content
        assert "'Products': Products," in init_content
    
    def test_model_no_set_connection_method(self, generated_models_dir):
        """Test that generated models don't have set_connection method."""
        # Check that individual model files don't have set_connection
        users_file = generated_models_dir / "users.py"
        assert users_file.exists()
        
        users_content = users_file.read_text()
        assert "def set_connection(" not in users_content
        assert "Model not initialized. Access models through CinchModels container." in users_content
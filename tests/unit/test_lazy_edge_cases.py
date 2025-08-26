"""Test edge cases and interactions between lazy databases and tenants."""

import tempfile
import json
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import list_databases, list_tenants
from cinchdb.core.database import CinchDB


def test_lazy_database_with_lazy_tenants():
    """Test creating lazy tenants within a lazy database."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Try to create tenant in lazy database (should auto-materialize)
        db = CinchDB(database="lazy-db", project_dir=project_dir)
        tenant_manager = TenantManager(project_dir, "lazy-db", "main")
        
        # Create lazy tenant
        tenant = tenant_manager.create_tenant("lazy-tenant", lazy=True)
        assert tenant.name == "lazy-tenant"
        
        # Check that database was materialized
        db_path = project_dir / ".cinchdb" / "databases" / "lazy-db"
        assert db_path.exists()
        
        # Check that tenant is lazy
        tenant_db = db_path / "branches" / "main" / "tenants" / "lazy_tenant.db"
        assert not tenant_db.exists()
        
        tenant_meta = db_path / "branches" / "main" / "tenants" / ".lazy-tenant.meta"
        assert tenant_meta.exists()


def test_mixed_lazy_and_eager_databases():
    """Test project with mix of lazy and eager databases."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project (creates main database eagerly)
        init_project(project_dir)
        
        # Create additional databases
        init_database(project_dir, "eager-db", lazy=False)
        init_database(project_dir, "lazy-db1", lazy=True)
        init_database(project_dir, "lazy-db2", lazy=True)
        
        # List all databases
        databases = list_databases(project_dir)
        assert len(databases) == 4
        assert "main" in databases
        assert "eager-db" in databases
        assert "lazy-db1" in databases
        assert "lazy-db2" in databases
        
        # Verify eager databases have directories
        assert (project_dir / ".cinchdb" / "databases" / "main").exists()
        assert (project_dir / ".cinchdb" / "databases" / "eager-db").exists()
        
        # Verify lazy databases have only metadata
        assert not (project_dir / ".cinchdb" / "databases" / "lazy-db1").exists()
        assert not (project_dir / ".cinchdb" / "databases" / "lazy-db2").exists()
        assert (project_dir / ".cinchdb" / "databases" / ".lazy-db1.meta").exists()
        assert (project_dir / ".cinchdb" / "databases" / ".lazy-db2.meta").exists()


def test_lazy_database_deletion_cleanup():
    """Test that deleting a lazy database removes metadata file."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        assert meta_file.exists()
        
        # Delete metadata file (simulating database deletion)
        meta_file.unlink()
        
        # Database should no longer appear in list
        databases = list_databases(project_dir)
        assert "lazy-db" not in databases


def test_lazy_database_with_description():
    """Test that database descriptions are preserved in lazy metadata."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database with description
        description = "Test database for development"
        init_database(project_dir, "test-db", description=description, lazy=True)
        
        # Check metadata contains description
        meta_file = project_dir / ".cinchdb" / "databases" / ".test-db.meta"
        with open(meta_file) as f:
            metadata = json.load(f)
        
        assert metadata["description"] == description
        
        # Materialize and verify description is preserved
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("test-db")
        
        # Description should be in branch metadata
        branch_meta = project_dir / ".cinchdb" / "databases" / "test-db" / "branches" / "main" / "metadata.json"
        with open(branch_meta) as f:
            branch_data = json.load(f)
        
        assert branch_data["description"] == description


def test_concurrent_access_to_lazy_database():
    """Test that concurrent access to lazy database handles materialization correctly."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, "lazy-db", lazy=True)
        
        # Create multiple connections (simulating concurrent access)
        db1 = CinchDB(database="lazy-db", project_dir=project_dir)
        db2 = CinchDB(database="lazy-db", project_dir=project_dir)
        
        # Both should work without errors
        assert db1.database == "lazy-db"
        assert db2.database == "lazy-db"
        
        # Database should be materialized only once
        db_path = project_dir / ".cinchdb" / "databases" / "lazy-db"
        assert db_path.exists()
        
        # Metadata should be updated
        meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["lazy"] is False


def test_lazy_database_error_handling():
    """Test error handling for invalid lazy database operations."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Try to create database with invalid name
        from cinchdb.utils.name_validator import InvalidNameError
        with pytest.raises(InvalidNameError):
            init_database(project_dir, "invalid name!", lazy=True)
        
        with pytest.raises(InvalidNameError):
            init_database(project_dir, "-starts-with-dash", lazy=True)
        
        with pytest.raises(InvalidNameError):
            init_database(project_dir, "UPPERCASE", lazy=True)
        
        # Try to create duplicate lazy database
        init_database(project_dir, "test-db", lazy=True)
        with pytest.raises(FileExistsError):
            init_database(project_dir, "test-db", lazy=True)
        
        # Try to create duplicate where eager exists
        init_database(project_dir, "eager-db", lazy=False)
        with pytest.raises(FileExistsError):
            init_database(project_dir, "eager-db", lazy=True)
        
        # Try to materialize non-existent database
        initializer = ProjectInitializer(project_dir)
        with pytest.raises(ValueError):
            initializer.materialize_database("nonexistent")


def test_lazy_tenant_in_lazy_database_lifecycle():
    """Test complete lifecycle of lazy tenant in lazy database."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, "lazy-db", lazy=True)
        
        # Connect to database (auto-materializes)
        db = CinchDB(database="lazy-db", project_dir=project_dir)
        
        # Create lazy tenant
        tenant_manager = TenantManager(project_dir, "lazy-db", "main")
        tenant_manager.create_tenant("tenant1", lazy=True)
        tenant_manager.create_tenant("tenant2", lazy=True)
        
        # List tenants (should include both lazy tenants and main)
        tenants = list_tenants(project_dir, "lazy-db", "main")
        assert len(tenants) == 3
        assert "main" in tenants
        assert "tenant1" in tenants
        assert "tenant2" in tenants
        
        # Materialize one tenant
        tenant_manager.materialize_tenant("tenant1")
        
        # Check states
        tenants_dir = project_dir / ".cinchdb" / "databases" / "lazy-db" / "branches" / "main" / "tenants"
        assert (tenants_dir / "tenant1.db").exists()  # Materialized
        assert not (tenants_dir / "tenant2.db").exists()  # Still lazy
        assert (tenants_dir / ".tenant2.meta").exists()  # Has metadata
        
        # Delete lazy tenant
        tenant_manager.delete_tenant("tenant2")
        
        # Should be removed from list
        tenants = list_tenants(project_dir, "lazy-db", "main")
        assert "tenant2" not in tenants
        assert "tenant1" in tenants
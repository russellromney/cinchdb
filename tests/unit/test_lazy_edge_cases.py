"""Test edge cases and interactions between lazy databases and tenants."""

import tempfile
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import list_databases, list_tenants
from cinchdb.core.database import CinchDB
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_lazy_database_with_lazy_tenants():
    """Test creating lazy tenants within a lazy database."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Try to create tenant in lazy database (should auto-materialize)
        CinchDB(database="lazy-db", project_dir=project_dir)
        tenant_manager = TenantManager(project_dir, "lazy-db", "main")
        
        # Create lazy tenant
        tenant = tenant_manager.create_tenant("lazy-tenant", lazy=True)
        assert tenant.name == "lazy-tenant"
        
        # Check that database was materialized
        db_path = project_dir / ".cinchdb" / "databases" / "lazy-db"
        assert db_path.exists()
        
        # Check that tenant is lazy (no physical .db file)
        tenant_db = db_path / "branches" / "main" / "tenants" / "lazy-tenant.db"
        assert not tenant_db.exists()
        
        # Check tenant is in metadata database
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("lazy-db")
            assert db_info is not None
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            lazy_tenant = next((t for t in tenants if t['name'] == 'lazy-tenant'), None)
            assert lazy_tenant is not None
            assert not lazy_tenant['materialized']


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
        
        # Verify lazy databases don't have physical directories
        assert not (project_dir / ".cinchdb" / "databases" / "lazy-db1").exists()
        assert not (project_dir / ".cinchdb" / "databases" / "lazy-db2").exists()
        
        # Verify lazy databases exist in metadata
        with MetadataDB(project_dir) as metadata_db:
            lazy_db1 = metadata_db.get_database("lazy-db1")
            lazy_db2 = metadata_db.get_database("lazy-db2")
            assert lazy_db1 is not None
            assert lazy_db2 is not None
            assert not lazy_db1['materialized']
            assert not lazy_db2['materialized']


def test_lazy_database_deletion_cleanup():
    """Test that deleting a lazy database removes metadata entry."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Verify database exists in metadata
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("lazy-db")
            assert db_info is not None
            assert not db_info['materialized']  # Should be lazy
            
            # Delete from metadata
            metadata_db.delete_database(db_info['id'])
        
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
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("test-db")
            assert db_info is not None
            assert db_info['description'] == description
            assert not db_info['materialized']  # lazy = not materialized
            
        # Access database to auto-materialize it
        CinchDB(database="test-db", project_dir=project_dir)
        
        # Verify it's now materialized but description is preserved
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("test-db")
            assert db_info is not None
            assert db_info['description'] == description
            assert db_info['materialized']  # now materialized


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
        
        # Metadata should be updated to show it's materialized
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("lazy-db")
            assert db_info is not None
            assert db_info['materialized']  # Now materialized


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
        CinchDB(database="lazy-db", project_dir=project_dir)
        
        # Create lazy tenant
        tenant_manager = TenantManager(project_dir, "lazy-db", "main")
        tenant_manager.create_tenant("tenant1", lazy=True)
        tenant_manager.create_tenant("tenant2", lazy=True)
        
        # List tenants (should include both lazy tenants, main, and __empty__)
        tenants = list_tenants(project_dir, "lazy-db", "main")
        assert len(tenants) == 4  # __empty__, main, tenant1, tenant2
        assert "__empty__" in tenants
        assert "main" in tenants
        assert "tenant1" in tenants
        assert "tenant2" in tenants
        
        # Materialize one tenant
        tenant_manager.materialize_tenant("tenant1")
        
        # Check states using sharded paths
        from cinchdb.core.path_utils import get_tenant_db_path
        tenant1_path = get_tenant_db_path(project_dir, "lazy-db", "main", "tenant1")
        tenant2_path = get_tenant_db_path(project_dir, "lazy-db", "main", "tenant2")
        assert tenant1_path.exists()  # Materialized
        assert not tenant2_path.exists()  # Still lazy
        
        # Check metadata state
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("lazy-db")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            
            tenant1_info = next(t for t in tenants if t['name'] == 'tenant1')
            assert tenant1_info['materialized']  # Should be materialized
            
            tenant2_info = next(t for t in tenants if t['name'] == 'tenant2')
            assert not tenant2_info['materialized']  # Still lazy
        
        # Delete lazy tenant
        tenant_manager.delete_tenant("tenant2")
        
        # Should be removed from list
        tenants = list_tenants(project_dir, "lazy-db", "main")
        assert "tenant2" not in tenants
        assert "tenant1" in tenants
        assert "__empty__" in tenants  # System tenant still exists
        assert "main" in tenants
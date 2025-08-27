"""Test lazy tenant creation functionality."""

import tempfile
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import list_tenants, get_tenant_db_path
from cinchdb.core.connection import DatabaseConnection
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_lazy_tenant_creation():
    """Test that lazy tenants don't create database files."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant = tenant_manager.create_tenant("lazy-tenant", lazy=True)
        assert tenant.name == "lazy-tenant"
        
        # Check that tenant is tracked in metadata database
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            assert db_info is not None
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            lazy_tenant = next((t for t in tenants if t['name'] == 'lazy-tenant'), None)
            assert lazy_tenant is not None
            assert not lazy_tenant['materialized']  # Not materialized = lazy
        
        # Check that database file does NOT exist
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy-tenant")
        assert not db_path.exists()
        
        # Verify tenant appears in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy-tenant" in tenants


def test_lazy_tenant_materialization():
    """Test materializing a lazy tenant."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with a table in main
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        # Add a table to __empty__ tenant (which serves as template for lazy tenants)
        empty_db_path = get_tenant_db_path(project_dir, "testdb", "main", "__empty__")
        with DatabaseConnection(empty_db_path) as conn:
            conn.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """)
            conn.commit()
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant_manager.create_tenant("lazy-tenant", lazy=True)
        
        # Database shouldn't exist yet
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy-tenant")
        assert not db_path.exists()
        
        # Materialize the tenant
        tenant_manager.materialize_tenant("lazy-tenant")
        
        # Now database should exist
        assert db_path.exists()
        
        # Check that the table structure was copied
        with DatabaseConnection(db_path) as conn:
            result = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='test_table'
            """)
            tables = [row["name"] for row in result.fetchall()]
            assert "test_table" in tables
            
            # Check that table is empty
            result = conn.execute("SELECT COUNT(*) as count FROM test_table")
            assert result.fetchone()["count"] == 0
        
        # Check that metadata was updated
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            lazy_tenant = next((t for t in tenants if t['name'] == 'lazy-tenant'), None)
            assert lazy_tenant is not None
            assert lazy_tenant['materialized']  # Now materialized


def test_lazy_vs_eager_tenant_size():
    """Test that lazy tenants use less space than eager tenants."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create eager tenant
        tenant_manager.create_tenant("eager-tenant", lazy=False)
        eager_db_path = tenant_manager._get_sharded_tenant_db_path("eager-tenant")
        eager_size = eager_db_path.stat().st_size
        
        # Create lazy tenant
        tenant_manager.create_tenant("lazy-tenant", lazy=True)
        
        # Check that lazy tenant has no physical .db file
        lazy_db_path = tenant_manager._get_sharded_tenant_db_path("lazy-tenant")
        assert not lazy_db_path.exists()
        
        # Eager tenant should have a physical database file
        assert eager_db_path.exists()
        assert eager_size >= 4096  # At least one 4KB page (SQLite default)
        assert eager_size <= 8192  # Should be very small for empty tenant


def test_duplicate_lazy_tenant_fails():
    """Test that creating duplicate lazy tenant fails."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant_manager.create_tenant("test-tenant", lazy=True)
        
        # Try to create again (should fail)
        with pytest.raises(ValueError) as exc_info:
            tenant_manager.create_tenant("test-tenant", lazy=True)
        assert "already exists" in str(exc_info.value)


def test_materialize_nonexistent_tenant_fails():
    """Test that materializing a non-existent tenant fails."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Try to materialize non-existent tenant
        with pytest.raises(ValueError) as exc_info:
            tenant_manager.materialize_tenant("nonexistent")
        assert "does not exist" in str(exc_info.value)


def test_materialize_already_materialized():
    """Test that materializing an already materialized tenant is a no-op."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create eager tenant
        tenant_manager.create_tenant("eager-tenant", lazy=False)
        db_path = tenant_manager._get_sharded_tenant_db_path("eager-tenant")
        
        # Get original modification time
        original_mtime = db_path.stat().st_mtime
        
        # Try to materialize (should be no-op)
        tenant_manager.materialize_tenant("eager-tenant")
        
        # Modification time should not change
        assert db_path.stat().st_mtime == original_mtime


def test_delete_lazy_tenant():
    """Test deleting a lazy tenant."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant_manager.create_tenant("lazy-tenant", lazy=True)
        
        # Verify tenant exists in metadata
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            assert any(t['name'] == 'lazy-tenant' for t in tenants)
        
        # Delete tenant
        tenant_manager.delete_tenant("lazy-tenant")
        
        # Tenant should be gone from metadata
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            assert not any(t['name'] == 'lazy-tenant' for t in tenants)
        
        # Tenant should not appear in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy-tenant" not in tenants
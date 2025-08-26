"""Test lazy tenant creation functionality."""

import tempfile
import json
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import list_tenants, get_tenant_db_path
from cinchdb.core.connection import DatabaseConnection


def test_lazy_tenant_creation():
    """Test that lazy tenants don't create database files."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant = tenant_manager.create_tenant("lazy_tenant", lazy=True)
        assert tenant.name == "lazy_tenant"
        
        # Check that metadata file exists
        meta_file = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / ".lazy_tenant.meta"
        assert meta_file.exists()
        
        # Check metadata content
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["name"] == "lazy_tenant"
        assert metadata["lazy"] is True
        
        # Check that database file does NOT exist
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy_tenant")
        assert not db_path.exists()
        
        # Verify tenant appears in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy_tenant" in tenants


def test_lazy_tenant_materialization():
    """Test materializing a lazy tenant."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with a table in main
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        # Add a table to main tenant
        main_db_path = get_tenant_db_path(project_dir, "testdb", "main", "main")
        with DatabaseConnection(main_db_path) as conn:
            conn.execute("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
            """)
            conn.commit()
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant_manager.create_tenant("lazy_tenant", lazy=True)
        
        # Database shouldn't exist yet
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy_tenant")
        assert not db_path.exists()
        
        # Materialize the tenant
        tenant_manager.materialize_tenant("lazy_tenant")
        
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
        meta_file = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / ".lazy_tenant.meta"
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["lazy"] is False
        assert "materialized_at" in metadata


def test_lazy_vs_eager_tenant_size():
    """Test that lazy tenants use less space than eager tenants."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create eager tenant
        tenant_manager.create_tenant("eager_tenant", lazy=False)
        eager_db_path = get_tenant_db_path(project_dir, "testdb", "main", "eager_tenant")
        eager_size = eager_db_path.stat().st_size
        
        # Create lazy tenant
        tenant_manager.create_tenant("lazy_tenant", lazy=True)
        lazy_meta_file = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / ".lazy_tenant.meta"
        lazy_size = lazy_meta_file.stat().st_size
        
        # Lazy tenant should be much smaller (metadata only)
        assert lazy_size < 1024  # Less than 1KB
        assert eager_size >= 4096  # At least 4KB  
        assert lazy_size < eager_size / 4  # At least 4x smaller


def test_duplicate_lazy_tenant_fails():
    """Test that creating duplicate lazy tenant fails."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        
        # Create lazy tenant
        tenant_manager.create_tenant("test_tenant", lazy=True)
        
        # Try to create again (should fail)
        with pytest.raises(ValueError) as exc_info:
            tenant_manager.create_tenant("test_tenant", lazy=True)
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
        tenant_manager.create_tenant("eager_tenant", lazy=False)
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "eager_tenant")
        
        # Get original modification time
        original_mtime = db_path.stat().st_mtime
        
        # Try to materialize (should be no-op)
        tenant_manager.materialize_tenant("eager_tenant")
        
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
        tenant_manager.create_tenant("lazy_tenant", lazy=True)
        meta_file = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / ".lazy_tenant.meta"
        assert meta_file.exists()
        
        # Delete tenant
        tenant_manager.delete_tenant("lazy_tenant")
        
        # Metadata file should be gone
        assert not meta_file.exists()
        
        # Tenant should not appear in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy_tenant" not in tenants
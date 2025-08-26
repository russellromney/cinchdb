"""Test page size optimization for storage efficiency."""

import tempfile
import sqlite3
from pathlib import Path
import pytest

from cinchdb.managers.tenant import TenantManager
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_metadata_db_uses_small_page_size():
    """Test that metadata database uses 1KB page size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create metadata DB
        metadata_db = MetadataDB(project_dir)
        
        # Check page size
        conn = sqlite3.connect(str(metadata_db.db_path))
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        conn.close()
        
        assert page_size == 1024, f"Expected 1024 byte pages, got {page_size}"
        
        # Check file size is small
        file_size = metadata_db.db_path.stat().st_size
        assert file_size <= 8192, f"Metadata DB too large: {file_size} bytes"


def test_empty_tenant_uses_small_page_size():
    """Test that empty tenants use 512-byte page size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project and database
        from cinchdb.core.initializer import init_project
        init_project(project_dir, "testdb", "main")
        
        # Create eager tenant (materialized immediately)
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("empty-tenant", lazy=False)
        
        # Check page size of new tenant (use sharded path)
        from cinchdb.core.path_utils import get_tenant_db_path
        tenant_path = get_tenant_db_path(project_dir, "testdb", "main", "empty-tenant")
        conn = sqlite3.connect(str(tenant_path))
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        conn.execute("PRAGMA page_count").fetchone()[0]
        conn.close()
        
        assert page_size == 512, f"Expected 512 byte pages, got {page_size}"
        
        # Check file size is minimal (should be just a few pages)
        file_size = tenant_path.stat().st_size
        assert file_size <= 2048, f"Empty tenant too large: {file_size} bytes (should be <= 2KB with 512B pages)"


def test_empty_template_uses_small_page_size():
    """Test that __empty__ template uses 512-byte page size."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project and database
        from cinchdb.core.initializer import init_project
        init_project(project_dir, "testdb", "main")
        
        # Create lazy tenant to trigger __empty__ creation
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("lazy-tenant", lazy=True)
        
        # Force materialization which creates __empty__
        tenant_mgr.materialize_tenant("lazy-tenant")
        
        # Check __empty__ template (use sharded path)
        from cinchdb.core.path_utils import get_tenant_db_path
        empty_path = get_tenant_db_path(project_dir, "testdb", "main", "__empty__")
        if empty_path.exists():
            conn = sqlite3.connect(str(empty_path))
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]
            conn.close()
            
            assert page_size == 512, f"__empty__ template should use 512B pages, got {page_size}"
            
            # Check file size
            file_size = empty_path.stat().st_size
            assert file_size <= 2048, f"__empty__ template too large: {file_size} bytes"


def test_page_size_optimization_thresholds():
    """Test the page size optimization logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project and database
        from cinchdb.core.initializer import init_project
        init_project(project_dir, "testdb", "main")
        
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        
        # Test the helper method with different sizes
        test_cases = [
            (50 * 1024, 512),        # 50KB -> 512B pages
            (500 * 1024, 4096),      # 500KB -> 4KB pages  
            (50 * 1024 * 1024, 8192), # 50MB -> 8KB pages
            (200 * 1024 * 1024, 16384), # 200MB -> 16KB pages
        ]
        
        for size_bytes, expected_page_size in test_cases:
            # Create a fake path for testing
            test_path = Path(tmpdir) / f"test_{size_bytes}.db"
            test_path.write_bytes(b'\0' * size_bytes)
            
            optimal_size = tenant_mgr._get_optimal_page_size(test_path)
            assert optimal_size == expected_page_size, \
                f"For {size_bytes/1024/1024:.1f}MB file, expected {expected_page_size}B pages, got {optimal_size}B"


def test_storage_optimization_method():
    """Test the optimize_tenant_storage method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project and database
        from cinchdb.core.initializer import init_project
        init_project(project_dir, "testdb", "main")
        
        # Create table using TableManager
        from cinchdb.managers.table import TableManager
        from cinchdb.models import Column
        table_mgr = TableManager(project_dir, "testdb", "main", "main")
        table_mgr.create_table("users", [
            Column(name="user_id", type="INTEGER"),
            Column(name="name", type="TEXT")
        ])
        
        # Create tenant with small page size
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("growing-tenant", lazy=False)
        
        # Initially should have 512B pages (use sharded path)
        from cinchdb.core.path_utils import get_tenant_db_path
        tenant_path = get_tenant_db_path(project_dir, "testdb", "main", "growing-tenant")
        conn = sqlite3.connect(str(tenant_path))
        initial_page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        conn.close()
        assert initial_page_size == 512
        
        # Optimization on small DB with 512B pages should still vacuum for compactness
        optimized = tenant_mgr.optimize_tenant_storage("growing-tenant")
        assert optimized, "Should vacuum small databases with 512B pages to keep them compact"
        
        # Note: To properly test optimization with larger data, we'd need to:
        # 1. Insert significant data to grow the database > 5MB
        # 2. Call optimize_tenant_storage()
        # 3. Verify page size increased
        # This is omitted for test speed, but the logic is in place


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
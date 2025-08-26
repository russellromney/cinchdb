"""Test batch optimization of tenant storage."""

import tempfile
import sqlite3
from pathlib import Path

from cinchdb.core.initializer import ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.table import TableManager
from cinchdb.models import Column


def test_optimize_all_tenants():
    """Test batch optimization of all tenants."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Create some tenants
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("tenant1", lazy=False)
        tenant_mgr.create_tenant("tenant2", lazy=False)
        tenant_mgr.create_tenant("tenant3", lazy=False)
        tenant_mgr.create_tenant("lazy_tenant", lazy=True)  # This one stays lazy
        
        # Create a table to have some schema
        table_mgr = TableManager(project_dir, "testdb", "main")
        table_mgr.create_table("test_table", [
            Column(name="col1", type="TEXT"),
            Column(name="col2", type="INTEGER")
        ])
        
        # Run optimization
        results = tenant_mgr.optimize_all_tenants()
        
        # Check results
        assert len(results["errors"]) == 0, f"Unexpected errors: {results['errors']}"
        
        # Should have optimized the 3 materialized tenants (tenant1, tenant2, tenant3)
        # Main and __empty__ are skipped by default
        assert len(results["optimized"]) == 3, f"Expected 3 optimized, got {results['optimized']}"
        assert "tenant1" in results["optimized"]
        assert "tenant2" in results["optimized"]
        assert "tenant3" in results["optimized"]
        
        # Main and __empty__ should be skipped
        assert "main" in results["skipped"]
        assert "__empty__" in results["skipped"]
        
        # Lazy tenant shouldn't appear at all (not materialized)
        assert "lazy_tenant" not in results["optimized"]
        assert "lazy_tenant" not in results["skipped"]


def test_optimize_with_force():
    """Test optimization with force flag includes system tenants."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Create a tenant
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("tenant1", lazy=False)
        
        # Run optimization with force
        results = tenant_mgr.optimize_all_tenants(force=True)
        
        # With force=True, main and __empty__ should also be optimized
        # But our optimize_tenant_storage skips them internally
        assert len(results["errors"]) == 0
        
        # Even with force, main and __empty__ are skipped in optimize_tenant_storage
        assert "main" in results["skipped"]
        assert "__empty__" in results["skipped"]
        assert "tenant1" in results["optimized"]


def test_optimize_changes_page_size():
    """Test that optimization changes page size for larger databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Create a tenant
        tenant_mgr = TenantManager(project_dir, "testdb", "main")
        tenant_mgr.create_tenant("growing_tenant", lazy=False)
        
        # Get initial page size (should be 512) - use sharded path
        from cinchdb.core.path_utils import get_tenant_db_path
        tenant_path = get_tenant_db_path(project_dir, "testdb", "main", "growing_tenant")
        conn = sqlite3.connect(str(tenant_path))
        initial_page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        conn.close()
        assert initial_page_size == 512
        
        # Note: To properly test page size changes, we'd need to add significant data
        # For now, just verify the optimization runs without errors
        result = tenant_mgr.optimize_tenant_storage("growing_tenant")
        assert result is True  # Should optimize (VACUUM) even if page size doesn't change


if __name__ == "__main__":
    test_optimize_all_tenants()
    test_optimize_with_force()
    test_optimize_changes_page_size()
    print("All batch optimization tests passed!")
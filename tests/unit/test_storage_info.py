"""Test storage information methods."""

import tempfile
from pathlib import Path

from cinchdb.core.database import CinchDB
from cinchdb.core.initializer import ProjectInitializer


def test_get_tenant_size():
    """Test getting size information for a single tenant."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create a table to materialize the main tenant
        from cinchdb.models import Column
        db.create_table("users", [
            Column(name="user_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT", nullable=False)
        ])
        
        # Get size of main tenant (should now be materialized)
        size = db.get_tenant_size("main")
        
        assert size["name"] == "main"
        assert size["size_bytes"] > 0
        assert size["size_kb"] > 0
        assert size["page_size"] == 4096  # Main uses default page size
        assert size["page_count"] >= 1
        
        # Create a lazy tenant
        db.create_tenant("lazy_tenant", lazy=True)
        
        # Get size of lazy tenant
        lazy_size = db.get_tenant_size("lazy_tenant")
        
        assert lazy_size["name"] == "lazy_tenant"
        assert lazy_size["size_bytes"] == 0
        assert lazy_size["size_kb"] == 0
        assert lazy_size["page_size"] is None
        
        # Create an eager tenant
        db.create_tenant("eager_tenant", lazy=False)
        
        # Get size of eager tenant
        eager_size = db.get_tenant_size("eager_tenant")
        
        assert eager_size["name"] == "eager_tenant"
        assert eager_size["size_bytes"] <= 20480  # Should be reasonably small with 4KB pages
        assert eager_size["page_size"] == 4096  # Should use 4KB pages (SQLite default)
        assert eager_size["page_count"] >= 1  # At least 1 page, possibly more for schema


def test_get_storage_info():
    """Test getting storage information for all tenants."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create some tenants
        db.create_tenant("tenant1", lazy=False)
        db.create_tenant("tenant2", lazy=False)
        db.create_tenant("lazy1", lazy=True)
        db.create_tenant("lazy2", lazy=True)
        
        # Get storage info
        info = db.get_storage_info()
        
        # Check counts
        assert info["tenant_count"] == 6  # main, __empty__, tenant1, tenant2, lazy1, lazy2
        
        # Check total size
        assert info["total_size_bytes"] > 0
        assert info["total_size_mb"] > 0
        
        # Check tenant list
        assert len(info["tenants"]) == 6  # All tenants including main and __empty__
        
        # Verify sorting (largest first)
        sizes = [t["size_bytes"] for t in info["tenants"]]
        assert sizes == sorted(sizes, reverse=True)
        
        # Find specific tenants
        tenant_names = [t["name"] for t in info["tenants"]]
        assert "main" in tenant_names
        assert "tenant1" in tenant_names
        assert "lazy1" in tenant_names
        
        # Check that lazy tenants have 0 size (but we can't tell which ones are lazy from the API)
        # Some tenants should have 0 size (the lazy ones)
        zero_size_tenants = [t for t in info["tenants"] if t["size_bytes"] == 0]
        non_zero_size_tenants = [t for t in info["tenants"] if t["size_bytes"] > 0]

        assert len(zero_size_tenants) == 2  # lazy1, lazy2
        assert len(non_zero_size_tenants) == 4  # main, __empty__, tenant1, tenant2


def test_default_tenant_size():
    """Test getting size of current tenant without specifying name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database (default tenant is "main")
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create a table to materialize the main tenant
        from cinchdb.models import Column
        db.create_table("test_table", [
            Column(name="value", type="TEXT", nullable=False)
        ])
        
        # Get size without specifying tenant name
        size = db.get_tenant_size()
        
        # Should return info for current tenant (main)
        assert size["name"] == "main"
        assert size["size_bytes"] > 0
        
        # Create another tenant and check its size directly
        db.create_tenant("other", lazy=False)
        
        # Get size of specific tenant
        size = db.get_tenant_size("other")
        
        # Should return info for "other"
        assert size["name"] == "other"
        assert size["page_size"] == 4096  # Default size


if __name__ == "__main__":
    test_get_tenant_size()
    test_get_storage_info()
    test_default_tenant_size()
    print("All storage info tests passed!")
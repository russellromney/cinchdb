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
        db.tables.create_table("users", [
            Column(name="user_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT", nullable=False)
        ])
        
        # Get size of main tenant (should now be materialized)
        size = db.get_tenant_size("main")
        
        assert size["name"] == "main"
        assert size["materialized"]  # Check truthiness, not identity
        assert size["size_bytes"] > 0
        assert size["size_kb"] > 0
        assert size["page_size"] == 4096  # Main uses default page size
        assert size["page_count"] >= 1
        
        # Create a lazy tenant
        db.tenants.create_tenant("lazy_tenant", lazy=True)
        
        # Get size of lazy tenant
        lazy_size = db.get_tenant_size("lazy_tenant")
        
        assert lazy_size["name"] == "lazy_tenant"
        assert not lazy_size["materialized"]
        assert lazy_size["size_bytes"] == 0
        assert lazy_size["size_kb"] == 0
        assert lazy_size["page_size"] is None
        
        # Create an eager tenant
        db.tenants.create_tenant("eager_tenant", lazy=False)
        
        # Get size of eager tenant
        eager_size = db.get_tenant_size("eager_tenant")
        
        assert eager_size["name"] == "eager_tenant"
        assert eager_size["materialized"]
        assert eager_size["size_bytes"] <= 4096  # Should be small with 512-byte page optimization  
        assert eager_size["page_size"] == 512  # Should use 512-byte pages
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
        db.tenants.create_tenant("tenant1", lazy=False)
        db.tenants.create_tenant("tenant2", lazy=False)
        db.tenants.create_tenant("lazy1", lazy=True)
        db.tenants.create_tenant("lazy2", lazy=True)
        
        # Get storage info
        info = db.get_storage_info()
        
        # Check counts
        assert info["materialized_count"] == 4  # main, __empty__, tenant1, tenant2
        assert info["lazy_count"] == 2  # lazy1, lazy2
        
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
        
        # Check materialized vs lazy
        materialized_tenants = [t for t in info["tenants"] if t["materialized"]]
        lazy_tenants = [t for t in info["tenants"] if not t["materialized"]]
        
        assert len(materialized_tenants) == 4
        assert len(lazy_tenants) == 2
        
        # All lazy tenants should have 0 size
        for tenant in lazy_tenants:
            assert tenant["size_bytes"] == 0


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
        db.tables.create_table("test_table", [
            Column(name="value", type="TEXT", nullable=False)
        ])
        
        # Get size without specifying tenant name
        size = db.get_tenant_size()
        
        # Should return info for current tenant (main)
        assert size["name"] == "main"
        assert size["materialized"]  # Check truthiness, not identity
        assert size["size_bytes"] > 0
        
        # Create another tenant and check its size directly
        db.tenants.create_tenant("other", lazy=False)
        
        # Get size of specific tenant
        size = db.get_tenant_size("other")
        
        # Should return info for "other"
        assert size["name"] == "other"
        assert size["page_size"] == 512  # Optimized size


if __name__ == "__main__":
    test_get_tenant_size()
    test_get_storage_info()
    test_default_tenant_size()
    print("All storage info tests passed!")
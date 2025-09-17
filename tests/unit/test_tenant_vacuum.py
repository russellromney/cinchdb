"""Tests for tenant vacuum functionality."""

import tempfile
from pathlib import Path
import pytest

from cinchdb.core.database import CinchDB
from cinchdb.models import Column
from cinchdb.core.initializer import ProjectInitializer


def test_vacuum_tenant():
    """Test vacuum operation on a materialized tenant."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table and add data to materialize main tenant
        db.create_table("test_data", [
            Column(name="item_id", type="INTEGER", unique=True),
            Column(name="data", type="TEXT")
        ])
        
        # Add some data
        for i in range(100):
            db.insert("test_data", {"item_id": i, "data": f"test data {i}"})
        
        # Delete half the data to create space that can be reclaimed
        # Delete even-numbered items (item_id 0, 2, 4, 6, ...)
        even_items = [i for i in range(0, 100, 2)]
        db.delete_where("test_data", item_id__in=even_items)
        
        # Get size before vacuum (not used but confirms tenant is materialized)
        db.get_tenant_size("main")
        
        # Run vacuum
        result = db.vacuum_tenant("main")
        
        # Check vacuum results
        assert result["success"] is True
        assert result["tenant"] == "main"
        assert result["size_before"] > 0
        assert result["size_after"] >= 0
        assert result["space_reclaimed"] >= 0
        assert result["duration_seconds"] >= 0
        assert "space_reclaimed_mb" in result
        
        # Verify the database is still functional after vacuum
        remaining_data = db.query("SELECT COUNT(*) as count FROM test_data")
        assert remaining_data[0]["count"] == 50  # Half the data should remain


def test_vacuum_tenant_specific():
    """Test vacuum operation on a specific tenant."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("users", [
            Column(name="user_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT")
        ])
        
        # Create a tenant
        db.create_tenant("customer_a", lazy=False)
        
        # Switch to the new tenant and add data
        db_tenant = CinchDB("testdb", tenant="customer_a", project_dir=project_dir)
        
        # Add and then delete data
        for i in range(50):
            db_tenant.insert("users", {"user_id": i, "name": f"user{i}"})
        
        db_tenant.delete_where("users", user_id__gt=25)
        
        # Vacuum the specific tenant
        result = db.vacuum_tenant("customer_a")
        
        # Check results
        assert result["success"] is True
        assert result["tenant"] == "customer_a"
        assert result["size_before"] > 0
        assert result["duration_seconds"] >= 0


def test_vacuum_lazy_tenant_returns_zeros():
    """Test that vacuuming a lazy tenant returns zero values instead of failing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")

        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)

        # Create a lazy tenant
        db.create_tenant("lazy_tenant", lazy=True)

        # Vacuum the lazy tenant - should return zero values
        result = db.vacuum_tenant("lazy_tenant")

        # Verify result has zero values but success=True
        assert result["success"] is True
        assert result["tenant"] == "lazy_tenant"
        assert result["size_before"] == 0
        assert result["size_after"] == 0
        assert result["space_reclaimed"] == 0
        assert result["space_reclaimed_mb"] == 0.0
        assert result["duration_seconds"] == 0.0


def test_vacuum_nonexistent_tenant_fails():
    """Test that vacuuming a nonexistent tenant fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Try to vacuum nonexistent tenant
        with pytest.raises(ValueError, match="does not exist"):
            db.vacuum_tenant("nonexistent")


def test_vacuum_current_tenant():
    """Test vacuum without specifying tenant name (uses current tenant)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table and add data
        db.create_table("items", [
            Column(name="item_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT")
        ])
        
        db.insert("items", {"item_id": 1, "name": "item1"})
        db.delete_where("items", item_id__gt=0)  # Delete all items to create reclaimable space
        
        # Vacuum current tenant (should default to "main")
        result = db.vacuum_tenant()
        
        assert result["success"] is True
        assert result["tenant"] == "main"


def test_vacuum_with_no_space_to_reclaim():
    """Test vacuum on a fresh database with no space to reclaim."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create minimal table but don't add/delete data
        db.create_table("simple", [
            Column(name="simple_id", type="INTEGER", unique=True)
        ])
        
        # Vacuum should succeed but reclaim little to no space
        result = db.vacuum_tenant("main")
        
        assert result["success"] is True
        assert result["tenant"] == "main"
        assert result["space_reclaimed"] >= 0
        # Space reclaimed might be 0 for a clean database
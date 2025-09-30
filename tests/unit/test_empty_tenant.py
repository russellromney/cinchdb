"""Tests for __empty__ tenant functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.tenant import TenantManager
from cinchdb.models import Column
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.database import CinchDB


class TestEmptyTenant:
    """Test __empty__ tenant behavior for lazy tenants."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def db(self, temp_project):
        """Create CinchDB instance."""
        return CinchDB(database="main", project_dir=temp_project)

    @pytest.fixture
    def tenant_mgr(self, temp_project):
        """Create tenant manager only for operations."""
        return TenantManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

    def test_empty_tenant_not_listed(self, db):
        """Test that __empty__ tenant is not shown in listings."""
        tenants = db.list_tenants()
        tenant_names = [t.name for t in tenants]
        assert "__empty__" not in tenant_names
        assert "main" in tenant_names

    def test_cannot_create_reserved_tenant_name(self, db):
        """Test that __empty__ name cannot be used for tenant creation."""
        with pytest.raises(ValueError, match="reserved tenant name"):
            db.create_tenant("__empty__")

    def test_cannot_delete_reserved_tenant(self, db, tenant_mgr):
        """Test that __empty__ tenant cannot be deleted."""
        # First ensure __empty__ exists by creating a lazy tenant and reading from it
        db.create_tenant("lazy-test", lazy=True)
        tenant_mgr._ensure_empty_tenant()

        with pytest.raises(ValueError, match="Cannot delete the reserved"):
            db.delete_tenant("__empty__")

    def test_empty_tenant_created_with_project(self, db, temp_project, tenant_mgr):
        """Test that __empty__ tenant is created when project is initialized."""
        # __empty__ should exist after project initialization
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        assert empty_db_path.exists()

        # Create a lazy tenant
        db.create_tenant("lazy-tenant", lazy=True)

        # __empty__ should still exist
        assert empty_db_path.exists()

        # Read operations on lazy tenant should use __empty__
        db_path = tenant_mgr.get_tenant_db_path_for_operation(
            "lazy-tenant", is_write=False
        )

        # Read operations on lazy tenant should use __empty__
        assert db_path == empty_db_path

    def test_lazy_tenant_materialized_on_write(self, db, temp_project, tenant_mgr):
        """Test that lazy tenant is materialized on first write."""
        # Create table in main first using CinchDB
        db.create_table("test_table", [
            Column(name="value", type="TEXT")
        ])

        # Create a lazy tenant
        db.create_tenant("write-test", lazy=True)

        # Verify it's lazy (no database file)
        tenant_db_path = get_tenant_db_path(temp_project, "main", "main", "write-test")
        assert not tenant_db_path.exists()
        assert tenant_mgr.is_tenant_lazy("write-test")

        # Perform a write operation using proper Database API
        db_write = CinchDB(database="main", project_dir=temp_project, tenant="write-test")
        db_write.insert("test_table", {"id": "1", "value": "test"})

        # Now tenant should be materialized
        assert tenant_db_path.exists()
        assert not tenant_mgr.is_tenant_lazy("write-test")

        # Verify data was written to the actual tenant
        db_verify = CinchDB(database="main", project_dir=temp_project, tenant="write-test")
        results = db_verify.query("SELECT * FROM test_table WHERE id = '1'")
        assert len(results) == 1
        assert results[0]["value"] == "test"

    def test_empty_tenant_has_schema_but_no_data(self, db, temp_project, tenant_mgr):
        """Test that __empty__ tenant has schema but no data."""
        # Create tables with data in main using CinchDB
        db.create_table("users", [
            Column(name="name", type="TEXT")
        ])
        db.create_table("posts", [
            Column(name="title", type="TEXT"),
            Column(name="user_id", type="TEXT")
        ])

        # Add some data to main
        db.insert("users", {"id": "u1", "name": "Alice"})
        db.insert("posts", {"id": "p1", "title": "First Post", "user_id": "u1"})

        # Ensure __empty__ tenant exists
        tenant_mgr._ensure_empty_tenant()
        
        # Check __empty__ has schema but no data
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        with DatabaseConnection(empty_db_path) as conn:
            # Check tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'posts')"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            assert "users" in tables
            assert "posts" in tables
            
            # Check no data exists
            cursor = conn.execute("SELECT COUNT(*) as count FROM users")
            assert cursor.fetchone()["count"] == 0
            
            cursor = conn.execute("SELECT COUNT(*) as count FROM posts")
            assert cursor.fetchone()["count"] == 0

    def test_empty_tenant_updated_after_schema_change(self, db, temp_project, tenant_mgr):
        """Test that __empty__ tenant is updated when schema changes."""
        # Create initial table using CinchDB
        db.create_table("initial_table", [])

        # Create a lazy tenant to ensure __empty__ exists
        db.create_tenant("lazy", lazy=True)
        tenant_mgr._ensure_empty_tenant()

        # Check __empty__ has the initial table
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        with DatabaseConnection(empty_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='initial_table'"
            )
            assert cursor.fetchone() is not None

        # Add another table using CinchDB
        db.create_table("new_table", [
            Column(name="data", type="TEXT")
        ])
        
        # __empty__ should have been updated and should have both tables
        with DatabaseConnection(empty_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('initial_table', 'new_table')"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            assert "initial_table" in tables
            assert "new_table" in tables

    def test_multiple_lazy_tenants_share_empty_for_reads(self, db, temp_project, tenant_mgr):
        """Test that multiple lazy tenants all use __empty__ for reads."""
        # Create table first using CinchDB
        db.create_table("shared_table", [
            Column(name="value", type="TEXT")
        ])

        # Create multiple lazy tenants
        for i in range(3):
            db.create_tenant(f"lazy-{i}", lazy=True)

        # All should use __empty__ for reads
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")

        for i in range(3):
            db_path = tenant_mgr.get_tenant_db_path_for_operation(
                f"lazy-{i}", is_write=False
            )
            assert db_path == empty_db_path

            # Verify we can read the schema using CinchDB
            db_lazy = CinchDB(database="main", project_dir=temp_project, tenant=f"lazy-{i}")
            results = db_lazy.query("SELECT * FROM shared_table")
            assert results == []  # No data, but query succeeds

    def test_lazy_tenant_isolation_after_materialization(self, db, temp_project):
        """Test that materialized tenants are isolated from each other."""
        # Create table using CinchDB
        db.create_table("data_table", [
            Column(name="tenant_data", type="TEXT")
        ])

        # Create two lazy tenants
        db.create_tenant("tenant-a", lazy=True)
        db.create_tenant("tenant-b", lazy=True)
        
        # Write different data to each (materializing them)
        # Insert data using proper Database API
        db_a = CinchDB(database="main", project_dir=temp_project, tenant="tenant-a")
        db_a.insert("data_table", {"id": "1", "tenant_data": "Data for A"})

        db_b = CinchDB(database="main", project_dir=temp_project, tenant="tenant-b")
        db_b.insert("data_table", {"id": "1", "tenant_data": "Data for B"})
        
        # Verify isolation - each has its own data
        results_a = db_a.query("SELECT * FROM data_table WHERE id = '1'")
        assert len(results_a) == 1
        assert results_a[0]["tenant_data"] == "Data for A"

        results_b = db_b.query("SELECT * FROM data_table WHERE id = '1'")
        assert len(results_b) == 1
        assert results_b[0]["tenant_data"] == "Data for B"

    def test_copy_on_write_semantics(self, db, temp_project, tenant_mgr):
        """Test copy-on-write behavior for lazy tenants."""
        # Create a table with an index and view using CinchDB
        db.create_table("products", [
            Column(name="name", type="TEXT"),
            Column(name="price", type="REAL")
        ])

        # Create index (correct parameter order: table, columns, name)
        db.create_index("products", ["price"], name="idx_price")

        # Create view
        db.create_view("expensive_products", "SELECT * FROM products WHERE price > 100")

        # Create lazy tenant
        db.create_tenant("cow-tenant", lazy=True)

        # Read operation - should use __empty__
        db_cow_read = CinchDB(database="main", project_dir=temp_project, tenant="cow-tenant")
        results = db_cow_read.query("SELECT * FROM expensive_products")
        assert results == []  # No data but view works

        # Tenant should still be lazy
        assert tenant_mgr.is_tenant_lazy("cow-tenant")
        
        # Write operation - should trigger materialization
        db_cow = CinchDB(database="main", project_dir=temp_project, tenant="cow-tenant")
        db_cow.insert("products", {"id": "p1", "name": "Luxury Item", "price": 500})

        # Tenant should now be materialized
        assert not tenant_mgr.is_tenant_lazy("cow-tenant")
        
        # Verify schema objects were copied and data was inserted
        tenant_db_path = get_tenant_db_path(temp_project, "main", "main", "cow-tenant")
        with DatabaseConnection(tenant_db_path) as conn:
            # Check table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
            )
            assert cursor.fetchone() is not None

            # Check data exists
            cursor = conn.execute("SELECT * FROM products WHERE id = 'p1'")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0]["name"] == "Luxury Item"
            assert rows[0]["price"] == 500
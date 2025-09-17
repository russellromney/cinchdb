"""Tests for __empty__ tenant functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.managers.query import QueryManager
from cinchdb.models import Change, ChangeType
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
    def managers(self, temp_project):
        """Create manager instances."""
        tenant_mgr = TenantManager(temp_project, "main", "main")
        change_tracker = ChangeTracker(temp_project, "main", "main")
        change_applier = ChangeApplier(temp_project, "main", "main")
        query_mgr = QueryManager(temp_project, "main", "main", "main")

        return {
            "tenant": tenant_mgr,
            "tracker": change_tracker,
            "applier": change_applier,
            "query": query_mgr,
        }

    def test_empty_tenant_not_listed(self, managers):
        """Test that __empty__ tenant is not shown in listings."""
        tenants = managers["tenant"].list_tenants()
        tenant_names = [t.name for t in tenants]
        assert "__empty__" not in tenant_names
        assert "main" in tenant_names

    def test_cannot_create_reserved_tenant_name(self, managers):
        """Test that __empty__ name cannot be used for tenant creation."""
        with pytest.raises(ValueError, match="reserved tenant name"):
            managers["tenant"].create_tenant("__empty__")

    def test_cannot_delete_reserved_tenant(self, managers):
        """Test that __empty__ tenant cannot be deleted."""
        # First ensure __empty__ exists by creating a lazy tenant and reading from it
        managers["tenant"].create_tenant("lazy-test", lazy=True)
        managers["tenant"]._ensure_empty_tenant()
        
        with pytest.raises(ValueError, match="Cannot delete the reserved"):
            managers["tenant"].delete_tenant("__empty__")

    def test_empty_tenant_created_with_project(self, managers, temp_project):
        """Test that __empty__ tenant is created when project is initialized."""
        # __empty__ should exist after project initialization
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        assert empty_db_path.exists()
        
        # Create a lazy tenant
        managers["tenant"].create_tenant("lazy-tenant", lazy=True)
        
        # __empty__ should still exist
        assert empty_db_path.exists()
        
        # Now perform a read operation on the lazy tenant
        query_mgr = QueryManager(temp_project, "main", "main", "lazy-tenant")
        db_path = query_mgr.tenant_manager.get_tenant_db_path_for_operation(
            "lazy-tenant", is_write=False
        )
        
        # Read operations on lazy tenant should use __empty__ 
        assert db_path == empty_db_path

    def test_lazy_tenant_materialized_on_write(self, managers, temp_project):
        """Test that lazy tenant is materialized on first write."""
        # Create table in main first
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="test_table",
            branch="main",
            sql="CREATE TABLE test_table (id TEXT PRIMARY KEY, value TEXT, created_at DATETIME, updated_at DATETIME)",
        )
        added = managers["tracker"].add_change(change)
        managers["applier"].apply_change(added.id)
        
        # Create a lazy tenant
        managers["tenant"].create_tenant("write-test", lazy=True)
        
        # Verify it's lazy (no database file)
        tenant_db_path = get_tenant_db_path(temp_project, "main", "main", "write-test")
        assert not tenant_db_path.exists()
        assert managers["tenant"].is_tenant_lazy("write-test")
        
        # Perform a write operation using proper Database API
        db = CinchDB(database="main", project_dir=temp_project, tenant="write-test")
        db.insert("test_table", {"id": "1", "value": "test"})
        
        # Now tenant should be materialized
        assert tenant_db_path.exists()
        assert not managers["tenant"].is_tenant_lazy("write-test")
        
        # Verify data was written to the actual tenant
        # Use CinchDB convenience function for verification
        db_verify = CinchDB(database="main", project_dir=temp_project, tenant="write-test")
        results = db_verify.query("SELECT * FROM test_table WHERE id = '1'")
        assert len(results) == 1
        assert results[0]["value"] == "test"

    def test_empty_tenant_has_schema_but_no_data(self, managers, temp_project):
        """Test that __empty__ tenant has schema but no data."""
        # Create tables with data in main
        changes = [
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="users",
                branch="main",
                sql="CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT, created_at DATETIME, updated_at DATETIME)",
            ),
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="posts",
                branch="main",
                sql="CREATE TABLE posts (id TEXT PRIMARY KEY, title TEXT, user_id TEXT, created_at DATETIME, updated_at DATETIME)",
            ),
        ]
        
        for change in changes:
            added = managers["tracker"].add_change(change)
            managers["applier"].apply_change(added.id)
        
        # Add some data to main using CinchDB convenience functions
        main_db = CinchDB(database="main", project_dir=temp_project, tenant="main")
        main_db.insert("users", {"id": "u1", "name": "Alice"})
        main_db.insert("posts", {"id": "p1", "title": "First Post", "user_id": "u1"})
        
        # Ensure __empty__ tenant exists
        managers["tenant"]._ensure_empty_tenant()
        
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

    def test_empty_tenant_updated_after_schema_change(self, managers, temp_project):
        """Test that __empty__ tenant is updated when schema changes."""
        # Create initial table
        change1 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="initial_table",
            branch="main",
            sql="CREATE TABLE initial_table (id TEXT PRIMARY KEY)",
        )
        added1 = managers["tracker"].add_change(change1)
        managers["applier"].apply_change(added1.id)
        
        # Create a lazy tenant to ensure __empty__ exists
        managers["tenant"].create_tenant("lazy", lazy=True)
        managers["tenant"]._ensure_empty_tenant()
        
        # Check __empty__ has the initial table
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        with DatabaseConnection(empty_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='initial_table'"
            )
            assert cursor.fetchone() is not None
        
        # Add another table
        change2 = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="new_table",
            branch="main",
            sql="CREATE TABLE new_table (id TEXT PRIMARY KEY, data TEXT)",
        )
        added2 = managers["tracker"].add_change(change2)
        managers["applier"].apply_change(added2.id)
        
        # __empty__ should have been updated and should have both tables
        with DatabaseConnection(empty_db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name IN ('initial_table', 'new_table')"
            )
            tables = [row["name"] for row in cursor.fetchall()]
            assert "initial_table" in tables
            assert "new_table" in tables

    def test_multiple_lazy_tenants_share_empty_for_reads(self, managers, temp_project):
        """Test that multiple lazy tenants all use __empty__ for reads."""
        # Create table first
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="shared_table",
            branch="main",
            sql="CREATE TABLE shared_table (id TEXT PRIMARY KEY, value TEXT)",
        )
        added = managers["tracker"].add_change(change)
        managers["applier"].apply_change(added.id)
        
        # Create multiple lazy tenants
        for i in range(3):
            managers["tenant"].create_tenant(f"lazy-{i}", lazy=True)
        
        # All should use __empty__ for reads
        empty_db_path = get_tenant_db_path(temp_project, "main", "main", "__empty__")
        
        for i in range(3):
            query_mgr = QueryManager(temp_project, "main", "main", f"lazy-{i}")
            db_path = query_mgr.tenant_manager.get_tenant_db_path_for_operation(
                f"lazy-{i}", is_write=False
            )
            assert db_path == empty_db_path
            
            # Verify we can read the schema using CinchDB
            db_lazy = CinchDB(database="main", project_dir=temp_project, tenant=f"lazy-{i}")
            results = db_lazy.query("SELECT * FROM shared_table")
            assert results == []  # No data, but query succeeds

    def test_lazy_tenant_isolation_after_materialization(self, managers, temp_project):
        """Test that materialized tenants are isolated from each other."""
        # Create table
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name="data_table",
            branch="main",
            sql="CREATE TABLE data_table (id TEXT PRIMARY KEY, tenant_data TEXT, created_at DATETIME, updated_at DATETIME)",
        )
        added = managers["tracker"].add_change(change)
        managers["applier"].apply_change(added.id)
        
        # Create two lazy tenants
        managers["tenant"].create_tenant("tenant-a", lazy=True)
        managers["tenant"].create_tenant("tenant-b", lazy=True)
        
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

    def test_copy_on_write_semantics(self, managers, temp_project):
        """Test copy-on-write behavior for lazy tenants."""
        # Create a table with an index and view
        changes = [
            Change(
                type=ChangeType.CREATE_TABLE,
                entity_type="table",
                entity_name="products",
                branch="main",
                sql="CREATE TABLE products (id TEXT PRIMARY KEY, name TEXT, price REAL, created_at DATETIME, updated_at DATETIME)",
            ),
            Change(
                type=ChangeType.CREATE_INDEX,
                entity_type="index",
                entity_name="idx_price",
                branch="main",
                sql="CREATE INDEX idx_price ON products(price)",
            ),
            Change(
                type=ChangeType.CREATE_VIEW,
                entity_type="view",
                entity_name="expensive_products",
                branch="main",
                sql="CREATE VIEW expensive_products AS SELECT * FROM products WHERE price > 100",
            ),
        ]
        
        for change in changes:
            added = managers["tracker"].add_change(change)
            managers["applier"].apply_change(added.id)
        
        # Create lazy tenant
        managers["tenant"].create_tenant("cow-tenant", lazy=True)
        
        # Read operation - should use __empty__
        db_cow_read = CinchDB(database="main", project_dir=temp_project, tenant="cow-tenant")
        results = db_cow_read.query("SELECT * FROM expensive_products")
        assert results == []  # No data but view works
        
        # Tenant should still be lazy
        assert managers["tenant"].is_tenant_lazy("cow-tenant")
        
        # Write operation - should trigger materialization
        db_cow = CinchDB(database="main", project_dir=temp_project, tenant="cow-tenant")
        db_cow.insert("products", {"id": "p1", "name": "Luxury Item", "price": 500})
        
        # Tenant should now be materialized
        assert not managers["tenant"].is_tenant_lazy("cow-tenant")
        
        # Verify all schema objects were copied
        tenant_db_path = get_tenant_db_path(temp_project, "main", "main", "cow-tenant")
        with DatabaseConnection(tenant_db_path) as conn:
            # Check table
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
            )
            assert cursor.fetchone() is not None
            
            # Check index
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_price'"
            )
            assert cursor.fetchone() is not None
            
            # Check view
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='expensive_products'"
            )
            assert cursor.fetchone() is not None
            
            # Check data exists
            cursor = conn.execute("SELECT * FROM expensive_products")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0]["name"] == "Luxury Item"
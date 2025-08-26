"""Tests for __empty__ tenant schema updates."""

import pytest
import tempfile
import uuid
from pathlib import Path
from cinchdb.core.initializer import ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.column import ColumnManager
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.models import Column, Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


@pytest.fixture
def test_project():
    """Create a test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        initializer = ProjectInitializer(project_root)
        initializer.init_project("testdb", "main")
        yield project_root


class TestEmptyTenantSchema:
    """Test that __empty__ tenant receives schema updates."""
    
    def test_empty_tenant_created_with_schema(self, test_project):
        """Test that __empty__ tenant gets created with proper schema."""
        tenant_manager = TenantManager(test_project, "testdb", "main")
        
        # Create a table in main tenant
        table_manager = TableManager(test_project, "testdb", "main", "main")
        table_manager.create_table("users", [
            Column(name="name", type="TEXT"),
            Column(name="email", type="TEXT", unique=True)
        ])
        
        # Create a lazy tenant (this will trigger __empty__ creation)
        tenant_manager.create_tenant("tenant1", lazy=True)
        
        # Ensure __empty__ was created
        tenant_manager._ensure_empty_tenant()
        
        # Check that __empty__ exists in metadata
        tenants_with_system = tenant_manager.list_tenants(include_system=True)
        empty_tenants = [t for t in tenants_with_system if t.name == "__empty__"]
        assert len(empty_tenants) == 1
        
        # Check that __empty__ has the schema
        empty_db_path = get_tenant_db_path(test_project, "testdb", "main", "__empty__")
        assert empty_db_path.exists()
        
        with DatabaseConnection(empty_db_path) as conn:
            # Check users table exists
            result = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
            assert result.fetchone() is not None
            
            # Check table has no data
            result = conn.execute("SELECT COUNT(*) as count FROM users")
            assert result.fetchone()["count"] == 0
    
    def test_empty_tenant_gets_schema_updates(self, test_project):
        """Test that __empty__ tenant receives schema updates along with other tenants."""
        tenant_manager = TenantManager(test_project, "testdb", "main")
        table_manager = TableManager(test_project, "testdb", "main", "main")
        column_manager = ColumnManager(test_project, "testdb", "main", "main")
        change_tracker = ChangeTracker(test_project, "testdb", "main")
        change_applier = ChangeApplier(test_project, "testdb", "main")
        
        # Create initial table
        table_manager.create_table("products", [
            Column(name="name", type="TEXT")
        ])
        
        # Create some tenants (one lazy to ensure __empty__ exists)
        tenant_manager.create_tenant("tenant1", lazy=True)
        tenant_manager.create_tenant("tenant2", lazy=False)
        
        # Ensure __empty__ exists
        tenant_manager._ensure_empty_tenant()
        
        # Track a schema change
        change = Change(
            id=str(uuid.uuid4()),
            type=ChangeType.ADD_COLUMN,
            entity_name="products",
            entity_type="column",
            sql="ALTER TABLE products ADD COLUMN price REAL",
            metadata={"column": "price", "type": "REAL"},
            branch="main",
            applied=False
        )
        change_tracker.add_change(change)
        
        # Apply the change
        changes = change_tracker.get_unapplied_changes()
        assert len(changes) == 1
        change_applier.apply_change(changes[0].id)
        
        # Check that __empty__ got the update
        empty_db_path = get_tenant_db_path(test_project, "testdb", "main", "__empty__")
        with DatabaseConnection(empty_db_path) as conn:
            # Check column exists
            result = conn.execute("PRAGMA table_info(products)")
            columns = {row["name"]: row["type"] for row in result.fetchall()}
            assert "price" in columns
            assert columns["price"] == "REAL"
            
            # Verify table still has no data
            result = conn.execute("SELECT COUNT(*) as count FROM products")
            assert result.fetchone()["count"] == 0
        
        # Also verify regular tenants got the update
        tenant2_db_path = get_tenant_db_path(test_project, "testdb", "main", "tenant2")
        with DatabaseConnection(tenant2_db_path) as conn:
            result = conn.execute("PRAGMA table_info(products)")
            columns = {row["name"]: row["type"] for row in result.fetchall()}
            assert "price" in columns
    
    def test_lazy_tenant_uses_updated_empty(self, test_project):
        """Test that new lazy tenants use __empty__ with latest schema."""
        tenant_manager = TenantManager(test_project, "testdb", "main")
        table_manager = TableManager(test_project, "testdb", "main", "main")
        change_tracker = ChangeTracker(test_project, "testdb", "main")
        change_applier = ChangeApplier(test_project, "testdb", "main")
        
        # Create initial table
        table_manager.create_table("items", [
            Column(name="name", type="TEXT")
        ])
        
        # Create a lazy tenant to ensure __empty__ exists
        tenant_manager.create_tenant("tenant1", lazy=True)
        tenant_manager._ensure_empty_tenant()
        
        # Add a column via schema change
        change = Change(
            id=str(uuid.uuid4()),
            type=ChangeType.ADD_COLUMN,
            entity_name="items",
            entity_type="column",
            sql="ALTER TABLE items ADD COLUMN quantity INTEGER DEFAULT 0",
            metadata={"column": "quantity", "type": "INTEGER"},
            branch="main",
            applied=False
        )
        change_tracker.add_change(change)
        
        changes = change_tracker.get_unapplied_changes()
        change_applier.apply_change(changes[0].id)
        
        # Create a new lazy tenant
        tenant_manager.create_tenant("tenant2", lazy=True)
        
        # Read from the lazy tenant (should use __empty__)
        db_path = tenant_manager.get_tenant_db_path_for_operation("tenant2", is_write=False)
        assert "__empty__" in str(db_path)
        
        # Verify the schema has the new column
        with DatabaseConnection(db_path) as conn:
            result = conn.execute("PRAGMA table_info(items)")
            columns = {row["name"]: row["type"] for row in result.fetchall()}
            assert "quantity" in columns
            assert columns["quantity"] == "INTEGER"
    
    def test_empty_tenant_excluded_from_user_listings(self, test_project):
        """Test that __empty__ is excluded from normal tenant listings."""
        tenant_manager = TenantManager(test_project, "testdb", "main")
        
        # Create some tenants
        tenant_manager.create_tenant("tenant1", lazy=True)
        tenant_manager.create_tenant("tenant2", lazy=False)
        
        # Ensure __empty__ exists
        tenant_manager._ensure_empty_tenant()
        
        # Normal listing should not include __empty__
        tenants = tenant_manager.list_tenants()
        tenant_names = [t.name for t in tenants]
        assert "__empty__" not in tenant_names
        assert "main" in tenant_names
        assert "tenant1" in tenant_names
        assert "tenant2" in tenant_names
        
        # System listing should include __empty__
        tenants_with_system = tenant_manager.list_tenants(include_system=True)
        tenant_names_with_system = [t.name for t in tenants_with_system]
        assert "__empty__" in tenant_names_with_system
        assert "main" in tenant_names_with_system
        assert "tenant1" in tenant_names_with_system
        assert "tenant2" in tenant_names_with_system
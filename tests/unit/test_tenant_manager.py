"""Tests for TenantManager."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.managers.tenant import TenantManager
from cinchdb.config import Config
from cinchdb.models import Tenant
from cinchdb.core.connection import DatabaseConnection


class TestTenantManager:
    """Test tenant management functionality."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        
        # Initialize project
        config = Config(project_dir)
        config.init_project()
        
        yield project_dir
        shutil.rmtree(temp)
    
    @pytest.fixture
    def tenant_manager(self, temp_project):
        """Create a TenantManager instance."""
        return TenantManager(temp_project, "main", "main")
    
    def test_list_tenants_initial(self, tenant_manager):
        """Test listing tenants in a new project."""
        tenants = tenant_manager.list_tenants()
        
        assert len(tenants) == 1
        assert tenants[0].name == "main"
        assert tenants[0].is_main
        assert tenants[0].database == "main"
        assert tenants[0].branch == "main"
    
    def test_create_tenant(self, tenant_manager):
        """Test creating a new tenant."""
        # Create a tenant
        new_tenant = tenant_manager.create_tenant("customer1", "Customer 1 data")
        
        assert new_tenant.name == "customer1"
        assert new_tenant.database == "main"
        assert new_tenant.branch == "main"
        assert new_tenant.description == "Customer 1 data"
        assert not new_tenant.is_main
        
        # Verify database file was created
        db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer1.db"
        assert db_path.exists()
        
        # List tenants should now show 2
        tenants = tenant_manager.list_tenants()
        assert len(tenants) == 2
        assert sorted([t.name for t in tenants]) == ["customer1", "main"]
    
    def test_create_tenant_copies_schema(self, tenant_manager):
        """Test that creating a tenant copies schema from main."""
        # Create a table in main tenant first
        main_db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "main.db"
        
        with DatabaseConnection(main_db_path) as conn:
            conn.execute("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.commit()
        
        # Create new tenant
        tenant_manager.create_tenant("customer1")
        
        # Check schema was copied
        customer_db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer1.db"
        
        with DatabaseConnection(customer_db_path) as conn:
            # Query table info
            result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert result.fetchone() is not None
    
    def test_create_tenant_duplicate_fails(self, tenant_manager):
        """Test creating a tenant with duplicate name fails."""
        tenant_manager.create_tenant("customer1")
        
        with pytest.raises(ValueError, match="Tenant 'customer1' already exists"):
            tenant_manager.create_tenant("customer1")
    
    def test_delete_tenant(self, tenant_manager):
        """Test deleting a tenant."""
        # Create a tenant first
        tenant_manager.create_tenant("customer1")
        assert len(tenant_manager.list_tenants()) == 2
        
        # Delete it
        tenant_manager.delete_tenant("customer1")
        
        # Should be gone
        tenants = tenant_manager.list_tenants()
        assert len(tenants) == 1
        assert tenants[0].name == "main"
        
        # Database file should be gone
        db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer1.db"
        assert not db_path.exists()
    
    def test_delete_main_tenant_fails(self, tenant_manager):
        """Test that deleting main tenant fails."""
        with pytest.raises(ValueError, match="Cannot delete the main tenant"):
            tenant_manager.delete_tenant("main")
    
    def test_delete_nonexistent_tenant_fails(self, tenant_manager):
        """Test deleting non-existent tenant fails."""
        with pytest.raises(ValueError, match="Tenant 'nonexistent' does not exist"):
            tenant_manager.delete_tenant("nonexistent")
    
    def test_copy_tenant(self, tenant_manager):
        """Test copying a tenant."""
        # Add some data to main tenant
        main_db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "main.db"
        
        with DatabaseConnection(main_db_path) as conn:
            conn.execute("""
                CREATE TABLE users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """)
            conn.execute("INSERT INTO users (id, name) VALUES ('1', 'Test User')")
            conn.commit()
        
        # Copy main to customer1
        new_tenant = tenant_manager.copy_tenant("main", "customer1")
        
        assert new_tenant.name == "customer1"
        
        # Check data was copied
        customer_db_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer1.db"
        
        with DatabaseConnection(customer_db_path) as conn:
            result = conn.execute("SELECT * FROM users WHERE id = '1'")
            row = result.fetchone()
            assert row["name"] == "Test User"
    
    def test_copy_nonexistent_tenant_fails(self, tenant_manager):
        """Test copying from non-existent tenant fails."""
        with pytest.raises(ValueError, match="Source tenant 'nonexistent' does not exist"):
            tenant_manager.copy_tenant("nonexistent", "customer1")
    
    def test_rename_tenant(self, tenant_manager):
        """Test renaming a tenant."""
        # Create a tenant
        tenant_manager.create_tenant("customer1")
        
        # Rename it
        tenant_manager.rename_tenant("customer1", "customer2")
        
        # Check it was renamed
        tenants = tenant_manager.list_tenants()
        tenant_names = [t.name for t in tenants]
        assert "customer1" not in tenant_names
        assert "customer2" in tenant_names
        
        # Check files were renamed
        old_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer1.db"
        new_path = tenant_manager.project_root / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants" / "customer2.db"
        assert not old_path.exists()
        assert new_path.exists()
    
    def test_rename_main_tenant_fails(self, tenant_manager):
        """Test that renaming main tenant fails."""
        with pytest.raises(ValueError, match="Cannot rename the main tenant"):
            tenant_manager.rename_tenant("main", "something_else")
    
    def test_rename_to_existing_fails(self, tenant_manager):
        """Test renaming to existing tenant name fails."""
        tenant_manager.create_tenant("customer1")
        
        with pytest.raises(ValueError, match="Tenant 'main' already exists"):
            tenant_manager.rename_tenant("customer1", "main")
    
    def test_get_tenant_connection(self, tenant_manager):
        """Test getting a database connection for a tenant."""
        conn = tenant_manager.get_tenant_connection("main")
        
        # Should be able to execute queries
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        
        # Verify table exists
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test'")
        assert result.fetchone() is not None
        
        conn.close()
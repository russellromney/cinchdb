"""Tests for TenantManager with SQLite metadata backend."""

import pytest
import tempfile
import uuid
from pathlib import Path
from cinchdb.managers.tenant import TenantManager
from cinchdb.managers.base import ConnectionContext
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.core.connection import DatabaseConnection


@pytest.fixture
def test_project():
    """Create a test project with database and branch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        
        # Initialize metadata database
        metadata_db = MetadataDB(project_root)
        
        # Create database in metadata
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb", "Test database")
        
        # Create branch in metadata
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, db_id, "main", schema_version="v1.0.0")
        
        # Create physical main tenant (always materialized) in sharded directory
        from cinchdb.core.path_utils import get_tenant_db_path
        main_db = get_tenant_db_path(project_root, "testdb", "main", "main")
        main_db.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a simple schema in main tenant
        with DatabaseConnection(main_db) as conn:
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE
                )
            """)
            conn.execute("""
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    title TEXT,
                    content TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            conn.commit()
        
        # Add main tenant to metadata as materialized
        import hashlib
        main_shard = hashlib.sha256("main".encode('utf-8')).hexdigest()[:2]
        main_tenant_id = str(uuid.uuid4())
        metadata_db.create_tenant(main_tenant_id, branch_id, "main", main_shard)
        metadata_db.mark_tenant_materialized(main_tenant_id)
        
        metadata_db.close()
        
        yield project_root


class TestTenantManagerWithMetadata:
    """Test TenantManager using SQLite metadata backend."""
    
    def test_create_lazy_tenant(self, test_project):
        """Test creating a lazy tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create lazy tenant
        tenant = manager.create_tenant("tenant1", "Test tenant", lazy=True)
        assert tenant.name == "tenant1"
        assert tenant.database == "testdb"
        assert tenant.branch == "main"
        
        # Verify tenant exists in metadata but not on filesystem
        assert manager.is_tenant_lazy("tenant1")
        from cinchdb.core.path_utils import get_tenant_db_path
        db_path = get_tenant_db_path(test_project, "testdb", "main", "tenant1")
        assert not db_path.exists()
        
        # Verify tenant appears in listing
        tenants = manager.list_tenants()
        assert any(t.name == "tenant1" for t in tenants)
        assert any(t.name == "main" for t in tenants)
    
    def test_create_materialized_tenant(self, test_project):
        """Test creating a materialized tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create materialized tenant
        tenant = manager.create_tenant("tenant2", "Test tenant", lazy=False)
        assert tenant.name == "tenant2"
        
        # Verify tenant exists both in metadata and on filesystem
        assert not manager.is_tenant_lazy("tenant2")
        # Use path utils to get correct sharded path with new tenant-first structure
        from cinchdb.core.path_utils import get_tenant_db_path
        db_path = get_tenant_db_path(test_project, "testdb", "main", "tenant2")
        assert db_path.exists()
        
        # Verify schema was copied correctly
        with DatabaseConnection(db_path) as conn:
            result = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('users', 'posts')
                ORDER BY name
            """)
            tables = [row["name"] for row in result.fetchall()]
            assert tables == ["posts", "users"]
    
    def test_materialize_lazy_tenant(self, test_project):
        """Test materializing a lazy tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create lazy tenant
        manager.create_tenant("tenant3", lazy=True)
        assert manager.is_tenant_lazy("tenant3")
        
        # Materialize it
        manager.materialize_tenant("tenant3")
        assert not manager.is_tenant_lazy("tenant3")
        
        # Verify database file was created
        from cinchdb.core.path_utils import get_tenant_db_path
        db_path = get_tenant_db_path(test_project, "testdb", "main", "tenant3")
        assert db_path.exists()
    
    def test_auto_materialize_on_write(self, test_project):
        """Test that lazy tenants auto-materialize on write operations."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create lazy tenant
        manager.create_tenant("tenant4", lazy=True)
        assert manager.is_tenant_lazy("tenant4")
        
        # Get path for write operation (should trigger materialization)
        db_path = manager.get_tenant_db_path_for_operation("tenant4", is_write=True)
        assert db_path.exists()
        assert not manager.is_tenant_lazy("tenant4")
    
    def test_read_lazy_tenant_uses_empty(self, test_project):
        """Test that reading from lazy tenant uses __empty__ tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create lazy tenant
        manager.create_tenant("tenant5", lazy=True)
        assert manager.is_tenant_lazy("tenant5")
        
        # Get path for read operation (should use __empty__)
        db_path = manager.get_tenant_db_path_for_operation("tenant5", is_write=False)
        assert "__empty__" in str(db_path)
        assert db_path.exists()
        
        # Tenant should still be lazy
        assert manager.is_tenant_lazy("tenant5")
    
    def test_delete_lazy_tenant(self, test_project):
        """Test deleting a lazy tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create and delete lazy tenant
        manager.create_tenant("tenant6", lazy=True)
        manager.delete_tenant("tenant6")
        
        # Verify it's gone from metadata
        tenants = manager.list_tenants()
        assert not any(t.name == "tenant6" for t in tenants)
    
    def test_delete_materialized_tenant(self, test_project):
        """Test deleting a materialized tenant."""
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create materialized tenant
        manager.create_tenant("tenant7", lazy=False)
        from cinchdb.core.path_utils import get_tenant_db_path
        db_path = get_tenant_db_path(test_project, "testdb", "main", "tenant7")
        assert db_path.exists()
        
        # Delete it
        manager.delete_tenant("tenant7")
        
        # Verify it's gone from both metadata and filesystem
        tenants = manager.list_tenants()
        assert not any(t.name == "tenant7" for t in tenants)
        assert not db_path.exists()
    
    def test_performance_with_many_lazy_tenants(self, test_project):
        """Test performance with many lazy tenants."""
        import time
        manager = TenantManager(ConnectionContext(project_root=test_project, database="testdb", branch="main"))
        
        # Create many lazy tenants
        n_tenants = 1000
        start = time.time()
        
        for i in range(n_tenants):
            manager.create_tenant(f"lazy_tenant_{i}", lazy=True)
        
        create_time = time.time() - start
        print(f"\nCreated {n_tenants} lazy tenants in {create_time:.2f}s")
        assert create_time < 10.0  # Should be fast
        
        # Test listing performance
        start = time.time()
        tenants = manager.list_tenants()
        list_time = time.time() - start
        print(f"Listed {len(tenants)} tenants in {list_time:.2f}s")
        assert len(tenants) == n_tenants + 1  # +1 for main tenant
        assert list_time < 1.0
        
        # Test existence check performance
        start = time.time()
        is_lazy = manager.is_tenant_lazy("lazy_tenant_500")
        check_time = time.time() - start
        print(f"Checked tenant laziness in {check_time*1000:.2f}ms")
        assert is_lazy
        assert check_time < 0.01  # Should be < 10ms
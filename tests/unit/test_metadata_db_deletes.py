"""Tests for MetadataDB delete operations."""

import pytest
import tempfile
from pathlib import Path
from cinchdb.infrastructure.metadata_db import MetadataDB
import uuid


class TestMetadataDBDeletes:
    """Test metadata database delete operations."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def populated_metadata_db(self, temp_project):
        """Create a metadata DB with test data."""
        metadata_db = MetadataDB(temp_project)
        
        # Create test databases
        db1_id = str(uuid.uuid4())
        db2_id = str(uuid.uuid4())
        metadata_db.create_database(db1_id, "test-db-1", "Test Database 1")
        metadata_db.create_database(db2_id, "test-db-2", "Test Database 2")
        
        # Create branches
        branch1_id = str(uuid.uuid4())
        branch2_id = str(uuid.uuid4())
        branch3_id = str(uuid.uuid4())
        metadata_db.create_branch(branch1_id, db1_id, "main")
        metadata_db.create_branch(branch2_id, db1_id, "feature")
        metadata_db.create_branch(branch3_id, db2_id, "main")
        
        # Create tenants
        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())
        tenant3_id = str(uuid.uuid4())
        tenant4_id = str(uuid.uuid4())
        metadata_db.create_tenant(tenant1_id, branch1_id, "main")
        metadata_db.create_tenant(tenant2_id, branch1_id, "tenant-1")
        metadata_db.create_tenant(tenant3_id, branch2_id, "main")
        metadata_db.create_tenant(tenant4_id, branch3_id, "main")
        
        yield {
            'metadata_db': metadata_db,
            'db1_id': db1_id,
            'db2_id': db2_id,
            'branch1_id': branch1_id,
            'branch2_id': branch2_id,
            'branch3_id': branch3_id,
            'tenant1_id': tenant1_id,
            'tenant2_id': tenant2_id,
            'tenant3_id': tenant3_id,
            'tenant4_id': tenant4_id
        }
        
        # Clean up - close the connection
        metadata_db.close()
    
    def test_delete_tenant(self, populated_metadata_db):
        """Test deleting a single tenant."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Verify tenant exists
        tenant = metadata_db.get_tenant(data['branch1_id'], "tenant-1")
        assert tenant is not None
        
        # Delete tenant
        metadata_db.delete_tenant(data['tenant2_id'])
        
        # Verify tenant is deleted
        tenant = metadata_db.get_tenant(data['branch1_id'], "tenant-1")
        assert tenant is None
        
        # Verify other tenants still exist
        tenant = metadata_db.get_tenant(data['branch1_id'], "main")
        assert tenant is not None
    
    def test_delete_tenant_by_name(self, populated_metadata_db):
        """Test deleting a tenant by name."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Delete tenant by name
        metadata_db.delete_tenant_by_name(data['branch1_id'], "tenant-1")
        
        # Verify tenant is deleted
        tenant = metadata_db.get_tenant(data['branch1_id'], "tenant-1")
        assert tenant is None
        
        # Other tenants should still exist
        tenants = metadata_db.list_tenants(data['branch1_id'])
        assert len(tenants) == 1
        assert tenants[0]['name'] == 'main'
    
    def test_delete_nonexistent_tenant(self, populated_metadata_db):
        """Test deleting a non-existent tenant raises error."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Try to delete non-existent tenant
        with pytest.raises(ValueError, match="not found"):
            metadata_db.delete_tenant("non-existent-id")
        
        with pytest.raises(ValueError, match="not found"):
            metadata_db.delete_tenant_by_name(data['branch1_id'], "non-existent")
    
    def test_delete_branch_archives_branch_deletes_tenants(self, populated_metadata_db):
        """Test that deleting a branch archives the branch and deletes all its tenants."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']

        # Verify branch has tenants
        tenants = metadata_db.list_tenants(data['branch1_id'])
        assert len(tenants) == 2

        # Delete branch (now archives)
        metadata_db.delete_branch(data['branch1_id'])

        # Verify branch is archived (not visible in normal queries)
        branch = metadata_db.get_branch(data['db1_id'], "main")
        assert branch is None

        # But should exist with archived_at set when queried directly
        with metadata_db.conn:
            cursor = metadata_db.conn.execute(
                "SELECT * FROM branches WHERE id = ?",
                (data['branch1_id'],)
            )
            archived_branch = cursor.fetchone()
            assert archived_branch is not None
            assert archived_branch['archived_at'] is not None

        # Verify all tenants are deleted (hard delete)
        tenants = metadata_db.list_tenants(data['branch1_id'])
        assert len(tenants) == 0

        # Other branches should still exist
        branches = metadata_db.list_branches(data['db1_id'])
        assert len(branches) == 1
        assert branches[0]['name'] == 'feature'
    
    def test_delete_branch_by_name(self, populated_metadata_db):
        """Test deleting a branch by name (now archives)."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']

        # Delete branch by name
        metadata_db.delete_branch_by_name(data['db1_id'], "feature")

        # Verify branch is archived (not visible in normal queries)
        branch = metadata_db.get_branch(data['db1_id'], "feature")
        assert branch is None

        # Main branch should still exist
        branches = metadata_db.list_branches(data['db1_id'])
        assert len(branches) == 1
        assert branches[0]['name'] == 'main'

    def test_archived_branch_name_can_be_reused(self, populated_metadata_db):
        """Test that archived branch names can be reused for new branches."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']

        # Archive the feature branch
        metadata_db.delete_branch_by_name(data['db1_id'], "feature")

        # Verify branch is archived
        branch = metadata_db.get_branch(data['db1_id'], "feature")
        assert branch is None

        # Create a new branch with the same name
        new_branch_id = str(uuid.uuid4())
        metadata_db.create_branch(
            new_branch_id, data['db1_id'], "feature",
            parent_branch="main"
        )

        # Verify new branch exists and is active
        new_branch = metadata_db.get_branch(data['db1_id'], "feature")
        assert new_branch is not None
        assert new_branch['id'] == new_branch_id
        assert new_branch['archived_at'] is None

        # Should have 2 active branches now
        branches = metadata_db.list_branches(data['db1_id'])
        assert len(branches) == 2
    
    def test_delete_database_cascades_to_all(self, populated_metadata_db):
        """Test that deleting a database deletes all branches and tenants."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Verify database has branches and tenants
        branches = metadata_db.list_branches(data['db1_id'])
        assert len(branches) == 2
        
        # Delete database
        metadata_db.delete_database(data['db1_id'])
        
        # Verify database is deleted
        db = metadata_db.get_database("test-db-1")
        assert db is None
        
        # Verify all branches are deleted
        branches = metadata_db.list_branches(data['db1_id'])
        assert len(branches) == 0
        
        # Other database should still exist
        databases = metadata_db.list_databases()
        assert len(databases) == 1
        assert databases[0]['name'] == 'test-db-2'
    
    def test_delete_database_by_name(self, populated_metadata_db):
        """Test deleting a database by name."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Delete database by name
        metadata_db.delete_database_by_name("test-db-2")
        
        # Verify database is deleted
        db = metadata_db.get_database("test-db-2")
        assert db is None
        
        # test-db-1 should still exist
        databases = metadata_db.list_databases()
        assert len(databases) == 1
        assert databases[0]['name'] == 'test-db-1'
    
    def test_atomic_delete_rollback_on_error(self, temp_project):
        """Test that delete operations are atomic (rollback on error)."""
        with MetadataDB(temp_project) as metadata_db:
            # Create a database
            db_id = str(uuid.uuid4())
            metadata_db.create_database(db_id, "test-db", "Test")
            
            # Close the connection to simulate an issue
            original_conn = metadata_db.conn
            metadata_db.conn.close()
            
            # Try to delete (should fail)
            metadata_db.conn = original_conn  # Restore for error handling
            try:
                # This should fail because connection is closed
                with pytest.raises(Exception):
                    metadata_db.conn = None  # Force error
                    metadata_db.delete_database(db_id)
            finally:
                metadata_db._connect()  # Reconnect
            
            # Database should still exist (rollback happened)
            db = metadata_db.get_database("test-db")
            assert db is not None
    
    def test_cascade_delete_integrity(self, populated_metadata_db):
        """Test that cascade deletes maintain referential integrity."""
        data = populated_metadata_db
        metadata_db = data['metadata_db']
        
        # Delete database with multiple branches and tenants
        metadata_db.delete_database(data['db1_id'])
        
        # Verify no orphaned branches
        with metadata_db.conn:
            cursor = metadata_db.conn.execute(
                "SELECT COUNT(*) as count FROM branches WHERE database_id = ?",
                (data['db1_id'],)
            )
            assert cursor.fetchone()['count'] == 0
        
        # Verify no orphaned tenants from deleted branches
        with metadata_db.conn:
            cursor = metadata_db.conn.execute(
                "SELECT COUNT(*) as count FROM tenants WHERE branch_id IN (?, ?)",
                (data['branch1_id'], data['branch2_id'])
            )
            assert cursor.fetchone()['count'] == 0
        
        # Verify other database's data is intact
        branches = metadata_db.list_branches(data['db2_id'])
        assert len(branches) == 1
        tenants = metadata_db.list_tenants(data['branch3_id'])
        assert len(tenants) == 1
    
    def test_delete_operations_with_transactions(self, temp_project):
        """Test that delete operations properly use transactions."""
        with MetadataDB(temp_project) as metadata_db:
            # Create test data
            db_id = str(uuid.uuid4())
            branch_id = str(uuid.uuid4())
            tenant_id = str(uuid.uuid4())
            
            metadata_db.create_database(db_id, "test-db", "Test")
            metadata_db.create_branch(branch_id, db_id, "main")
            metadata_db.create_tenant(tenant_id, branch_id, "main")
            
            # Start a transaction and delete
            with metadata_db.conn:
                metadata_db.conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
                # Transaction should auto-commit at end of with block
            
            # Verify deletion persisted
            tenant = metadata_db.get_tenant(branch_id, "main")
            assert tenant is None
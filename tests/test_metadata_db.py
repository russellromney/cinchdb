"""Tests for SQLite metadata database."""

import pytest
import tempfile
from pathlib import Path
import uuid
from cinchdb.infrastructure.metadata_db import MetadataDB


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def metadata_db(temp_project_dir):
    """Create a metadata database instance."""
    db = MetadataDB(temp_project_dir)
    yield db
    db.close()


class TestMetadataDB:
    """Test metadata database operations."""
    
    def test_database_operations(self, metadata_db):
        """Test database CRUD operations."""
        # Create a database
        db_id = str(uuid.uuid4())
        metadata_db.create_database(
            db_id, "testdb", "Test database", {"key": "value"}
        )
        
        # Get the database
        db = metadata_db.get_database("testdb")
        assert db is not None
        assert db["name"] == "testdb"
        assert db["description"] == "Test database"
        assert db["materialized"] == 0  # SQLite stores as 0/1
        
        # List databases
        dbs = metadata_db.list_databases()
        assert len(dbs) == 1
        assert dbs[0]["name"] == "testdb"
        
        # Mark as materialized
        metadata_db.mark_database_materialized(db_id)
        db = metadata_db.get_database("testdb")
        assert db["materialized"] == 1
        
        # List only materialized
        dbs = metadata_db.list_databases(materialized_only=True)
        assert len(dbs) == 1
    
    def test_branch_operations(self, metadata_db):
        """Test branch CRUD operations."""
        # Create database first
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb")
        
        # Create branches
        branch1_id = str(uuid.uuid4())
        metadata_db.create_branch(
            branch1_id, db_id, "main", 
            schema_version="v1.0.0"
        )
        
        branch2_id = str(uuid.uuid4())
        metadata_db.create_branch(
            branch2_id, db_id, "feature",
            parent_branch="main",
            schema_version="v1.0.1"
        )
        
        # Get branch
        branch = metadata_db.get_branch(db_id, "main")
        assert branch is not None
        assert branch["name"] == "main"
        assert branch["schema_version"] == "v1.0.0"
        
        # List branches
        branches = metadata_db.list_branches(db_id)
        assert len(branches) == 2
        
        # Mark as materialized
        metadata_db.mark_branch_materialized(branch1_id)
        branches = metadata_db.list_branches(db_id, materialized_only=True)
        assert len(branches) == 1
        assert branches[0]["name"] == "main"
    
    def test_tenant_operations(self, metadata_db):
        """Test tenant CRUD operations."""
        # Create database and branch first
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb")
        
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, db_id, "main")
        
        # Create tenants
        tenant1_id = str(uuid.uuid4())
        metadata_db.create_tenant(tenant1_id, branch_id, "tenant1")
        
        tenant2_id = str(uuid.uuid4())
        metadata_db.create_tenant(tenant2_id, branch_id, "tenant2")
        
        # Get tenant
        tenant = metadata_db.get_tenant(branch_id, "tenant1")
        assert tenant is not None
        assert tenant["name"] == "tenant1"
        
        # List tenants
        tenants = metadata_db.list_tenants(branch_id)
        assert len(tenants) == 2
        
        # Check existence
        assert metadata_db.tenant_exists("testdb", "main", "tenant1")
        assert not metadata_db.tenant_exists("testdb", "main", "nonexistent")
        
        # Get full info
        info = metadata_db.get_full_tenant_info("testdb", "main", "tenant1")
        assert info is not None
        assert info["name"] == "tenant1"
        assert info["branch_name"] == "main"
        assert info["database_name"] == "testdb"
        
        # Mark as materialized
        metadata_db.mark_tenant_materialized(tenant1_id)
        tenants = metadata_db.list_tenants(branch_id, materialized_only=True)
        assert len(tenants) == 1
        assert tenants[0]["name"] == "tenant1"
    
    def test_cascade_delete(self, metadata_db):
        """Test cascade deletion."""
        # Create hierarchy
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb")
        
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, db_id, "main")
        
        tenant_id = str(uuid.uuid4())
        metadata_db.create_tenant(tenant_id, branch_id, "tenant1")
        
        # Delete database (should cascade)
        with metadata_db.conn:
            metadata_db.conn.execute("DELETE FROM databases WHERE id = ?", (db_id,))
        
        # Check cascading worked
        assert metadata_db.get_branch(db_id, "main") is None
        assert metadata_db.get_tenant(branch_id, "tenant1") is None
    
    def test_unique_constraints(self, metadata_db):
        """Test unique constraints."""
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb")
        
        # Try to create duplicate database name
        with pytest.raises(sqlite3.IntegrityError):
            metadata_db.create_database(str(uuid.uuid4()), "testdb")
        
        # Try to create duplicate branch name in same database
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, db_id, "main")
        
        with pytest.raises(sqlite3.IntegrityError):
            metadata_db.create_branch(str(uuid.uuid4()), db_id, "main")
        
        # Try to create duplicate tenant name in same branch
        tenant_id = str(uuid.uuid4())
        metadata_db.create_tenant(tenant_id, branch_id, "tenant1")
        
        with pytest.raises(sqlite3.IntegrityError):
            metadata_db.create_tenant(str(uuid.uuid4()), branch_id, "tenant1")
    
    def test_performance_with_many_tenants(self, metadata_db):
        """Test performance with many tenants."""
        import time
        
        # Create database and branch
        db_id = str(uuid.uuid4())
        metadata_db.create_database(db_id, "testdb")
        
        branch_id = str(uuid.uuid4())
        metadata_db.create_branch(branch_id, db_id, "main")
        
        # Create many tenants
        n_tenants = 10000
        start = time.time()
        
        with metadata_db.conn:
            for i in range(n_tenants):
                metadata_db.conn.execute("""
                    INSERT INTO tenants (id, branch_id, name, metadata)
                    VALUES (?, ?, ?, ?)
                """, (str(uuid.uuid4()), branch_id, f"tenant_{i}", None))
        
        create_time = time.time() - start
        print(f"\nCreated {n_tenants} tenants in {create_time:.2f}s")
        assert create_time < 5.0  # Should be much faster, typically < 1s
        
        # Test lookup performance
        start = time.time()
        exists = metadata_db.tenant_exists("testdb", "main", "tenant_5000")
        lookup_time = time.time() - start
        print(f"Lookup time: {lookup_time*1000:.2f}ms")
        assert exists
        assert lookup_time < 0.01  # Should be < 10ms
        
        # Test listing performance
        start = time.time()
        tenants = metadata_db.list_tenants(branch_id)
        list_time = time.time() - start
        print(f"List {n_tenants} tenants in {list_time:.2f}s")
        assert len(tenants) == n_tenants
        assert list_time < 1.0  # Should be fast


import sqlite3
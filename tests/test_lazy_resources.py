"""Tests for lazy databases, branches, and tenants with SQLite metadata."""

import pytest
import tempfile
from pathlib import Path
from cinchdb.core.initializer import ProjectInitializer, init_project
from cinchdb.managers.branch import BranchManager
from cinchdb.managers.tenant import TenantManager
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.core.path_utils import list_databases, list_branches


@pytest.fixture
def test_project():
    """Create a test project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        init_project(project_root, "testdb", "main")
        yield project_root


class TestLazyDatabases:
    """Test lazy database functionality."""
    
    def test_create_lazy_database(self, test_project):
        """Test creating a lazy database."""
        initializer = ProjectInitializer(test_project)
        
        # Create lazy database
        initializer.init_database("lazy_db", "main", "Lazy database", lazy=True)
        
        # Verify database exists in metadata
        databases = list_databases(test_project)
        assert "lazy_db" in databases
        assert "testdb" in databases  # Original database
        
        # Verify no physical directory created
        db_path = test_project / ".cinchdb" / "databases" / "lazy_db"
        assert not db_path.exists()
        
        # Verify it's in metadata database
        metadata_db = MetadataDB(test_project)
        db_info = metadata_db.get_database("lazy_db")
        assert db_info is not None
        assert db_info['name'] == "lazy_db"
        assert not db_info['materialized']
    
    def test_materialize_lazy_database(self, test_project):
        """Test materializing a lazy database."""
        initializer = ProjectInitializer(test_project)
        
        # Create lazy database
        initializer.init_database("lazy_db2", "main", lazy=True)
        
        # Materialize it
        initializer.materialize_database("lazy_db2")
        
        # Verify physical directory now exists
        db_path = test_project / ".cinchdb" / "databases" / "lazy_db2"
        assert db_path.exists()
        
        # Verify branch structure exists (but tenant files don't until tables are added)
        branch_path = db_path / "branches" / "main"
        assert branch_path.exists()
        assert (branch_path / "metadata.json").exists()
        assert (branch_path / "changes.json").exists()
        assert (branch_path / "tenants").exists()  # Directory exists but no tenant files yet
        
        # Main tenant database file should NOT exist yet (no tables = no materialization)
        from cinchdb.core.path_utils import get_tenant_db_path
        main_tenant_path = get_tenant_db_path(test_project, "lazy_db2", "main", "main")
        assert not main_tenant_path.exists()  # Should be lazy until tables are added
        
        # Verify marked as materialized in metadata
        metadata_db = MetadataDB(test_project)
        db_info = metadata_db.get_database("lazy_db2")
        assert db_info['materialized']
    
    def test_auto_materialize_on_access(self, test_project):
        """Test that lazy databases auto-materialize when accessed."""
        from cinchdb.core.database import CinchDB
        
        initializer = ProjectInitializer(test_project)
        
        # Create lazy database
        initializer.init_database("lazy_db3", lazy=True)
        
        # Access it through CinchDB (should trigger materialization)
        CinchDB(database="lazy_db3", project_dir=test_project)
        
        # Verify it was materialized
        db_path = test_project / ".cinchdb" / "databases" / "lazy_db3"
        assert db_path.exists()


class TestLazyBranches:
    """Test lazy branch functionality."""
    
    def test_create_lazy_branch(self, test_project):
        """Test creating a branch (branches are no longer lazy)."""
        branch_manager = BranchManager(test_project, "testdb")
        
        # Create branch (no lazy parameter anymore)
        branch = branch_manager.create_branch("main", "feature1")
        assert branch.name == "feature1"
        assert branch.parent_branch == "main"
        
        # Verify branch exists in listings
        branches = list_branches(test_project, "testdb")
        assert "feature1" in branches
        assert "main" in branches
        
        # Verify physical directory is created (branches are always materialized)
        branch_path = test_project / ".cinchdb" / "databases" / "testdb" / "branches" / "feature1"
        assert branch_path.exists()
    
    def test_materialize_lazy_branch(self, test_project):
        """Test branch creation (branches are always materialized now)."""
        branch_manager = BranchManager(test_project, "testdb")
        
        # Create branch (always materialized)
        branch_manager.create_branch("main", "feature2")
        
        # Verify physical directory now exists
        branch_path = test_project / ".cinchdb" / "databases" / "testdb" / "branches" / "feature2"
        assert branch_path.exists()
        assert (branch_path / "metadata.json").exists()
        assert (branch_path / "changes.json").exists()
        assert (branch_path / "tenants").exists()  # Directory exists
        
        # Main tenant database file should exist (copied from source branch)
        from cinchdb.core.path_utils import get_tenant_db_path
        main_tenant_path = get_tenant_db_path(test_project, "testdb", "feature2", "main")
        assert main_tenant_path.exists()  # Should be copied from source branch
    
    def test_delete_lazy_branch(self, test_project):
        """Test deleting a branch."""
        branch_manager = BranchManager(test_project, "testdb")
        
        # Create and delete branch
        branch_manager.create_branch("main", "feature3")
        branch_manager.delete_branch("feature3")
        
        # Verify it's gone
        branches = list_branches(test_project, "testdb")
        assert "feature3" not in branches
    
    def test_nested_lazy_branches(self, test_project):
        """Test creating nested branches."""
        branch_manager = BranchManager(test_project, "testdb")
        
        # Create chain of branches
        branch_manager.create_branch("main", "dev")
        branch_manager.create_branch("dev", "feature")
        branch_manager.create_branch("feature", "bugfix")
        
        # All should be materialized (branches are always materialized)
        dev_path = test_project / ".cinchdb" / "databases" / "testdb" / "branches" / "dev"
        feature_path = test_project / ".cinchdb" / "databases" / "testdb" / "branches" / "feature"
        assert dev_path.exists()
        assert feature_path.exists()
        
        # Verify bugfix branch exists
        bugfix_path = test_project / ".cinchdb" / "databases" / "testdb" / "branches" / "bugfix"
        assert bugfix_path.exists()


class TestIntegration:
    """Test integration of lazy resources across database, branch, and tenant levels."""
    
    def test_fully_lazy_hierarchy(self, test_project):
        """Test creating a fully lazy hierarchy."""
        initializer = ProjectInitializer(test_project)
        
        # Create lazy database
        initializer.init_database("app_db", lazy=True)
        
        # Verify metadata database has the structure
        metadata_db = MetadataDB(test_project)
        
        # Check database
        db_info = metadata_db.get_database("app_db")
        assert db_info is not None
        assert not db_info['materialized']
        
        # Check initial branch
        branch_info = metadata_db.get_branch(db_info['id'], "main")
        assert branch_info is not None
        assert not branch_info['materialized']
        
        # No physical files should exist
        db_path = test_project / ".cinchdb" / "databases" / "app_db"
        assert not db_path.exists()
    
    def test_lazy_resource_performance(self, test_project):
        """Test performance with many lazy resources."""
        import time
        
        initializer = ProjectInitializer(test_project)
        
        # Create many lazy databases
        n_databases = 100
        start = time.time()
        
        for i in range(n_databases):
            initializer.init_database(f"db_{i}", lazy=True)
        
        create_time = time.time() - start
        print(f"\nCreated {n_databases} lazy databases in {create_time:.2f}s")
        assert create_time < 5.0  # Should be fast
        
        # Test listing performance
        start = time.time()
        databases = list_databases(test_project)
        list_time = time.time() - start
        print(f"Listed {len(databases)} databases in {list_time:.2f}s")
        assert len(databases) == n_databases + 1  # +1 for initial testdb
        assert list_time < 1.0
        
        # No physical directories should exist
        databases_dir = test_project / ".cinchdb" / "databases"
        physical_dbs = [d for d in databases_dir.iterdir() if d.is_dir()]
        assert len(physical_dbs) == 1  # Only testdb should be materialized
    
    def test_mixed_lazy_and_materialized(self, test_project):
        """Test system with mix of lazy and materialized resources."""
        initializer = ProjectInitializer(test_project)
        
        # Create mix of lazy and materialized databases
        initializer.init_database("lazy1", lazy=True)
        initializer.init_database("materialized1", lazy=False)
        initializer.init_database("lazy2", lazy=True)
        
        # Create branches (branches are always materialized)
        branch_mgr_mat = BranchManager(test_project, "materialized1")
        branch_mgr_mat.create_branch("main", "dev")
        branch_mgr_mat.create_branch("main", "prod")
        
        # Create tenants in materialized database
        tenant_mgr = TenantManager(test_project, "materialized1", "main")
        tenant_mgr.create_tenant("lazy_tenant", lazy=True)
        tenant_mgr.create_tenant("real_tenant", lazy=False)
        
        # Verify mixed state
        databases = list_databases(test_project)
        assert all(db in databases for db in ["testdb", "lazy1", "lazy2", "materialized1"])
        
        # Check physical existence
        assert not (test_project / ".cinchdb" / "databases" / "lazy1").exists()
        assert not (test_project / ".cinchdb" / "databases" / "lazy2").exists()
        assert (test_project / ".cinchdb" / "databases" / "materialized1").exists()
        
        # Check branches (all branches are materialized)
        assert (test_project / ".cinchdb" / "databases" / "materialized1" / "branches" / "dev").exists()
        assert (test_project / ".cinchdb" / "databases" / "materialized1" / "branches" / "prod").exists()
        
        # Check tenants
        assert tenant_mgr.is_tenant_lazy("lazy_tenant")
        assert not tenant_mgr.is_tenant_lazy("real_tenant")
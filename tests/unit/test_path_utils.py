"""Tests for path utilities."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.core.path_utils import (
    get_project_root,
    get_database_path,
    get_branch_path,
    get_tenant_path,
    get_tenant_db_path,
    ensure_directory,
    list_databases,
    list_branches,
    list_tenants,
)


class TestPathUtils:
    """Test path utility functions."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp) / ".cinchdb"
        project_dir.mkdir()
        yield Path(temp)
        shutil.rmtree(temp)
    
    def test_get_project_root(self, temp_project):
        """Test getting project root."""
        # From project directory
        assert get_project_root(temp_project) == temp_project.resolve()
        
        # From subdirectory
        subdir = temp_project / "subdir"
        subdir.mkdir()
        assert get_project_root(subdir) == temp_project.resolve()
        
        # No project found
        with pytest.raises(FileNotFoundError):
            get_project_root(Path("/tmp/nonexistent"))
    
    def test_get_database_path(self, temp_project):
        """Test getting database path."""
        db_path = get_database_path(temp_project, "test_db")
        expected = temp_project / ".cinchdb" / "databases" / "test_db"
        assert db_path == expected
    
    def test_get_branch_path(self, temp_project):
        """Test getting branch path."""
        branch_path = get_branch_path(temp_project, "test_db", "feature")
        expected = temp_project / ".cinchdb" / "databases" / "test_db" / "branches" / "feature"
        assert branch_path == expected
    
    def test_get_tenant_path(self, temp_project):
        """Test getting tenant path."""
        tenant_path = get_tenant_path(temp_project, "test_db", "main", "customer1")
        expected = temp_project / ".cinchdb" / "databases" / "test_db" / "branches" / "main" / "tenants"
        assert tenant_path == expected
    
    def test_get_tenant_db_path(self, temp_project):
        """Test getting tenant database file path."""
        db_path = get_tenant_db_path(temp_project, "test_db", "main", "customer1")
        expected = temp_project / ".cinchdb" / "databases" / "test_db" / "branches" / "main" / "tenants" / "customer1.db"
        assert db_path == expected
    
    def test_ensure_directory(self, temp_project):
        """Test ensuring directory exists."""
        test_dir = temp_project / "test" / "nested" / "dir"
        
        # Directory doesn't exist
        assert not test_dir.exists()
        
        # Create it
        ensure_directory(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()
        
        # Call again - should not fail
        ensure_directory(test_dir)
        assert test_dir.exists()
    
    def test_list_databases(self, temp_project):
        """Test listing databases."""
        # Initially empty
        assert list_databases(temp_project) == []
        
        # Create some databases
        db_base = temp_project / ".cinchdb" / "databases"
        db_base.mkdir(parents=True)
        
        (db_base / "db1").mkdir()
        (db_base / "db2").mkdir()
        (db_base / "db3").mkdir()
        
        # List them
        dbs = list_databases(temp_project)
        assert sorted(dbs) == ["db1", "db2", "db3"]
    
    def test_list_branches(self, temp_project):
        """Test listing branches."""
        # Create database structure
        db_path = get_database_path(temp_project, "test_db")
        branches_path = db_path / "branches"
        branches_path.mkdir(parents=True)
        
        # Initially empty
        assert list_branches(temp_project, "test_db") == []
        
        # Create branches
        (branches_path / "main").mkdir()
        (branches_path / "feature1").mkdir()
        (branches_path / "feature2").mkdir()
        
        # List them
        branches = list_branches(temp_project, "test_db")
        assert sorted(branches) == ["feature1", "feature2", "main"]
    
    def test_list_tenants(self, temp_project):
        """Test listing tenants."""
        # Create branch structure
        branch_path = get_branch_path(temp_project, "test_db", "main")
        tenants_path = branch_path / "tenants"
        tenants_path.mkdir(parents=True)
        
        # Initially empty
        assert list_tenants(temp_project, "test_db", "main") == []
        
        # Create tenant files
        (tenants_path / "main.db").touch()
        (tenants_path / "customer1.db").touch()
        (tenants_path / "customer2.db").touch()
        (tenants_path / "customer1.db-wal").touch()  # Should be ignored
        
        # List them
        tenants = list_tenants(temp_project, "test_db", "main")
        assert sorted(tenants) == ["customer1", "customer2", "main"]
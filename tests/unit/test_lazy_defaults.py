"""Test that lazy is the default for database and tenant creation."""

import tempfile
import json
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import get_database_path, get_tenant_db_path


def test_database_default_is_lazy():
    """Test that databases are created as lazy by default."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create database without specifying lazy parameter
        init_database(project_dir, "test-db")
        
        # Should be lazy (only metadata file exists)
        db_path = get_database_path(project_dir, "test-db")
        meta_file = project_dir / ".cinchdb" / "databases" / ".test-db.meta"
        
        assert not db_path.exists()  # Directory should not exist
        assert meta_file.exists()  # Metadata should exist
        
        # Verify metadata indicates it's lazy
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["lazy"] is True


def test_database_explicit_eager():
    """Test that databases can still be created eagerly when specified."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create database explicitly as eager
        init_database(project_dir, "eager-db", lazy=False)
        
        # Should be eager (directory structure exists)
        db_path = get_database_path(project_dir, "eager-db")
        meta_file = project_dir / ".cinchdb" / "databases" / ".eager-db.meta"
        
        assert db_path.exists()  # Directory should exist
        assert not meta_file.exists()  # No metadata file for eager databases
        assert (db_path / "branches" / "main").exists()


def test_tenant_default_is_lazy():
    """Test that tenants are created as lazy by default."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with eager database so we can test tenants
        init_project(project_dir)
        init_database(project_dir, "test-db", lazy=False)
        
        tenant_manager = TenantManager(project_dir, "test-db", "main")
        
        # Create tenant without specifying lazy parameter
        tenant = tenant_manager.create_tenant("test-tenant")
        
        # Should be lazy (only metadata file exists)
        tenant_db = get_tenant_db_path(project_dir, "test-db", "main", "test-tenant")
        tenant_meta = project_dir / ".cinchdb" / "databases" / "test-db" / "branches" / "main" / "tenants" / ".test-tenant.meta"
        
        assert not tenant_db.exists()  # Database file should not exist
        assert tenant_meta.exists()  # Metadata should exist
        
        # Verify metadata indicates it's lazy
        with open(tenant_meta) as f:
            metadata = json.load(f)
        assert metadata["lazy"] is True


def test_tenant_explicit_eager():
    """Test that tenants can still be created eagerly when specified."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with eager database
        init_project(project_dir)
        init_database(project_dir, "test-db", lazy=False)
        
        tenant_manager = TenantManager(project_dir, "test-db", "main")
        
        # Create tenant explicitly as eager
        tenant = tenant_manager.create_tenant("eager-tenant", lazy=False)
        
        # Should be eager (database file exists)
        tenant_db = get_tenant_db_path(project_dir, "test-db", "main", "eager-tenant")
        tenant_meta = project_dir / ".cinchdb" / "databases" / "test-db" / "branches" / "main" / "tenants" / ".eager-tenant.meta"
        
        assert tenant_db.exists()  # Database file should exist
        assert not tenant_meta.exists()  # No metadata for eager tenants


def test_mixed_lazy_eager_defaults():
    """Test mixing default lazy with explicit eager."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create some databases with defaults and some explicit
        init_database(project_dir, "default-lazy")  # Should be lazy
        init_database(project_dir, "explicit-eager", lazy=False)  # Should be eager
        init_database(project_dir, "explicit-lazy", lazy=True)  # Should be lazy
        
        # Check default-lazy
        assert not (project_dir / ".cinchdb" / "databases" / "default-lazy").exists()
        assert (project_dir / ".cinchdb" / "databases" / ".default-lazy.meta").exists()
        
        # Check explicit-eager
        assert (project_dir / ".cinchdb" / "databases" / "explicit-eager").exists()
        assert not (project_dir / ".cinchdb" / "databases" / ".explicit-eager.meta").exists()
        
        # Check explicit-lazy
        assert not (project_dir / ".cinchdb" / "databases" / "explicit-lazy").exists()
        assert (project_dir / ".cinchdb" / "databases" / ".explicit-lazy.meta").exists()


def test_initializer_method_defaults():
    """Test that ProjectInitializer methods have correct defaults."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        initializer = ProjectInitializer(project_dir)
        
        # Create database using initializer directly without lazy param
        initializer.init_database("from-initializer")
        
        # Should be lazy by default
        assert not (project_dir / ".cinchdb" / "databases" / "from-initializer").exists()
        assert (project_dir / ".cinchdb" / "databases" / ".from-initializer.meta").exists()
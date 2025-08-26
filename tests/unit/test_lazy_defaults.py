"""Test that lazy is the default for database and tenant creation."""

import tempfile
from pathlib import Path

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import get_database_path, get_tenant_db_path
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_database_default_is_lazy():
    """Test that databases are created as lazy by default."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create database without specifying lazy parameter
        init_database(project_dir, "test-db")
        
        # Should be lazy (directory should not exist)
        db_path = get_database_path(project_dir, "test-db")
        assert not db_path.exists()  # Directory should not exist
        
        # Check metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("test-db")
        assert db_info is not None
        assert not db_info["materialized"]  # Should be lazy (0 in SQLite)


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
        assert db_path.exists()  # Directory should exist
        assert (db_path / "branches" / "main").exists()
        
        # Check metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("eager-db")
        assert db_info is not None
        assert db_info["materialized"]  # Should be materialized (1 in SQLite)


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
        
        # Should be lazy (database file should not exist)
        tenant_db = get_tenant_db_path(project_dir, "test-db", "main", "test-tenant")
        assert not tenant_db.exists()  # Database file should not exist
        
        # Check metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("test-db")
        branches = metadata_db.list_branches(db_info["id"])
        main_branch = next(b for b in branches if b["name"] == "main")
        tenants = metadata_db.list_tenants(main_branch["id"])
        test_tenant = next(t for t in tenants if t["name"] == "test-tenant")
        assert not test_tenant["materialized"]  # Should be lazy


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
        assert tenant_db.exists()  # Database file should exist
        
        # Check metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("test-db")
        branches = metadata_db.list_branches(db_info["id"])
        main_branch = next(b for b in branches if b["name"] == "main")
        tenants = metadata_db.list_tenants(main_branch["id"])
        eager_tenant = next(t for t in tenants if t["name"] == "eager-tenant")
        assert eager_tenant["materialized"]  # Should be materialized


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
        
        # Check explicit-eager
        assert (project_dir / ".cinchdb" / "databases" / "explicit-eager").exists()
        
        # Check explicit-lazy
        assert not (project_dir / ".cinchdb" / "databases" / "explicit-lazy").exists()
        
        # Verify in metadata database
        metadata_db = MetadataDB(project_dir)
        
        default_lazy = metadata_db.get_database("default-lazy")
        assert not default_lazy["materialized"]
        
        explicit_eager = metadata_db.get_database("explicit-eager")
        assert explicit_eager["materialized"]
        
        explicit_lazy = metadata_db.get_database("explicit-lazy")
        assert not explicit_lazy["materialized"]


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
        
        # Check metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("from-initializer")
        assert db_info is not None
        assert not db_info["materialized"]  # Should be lazy by default
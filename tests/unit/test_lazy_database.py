"""Test lazy database creation functionality."""

import tempfile
import json
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.core.path_utils import list_databases, get_database_path, get_context_root, get_tenant_db_path
from cinchdb.core.database import CinchDB, connect
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_lazy_database_creation():
    """Test that lazy databases don't create directory structure."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with main database
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Check that database is in metadata database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("lazy-db")
        assert db_info is not None
        assert db_info["name"] == "lazy-db"
        assert not db_info["materialized"]  # Lazy database not materialized (0 in SQLite)
        
        # Check metadata content
        metadata = json.loads(db_info["metadata"]) if db_info["metadata"] else {}
        assert metadata.get("initial_branch") == "main"
        
        # Check that context root does NOT exist (tenant-first architecture)
        context_root = get_context_root(project_dir, "lazy-db", "main")
        assert not context_root.exists()
        
        # Verify database appears in list
        databases = list_databases(project_dir)
        assert "lazy-db" in databases
        assert "main" in databases  # Main database should still exist


def test_lazy_database_materialization():
    """Test materializing a lazy database."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", branch_name="dev", lazy=True)
        
        # Context root shouldn't exist yet
        context_root = get_context_root(project_dir, "lazy-db", "dev")
        assert not context_root.exists()
        
        # Materialize the database
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("lazy-db")
        
        # Now context root should exist
        assert context_root.exists()
        
        # Main tenant database should NOT exist until tables are added
        main_tenant_path = get_tenant_db_path(project_dir, "lazy-db", "dev", "main")
        assert not main_tenant_path.exists()  # Should be lazy until tables are added
        
        # Check that metadata was updated in database
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("lazy-db")
        assert db_info["materialized"]  # Now materialized (1 in SQLite)


def test_auto_materialization_on_connect():
    """Test that lazy databases are auto-materialized when connected to."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Context root shouldn't exist
        context_root = get_context_root(project_dir, "lazy-db", "main")
        assert not context_root.exists()
        
        # Connect to the database
        connect("lazy-db", project_dir=project_dir)
        
        # Context root should now be materialized
        assert context_root.exists()


def test_lazy_vs_eager_database_size():
    """Test that lazy databases use less space than eager databases."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create eager database
        init_database(project_dir, database_name="eager-db", lazy=False)
        eager_context_root = get_context_root(project_dir, "eager-db", "main")
        
        # Calculate size of eager database (directory tree)
        def get_dir_size(path):
            total = 0
            if path.exists():
                for item in path.rglob('*'):
                    if item.is_file():
                        total += item.stat().st_size
            return total
        
        eager_size = get_dir_size(eager_context_root)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # For lazy database, we now use metadata database (not .meta file)
        # The lazy database info is stored in the metadata.db SQLite file
        # which is shared by all databases. So we just check that no context root exists
        lazy_context_root = get_context_root(project_dir, "lazy-db", "main")
        assert not lazy_context_root.exists()  # No context root for lazy database
        
        # Eager database should have actual files (even if small due to optimization)
        assert eager_size > 0  # Should have some files
        assert eager_size >= 100  # At least some meaningful content


def test_duplicate_lazy_database_fails():
    """Test that creating duplicate lazy database fails."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="test-db", lazy=True)
        
        # Try to create again (should fail)
        with pytest.raises(FileExistsError) as exc_info:
            init_database(project_dir, database_name="test-db", lazy=True)
        assert "already exists" in str(exc_info.value)


def test_materialize_nonexistent_database_fails():
    """Test that materializing a non-existent database fails."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        initializer = ProjectInitializer(project_dir)
        
        # Try to materialize non-existent database
        with pytest.raises(ValueError) as exc_info:
            initializer.materialize_database("nonexistent")
        assert "does not exist" in str(exc_info.value)


def test_materialize_already_materialized():
    """Test that materializing an already materialized database is a no-op."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create eager database
        init_database(project_dir, database_name="eager-db", lazy=False)
        context_root = get_context_root(project_dir, "eager-db", "main")
        
        # Get original modification time of context root
        original_mtime = context_root.stat().st_mtime if context_root.exists() else 0
        
        # Try to materialize (should be no-op)
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("eager-db")
        
        # Context root should still exist
        assert context_root.exists()


def test_lazy_database_with_custom_branch():
    """Test that lazy databases remember their initial branch."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database with custom branch
        init_database(project_dir, database_name="lazy-db", branch_name="develop", lazy=True)
        
        # Check metadata has correct branch
        metadata_db = MetadataDB(project_dir)
        db_info = metadata_db.get_database("lazy-db")
        metadata = json.loads(db_info["metadata"]) if db_info["metadata"] else {}
        assert metadata["initial_branch"] == "develop"
        
        # Materialize and verify context root is created with correct branch
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("lazy-db")
        
        context_root = get_context_root(project_dir, "lazy-db", "develop")
        assert context_root.exists()
        
        # Should not create main branch context
        main_context = get_context_root(project_dir, "lazy-db", "main")
        assert not main_context.exists()


def test_cinchdb_class_with_lazy_database():
    """Test using CinchDB class with lazy database."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Use CinchDB class
        db = CinchDB(database="lazy-db", project_dir=project_dir)
        
        # Context root should be materialized
        context_root = get_context_root(project_dir, "lazy-db", "main")
        assert context_root.exists()
        
        # Should be able to use it normally
        assert db.database == "lazy-db"
        assert db.branch == "main"
        assert db.tenant == "main"
        assert db.is_local is True
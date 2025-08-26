"""Test lazy database creation functionality."""

import tempfile
import json
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project, init_database, ProjectInitializer
from cinchdb.core.path_utils import list_databases, get_database_path
from cinchdb.core.database import CinchDB, connect


def test_lazy_database_creation():
    """Test that lazy databases don't create directory structure."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with main database
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Check that metadata file exists
        meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        assert meta_file.exists()
        
        # Check metadata content
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["name"] == "lazy-db"
        assert metadata["lazy"] is True
        assert metadata["initial_branch"] == "main"
        
        # Check that database directory does NOT exist
        db_path = get_database_path(project_dir, "lazy-db")
        assert not db_path.exists()
        
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
        
        # Database directory shouldn't exist yet
        db_path = get_database_path(project_dir, "lazy-db")
        assert not db_path.exists()
        
        # Materialize the database
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("lazy-db")
        
        # Now database directory should exist
        assert db_path.exists()
        
        # Check that branch was created with specified name
        branch_path = db_path / "branches" / "dev"
        assert branch_path.exists()
        
        # Check that main tenant was created
        tenant_db = branch_path / "tenants" / "main.db"
        assert tenant_db.exists()
        
        # Check that metadata was updated
        meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["lazy"] is False
        assert "materialized_at" in metadata


def test_auto_materialization_on_connect():
    """Test that lazy databases are auto-materialized when connected to."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        
        # Database directory shouldn't exist
        db_path = get_database_path(project_dir, "lazy-db")
        assert not db_path.exists()
        
        # Connect to the database
        db = connect("lazy-db", project_dir=project_dir)
        
        # Database should now be materialized
        assert db_path.exists()
        assert (db_path / "branches" / "main").exists()


def test_lazy_vs_eager_database_size():
    """Test that lazy databases use less space than eager databases."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create eager database
        init_database(project_dir, database_name="eager-db", lazy=False)
        eager_db_path = get_database_path(project_dir, "eager-db")
        
        # Calculate size of eager database (directory tree)
        def get_dir_size(path):
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return total
        
        eager_size = get_dir_size(eager_db_path)
        
        # Create lazy database
        init_database(project_dir, database_name="lazy-db", lazy=True)
        lazy_meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        lazy_size = lazy_meta_file.stat().st_size
        
        # Lazy database should be much smaller (metadata only)
        assert lazy_size < 1024  # Less than 1KB
        assert eager_size >= 4096  # At least 4KB (main.db alone is bigger)
        assert lazy_size < eager_size / 4  # At least 4x smaller


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
        db_path = get_database_path(project_dir, "eager-db")
        
        # Get original modification time of a file
        branch_metadata = db_path / "branches" / "main" / "metadata.json"
        original_mtime = branch_metadata.stat().st_mtime
        
        # Try to materialize (should be no-op)
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("eager-db")
        
        # Modification time should not change
        assert branch_metadata.stat().st_mtime == original_mtime


def test_lazy_database_with_custom_branch():
    """Test that lazy databases remember their initial branch."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir)
        
        # Create lazy database with custom branch
        init_database(project_dir, database_name="lazy-db", branch_name="develop", lazy=True)
        
        # Check metadata has correct branch
        meta_file = project_dir / ".cinchdb" / "databases" / ".lazy-db.meta"
        with open(meta_file) as f:
            metadata = json.load(f)
        assert metadata["initial_branch"] == "develop"
        
        # Materialize and verify branch is created
        initializer = ProjectInitializer(project_dir)
        initializer.materialize_database("lazy-db")
        
        db_path = get_database_path(project_dir, "lazy-db")
        assert (db_path / "branches" / "develop").exists()
        assert not (db_path / "branches" / "main").exists()  # Should not create main


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
        
        # Database should be materialized
        db_path = get_database_path(project_dir, "lazy-db")
        assert db_path.exists()
        
        # Should be able to use it normally
        assert db.database == "lazy-db"
        assert db.branch == "main"
        assert db.tenant == "main"
        assert db.is_local is True
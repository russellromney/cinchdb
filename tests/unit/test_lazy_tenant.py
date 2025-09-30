"""Test lazy tenant creation functionality."""

import tempfile
from pathlib import Path
import pytest

from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.path_utils import list_tenants, get_tenant_db_path
from cinchdb.core.database import CinchDB
from cinchdb.models import Column
from cinchdb.infrastructure.metadata_db import MetadataDB


def test_lazy_tenant_creation():
    """Test that lazy tenants don't create database files."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        # Create lazy tenant using CinchDB
        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)
        db.create_tenant("lazy-tenant", lazy=True)

        # Check that tenant is tracked in metadata database
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            assert db_info is not None
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            lazy_tenant = next((t for t in tenants if t['name'] == 'lazy-tenant'), None)
            assert lazy_tenant is not None
            assert not lazy_tenant['materialized']  # Not materialized = lazy

        # Check that database file does NOT exist
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy-tenant")
        assert not db_path.exists()

        # Verify tenant appears in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy-tenant" in tenants


def test_lazy_tenant_materialization():
    """Test materializing a lazy tenant."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project with a table in main
        init_project(project_dir, database_name="testdb", branch_name="main")

        # Create a table using CinchDB (will be in __empty__ template)
        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)
        db.create_table("test_table", [
            Column(name="data", type="TEXT")
        ])

        # Create lazy tenant
        db.create_tenant("lazy-tenant", lazy=True)

        # Database shouldn't exist yet
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy-tenant")
        assert not db_path.exists()

        # Materialize the tenant by doing a write operation
        db_lazy = CinchDB(database="testdb", branch="main", tenant="lazy-tenant", project_dir=project_dir)
        db_lazy.insert("test_table", {"data": "test"})

        # Now database should exist
        assert db_path.exists()

        # Check that the table structure was copied
        tables = db_lazy.list_tables()
        table_names = [t.name for t in tables]
        assert "test_table" in table_names

        # Check that data exists
        results = db_lazy.query("SELECT COUNT(*) as count FROM test_table")
        assert results[0]["count"] == 1

        # Check that metadata was updated
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            lazy_tenant = next((t for t in tenants if t['name'] == 'lazy-tenant'), None)
            assert lazy_tenant is not None
            assert lazy_tenant['materialized']  # Now materialized


def test_lazy_vs_eager_tenant_size():
    """Test that lazy tenants use less space than eager tenants."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)

        # Create eager tenant
        db.create_tenant("eager-tenant", lazy=False)
        eager_db_path = get_tenant_db_path(project_dir, "testdb", "main", "eager-tenant")
        eager_size = eager_db_path.stat().st_size

        # Create lazy tenant
        db.create_tenant("lazy-tenant", lazy=True)

        # Check that lazy tenant has no physical .db file
        lazy_db_path = get_tenant_db_path(project_dir, "testdb", "main", "lazy-tenant")
        assert not lazy_db_path.exists()

        # Eager tenant should have a physical database file
        assert eager_db_path.exists()
        assert eager_size >= 4096  # At least one 4KB page (SQLite default)
        assert eager_size <= 24576  # Should be very small for empty tenant (increased due to schema additions)


def test_duplicate_lazy_tenant_fails():
    """Test that creating duplicate lazy tenant fails."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)

        # Create lazy tenant
        db.create_tenant("test-tenant", lazy=True)

        # Try to create again (should fail)
        with pytest.raises(ValueError) as exc_info:
            db.create_tenant("test-tenant", lazy=True)
        assert "already exists" in str(exc_info.value)


def test_materialize_nonexistent_tenant_fails():
    """Test that materializing a non-existent tenant fails."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        # Use TenantManager
        tenant_manager = TenantManager(ConnectionContext(project_root=project_dir, database="testdb", branch="main"))

        # Try to materialize non-existent tenant
        with pytest.raises(ValueError) as exc_info:
            tenant_manager.materialize_tenant("nonexistent")
        assert "does not exist" in str(exc_info.value)


def test_materialize_already_materialized():
    """Test that materializing an already materialized tenant is a no-op."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)

        # Create eager tenant
        db.create_tenant("eager-tenant", lazy=False)
        db_path = get_tenant_db_path(project_dir, "testdb", "main", "eager-tenant")

        # Get original modification time
        original_mtime = db_path.stat().st_mtime

        # Use TenantManager
        tenant_manager = TenantManager(ConnectionContext(project_root=project_dir, database="testdb", branch="main"))

        # Try to materialize (should be no-op)
        tenant_manager.materialize_tenant("eager-tenant")

        # Modification time should not change
        assert db_path.stat().st_mtime == original_mtime


def test_delete_lazy_tenant():
    """Test deleting a lazy tenant."""

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")

        db = CinchDB(database="testdb", branch="main", project_dir=project_dir)

        # Create lazy tenant
        db.create_tenant("lazy-tenant", lazy=True)

        # Verify tenant exists in metadata
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            assert any(t['name'] == 'lazy-tenant' for t in tenants)

        # Delete tenant
        db.delete_tenant("lazy-tenant")

        # Tenant should be gone from metadata
        with MetadataDB(project_dir) as metadata_db:
            db_info = metadata_db.get_database("testdb")
            branches = metadata_db.list_branches(db_info['id'])
            main_branch = next(b for b in branches if b['name'] == 'main')
            tenants = metadata_db.list_tenants(main_branch['id'])
            assert not any(t['name'] == 'lazy-tenant' for t in tenants)

        # Tenant should not appear in list
        tenants = list_tenants(project_dir, "testdb", "main")
        assert "lazy-tenant" not in tenants

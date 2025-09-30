"""Tests for BOOLEAN type and case-insensitive types."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.base import ConnectionContext
from cinchdb.managers.table import TableManager
from cinchdb.models import Column
from cinchdb.core.database import CinchDB
from cinchdb.utils.type_utils import normalize_type


class TestBooleanType:
    """Test BOOLEAN type functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir

        # Clean up connection pool
        from cinchdb.infrastructure.metadata_connection_pool import MetadataConnectionPool
        MetadataConnectionPool.close_all()

        shutil.rmtree(temp)

    @pytest.fixture
    def table_manager(self, temp_project):
        """Create a TableManager instance."""
        return TableManager(ConnectionContext(project_root=temp_project, database="main", branch="main"))

    def test_boolean_column_creation(self, table_manager):
        """Test creating a table with BOOLEAN column."""
        table = table_manager.create_table("users", [
            Column(name="email", type="TEXT"),
            Column(name="active", type="BOOLEAN", nullable=False),
            Column(name="verified", type="BOOLEAN", nullable=True)
        ])

        # Verify columns
        assert len(table.columns) == 6  # 3 user + 3 system columns

        # Find boolean columns
        active_col = next(c for c in table.columns if c.name == "active")
        assert active_col.type == "BOOLEAN"
        assert active_col.nullable == False

        verified_col = next(c for c in table.columns if c.name == "verified")
        assert verified_col.type == "BOOLEAN"
        assert verified_col.nullable == True

    def test_case_insensitive_types(self, table_manager):
        """Test that types are case-insensitive."""
        # All these should work
        table = table_manager.create_table("test_table", [
            Column(name="col1", type="text"),      # lowercase
            Column(name="col2", type="INTEGER"),   # uppercase
            Column(name="col3", type="Real"),      # mixed case
            Column(name="col4", type="boolean"),   # lowercase boolean
            Column(name="col5", type="NUMERIC")    # uppercase
        ])

        # Verify all columns created successfully
        assert len(table.columns) == 8  # 5 user + 3 system columns

    def test_type_aliases(self, table_manager):
        """Test that type aliases work."""
        table = table_manager.create_table("alias_test", [
            Column(name="col1", type="int"),       # alias for INTEGER
            Column(name="col2", type="bool"),      # alias for BOOLEAN
            Column(name="col3", type="str"),       # alias for TEXT
            Column(name="col4", type="float"),     # alias for REAL
            Column(name="col5", type="varchar")    # alias for TEXT
        ])

        # Verify columns with canonical types
        col1 = next(c for c in table.columns if c.name == "col1")
        assert col1.type == "INTEGER"

        col2 = next(c for c in table.columns if c.name == "col2")
        assert col2.type == "BOOLEAN"

        col3 = next(c for c in table.columns if c.name == "col3")
        assert col3.type == "TEXT"

        col4 = next(c for c in table.columns if c.name == "col4")
        assert col4.type == "REAL"

        col5 = next(c for c in table.columns if c.name == "col5")
        assert col5.type == "TEXT"

    def test_normalize_type_function(self):
        """Test the normalize_type utility function."""
        # Standard types
        assert normalize_type("TEXT") == "TEXT"
        assert normalize_type("text") == "TEXT"
        assert normalize_type("Text") == "TEXT"

        # Aliases
        assert normalize_type("int") == "INTEGER"
        assert normalize_type("INT") == "INTEGER"
        assert normalize_type("bool") == "BOOLEAN"
        assert normalize_type("BOOL") == "BOOLEAN"
        assert normalize_type("float") == "REAL"
        assert normalize_type("double") == "REAL"
        assert normalize_type("str") == "TEXT"
        assert normalize_type("string") == "TEXT"
        assert normalize_type("varchar") == "TEXT"

        # Invalid type
        with pytest.raises(ValueError) as exc:
            normalize_type("invalid_type")
        assert "Invalid type" in str(exc.value)

    def test_get_table_detects_boolean(self, table_manager):
        """Test that get_table correctly detects BOOLEAN columns."""
        # Create table with BOOLEAN
        table_manager.create_table("test", [
            Column(name="flag", type="BOOLEAN")
        ])

        # Get table info
        table = table_manager.get_table("test")

        # Find boolean column
        flag_col = next(c for c in table.columns if c.name == "flag")
        assert flag_col.type == "BOOLEAN"  # Should detect from CHECK constraint
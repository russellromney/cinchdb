"""Tests for CDC table protection in table manager."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.managers.table import TableManager
from cinchdb.models import Column
from cinchdb.core.initializer import init_project


class TestCDCTableProtection:
    """Test that CDC tables are properly protected from user access."""
    
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
        """Create a table manager for testing."""
        return TableManager(temp_project, "main", "main", "main")
    
    def test_list_tables_excludes_cdc_tables(self, table_manager):
        """Test that list_tables() excludes CDC and system tables."""
        # Create some user tables
        user_columns = [Column(name="name", type="TEXT", nullable=False)]
        table_manager.create_table("users", user_columns)
        table_manager.create_table("orders", user_columns)
        
        # Manually create CDC tables in the database (simulating bdhcnic plugin)
        from cinchdb.core.connection import DatabaseConnection
        with DatabaseConnection(table_manager.db_path) as conn:
            # Create CDC tables
            conn.execute("""
                CREATE TABLE __cdc_log (
                    id INTEGER PRIMARY KEY,
                    operation TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE __cdc_metadata (
                    table_name TEXT PRIMARY KEY,
                    enabled BOOLEAN DEFAULT TRUE
                )
            """)
            conn.execute("""
                CREATE TABLE __tenant_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
        
        # List tables should only return user tables
        tables = table_manager.list_tables()
        table_names = [table.name for table in tables]
        
        # Should include user tables
        assert "users" in table_names
        assert "orders" in table_names
        
        # Should exclude CDC/system tables
        assert "__cdc_log" not in table_names
        assert "__cdc_metadata" not in table_names
        assert "__tenant_metadata" not in table_names
        
        # Should have exactly 2 user tables
        assert len(table_names) == 2
    
    def test_create_table_rejects_double_underscore_prefix(self, table_manager):
        """Test that creating tables with __ prefix is rejected."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # Should reject tables starting with __
        with pytest.raises(ValueError, match="Table name '__cdc_log' is not allowed"):
            table_manager.create_table("__cdc_log", columns)
        
        with pytest.raises(ValueError, match="Table name '__custom_system' is not allowed"):
            table_manager.create_table("__custom_system", columns)
        
        with pytest.raises(ValueError, match="reserved for system use"):
            table_manager.create_table("__test", columns)
    
    def test_create_table_rejects_sqlite_prefix(self, table_manager):
        """Test that creating tables with sqlite_ prefix is rejected."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # Should reject tables starting with sqlite_
        with pytest.raises(ValueError, match="Table name 'sqlite_master' is not allowed"):
            table_manager.create_table("sqlite_master", columns)
        
        with pytest.raises(ValueError, match="reserved for system use"):
            table_manager.create_table("sqlite_sequence", columns)
    
    def test_create_table_allows_normal_names(self, table_manager):
        """Test that normal table names are allowed."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # These should all work
        table_manager.create_table("users", columns)
        table_manager.create_table("orders", columns)
        table_manager.create_table("_private", columns)  # Single underscore is OK
        table_manager.create_table("test__table", columns)  # __ in middle is OK
        
        # Verify all tables were created
        tables = table_manager.list_tables()
        table_names = [table.name for table in tables]
        
        assert "users" in table_names
        assert "orders" in table_names
        assert "_private" in table_names
        assert "test__table" in table_names
        assert len(table_names) == 4
    
    def test_copy_table_rejects_double_underscore_target(self, table_manager):
        """Test that copying to tables with __ prefix is rejected."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # Create source table
        table_manager.create_table("source", columns)
        
        # Should reject target tables starting with __
        with pytest.raises(ValueError, match="Table name '__target' is not allowed"):
            table_manager.copy_table("source", "__target")
        
        with pytest.raises(ValueError, match="reserved for system use"):
            table_manager.copy_table("source", "__cdc_backup")
    
    def test_copy_table_rejects_sqlite_target(self, table_manager):
        """Test that copying to tables with sqlite_ prefix is rejected."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # Create source table
        table_manager.create_table("source", columns)
        
        # Should reject target tables starting with sqlite_
        with pytest.raises(ValueError, match="reserved for system use"):
            table_manager.copy_table("source", "sqlite_backup")
    
    def test_copy_table_allows_normal_target_names(self, table_manager):
        """Test that copying to normal table names works."""
        columns = [Column(name="data", type="TEXT", nullable=False)]
        
        # Create source table
        table_manager.create_table("source", columns)
        
        # These should all work
        copied_table = table_manager.copy_table("source", "target")
        assert copied_table.name == "target"
        
        table_manager.copy_table("source", "_backup")  # Single underscore OK
        table_manager.copy_table("source", "test__copy")  # __ in middle OK
        
        # Verify tables exist
        tables = table_manager.list_tables()
        table_names = [table.name for table in tables]
        
        assert "source" in table_names
        assert "target" in table_names
        assert "_backup" in table_names
        assert "test__copy" in table_names
        assert len(table_names) == 4


if __name__ == "__main__":
    pytest.main([__file__])
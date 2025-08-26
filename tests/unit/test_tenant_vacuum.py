"""Test that tenant creation properly vacuums the database."""

import tempfile
from pathlib import Path
import sqlite3
import pytest

from cinchdb.core.initializer import init_project
from cinchdb.managers.tenant import TenantManager
from cinchdb.core.connection import DatabaseConnection


def get_file_size_kb(path):
    """Get file size in KB."""
    return path.stat().st_size / 1024


def test_tenant_vacuum_reduces_size():
    """Test that vacuum properly reduces tenant database size after creation."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project with database
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        # Add tables and data to main tenant
        main_db_path = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / "main.db"
        
        with DatabaseConnection(main_db_path) as conn:
            # Create tables with data
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    email TEXT,
                    data TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    price REAL,
                    description TEXT
                )
            """)
            
            # Insert sample data
            for i in range(100):
                conn.execute(
                    "INSERT INTO users (name, email, data) VALUES (?, ?, ?)",
                    (f"User {i}", f"user{i}@example.com", "x" * 200)
                )
                conn.execute(
                    "INSERT INTO products (name, price, description) VALUES (?, ?, ?)",
                    (f"Product {i}", 10.0 + i, "y" * 200)
                )
            
            conn.commit()
        
        # Get size of main tenant with data
        main_size_with_data = get_file_size_kb(main_db_path)
        
        # Create new tenant
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        tenant_manager.create_tenant("test_tenant")
        
        # Check new tenant size
        new_tenant_path = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / "test_tenant.db"
        new_tenant_size = get_file_size_kb(new_tenant_path)
        
        # New tenant should be MUCH smaller (less than 25% of main with data)
        assert new_tenant_size < main_size_with_data * 0.25, \
            f"New tenant too large: {new_tenant_size:.2f} KB vs main: {main_size_with_data:.2f} KB"
        
        # New tenant should have empty tables
        conn = sqlite3.connect(str(new_tenant_path))
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        product_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        conn.close()
        
        assert user_count == 0, "Users table should be empty"
        assert product_count == 0, "Products table should be empty"
        
        # New tenant should be close to minimum size (8-12 KB for 2 empty tables)
        assert new_tenant_size <= 12, \
            f"New tenant larger than expected: {new_tenant_size:.2f} KB (should be <= 12 KB)"


def test_tenant_vacuum_with_indexes():
    """Test that vacuum works correctly with indexes."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        init_project(project_dir, database_name="testdb", branch_name="main")
        
        # Add tables with indexes to main tenant
        main_db_path = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / "main.db"
        
        with DatabaseConnection(main_db_path) as conn:
            conn.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email TEXT UNIQUE,
                    name TEXT
                )
            """)
            
            conn.execute("CREATE INDEX idx_users_name ON users(name)")
            
            # Add lots of data
            for i in range(500):
                conn.execute(
                    "INSERT INTO users (email, name) VALUES (?, ?)",
                    (f"user{i}@example.com", f"User {i}")
                )
            
            conn.commit()
        
        main_size = get_file_size_kb(main_db_path)
        
        # Create new tenant
        tenant_manager = TenantManager(project_dir, "testdb", "main")
        tenant_manager.create_tenant("indexed_tenant")
        
        # Check new tenant
        new_tenant_path = project_dir / ".cinchdb" / "databases" / "testdb" / "branches" / "main" / "tenants" / "indexed_tenant.db"
        new_tenant_size = get_file_size_kb(new_tenant_path)
        
        # Should be much smaller (less than 30% of original)
        assert new_tenant_size < main_size * 0.3, \
            f"New tenant with indexes too large: {new_tenant_size:.2f} KB vs main: {main_size:.2f} KB"
        
        # Verify index exists but table is empty
        conn = sqlite3.connect(str(new_tenant_path))
        
        # Check index exists
        indexes = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """).fetchall()
        assert len(indexes) > 0, "Indexes should be preserved"
        
        # Check table is empty
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        assert count == 0, "Table should be empty"
        
        conn.close()
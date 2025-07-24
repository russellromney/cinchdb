"""Tests for SQLite connection management."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.core.connection import DatabaseConnection, ConnectionPool


class TestDatabaseConnection:
    """Test database connection management."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        temp = tempfile.mkdtemp()
        db_path = Path(temp) / "test.db"
        yield db_path
        shutil.rmtree(temp)
    
    def test_connection_init(self, temp_db):
        """Test initializing a database connection."""
        conn = DatabaseConnection(temp_db)
        
        # Connection should be established
        assert conn.path == temp_db
        assert conn._conn is not None
        
        # Check WAL mode is enabled
        cursor = conn._conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"
        
        conn.close()
    
    def test_wal_configuration(self, temp_db):
        """Test WAL mode configuration."""
        conn = DatabaseConnection(temp_db)
        
        # Check all WAL-related settings
        cursor = conn._conn.execute("PRAGMA journal_mode")
        assert cursor.fetchone()[0] == "wal"
        
        cursor = conn._conn.execute("PRAGMA synchronous")
        assert cursor.fetchone()[0] == 1  # NORMAL mode
        
        cursor = conn._conn.execute("PRAGMA wal_autocheckpoint")
        assert cursor.fetchone()[0] == 0  # Disabled
        
        conn.close()
    
    def test_execute(self, temp_db):
        """Test executing SQL statements."""
        conn = DatabaseConnection(temp_db)
        
        # Create table
        conn.execute("""
            CREATE TABLE test (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # Insert data
        conn.execute("INSERT INTO test (id, name) VALUES (?, ?)", ("1", "Test"))
        
        # Query data
        result = conn.execute("SELECT * FROM test WHERE id = ?", ("1",))
        row = result.fetchone()
        assert row["id"] == "1"
        assert row["name"] == "Test"
        
        conn.close()
    
    def test_transaction(self, temp_db):
        """Test transaction management."""
        conn = DatabaseConnection(temp_db)
        
        # Create table
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        
        # Successful transaction
        with conn.transaction():
            conn.execute("INSERT INTO test (value) VALUES (?)", ("test1",))
            conn.execute("INSERT INTO test (value) VALUES (?)", ("test2",))
        
        result = conn.execute("SELECT COUNT(*) as count FROM test")
        assert result.fetchone()["count"] == 2
        
        # Failed transaction should rollback
        try:
            with conn.transaction():
                conn.execute("INSERT INTO test (value) VALUES (?)", ("test3",))
                raise Exception("Test error")
        except Exception:
            pass
        
        result = conn.execute("SELECT COUNT(*) as count FROM test")
        assert result.fetchone()["count"] == 2  # Still 2, not 3
        
        conn.close()
    
    def test_row_factory(self, temp_db):
        """Test that rows are returned as dictionaries."""
        conn = DatabaseConnection(temp_db)
        
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'Test')")
        
        result = conn.execute("SELECT * FROM test")
        row = result.fetchone()
        
        # Should be dict-like
        assert row["id"] == 1
        assert row["name"] == "Test"
        assert list(row.keys()) == ["id", "name"]
        
        conn.close()
    
    def test_context_manager(self, temp_db):
        """Test using connection as context manager."""
        with DatabaseConnection(temp_db) as conn:
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.execute("INSERT INTO test VALUES (1)")
            conn.commit()
        
        # Connection should be closed
        assert conn._conn is None
        
        # But database should still exist with data
        with DatabaseConnection(temp_db) as conn:
            result = conn.execute("SELECT * FROM test")
            assert result.fetchone()["id"] == 1


class TestConnectionPool:
    """Test connection pooling."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)
    
    def test_pool_get_connection(self, temp_dir):
        """Test getting connections from pool."""
        pool = ConnectionPool()
        
        db1 = temp_dir / "db1.db"
        db2 = temp_dir / "db2.db"
        
        # Get connections
        conn1 = pool.get_connection(db1)
        conn2 = pool.get_connection(db2)
        
        assert conn1.path == db1.resolve()
        assert conn2.path == db2.resolve()
        assert conn1 != conn2
        
        # Same path should return same connection
        conn1_again = pool.get_connection(db1)
        assert conn1 is conn1_again
        
        pool.close_all()
    
    def test_pool_close_all(self, temp_dir):
        """Test closing all connections."""
        pool = ConnectionPool()
        
        # Create some connections
        for i in range(3):
            db = temp_dir / f"db{i}.db"
            conn = pool.get_connection(db)
            conn.execute("CREATE TABLE test (id INTEGER)")
        
        # Close all
        pool.close_all()
        
        # Pool should be empty
        assert len(pool._connections) == 0
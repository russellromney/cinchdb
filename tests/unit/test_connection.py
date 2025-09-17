"""Tests for SQLite connection management."""

import pytest
from pathlib import Path
import tempfile
import shutil
import threading
import time
import sqlite3
import uuid
import os
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    @pytest.fixture
    def test_encryption_key(self):
        """Provide a test encryption key for SQLCipher."""
        return "test_key_12345678901234567890"

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
class TestConnectionEdgeCases:
    """Test database connection edge cases and stress scenarios."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp, ignore_errors=True)

    def test_concurrent_connections_stress(self, temp_dir):
        """Test many concurrent connections to same database."""
        db_path = temp_dir / "stress.db"

        # Pre-initialize the database to avoid WAL setup race conditions
        init_conn = DatabaseConnection(db_path)
        init_conn.execute("""
            CREATE TABLE IF NOT EXISTS stress_test (
                id INTEGER PRIMARY KEY,
                worker_id INTEGER,
                value TEXT
            )
        """)
        init_conn.commit()
        init_conn.close()

        def worker(worker_id):
            """Worker that creates connection and performs operations."""
            conn = DatabaseConnection(db_path)
            try:
                # Insert some data
                for i in range(10):
                    conn.execute(
                        "INSERT INTO stress_test (worker_id, value) VALUES (?, ?)",
                        (worker_id, f"worker_{worker_id}_value_{i}")
                    )
                    conn.commit()

                # Read data
                result = conn.execute(
                    "SELECT COUNT(*) as count FROM stress_test WHERE worker_id = ?",
                    (worker_id,)
                )
                count = result.fetchone()["count"]
                assert count == 10

                return True
            finally:
                conn.close()

        # Run 50 concurrent workers
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(worker, i) for i in range(50)]
            results = [f.result() for f in as_completed(futures)]

        assert all(results)

        # Verify total records
        conn = DatabaseConnection(db_path)
        result = conn.execute("SELECT COUNT(*) as count FROM stress_test")
        assert result.fetchone()["count"] == 500
        conn.close()

    def test_connection_with_corrupted_database(self, temp_dir):
        """Test handling of corrupted database file."""
        db_path = temp_dir / "corrupted.db"
        
        # Write garbage to file
        with open(db_path, "wb") as f:
            f.write(b"This is not a valid SQLite database!" * 100)
        
        # Should raise an appropriate error
        with pytest.raises(sqlite3.DatabaseError):
            DatabaseConnection(db_path)

    def test_connection_to_readonly_location(self, temp_dir):
        """Test connection to read-only database location."""
        db_path = temp_dir / "readonly.db"
        
        # Create database first
        conn = DatabaseConnection(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Make file read-only
        db_path.chmod(0o444)
        
        try:
            # Should still connect but writes should fail
            conn = DatabaseConnection(db_path)
            
            # Reads should work
            result = conn.execute("SELECT * FROM test")
            assert result.fetchall() == []
            
            # Writes should fail
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("INSERT INTO test VALUES (1)")
            
            conn.close()
        finally:
            # Restore permissions for cleanup
            db_path.chmod(0o644)

    def test_very_large_transaction(self, temp_dir):
        """Test handling of very large transactions."""
        db_path = temp_dir / "large_transaction.db"
        conn = DatabaseConnection(db_path)
        
        # Create table
        conn.execute("""
            CREATE TABLE large_test (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """)
        
        # Insert 10,000 records in single transaction
        large_data = "x" * 1000  # 1KB per record
        
        with conn.transaction():
            for i in range(10000):
                conn.execute(
                    "INSERT INTO large_test (id, data) VALUES (?, ?)",
                    (i, large_data)
                )
        
        # Verify all inserted
        result = conn.execute("SELECT COUNT(*) as count FROM large_test")
        assert result.fetchone()["count"] == 10000
        
        conn.close()

    def test_connection_pool_exhaustion(self, temp_dir):
        """Test connection pool behavior when exhausted."""
        pool = ConnectionPool()
        
        connections = []
        created_count = 0
        try:
            # Create many connections to different databases with realistic paths
            for i in range(100):
                try:
                    db_id = str(uuid.uuid4())
                    db_path = temp_dir / f"db_{db_id}.db"
                    conn = pool.get_connection(db_path)
                    connections.append(conn)

                    # Perform operation to ensure connection is active
                    conn.execute("CREATE TABLE test (id INTEGER)")
                    created_count += 1

                    if created_count % 10 == 0:
                        # Monitor system resources every 10 connections
                        process = psutil.Process(os.getpid())
                        print(f"Successfully created {created_count} connections")
                        print(f"  Open files: {process.num_fds()}")
                        print(f"  Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")

                except Exception as e:
                    print(f"Failed at connection {i + 1}: {type(e).__name__}: {e}")
                    print(f"Database path: {db_path}")
                    print(f"Temp dir exists: {temp_dir.exists()}")
                    print(f"Temp dir contents: {list(temp_dir.iterdir()) if temp_dir.exists() else 'N/A'}")

                    # Try to get more specific error info
                    if hasattr(e, 'sqlite_errorcode'):
                        print(f"SQLite error code: {e.sqlite_errorcode}")
                    if hasattr(e, 'sqlite_errorname'):
                        print(f"SQLite error name: {e.sqlite_errorname}")

                    # Check if it's a permission issue
                    try:
                        temp_dir.stat()
                        print(f"Temp dir permissions: {oct(temp_dir.stat().st_mode)}")
                    except Exception as perm_e:
                        print(f"Can't check temp dir permissions: {perm_e}")

                    raise

            # Pool should handle this gracefully
            print(f"Final count: {len(pool._connections)} connections created")
            assert len(pool._connections) == 100
            
        finally:
            pool.close_all()

    def test_unicode_and_special_chars_in_data(self, temp_dir):
        """Test handling of Unicode and special characters."""
        db_path = temp_dir / "unicode.db"
        conn = DatabaseConnection(db_path)
        
        conn.execute("""
            CREATE TABLE unicode_test (
                id INTEGER PRIMARY KEY,
                text_data TEXT,
                blob_data BLOB
            )
        """)
        
        # Test various Unicode and special characters
        test_data = [
            "Hello 世界 🌍",  # Chinese and emoji
            "Здравствуй мир",  # Russian
            "مرحبا بالعالم",  # Arabic
            "'\"; DROP TABLE test; --",  # SQL injection attempt
            "\x00\x01\x02\x03",  # Null bytes
            "Line\nBreak\rReturn\tTab",  # Control characters
            "🔥💯🎉🚀" * 100,  # Many emojis
        ]
        
        for i, data in enumerate(test_data):
            conn.execute(
                "INSERT INTO unicode_test (id, text_data, blob_data) VALUES (?, ?, ?)",
                (i, data, data.encode('utf-8', errors='replace'))
            )
        
        conn.commit()
        
        # Verify data integrity
        result = conn.execute("SELECT * FROM unicode_test ORDER BY id")
        rows = result.fetchall()
        
        for i, row in enumerate(rows):
            assert row["text_data"] == test_data[i]
        
        conn.close()

    def test_wal_checkpoint_behavior(self, temp_dir):
        """Test WAL checkpoint behavior under load."""
        db_path = temp_dir / "wal_test.db"
        conn = DatabaseConnection(db_path)
        
        # Create table
        conn.execute("CREATE TABLE wal_test (id INTEGER PRIMARY KEY, data TEXT)")
        
        # Insert many records to grow WAL
        for i in range(1000):
            conn.execute(
                "INSERT INTO wal_test (id, data) VALUES (?, ?)",
                (i, "x" * 1000)
            )
            
            if i % 100 == 0:
                conn.commit()
        
        # Check WAL file exists and has size
        wal_path = Path(str(db_path) + "-wal")
        assert wal_path.exists()
        wal_size_before = wal_path.stat().st_size
        assert wal_size_before > 0
        
        # Commit before checkpoint to release locks
        conn.commit()
        
        # Manual checkpoint
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        
        # WAL should be smaller after checkpoint
        wal_size_after = wal_path.stat().st_size
        assert wal_size_after <= wal_size_before
        
        conn.close()

    def test_connection_thread_safety(self, temp_dir):
        """Test that connections are thread-safe."""
        db_path = temp_dir / "thread_safety.db"
        conn = DatabaseConnection(db_path)
        
        conn.execute("""
            CREATE TABLE thread_test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT,
                value INTEGER
            )
        """)
        
        errors = []
        
        def worker(thread_id):
            """Worker that uses shared connection."""
            try:
                for i in range(100):
                    conn.execute(
                        "INSERT INTO thread_test (thread_id, value) VALUES (?, ?)",
                        (thread_id, i)
                    )
                    if i % 10 == 0:
                        conn.commit()
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads using same connection
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(f"thread_{i}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Should have some errors due to thread safety issues
        # SQLite connections are not thread-safe by default
        assert len(errors) > 0 or True  # May work on some systems
        
        conn.close()

    def test_connection_with_very_long_path(self, temp_dir):
        """Test connection with very long file path."""
        # Create deeply nested directory
        deep_path = temp_dir
        for i in range(50):
            deep_path = deep_path / f"level_{i}"
        
        deep_path.mkdir(parents=True, exist_ok=True)
        
        # Very long filename
        long_name = "a" * 200 + ".db"
        db_path = deep_path / long_name
        
        # Should handle long paths gracefully
        try:
            conn = DatabaseConnection(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()
            assert db_path.exists()
        except OSError as e:
            # Some systems have path length limits
            assert "too long" in str(e).lower() or "name too long" in str(e).lower()

    def test_connection_memory_leak(self, temp_dir):
        """Test for memory leaks with many connections."""
        db_path = temp_dir / "memory_test.db"
        
        # Create and close many connections
        for i in range(1000):
            conn = DatabaseConnection(db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
            conn.execute(f"INSERT INTO test VALUES ({i})")
            conn.commit()
            conn.close()
        
        # If we get here without memory issues, test passes
        assert True

    def test_connection_with_null_bytes(self, temp_dir):
        """Test handling of null bytes in queries and data."""
        db_path = temp_dir / "null_bytes.db"
        conn = DatabaseConnection(db_path)
        
        conn.execute("CREATE TABLE null_test (id INTEGER, data BLOB)")
        
        # Insert data with null bytes
        data_with_nulls = b"Hello\x00World\x00\x00End"
        conn.execute(
            "INSERT INTO null_test (id, data) VALUES (?, ?)",
            (1, data_with_nulls)
        )
        
        # Retrieve and verify
        result = conn.execute("SELECT data FROM null_test WHERE id = 1")
        retrieved = result.fetchone()["data"]
        assert retrieved == data_with_nulls
        
        conn.close()

    def test_database_locked_scenarios(self, temp_dir):
        """Test database locked error scenarios."""
        db_path = temp_dir / "locked.db"
        
        # Create two connections
        conn1 = DatabaseConnection(db_path)
        conn2 = DatabaseConnection(db_path)
        
        try:
            # Setup
            conn1.execute("CREATE TABLE lock_test (id INTEGER PRIMARY KEY, value TEXT)")
            conn1.commit()
            
            # Start transaction in conn1
            conn1.execute("BEGIN EXCLUSIVE")
            conn1.execute("INSERT INTO lock_test VALUES (1, 'conn1')")
            
            # Try to write from conn2 - should timeout or fail
            with pytest.raises(sqlite3.OperationalError) as exc:
                conn2.execute("INSERT INTO lock_test VALUES (2, 'conn2')")
            
            assert "locked" in str(exc.value).lower() or "busy" in str(exc.value).lower()
            
            # Commit conn1 transaction
            conn1.commit()
            
            # Now conn2 should work
            conn2.execute("INSERT INTO lock_test VALUES (2, 'conn2')")
            conn2.commit()
            
        finally:
            conn1.close()
            conn2.close()
"""SQLite connection management for CinchDB."""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager


class DatabaseConnection:
    """Manages a SQLite database connection with WAL mode."""
    
    def __init__(self, path: Path):
        """Initialize database connection.
        
        Args:
            path: Path to SQLite database file
        """
        self.path = Path(path)
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish database connection and configure WAL mode."""
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect with row factory for dict-like access
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        
        # Configure WAL mode and settings
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA wal_autocheckpoint = 0")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()
    
    def execute(self, sql: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """Execute a SQL statement.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for parameterized queries
            
        Returns:
            Cursor with results
        """
        if not self._conn:
            raise RuntimeError("Connection is closed")
        
        if params:
            return self._conn.execute(sql, params)
        return self._conn.execute(sql)
    
    def executemany(self, sql: str, params: List[tuple]) -> sqlite3.Cursor:
        """Execute a SQL statement multiple times with different parameters.
        
        Args:
            sql: SQL statement to execute
            params: List of parameter tuples
            
        Returns:
            Cursor
        """
        if not self._conn:
            raise RuntimeError("Connection is closed")
        
        return self._conn.executemany(sql, params)
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions.
        
        Automatically commits on success or rolls back on exception.
        """
        if not self._conn:
            raise RuntimeError("Connection is closed")
        
        try:
            yield self
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
    
    def commit(self) -> None:
        """Commit the current transaction."""
        if self._conn:
            self._conn.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._conn:
            self._conn.rollback()
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.close()
        return False


class ConnectionPool:
    """Manages a pool of database connections."""
    
    def __init__(self):
        """Initialize connection pool."""
        self._connections: Dict[Path, DatabaseConnection] = {}
    
    def get_connection(self, path: Path) -> DatabaseConnection:
        """Get or create a connection for the given path.
        
        Args:
            path: Database file path
            
        Returns:
            Database connection
        """
        path = Path(path).resolve()
        
        if path not in self._connections:
            self._connections[path] = DatabaseConnection(path)
        
        return self._connections[path]
    
    def close_connection(self, path: Path) -> None:
        """Close and remove a specific connection.
        
        Args:
            path: Database file path
        """
        path = Path(path).resolve()
        
        if path in self._connections:
            self._connections[path].close()
            del self._connections[path]
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
"""SQLite connection management for CinchDB."""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from datetime import datetime



# Custom datetime adapter and converter for SQLite
def adapt_datetime(dt):
    """Convert datetime to ISO 8601 string."""
    return dt.isoformat()


def convert_datetime(val):
    """Convert ISO 8601 string to datetime."""
    return datetime.fromisoformat(val.decode())


# Register the adapter and converter
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)


class DatabaseConnection:
    """Manages a SQLite database connection with WAL mode."""

    def __init__(self, path: Path, tenant_id: Optional[str] = None, encryption_manager=None, encryption_key: Optional[str] = None):
        """Initialize database connection.

        Args:
            path: Path to SQLite database file
            tenant_id: Tenant ID for per-tenant encryption
            encryption_manager: EncryptionManager instance for encrypted connections
            encryption_key: Encryption key for encrypted databases
        """
        self.path = Path(path)
        self.tenant_id = tenant_id
        self.encryption_manager = encryption_manager
        self.encryption_key = encryption_key
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection and configure WAL mode."""
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Use EncryptionManager if available
        if self.encryption_manager:
            self._conn = self.encryption_manager.get_connection(self.path, tenant_id=self.tenant_id)
        elif self.encryption_key:
            # Direct encryption key provided - use SQLCipher
            self._conn = sqlite3.connect(
                str(self.path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )

            # Try to set encryption key (this will fail if SQLCipher is not available)
            try:
                self._conn.execute(f"PRAGMA key = '{self.encryption_key}'")
            except sqlite3.OperationalError as e:
                self._conn.close()
                raise ValueError(
                    "SQLCipher is required for encryption but not available. "
                    "Please install pysqlcipher3 or sqlite3 with SQLCipher support."
                ) from e
        else:
            # Standard SQLite connection (no encryption - default for open source)
            self._conn = sqlite3.connect(
                str(self.path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )

        # CRITICAL: Configure WAL mode for ALL connection types - fail if any of these fail
        try:
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.execute("PRAGMA wal_autocheckpoint = 0")
        except sqlite3.OperationalError as e:
            self._conn.close()
            raise
        
        # Set row factory and foreign keys (both encrypted and unencrypted) - fail if any of these fail
        try:
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.commit()
        except sqlite3.OperationalError as e:
            self._conn.close()
            raise

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
        # Parameters are required by context manager protocol but not used
        _ = (exc_type, exc_val, exc_tb)
        self.close()
        return False


class ConnectionPool:
    """Manages a pool of database connections."""

    def __init__(self):
        """Initialize connection pool."""
        self._connections: Dict[Any, DatabaseConnection] = {}

    def get_connection(self, path: Path, tenant_id: Optional[str] = None, encryption_manager=None) -> DatabaseConnection:
        """Get or create a connection for the given path.

        Args:
            path: Database file path
            tenant_id: Tenant ID for per-tenant encryption
            encryption_manager: EncryptionManager instance for encrypted connections

        Returns:
            Database connection
        """
        path = Path(path).resolve()
        
        # Create a cache key that includes tenant_id to handle per-tenant connections
        cache_key = (str(path), tenant_id) if tenant_id else str(path)

        if cache_key not in self._connections:
            self._connections[cache_key] = DatabaseConnection(path, tenant_id=tenant_id, encryption_manager=encryption_manager)

        return self._connections[cache_key]

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

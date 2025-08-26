"""Connection pool for MetadataDB to ensure efficient connection reuse."""

import threading
from pathlib import Path
from typing import Optional, Dict

from cinchdb.infrastructure.metadata_db import MetadataDB


class MetadataConnectionPool:
    """Thread-safe, lazy-initialized connection pool for MetadataDB.
    
    Uses a singleton pattern per project directory to ensure connection reuse
    across all managers and operations within a project.
    """
    
    _instances: Dict[str, 'MetadataConnectionPool'] = {}
    _lock = threading.Lock()
    
    def __init__(self, project_path: Path):
        """Initialize the connection pool (but don't create connection yet).
        
        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path)
        self._connection: Optional[MetadataDB] = None
        self._connection_lock = threading.Lock()
        self._ref_count = 0
        
    @classmethod
    def get_instance(cls, project_path: Path) -> 'MetadataConnectionPool':
        """Get or create a connection pool for the given project.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            MetadataConnectionPool instance for this project
        """
        path_str = str(project_path.resolve())
        
        # Fast path - check if instance exists
        if path_str in cls._instances:
            return cls._instances[path_str]
        
        # Slow path - create new instance with lock
        with cls._lock:
            # Double-check pattern
            if path_str not in cls._instances:
                cls._instances[path_str] = cls(project_path)
            return cls._instances[path_str]
    
    def get_connection(self) -> MetadataDB:
        """Get or create a MetadataDB connection (lazy initialization).
        
        Returns:
            MetadataDB instance (shared across all callers for this project)
        """
        # Fast path - connection already exists
        if self._connection is not None:
            return self._connection
        
        # Slow path - create connection with lock
        with self._connection_lock:
            # Double-check pattern
            if self._connection is None:
                self._connection = MetadataDB(self.project_path)
            return self._connection
    
    def acquire(self) -> MetadataDB:
        """Acquire a reference to the connection.
        
        Returns:
            MetadataDB instance
        """
        with self._connection_lock:
            self._ref_count += 1
            return self.get_connection()
    
    def release(self) -> None:
        """Release a reference to the connection.
        
        When ref count reaches 0, we could close the connection,
        but we keep it open for performance since SQLite handles
        concurrent access well with WAL mode.
        """
        with self._connection_lock:
            self._ref_count = max(0, self._ref_count - 1)
    
    def close(self) -> None:
        """Explicitly close the connection (called on shutdown)."""
        with self._connection_lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None
                self._ref_count = 0
    
    @classmethod
    def close_all(cls) -> None:
        """Close all connection pools (useful for cleanup in tests)."""
        with cls._lock:
            for pool in cls._instances.values():
                pool.close()
            cls._instances.clear()


class MetadataDBHandle:
    """Context manager for safely acquiring and releasing metadata connections."""
    
    def __init__(self, project_path: Path):
        """Initialize handle for metadata connection.
        
        Args:
            project_path: Path to the project directory
        """
        self.pool = MetadataConnectionPool.get_instance(project_path)
        self.connection: Optional[MetadataDB] = None
    
    def __enter__(self) -> MetadataDB:
        """Acquire connection from pool."""
        self.connection = self.pool.acquire()
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release connection back to pool."""
        self.pool.release()
        self.connection = None


def get_metadata_db(project_path: Path) -> MetadataDB:
    """Get a metadata database connection from the pool.
    
    This is a convenience function for code that doesn't use context managers.
    The connection is shared and should NOT be closed by the caller.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        MetadataDB instance (shared, do not close)
    """
    pool = MetadataConnectionPool.get_instance(project_path)
    return pool.get_connection()
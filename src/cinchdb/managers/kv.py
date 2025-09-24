"""Key-Value store manager for CinchDB - provides fast unstructured data storage with TTL support."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.managers.tenant import TenantManager


class KVManager:
    """Key-Value store manager for CinchDB.

    Provides fast unstructured data storage with TTL support and native type handling.
    Supports text, numbers, binary data, JSON objects, and null values.
    """

    def __init__(
        self,
        project_root: Path,
        database: str,
        branch: str,
        tenant: str = "main",
        encryption_manager=None
    ):
        """Initialize KV manager.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
            tenant: Tenant name (default: main)
            encryption_manager: EncryptionManager instance for encrypted connections
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.encryption_manager = encryption_manager
        self.db_path = get_tenant_db_path(project_root, database, branch, tenant)
        self.tenant_manager = TenantManager(project_root, database, branch, encryption_manager)

    def _is_tenant_materialized(self) -> bool:
        """Check if the tenant is materialized (has actual database file)."""
        return not self.tenant_manager.is_tenant_lazy(self.tenant)

    def _ensure_tenant_materialized(self) -> None:
        """Ensure tenant is materialized for write operations."""
        if not self._is_tenant_materialized():
            if self.tenant == "main":
                # Main tenant should always exist, but might need materialization
                self.tenant_manager.materialize_tenant(self.tenant)
            else:
                # Create lazy tenant first if it doesn't exist, then materialize
                try:
                    self.tenant_manager.create_tenant(self.tenant, lazy=True)
                except ValueError:
                    # Tenant already exists, just materialize it
                    pass
                self.tenant_manager.materialize_tenant(self.tenant)

    def _ensure_kv_table(self, conn: DatabaseConnection) -> None:
        """Ensure the __kv table exists with the multi-type schema."""
        # Check if table exists
        result = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='__kv'
        """).fetchone()

        if not result:
            # Create the multi-type KV table
            conn.execute("""
                CREATE TABLE __kv (
                    key TEXT PRIMARY KEY,
                    value_type TEXT NOT NULL CHECK (value_type IN ('text', 'number', 'boolean', 'blob', 'json', 'null')),
                    value_text TEXT,
                    value_number REAL,
                    value_bool BOOLEAN,
                    value_blob BLOB,
                    value_json TEXT,
                    value_size INTEGER,
                    expires_at INTEGER,
                    created_at INTEGER DEFAULT (unixepoch()),
                    updated_at INTEGER DEFAULT (unixepoch()),

                    -- Ensure only one value column is populated (or none for null)
                    CHECK (
                        (CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN value_number IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN value_blob IS NOT NULL THEN 1 ELSE 0 END +
                         CASE WHEN value_json IS NOT NULL THEN 1 ELSE 0 END) <= 1
                    ),

                    -- Ensure type matches populated column
                    CHECK (
                        (value_type = 'text' AND value_text IS NOT NULL AND value_number IS NULL AND value_bool IS NULL AND value_blob IS NULL AND value_json IS NULL) OR
                        (value_type = 'number' AND value_number IS NOT NULL AND value_text IS NULL AND value_bool IS NULL AND value_blob IS NULL AND value_json IS NULL) OR
                        (value_type = 'boolean' AND value_bool IS NOT NULL AND value_text IS NULL AND value_number IS NULL AND value_blob IS NULL AND value_json IS NULL) OR
                        (value_type = 'blob' AND value_blob IS NOT NULL AND value_text IS NULL AND value_number IS NULL AND value_bool IS NULL AND value_json IS NULL) OR
                        (value_type = 'json' AND value_json IS NOT NULL AND value_text IS NULL AND value_number IS NULL AND value_bool IS NULL AND value_blob IS NULL) OR
                        (value_type = 'null' AND value_text IS NULL AND value_number IS NULL AND value_bool IS NULL AND value_blob IS NULL AND value_json IS NULL)
                    )
                )
            """)

            # Create index for expiry cleanup
            conn.execute("""
                CREATE INDEX __kv_expires_at ON __kv(expires_at)
                WHERE expires_at IS NOT NULL
            """)

            conn.commit()

    def _glob_to_like(self, pattern: str) -> str:
        """Convert Redis glob pattern to SQL LIKE pattern.

        Args:
            pattern: Redis-style pattern with * and ?

        Returns:
            SQL LIKE pattern with % and _
        """
        # Escape SQL special chars first, then convert glob to LIKE
        pattern = pattern.replace('%', r'\%').replace('_', r'\_')
        pattern = pattern.replace('*', '%').replace('?', '_')
        return pattern

    def _validate_key(self, key: Any) -> None:
        """Validate key format and constraints.

        Args:
            key: The key to validate

        Raises:
            ValueError: If key is invalid
        """
        # Must be a string
        if not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        # Must not be empty
        if not key:
            raise ValueError("Key must be a non-empty string")

        # Must not exceed 255 characters
        if len(key) > 255:
            raise ValueError(f"Key length cannot exceed 255 characters (got {len(key)})")

        # Allow a broader set of characters common in KV stores (including Redis)
        # Following Redis patterns - very permissive
        # Disallow only: control characters, null bytes, newlines, tabs
        import re

        # Check for control characters and problematic whitespace
        if '\n' in key or '\r' in key or '\t' in key or '\0' in key:
            raise ValueError(
                "Key cannot contain newlines, tabs, or null bytes"
            )

        # Check if key contains only printable characters (including spaces)
        # This is more permissive, similar to Redis
        if not all(c.isprintable() for c in key):
            raise ValueError(
                "Key must contain only printable characters"
            )

        # Additional safety checks
        if key.startswith('__'):
            raise ValueError(
                "Keys cannot start with '__' (reserved for system use)"
            )

    def _detect_type_and_value(self, value: Any) -> tuple[str, dict]:
        """Detect value type and prepare for storage.

        Returns:
            (value_type, {column: value})
        """
        if value is None:
            return 'null', {}
        elif isinstance(value, bool):
            # Check bool before number to avoid treating as int
            return 'boolean', {'value_bool': value}
        elif isinstance(value, int):
            return 'number', {'value_number': float(value)}
        elif isinstance(value, float):
            return 'number', {'value_number': value}
        elif isinstance(value, str):
            return 'text', {'value_text': value}
        elif isinstance(value, bytes):
            return 'blob', {'value_blob': value}
        else:
            # Everything else as JSON (list, dict, tuple, etc)
            try:
                json_str = json.dumps(value)
                return 'json', {'value_json': json_str}
            except (TypeError, ValueError) as e:
                raise ValueError(f"Value is not JSON serializable: {e}")

    def _calculate_value_size(self, value: Any) -> int:
        """Calculate size of value in bytes."""
        if value is None:
            return 0
        elif isinstance(value, bytes):
            return len(value)
        elif isinstance(value, (int, float, bool)):
            return len(str(value).encode('utf-8'))
        elif isinstance(value, str):
            return len(value.encode('utf-8'))
        else:
            # JSON types
            return len(json.dumps(value).encode('utf-8'))

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a key-value pair with optional TTL.

        Args:
            key: Key to set
            value: Value to store (any type)
            ttl: Time-to-live in seconds (can be fractional, None for no expiry)

        Raises:
            ValueError: If key is empty or invalid
        """
        self._validate_key(key)

        expires_at = None
        if ttl is not None:
            if ttl <= 0:
                raise ValueError("TTL must be positive")
            expires_at = time.time() + ttl

        # Detect type and prepare value
        value_type, value_dict = self._detect_type_and_value(value)
        value_size = self._calculate_value_size(value)

        # Ensure tenant is materialized for write operation
        self._ensure_tenant_materialized()

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            # Build the INSERT/UPDATE based on type
            if value_type == 'null':
                # NULL type: no value columns
                sql = """
                    INSERT INTO __kv (key, value_type, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = NULL,
                        value_number = NULL,
                        value_bool = NULL,
                        value_blob = NULL,
                        value_json = NULL,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_size, expires_at])
                conn.commit()

            elif value_type == 'text':
                sql = """
                    INSERT INTO __kv (key, value_type, value_text, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = excluded.value_text,
                        value_number = NULL,
                        value_bool = NULL,
                        value_blob = NULL,
                        value_json = NULL,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_dict['value_text'], value_size, expires_at])
                conn.commit()

            elif value_type == 'number':
                sql = """
                    INSERT INTO __kv (key, value_type, value_number, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = NULL,
                        value_number = excluded.value_number,
                        value_bool = NULL,
                        value_blob = NULL,
                        value_json = NULL,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_dict['value_number'], value_size, expires_at])
                conn.commit()

            elif value_type == 'blob':
                sql = """
                    INSERT INTO __kv (key, value_type, value_blob, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = NULL,
                        value_number = NULL,
                        value_bool = NULL,
                        value_blob = excluded.value_blob,
                        value_json = NULL,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_dict['value_blob'], value_size, expires_at])
                conn.commit()

            elif value_type == 'boolean':
                sql = """
                    INSERT INTO __kv (key, value_type, value_bool, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = NULL,
                        value_number = NULL,
                        value_bool = excluded.value_bool,
                        value_blob = NULL,
                        value_json = NULL,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_dict['value_bool'], value_size, expires_at])
                conn.commit()

            elif value_type == 'json':
                sql = """
                    INSERT INTO __kv (key, value_type, value_json, value_size, expires_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, unixepoch())
                    ON CONFLICT(key) DO UPDATE SET
                        value_type = excluded.value_type,
                        value_text = NULL,
                        value_number = NULL,
                        value_bool = NULL,
                        value_blob = NULL,
                        value_json = excluded.value_json,
                        value_size = excluded.value_size,
                        expires_at = excluded.expires_at,
                        updated_at = unixepoch()
                """
                conn.execute(sql, [key, value_type, value_dict['value_json'], value_size, expires_at])
                conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """Get value by key, automatically excluding expired entries.

        Args:
            key: Key to retrieve

        Returns:
            Original value or None if key doesn't exist or is expired
        """
        if not key or not isinstance(key, str):
            return None

        # If tenant is not materialized, key doesn't exist
        if not self._is_tenant_materialized():
            return None

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute("""
                SELECT value_type, value_text, value_number, value_bool, value_blob, value_json
                FROM __kv
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [key]).fetchone()

            if not result:
                return None

            value_type = result['value_type']

            if value_type == 'null':
                return None
            elif value_type == 'text':
                return result['value_text']
            elif value_type == 'number':
                num = result['value_number']
                # Try to preserve int vs float
                if num == int(num):
                    return int(num)
                return num
            elif value_type == 'boolean':
                return bool(result['value_bool'])
            elif value_type == 'blob':
                return result['value_blob']
            elif value_type == 'json':
                return json.loads(result['value_json'])

            return None

    def delete(self, *keys) -> int:
        """Delete one or more keys.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys that were deleted
        """
        if not keys:
            return 0

        # Flatten any nested lists/tuples and validate keys
        valid_keys = []
        for key in keys:
            if isinstance(key, (list, tuple)):
                for k in key:
                    self._validate_key(k)
                    valid_keys.append(k)
            else:
                self._validate_key(key)
                valid_keys.append(key)

        if not valid_keys:
            return 0

        # If tenant is not materialized, no keys to delete
        if not self._is_tenant_materialized():
            return 0

        deleted_count = 0

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            for key in valid_keys:
                result = conn.execute("DELETE FROM __kv WHERE key = ?", [key])
                deleted_count += result.rowcount

            conn.commit()

        return deleted_count

    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired.

        Args:
            key: Key to check

        Returns:
            True if key exists and is not expired
        """
        if not key or not isinstance(key, str):
            return False

        # If tenant is not materialized, key doesn't exist
        if not self._is_tenant_materialized():
            return False

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute("""
                SELECT 1 FROM __kv
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [key]).fetchone()

            return result is not None

    def setnx(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Set key only if it doesn't exist (SET if Not eXists).

        Args:
            key: Key to set
            value: Value to store
            ttl: Optional TTL in seconds

        Returns:
            True if key was set, False if key already existed
        """
        self._validate_key(key)

        expires_at = None
        if ttl is not None:
            if ttl <= 0:
                raise ValueError("TTL must be positive")
            expires_at = time.time() + ttl

        # Detect type and prepare value
        value_type, value_dict = self._detect_type_and_value(value)
        value_size = self._calculate_value_size(value)

        # Ensure tenant is materialized for write operation
        self._ensure_tenant_materialized()

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            # First, check if key exists and is not expired
            existing = conn.execute("""
                SELECT 1 FROM __kv
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [key]).fetchone()

            if existing:
                return False

            # Delete expired key if it exists
            conn.execute("""
                DELETE FROM __kv
                WHERE key = ?
                AND expires_at IS NOT NULL
                AND expires_at <= ((julianday('now') - 2440587.5) * 86400.0)
            """, [key])

            try:
                # Use type-specific INSERT (no ON CONFLICT)
                if value_type == 'null':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_size, expires_at])
                elif value_type == 'text':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_text, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_dict['value_text'], value_size, expires_at])
                elif value_type == 'number':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_number, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_dict['value_number'], value_size, expires_at])
                elif value_type == 'boolean':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_bool, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_dict['value_bool'], value_size, expires_at])
                elif value_type == 'blob':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_blob, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_dict['value_blob'], value_size, expires_at])
                elif value_type == 'json':
                    sql = """
                        INSERT INTO __kv (key, value_type, value_json, value_size, expires_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, unixepoch())
                    """
                    conn.execute(sql, [key, value_type, value_dict['value_json'], value_size, expires_at])

                conn.commit()
                return True

            except sqlite3.IntegrityError:
                # Key already exists
                return False

    def keys(self, pattern: str = '*') -> List[str]:
        """List keys matching a pattern.

        Args:
            pattern: Redis-style glob pattern (default: '*' for all keys)

        Returns:
            List of matching keys (sorted)
        """
        # If tenant is not materialized, no keys exist
        if not self._is_tenant_materialized():
            return []

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            sql_pattern = self._glob_to_like(pattern)
            results = conn.execute("""
                SELECT key FROM __kv
                WHERE key LIKE ? ESCAPE '\\'
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
                ORDER BY key
            """, [sql_pattern]).fetchall()

            return [row['key'] for row in results]

    def ttl(self, key: str) -> Optional[float]:
        """Get remaining TTL for a key.

        Args:
            key: Key to check

        Returns:
            TTL in seconds (can be fractional), None if no expiry set, -1 if key doesn't exist or is expired
        """
        if not key or not isinstance(key, str):
            return -1

        # If tenant is not materialized, key doesn't exist
        if not self._is_tenant_materialized():
            return -1

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute(
                "SELECT expires_at FROM __kv WHERE key = ?", [key]
            ).fetchone()

            if not result:
                return -1

            expires_at = result['expires_at']
            if expires_at is None:
                return None

            ttl = expires_at - time.time()
            return ttl if ttl > 0 else -1

    def expire(self, key: str, ttl: float) -> bool:
        """Set/update TTL for an existing key.

        Args:
            key: Key to update
            ttl: TTL in seconds

        Returns:
            True if key existed and TTL was set, False otherwise
        """
        if not key or not isinstance(key, str) or ttl <= 0:
            return False

        # If tenant is not materialized, key doesn't exist
        if not self._is_tenant_materialized():
            return False

        expires_at = time.time() + ttl

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute("""
                UPDATE __kv
                SET expires_at = ?, updated_at = unixepoch()
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [expires_at, key])
            conn.commit()

            return result.rowcount > 0

    def persist(self, key: str) -> bool:
        """Remove expiration from a key, making it permanent.

        Args:
            key: Key to persist

        Returns:
            True if TTL was removed, False if key doesn't exist or had no TTL
        """
        if not key or not isinstance(key, str):
            return False

        # If tenant is not materialized, key doesn't exist
        if not self._is_tenant_materialized():
            return False

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute("""
                UPDATE __kv
                SET expires_at = NULL, updated_at = unixepoch()
                WHERE key = ?
                AND expires_at IS NOT NULL
                AND (expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [key])
            conn.commit()

            return result.rowcount > 0

    def delete_expired(self) -> int:
        """Delete all expired keys from storage.

        Returns:
            Number of keys removed
        """
        # If tenant is not materialized, no keys to clean up
        if not self._is_tenant_materialized():
            return 0

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            result = conn.execute("""
                DELETE FROM __kv
                WHERE expires_at IS NOT NULL
                AND expires_at <= ((julianday('now') - 2440587.5) * 86400.0)
            """)
            conn.commit()
            return result.rowcount

    # Batch operations

    def mget(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple keys at once.

        Args:
            keys: List of keys to retrieve

        Returns:
            Dictionary mapping keys to values

        Raises:
            ValueError: If any key is invalid or doesn't exist
        """
        if not keys:
            return {}

        # Validate all keys first
        for key in keys:
            if not key or not isinstance(key, str):
                raise ValueError(f"Invalid key: {key}")

        # If tenant is not materialized, no keys exist
        if not self._is_tenant_materialized():
            raise ValueError(f"Keys not found: {keys}")

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            # First, check that all keys exist (non-expired)
            placeholders = ','.join(['?'] * len(keys))
            existing = conn.execute(f"""
                SELECT key FROM __kv
                WHERE key IN ({placeholders})
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, keys).fetchall()

            existing_keys = {row['key'] for row in existing}
            missing_keys = set(keys) - existing_keys

            if missing_keys:
                raise ValueError(f"Keys not found: {sorted(missing_keys)}")

            # Now get all values in one query
            results = conn.execute(f"""
                SELECT key, value_type, value_text, value_number, value_bool, value_blob, value_json
                FROM __kv
                WHERE key IN ({placeholders})
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, keys).fetchall()

            result_dict = {}
            for row in results:
                key = row['key']
                value_type = row['value_type']

                if value_type == 'null':
                    result_dict[key] = None
                elif value_type == 'text':
                    result_dict[key] = row['value_text']
                elif value_type == 'number':
                    num = row['value_number']
                    result_dict[key] = int(num) if num == int(num) else num
                elif value_type == 'boolean':
                    result_dict[key] = bool(row['value_bool'])
                elif value_type == 'blob':
                    result_dict[key] = row['value_blob']
                elif value_type == 'json':
                    result_dict[key] = json.loads(row['value_json'])

            return result_dict

    def mset(self, items: Dict[str, Any], ttl: Optional[float] = None) -> None:
        """Set multiple key-value pairs atomically.

        Args:
            items: Dictionary of key-value pairs to set
            ttl: TTL in seconds for all items (None for no expiry)

        Raises:
            ValueError: If items is empty or contains invalid keys/values
        """
        if not items:
            return

        expires_at = None
        if ttl is not None:
            if ttl <= 0:
                raise ValueError("TTL must be positive")
            expires_at = time.time() + ttl

        # Prepare all items first
        prepared_items = []
        for key, value in items.items():
            if not key or not isinstance(key, str):
                raise ValueError(f"Invalid key: {key}")

            value_type, value_dict = self._detect_type_and_value(value)
            value_size = self._calculate_value_size(value)
            prepared_items.append((key, value_type, value_dict, value_size, expires_at))

        # Ensure tenant is materialized for write operation
        self._ensure_tenant_materialized()

        # Use transaction for atomicity
        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            conn.execute("BEGIN TRANSACTION")
            try:
                for key, value_type, value_dict, value_size, exp_at in prepared_items:
                    # Build dynamic SQL for each item
                    columns = ['key', 'value_type', 'value_size', 'expires_at', 'updated_at']
                    values = [key, value_type, value_size, exp_at, 'unixepoch()']

                    for col, val in value_dict.items():
                        columns.insert(2, col)
                        values.insert(2, val)

                    clear_columns = []
                    for col in ['value_text', 'value_number', 'value_bool', 'value_blob', 'value_json']:
                        if col not in value_dict:
                            clear_columns.append(f"{col} = NULL")

                    placeholders = ['?' if v != 'unixepoch()' else v for v in values]

                    # Build UPDATE clause parts
                    update_parts = ['value_type = excluded.value_type']
                    if value_dict:
                        update_parts.extend([f"{col} = excluded.{col}" for col in value_dict.keys()])
                    if clear_columns:
                        update_parts.extend(clear_columns)
                    update_parts.extend([
                        'value_size = excluded.value_size',
                        'expires_at = excluded.expires_at',
                        'updated_at = unixepoch()'
                    ])

                    sql = f"""
                        INSERT INTO __kv ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        ON CONFLICT(key) DO UPDATE SET
                            {', '.join(update_parts)}
                    """

                    actual_values = [v for v in values if v != 'unixepoch()']
                    conn.execute(sql, actual_values)

                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    # Atomic operations

    def increment(self, key: str, amount: Union[int, float] = 1) -> Union[int, float]:
        """Atomically increment a numeric value.

        Args:
            key: Key to increment
            amount: Amount to increment by (default: 1)

        Returns:
            New value after increment

        Raises:
            ValueError: If key is invalid or current value is not numeric
        """
        if not key or not isinstance(key, str):
            raise ValueError("Key must be a non-empty string")

        if not isinstance(amount, (int, float)):
            raise ValueError("Amount must be numeric")

        # Ensure tenant is materialized for write operation
        self._ensure_tenant_materialized()

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            # Try atomic increment on existing numeric key
            result = conn.execute("""
                UPDATE __kv
                SET value_number = value_number + ?,
                    value_size = LENGTH(CAST(value_number + ? AS TEXT)),
                    updated_at = unixepoch()
                WHERE key = ?
                AND value_type = 'number'
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
                RETURNING value_number
            """, [amount, amount, key]).fetchone()

            if result:
                conn.commit()
                num = result[0]
                return int(num) if num == int(num) else num

            # Check why it failed
            existing = conn.execute("""
                SELECT value_type FROM __kv
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [key]).fetchone()

            if existing:
                raise ValueError(f"Cannot increment non-numeric value")

            # Key doesn't exist - create as number
            value_size = len(str(amount).encode('utf-8'))
            conn.execute("""
                INSERT INTO __kv (key, value_type, value_number, value_size, updated_at)
                VALUES (?, 'number', ?, ?, unixepoch())
            """, [key, float(amount), value_size])
            conn.commit()

            return amount

    # Statistics and introspection

    def key_count(self, pattern: str = '*') -> int:
        """Count keys matching a pattern.

        Args:
            pattern: Redis-style glob pattern (default: '*' for all keys)

        Returns:
            Number of matching keys
        """
        # If tenant is not materialized, no keys exist
        if not self._is_tenant_materialized():
            return 0

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            sql_pattern = self._glob_to_like(pattern)
            result = conn.execute("""
                SELECT COUNT(*) as count FROM __kv
                WHERE key LIKE ? ESCAPE '\\'
                AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
            """, [sql_pattern]).fetchone()

            return result['count'] if result else 0

    def storage_size(self, *keys) -> Dict[str, int]:
        """Get storage size in bytes for keys.

        Args:
            *keys: Specific keys to check. If none, returns total for all keys.

        Returns:
            Dict mapping keys to their sizes in bytes.
            For non-existent keys, size is 0.
            If no keys specified, returns {'total': total_bytes}.
        """
        # If tenant is not materialized, no storage
        if not self._is_tenant_materialized():
            if not keys:
                return {'total': 0}
            return {key: 0 for key in keys}

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Ensure the __kv table exists
            self._ensure_kv_table(conn)

            if not keys:
                # Get total storage size
                result = conn.execute("""
                    SELECT COALESCE(SUM(value_size), 0) as total
                    FROM __kv
                    WHERE expires_at IS NULL OR expires_at > unixepoch()
                """).fetchone()
                return {'total': result['total'] if result else 0}
            else:
                # Get size for specific keys
                size_dict = {}
                for key in keys:
                    self._validate_key(key)
                    result = conn.execute("""
                        SELECT value_size
                        FROM __kv
                        WHERE key = ?
                        AND (expires_at IS NULL OR expires_at > ((julianday('now') - 2440587.5) * 86400.0))
                    """, [key]).fetchone()
                    size_dict[key] = result['value_size'] if result else 0
                return size_dict


"""Unified database connection interface for CinchDB."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from cinchdb.models import Column, Change, Index
from cinchdb.core.path_utils import get_project_root
from cinchdb.utils import validate_query_safe
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db

if TYPE_CHECKING:
    from cinchdb.managers.table import TableManager
    from cinchdb.managers.column import ColumnManager
    from cinchdb.managers.query import QueryManager
    from cinchdb.managers.data import DataManager
    from cinchdb.managers.view import ViewModel
    from cinchdb.managers.branch import BranchManager
    from cinchdb.managers.tenant import TenantManager
    from cinchdb.managers.codegen import CodegenManager
    from cinchdb.managers.merge_manager import MergeManager
    from cinchdb.managers.index import IndexManager
    from cinchdb.managers.kv import KVManager


class _Managers:
    """Internal manager access - for internal use only. 

    This class provides typed access to managers for internal convenience method implementations
    and advanced use cases only. Users should use the direct methods like create_table(),
    list_tenants(), etc.
    """

    def __init__(self, db: "CinchDB"):
        self._db = db

    @property
    def tables(self) -> "TableManager":
        """Table management operations."""
        if self._db._table_manager is None:
            from cinchdb.managers.table import TableManager
            self._db._table_manager = TableManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant, self._db.encryption_manager
            )
        return self._db._table_manager

    @property
    def columns(self) -> "ColumnManager":
        """Column management operations."""
        if self._db._column_manager is None:
            from cinchdb.managers.column import ColumnManager
            self._db._column_manager = ColumnManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant, self._db.encryption_manager
            )
        return self._db._column_manager

    @property
    def views(self) -> "ViewModel":
        """View management operations."""
        if self._db._view_manager is None:
            from cinchdb.managers.view import ViewModel
            self._db._view_manager = ViewModel(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant
            )
        return self._db._view_manager

    @property
    def branches(self) -> "BranchManager":
        """Branch management operations."""
        if self._db._branch_manager is None:
            from cinchdb.managers.branch import BranchManager
            self._db._branch_manager = BranchManager(self._db.project_dir, self._db.database)
        return self._db._branch_manager

    @property
    def tenants(self) -> "TenantManager":
        """Tenant management operations."""
        if self._db._tenant_manager is None:
            from cinchdb.managers.tenant import TenantManager
            self._db._tenant_manager = TenantManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.encryption_manager
            )
        return self._db._tenant_manager

    @property
    def data(self) -> "DataManager":
        """Data management operations."""
        if self._db._data_manager is None:
            from cinchdb.managers.data import DataManager
            self._db._data_manager = DataManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant, self._db.encryption_manager
            )
        return self._db._data_manager

    @property
    def codegen(self) -> "CodegenManager":
        """Code generation operations."""
        if self._db._codegen_manager is None:
            from cinchdb.managers.codegen import CodegenManager
            self._db._codegen_manager = CodegenManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant
            )
        return self._db._codegen_manager

    @property
    def merge(self) -> "MergeManager":
        """Merge operations."""
        if self._db._merge_manager is None:
            from cinchdb.managers.merge_manager import MergeManager
            self._db._merge_manager = MergeManager(self._db.project_dir, self._db.database)
        return self._db._merge_manager

    @property
    def indexes(self) -> "IndexManager":
        """Index management operations."""
        if self._db._index_manager is None:
            from cinchdb.managers.index import IndexManager
            self._db._index_manager = IndexManager(
                self._db.project_dir, self._db.database, self._db.branch
            )
        return self._db._index_manager

    @property
    def kv(self) -> "KVManager":
        """Key-Value store operations."""
        if self._db._kv_manager is None:
            from cinchdb.managers.kv import KVManager
            self._db._kv_manager = KVManager(
                self._db.project_dir, self._db.database, self._db.branch, self._db.tenant,
                self._db.encryption_manager
            )
        return self._db._kv_manager


class CinchDB:
    """Unified interface for CinchDB operations.

    Provides a simple, user-friendly interface for both local and remote
    connections while preserving access to all manager functionality.

    Examples:
        # Local connection
        db = CinchDB(project_dir="/path/to/project", database="mydb", branch="dev")

        # Remote connection
        db = CinchDB(
            api_url="https://api.example.com",
            api_key="your-api-key",
            database="mydb",
            branch="dev"
        )

        # Execute queries
        results = db.query("SELECT * FROM users WHERE active = ?", [True])

        # Create tables
        db.create_table("products", [
            Column(name="name", type="TEXT"),
            Column(name="price", type="REAL")
        ])

        # Access managers for advanced operations (local only)
        if db.is_local:
            db.tables.copy_table("products", "products_backup")
            db.columns.add_column("users", Column(name="phone", type="TEXT"))
    """

    def __init__(
        self,
        database: str,
        branch: str = "main",
        tenant: str = "main",
        project_dir: Optional[Path] = None,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        encryption_manager=None,
        encryption_key: Optional[str] = None,
    ):
        """Initialize CinchDB connection.

        Args:
            database: Database name
            branch: Branch name (default: main)
            tenant: Tenant name (default: main)
            project_dir: Path to project directory for local connection
            api_url: Base URL for remote API connection
            api_key: API key for remote connection
            encryption_manager: EncryptionManager instance for encrypted connections
            encryption_key: Encryption key for encrypted tenant databases

        Raises:
            ValueError: If neither local nor remote connection params provided
        """
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.encryption_manager = encryption_manager
        self.encryption_key = encryption_key
        
        # Determine connection type
        if project_dir is not None:
            # Local connection
            self.project_dir = Path(project_dir)
            self.api_url = None
            self.api_key = None
            self.is_local = True
            
            # Auto-materialize lazy database if needed
            self._materialize_database_if_lazy()
        elif api_url is not None and api_key is not None:
            # Remote connection
            self.project_dir = None
            self.api_url = api_url.rstrip("/")
            self.api_key = api_key
            self.is_local = False
            self._session = None
        else:
            raise ValueError(
                "Must provide either project_dir for local connection "
                "or both api_url and api_key for remote connection"
            )

        # Lazy-loaded managers (local only)
        self._table_manager: Optional["TableManager"] = None
        self._column_manager: Optional["ColumnManager"] = None
        self._query_manager: Optional["QueryManager"] = None
        self._data_manager: Optional["DataManager"] = None
        self._view_manager: Optional["ViewModel"] = None
        self._branch_manager: Optional["BranchManager"] = None
        self._tenant_manager: Optional["TenantManager"] = None
        self._codegen_manager: Optional["CodegenManager"] = None
        self._merge_manager: Optional["MergeManager"] = None
        self._index_manager: Optional["IndexManager"] = None
        self._kv_manager: Optional["KVManager"] = None

        # Manager access class
        self._managers_instance: Optional["_Managers"] = None

    def _materialize_database_if_lazy(self) -> None:
        """Auto-materialize a lazy database if accessing it."""
        if not self.is_local:
            return
            
        # Check if this is a lazy database using metadata DB
        metadata_db = get_metadata_db(self.project_dir)
        db_info = metadata_db.get_database(self.database)
        
        if db_info and not db_info['materialized']:
            # Database exists in metadata but not materialized
            from cinchdb.core.initializer import ProjectInitializer
            initializer = ProjectInitializer(self.project_dir)
            initializer.materialize_database(self.database)
    
    def get_connection(self, db_path, tenant_id: Optional[str] = None, encryption_manager=None, encryption_key: Optional[str] = None) -> "DatabaseConnection":
        """Get a database connection.
        
        Args:
            db_path: Path to database file
            tenant_id: Tenant ID for per-tenant encryption
            encryption_manager: EncryptionManager instance for encrypted connections
            encryption_key: Encryption key for encrypted databases
            
        Returns:
            DatabaseConnection instance
        """
        from cinchdb.core.connection import DatabaseConnection
        return DatabaseConnection(db_path, tenant_id=tenant_id, encryption_manager=encryption_manager, encryption_key=encryption_key)

    @property
    def session(self):
        """Get or create HTTP session for remote connections."""
        if not self.is_local and self._session is None:
            try:
                import requests
            except ImportError:
                raise ImportError(
                    "The 'requests' package is required for remote connections. "
                    "Install it with: pip install requests"
                )
            self._session = requests.Session()
            self._session.headers.update(
                {"X-API-Key": self.api_key, "Content-Type": "application/json"}
            )
        return self._session

    def _endpoint_needs_tenant(self, endpoint: str) -> bool:
        """Check if an API endpoint needs tenant parameter.

        Args:
            endpoint: API endpoint path

        Returns:
            True if endpoint needs tenant parameter
        """
        # Query operations need tenant
        if endpoint.startswith("/query"):
            return True

        # Data CRUD operations need tenant (tables/{table}/data)
        if "/data" in endpoint:
            return True

        # Tenant management operations need tenant
        if endpoint.startswith("/tenants"):
            return True

        # Schema operations don't need tenant
        return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an API request for remote connections.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response data

        Raises:
            Exception: If request fails
        """
        if self.is_local:
            raise RuntimeError("Cannot make API requests on local connection")

        url = f"{self.api_url}{endpoint}"

        # Add default query parameters
        params = kwargs.get("params", {})
        params.update({"database": self.database, "branch": self.branch})

        # Only add tenant for data operations (query, data CRUD, tenant management)
        if self._endpoint_needs_tenant(endpoint):
            params["tenant"] = self.tenant

        kwargs["params"] = params

        response = self.session.request(method, url, **kwargs)

        if response.status_code >= 400:
            error_detail = response.json().get("detail", "Unknown error")
            raise Exception(f"API Error ({response.status_code}): {error_detail}")

        return response.json()

    @property
    def _managers(self) -> "_Managers":
        """Internal manager access - For CinchDB internal only. Use convenience methods instead.

        This property provides typed access to managers for internal convenience method implementations
        and advanced use cases only. Users should use the direct methods like create_table(),
        list_tenants(), etc.
        """
        if not self.is_local:
            raise RuntimeError("Manager access not available for remote connections")

        if self._managers_instance is None:
            self._managers_instance = _Managers(self)

        return self._managers_instance

    @property
    def kv(self) -> "KVManager":
        """Key-Value store for fast unstructured data storage.

        Examples:
            # Set a key-value pair
            db.kv.set("user:123", {"name": "Alice", "email": "alice@example.com"})

            # Get a value
            user = db.kv.get("user:123")

            # Set with TTL (expires in 1 hour)
            db.kv.set("session:abc", session_data, ttl=3600)

            # Batch operations
            db.kv.mset({"key1": "value1", "key2": "value2"})
            values = db.kv.mget(["key1", "key2"])

            # Pattern operations
            user_keys = db.kv.keys("user:*")
            db.kv.delete(*user_keys)

            # Atomic increment
            count = db.kv.increment("counter", 5)

        Returns:
            KVStore instance for this database/branch/tenant
        """
        if not self.is_local:
            raise RuntimeError("KV store is not available for remote connections yet")

        return self._managers.kv

    # Convenience methods for common operations

    def query(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        skip_validation: bool = False,
        mask_columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query.

        Args:
            sql: SQL query to execute
            params: Query parameters (optional)
            skip_validation: Skip SQL validation (default: False)
            mask_columns: List of column names to mask in results (optional)

        Returns:
            List of result rows as dictionaries

        Raises:
            SQLValidationError: If the query contains restricted operations
        """
        # Validate query unless explicitly skipped
        if not skip_validation:
            from cinchdb.utils.sql_validator import validate_query_safe
            validate_query_safe(sql)

        if self.is_local:
            if self._query_manager is None:
                from cinchdb.managers.query import QueryManager

                self._query_manager = QueryManager(
                    self.project_dir, self.database, self.branch, self.tenant, self.encryption_manager
                )
            # Execute SELECT query directly (replacing removed execute method)
            from cinchdb.utils.sql_validator import validate_query_safe
            from cinchdb.core.connection import DatabaseConnection

            # Validate query unless explicitly skipped
            if not skip_validation:
                validate_query_safe(sql)

            # Ensure this is a SELECT query
            if not sql.strip().upper().startswith("SELECT"):
                raise ValueError("query() can only be used with SELECT queries. Use insert(), update(), delete() for data modifications.")

            # Get appropriate database path
            db_path = self._query_manager.tenant_manager.get_tenant_db_path_for_operation(
                self.tenant, is_write=False
            )

            with DatabaseConnection(db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]

                # Apply column masking if requested
                if mask_columns and results:
                    for row in results:
                        for col in mask_columns:
                            if col in row and row[col] is not None:
                                row[col] = "***REDACTED***"

                return results
        else:
            # Remote query
            data = {"sql": sql}
            if params:
                data["params"] = params
            result = self._make_request("POST", "/query", json=data)
            results = result.get("data", [])

            # Apply column masking if requested
            if mask_columns and results:
                for row in results:
                    for col in mask_columns:
                        if col in row and row[col] is not None:
                            row[col] = "***REDACTED***"

            return results

    def create_table(self, name: str, columns: List[Column], indexes: Optional[List["Index"]] = None) -> "Table":
        """Create a new table.

        Args:
            name: Table name
            columns: List of column definitions
            indexes: Optional list of indexes to create

        Returns:
            Table object with metadata
        """
        if self.is_local:
            return self._managers.tables.create_table(name, columns, indexes)
        else:
            # Remote table creation
            columns_data = [
                {"name": col.name, "type": col.type, "nullable": col.nullable}
                for col in columns
            ]

            # Prepare request data
            request_data = {"name": name, "columns": columns_data}

            # Add indexes if provided
            if indexes:
                indexes_data = [
                    {
                        "columns": idx.columns,
                        "unique": idx.unique,
                        "name": idx.name
                    }
                    for idx in indexes
                ]
                request_data["indexes"] = indexes_data

            response = self._make_request(
                "POST", "/tables", json=request_data
            )

            # Return a Table object matching what local returns
            from cinchdb.models import Table
            # The response should contain the table info, but if not,
            # construct from what we know
            return Table(
                name=name,
                database=self.database,
                branch=self.branch,
                columns=columns
            )

    def insert(self, table: str, *data: Dict[str, Any]) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Insert one or more records into a table.

        Args:
            table: Table name
            *data: One or more record data dictionaries

        Returns:
            Single record dict if one record inserted, list of dicts if multiple

        Examples:
            # Single insert
            db.insert("users", {"name": "John", "email": "john@example.com"})
            
            # Multiple inserts using star expansion
            db.insert("users", 
                {"name": "John", "email": "john@example.com"},
                {"name": "Jane", "email": "jane@example.com"},
                {"name": "Bob", "email": "bob@example.com"}
            )
            
            # Or with a list using star expansion
            users = [
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Charlie", "email": "charlie@example.com"}
            ]
            db.insert("users", *users)
        """
        if not data:
            raise ValueError("At least one record must be provided")
            
        if self.is_local:            
            # Single record
            if len(data) == 1:
                return self._managers.data.create_from_dict(table, data[0])
            
            # Multiple records - use bulk insert
            return self._managers.data.bulk_create_from_dict(table, list(data))
        else:
            # Remote insert
            if len(data) == 1:
                # Single record - use existing endpoint
                result = self._make_request(
                    "POST", f"/tables/{table}/data", json={"data": data[0]}
                )
                return result
            else:
                # Multiple records - use bulk endpoint
                result = self._make_request(
                    "POST", f"/tables/{table}/data/bulk", json={"records": list(data)}
                )
                return result

    def update(self, table: str, *updates: Dict[str, Any]) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Update one or more records in a table.

        Args:
            table: Table name
            *updates: One or more update dictionaries, each must contain 'id' field

        Returns:
            Single record dict if one record updated, list of dicts if multiple

        Examples:
            # Single update
            db.update("users", {"id": "123", "name": "John Updated", "status": "active"})
            
            # Multiple updates using star expansion
            db.update("users", 
                {"id": "123", "name": "John Updated", "status": "active"},
                {"id": "456", "name": "Jane Updated", "email": "jane.new@example.com"},
                {"id": "789", "status": "inactive"}
            )
            
            # Or with a list using star expansion
            user_updates = [
                {"id": "abc", "name": "Alice Updated"},
                {"id": "def", "status": "premium"}
            ]
            db.update("users", *user_updates)
        """
        if not updates:
            raise ValueError("At least one update record must be provided")
            
        # Validate that all updates have an 'id' field
        for i, update_data in enumerate(updates):
            if 'id' not in update_data:
                raise ValueError(f"Update record {i} missing required 'id' field")
            
        if self.is_local:
            # Single record
            if len(updates) == 1:
                update_data = updates[0].copy()
                record_id = update_data.pop('id')
                return self._managers.data.update_by_id(table, record_id, update_data)

            # Multiple records - batch update
            results = []
            for update_data in updates:
                update_copy = update_data.copy()
                record_id = update_copy.pop('id')
                try:
                    result = self._managers.data.update_by_id(table, record_id, update_copy)
                    results.append(result)
                except ValueError as e:
                    # Record not found - include error in results
                    results.append({"id": record_id, "error": str(e)})
            return results
        else:
            # Remote update
            if len(updates) == 1:
                # Single record - use existing endpoint
                update_data = updates[0].copy()
                record_id = update_data.pop('id')
                result = self._make_request(
                    "PUT", f"/tables/{table}/data/{record_id}", json={"data": update_data}
                )
                return result
            else:
                # Multiple records - use bulk endpoint
                result = self._make_request(
                    "PUT", f"/tables/{table}/data/bulk", json={"updates": list(updates)}
                )
                return result

    def delete(self, table: str, *ids: str) -> int:
        """Delete one or more records from a table.

        Args:
            table: Table name
            *ids: One or more record IDs

        Returns:
            Number of records deleted

        Examples:
            # Single delete
            db.delete("users", "123")
            
            # Multiple deletes
            db.delete("users", "123", "456", "789")
            
            # Or with a list using star expansion
            user_ids = ["abc", "def", "ghi"]
            db.delete("users", *user_ids)
        """
        if not ids:
            raise ValueError("At least one ID must be provided")
            
        if self.is_local:
            # Single record
            if len(ids) == 1:
                success = self._managers.data.delete_by_id(table, ids[0])
                return 1 if success else 0

            # Multiple records - batch delete
            deleted_count = 0
            for record_id in ids:
                success = self._managers.data.delete_by_id(table, record_id)
                if success:
                    deleted_count += 1
            return deleted_count
        else:
            # Remote delete
            if len(ids) == 1:
                # Single record - use existing endpoint
                self._make_request("DELETE", f"/tables/{table}/data/{ids[0]}")
                return 1
            else:
                # Multiple records - use bulk endpoint
                result = self._make_request(
                    "DELETE", f"/tables/{table}/data/bulk", json={"ids": list(ids)}
                )
                return result.get("deleted_count", len(ids))

    def delete_where(self, table: str, operator: str = "AND", **filters) -> int:
        """Delete records from a table based on filter criteria.
        
        Args:
            table: Table name
            operator: Logical operator to combine conditions - "AND" (default) or "OR"
            **filters: Filter criteria (supports operators like __gt, __lt, __in, __like, __not)
                      Multiple conditions are combined with the specified operator
            
        Returns:
            Number of records deleted
            
        Examples:
            # Delete records where status = 'inactive' (single condition)
            count = db.delete_where('users', status='inactive')
            
            # Delete records where status = 'inactive' AND age > 65 (default AND)
            count = db.delete_where('users', status='inactive', age__gt=65)
            
            # Delete records where status = 'inactive' OR age > 65
            count = db.delete_where('users', operator='OR', status='inactive', age__gt=65)
            
            # Delete records where item_id in [1, 2, 3]
            count = db.delete_where('items', item_id__in=[1, 2, 3])
        """
        if self.is_local:
            return self._managers.data.delete_where(table, operator=operator, **filters)
        else:
            raise NotImplementedError("Remote bulk delete not implemented")

    def update_where(self, table: str, data: Dict[str, Any], operator: str = "AND", **filters) -> int:
        """Update records in a table based on filter criteria.
        
        Args:
            table: Table name
            data: Dictionary of column-value pairs to update
            operator: Logical operator to combine conditions - "AND" (default) or "OR"
            **filters: Filter criteria (supports operators like __gt, __lt, __in, __like, __not)
                      Multiple conditions are combined with the specified operator
            
        Returns:
            Number of records updated
            
        Examples:
            # Update status for all users with age > 65 (single condition)
            count = db.update_where('users', {'status': 'senior'}, age__gt=65)
            
            # Update status where age > 65 AND status = 'active' (default AND)
            count = db.update_where('users', {'status': 'senior'}, age__gt=65, status='active')
            
            # Update status where age > 65 OR status = 'pending' 
            count = db.update_where('users', {'status': 'senior'}, operator='OR', age__gt=65, status='pending')
            
            # Update multiple fields where item_id in specific list
            count = db.update_where(
                'items', 
                {'status': 'inactive', 'updated_at': datetime.now()},
                item_id__in=[1, 2, 3]
            )
        """
        if self.is_local:
            return self._managers.data.update_where(table, data, operator=operator, **filters)
        else:
            raise NotImplementedError("Remote bulk update not implemented")


    def create_index(
        self,
        table: str,
        columns: List[str],
        name: Optional[str] = None,
        unique: bool = False,
    ) -> str:
        """Create an index on a table at the branch level.
        
        Indexes are created for the current branch and apply to all tenants.

        Args:
            table: Table name
            columns: List of column names to index
            name: Optional index name (auto-generated if not provided)
            unique: Whether to create a unique index

        Returns:
            str: Name of the created index

        Examples:
            # Simple index on one column
            db.create_index("users", ["email"])
            
            # Unique compound index
            db.create_index("orders", ["user_id", "order_number"], unique=True)
            
            # Named index
            db.create_index("products", ["category", "price"], name="idx_category_price")
        """
        # Convert parameters to Index model for validation
        from cinchdb.models import Index
        index = Index(columns=columns, name=name, unique=unique)
        
        if self.is_local:
            return self._managers.indexes.create_index(table, index.columns, index.name, index.unique)
        else:
            # Remote index creation
            result = self._make_request(
                "POST",
                "/indexes",
                json={
                    "table": table,
                    "columns": index.columns,
                    "name": index.name,
                    "unique": index.unique,
                },
            )
            return result.get("name")

    def list_changes(self) -> List["Change"]:
        """List all changes for the current branch.

        Returns:
            List of Change objects containing change history

        Examples:
            # List all changes
            changes = db.list_changes()
            for change in changes:
                print(f"{change.type}: {change.entity_name} (applied: {change.applied})")
        """
        if self.is_local:
            from cinchdb.managers.change_tracker import ChangeTracker

            tracker = ChangeTracker(self.project_dir, self.database, self.branch)
            return tracker.get_changes()
        else:
            # Remote API call
            result = self._make_request("GET", f"/branches/{self.branch}/changes")
            # Convert API response to Change objects
            from cinchdb.models import Change
            from datetime import datetime

            changes = []
            for data in result.get("changes", []):
                # Convert string dates back to datetime if present
                if data.get("created_at"):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                if data.get("updated_at"):
                    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
                changes.append(Change(**data))
            return changes


    def get_tenant_size(self, tenant_name: str = None) -> dict:
        """Get storage size information for a tenant.
        
        Args:
            tenant_name: Name of tenant (default: current tenant)
            
        Returns:
            Dictionary with size information:
            - name: Tenant name
            - size_bytes: Size in bytes (0 if no data)
            - size_kb: Size in KB
            - size_mb: Size in MB
            - page_size: SQLite page size (if available)
            - page_count: Number of pages (if available)
            
        Examples:
            # Get size of current tenant
            size = db.get_tenant_size()
            print(f"Current tenant uses {size['size_mb']:.2f} MB")
            
            # Get size of specific tenant
            size = db.get_tenant_size("store_west")
            if size['page_size']:
                print(f"Page size: {size['page_size']} bytes")
        """
        if self.is_local:
            tenant_to_check = tenant_name or self.tenant
            return self._managers.tenants.get_tenant_size(tenant_to_check)
        else:
            raise NotImplementedError("Remote tenant size query not implemented")
    
    def vacuum_tenant(self, tenant_name: str = None) -> dict:
        """Run VACUUM operation on a specific tenant to optimize storage and performance.
        
        VACUUM reclaims space from deleted records, defragments the database file,
        and can improve query performance by rebuilding internal structures.
        
        Args:
            tenant_name: Name of tenant to vacuum (default: current tenant)
            
        Returns:
            Dictionary with vacuum results:
            - success: Whether vacuum completed successfully
            - tenant: Name of the tenant
            - size_before: Size in bytes before vacuum
            - size_after: Size in bytes after vacuum
            - space_reclaimed: Bytes reclaimed by vacuum
            - space_reclaimed_mb: MB reclaimed (rounded to 2 decimals)
            - duration_seconds: Time taken for vacuum operation
            - error: Error message if vacuum failed
            
        Raises:
            ValueError: If tenant doesn't exist or is not materialized
            NotImplementedError: If called on remote database
            
        Examples:
            # Vacuum current tenant
            result = db.vacuum_tenant()
            if result['success']:
                print(f"Reclaimed {result['space_reclaimed_mb']:.2f} MB")
            
            # Vacuum specific tenant
            result = db.vacuum_tenant("store_east")
            print(f"Vacuum took {result['duration_seconds']} seconds")
        """
        if self.is_local:
            tenant_to_vacuum = tenant_name or self.tenant
            return self._managers.tenants.vacuum_tenant(tenant_to_vacuum)
        else:
            raise NotImplementedError("Remote tenant vacuum not implemented")
    
    def get_storage_info(self) -> dict:
        """Get storage size information for all tenants in current branch.
        
        Returns:
            Dictionary with:
            - tenants: List of individual tenant size info (sorted by size)
            - total_size_bytes: Total size of all tenants
            - total_size_mb: Total size in MB
            - tenant_count: Total number of tenants
            
        Examples:
            # Get storage overview
            info = db.get_storage_info()
            print(f"Total storage: {info['total_size_mb']:.2f} MB")
            print(f"Total tenants: {info['tenant_count']}")
            
            # List largest tenants
            for tenant in info['tenants'][:5]:  # Top 5
                if tenant['size_mb'] > 0:
                    print(f"{tenant['name']}: {tenant['size_mb']:.2f} MB")
        """
        if self.is_local:
            return self._managers.tenants.get_all_tenant_sizes()
        else:
            raise NotImplementedError("Remote storage info not implemented")

    # Tenant convenience methods

    def list_tenants(self, include_system: bool = False) -> List["Tenant"]:
        """List all tenants in the branch.

        Args:
            include_system: If True, include system tenants like __empty__

        Returns:
            List of Tenant objects

        Examples:
            # List all user tenants
            tenants = db.list_tenants()
            for tenant in tenants:
                print(f"Tenant: {tenant.name}")

            # Include system tenants
            all_tenants = db.list_tenants(include_system=True)
        """
        if self.is_local:
            return self._managers.tenants.list_tenants(include_system=include_system)
        else:
            raise NotImplementedError("Remote tenant listing not implemented")

    def create_tenant(self, name: str, copy_from: Optional[str] = None, lazy: bool = True) -> "Tenant":
        """Create a new tenant.

        Args:
            name: Tenant name
            copy_from: Optional tenant to copy data from
            lazy: Whether to create as lazy tenant (default: True)

        Returns:
            Created Tenant object

        Examples:
            # Create lazy tenant (default)
            tenant = db.create_tenant("acme_corp")

            # Create materialized tenant
            tenant = db.create_tenant("acme_corp", lazy=False)

            # Create tenant with data copied from template
            tenant = db.create_tenant("new_customer", copy_from="template")
        """
        if self.is_local:
            if copy_from:
                return self._managers.tenants.copy_tenant(copy_from, name)
            else:
                return self._managers.tenants.create_tenant(name, lazy=lazy)
        else:
            raise NotImplementedError("Remote tenant creation not implemented")

    def delete_tenant(self, name: str) -> None:
        """Delete a tenant and all its data.

        Args:
            name: Tenant name to delete

        Examples:
            # Delete tenant permanently
            db.delete_tenant("old_customer")
        """
        if self.is_local:
            self._managers.tenants.delete_tenant(name)
        else:
            raise NotImplementedError("Remote tenant deletion not implemented")

    def copy_tenant(self, source: str, target: str) -> "Tenant":
        """Copy a tenant and all its data to a new tenant.

        Args:
            source: Source tenant name
            target: Target tenant name

        Returns:
            Created Tenant object

        Examples:
            # Copy tenant data
            new_tenant = db.copy_tenant("template", "new_customer")
        """
        if self.is_local:
            return self._managers.tenants.copy_tenant(source, target)
        else:
            raise NotImplementedError("Remote tenant copying not implemented")

    def rename_tenant(self, old_name: str, new_name: str) -> None:
        """Rename a tenant.

        Args:
            old_name: Current tenant name
            new_name: New tenant name

        Examples:
            # Rename tenant
            db.rename_tenant("old_customer", "acme_corp")
        """
        if self.is_local:
            self._managers.tenants.rename_tenant(old_name, new_name)
        else:
            raise NotImplementedError("Remote tenant renaming not implemented")

    # Branch convenience methods

    def list_branches(self) -> List["Branch"]:
        """List all branches in the database.

        Returns:
            List of Branch objects

        Examples:
            # List all branches
            branches = db.list_branches()
            for branch in branches:
                print(f"Branch: {branch.name} (created: {branch.created_at})")
        """
        if self.is_local:
            return self._managers.branches.list_branches()
        else:
            raise NotImplementedError("Remote branch listing not implemented")

    def create_branch(self, name: str, source_branch: str = "main") -> "Branch":
        """Create a new branch.

        Args:
            name: Branch name
            source_branch: Branch to create from (default: main)

        Returns:
            Created Branch object

        Examples:
            # Create feature branch from main
            branch = db.create_branch("feature-auth")

            # Create from specific branch
            branch = db.create_branch("hotfix-123", source_branch="production")
        """
        if self.is_local:
            return self._managers.branches.create_branch(source_branch, name)
        else:
            raise NotImplementedError("Remote branch creation not implemented")

    def delete_branch(self, name: str) -> None:
        """Delete a branch.

        Args:
            name: Branch name to delete

        Examples:
            # Delete old feature branch
            db.delete_branch("old-feature")
        """
        if self.is_local:
            self._managers.branches.delete_branch(name)
        else:
            raise NotImplementedError("Remote branch deletion not implemented")

    def get_branch_changes(self, branch_name: str) -> List["Change"]:
        """Get changes for a specific branch.

        Args:
            branch_name: Branch name

        Returns:
            List of Change objects for the branch

        Examples:
            # Get changes in feature branch
            changes = db.get_branch_changes("feature.new-auth")
            for change in changes:
                print(f"{change.type}: {change.description}")
        """
        if self.is_local:
            from cinchdb.managers.change_comparator import ChangeComparator
            comparator = ChangeComparator(self.project_dir, self.database)
            return comparator.get_branch_changes(branch_name)
        else:
            raise NotImplementedError("Remote branch changes not implemented")

    # Merge convenience methods

    def can_merge(self, source_branch: str, target_branch: str) -> Dict[str, Any]:
        """Check if branches can be merged safely.

        Args:
            source_branch: Source branch name
            target_branch: Target branch name

        Returns:
            Dictionary with merge analysis including conflicts

        Examples:
            # Check if merge is safe
            result = db.can_merge("feature-auth", "main")
            if result["can_merge"]:
                print("Safe to merge")
            else:
                print(f"Conflicts: {result['conflicts']}")
        """
        if self.is_local:
            return self._managers.merge.can_merge(source_branch, target_branch)
        else:
            raise NotImplementedError("Remote merge checking not implemented")

    def merge_branches(self, source_branch: str, target_branch: str = "main") -> Dict[str, Any]:
        """Merge one branch into another.

        Args:
            source_branch: Source branch name
            target_branch: Target branch name (default: main)

        Returns:
            Dictionary with merge results

        Examples:
            # Merge feature into main
            result = db.merge_branches("feature-auth", "main")
            print(f"Merged {result['changes_applied']} changes")
        """
        if self.is_local:
            return self._managers.merge.merge_branches(source_branch, target_branch)
        else:
            raise NotImplementedError("Remote merging not implemented")

    def merge_into_main(self, source_branch: str, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Merge a branch into main with advanced options.

        Args:
            source_branch: Source branch name
            force: Force merge even if conflicts exist
            dry_run: Show what would be merged without applying changes

        Returns:
            Dictionary with merge results and preview

        Examples:
            # Preview merge
            result = db.merge_into_main("feature-auth", dry_run=True)
            print(f"Would merge {len(result['changes'])} changes")

            # Force merge with conflicts
            result = db.merge_into_main("hotfix", force=True)
            print(f"Force merged {result['changes_applied']} changes")
        """
        if self.is_local:
            return self._managers.merge.merge_into_main(source_branch, force=force, dry_run=dry_run)
        else:
            raise NotImplementedError("Remote advanced merging not implemented")

    # Index convenience methods

    def list_indexes(self, table: Optional[str] = None) -> List[Dict[str, Any]]:
        """List indexes for a table or all tables.

        Args:
            table: Filter by table name (optional)

        Returns:
            List of index information dictionaries

        Examples:
            # List all indexes
            indexes = db.list_indexes()

            # List indexes for specific table
            user_indexes = db.list_indexes("users")
        """
        if self.is_local:
            return self._managers.indexes.list_indexes(table)
        else:
            raise NotImplementedError("Remote index listing not implemented")

    def drop_index(self, name: str, if_exists: bool = True) -> None:
        """Drop an index.

        Args:
            name: Index name
            if_exists: Use IF EXISTS clause (default: True)

        Examples:
            # Drop index safely
            db.drop_index("idx_users_email")

            # Drop index (error if not exists)
            db.drop_index("idx_old", if_exists=False)
        """
        if self.is_local:
            self._managers.indexes.drop_index(name, if_exists)
        else:
            raise NotImplementedError("Remote index dropping not implemented")

    def get_index_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about an index.

        Args:
            name: Index name

        Returns:
            Dictionary with index details

        Examples:
            # Get index details
            info = db.get_index_info("idx_users_email")
            print(f"Columns: {info['columns']}")
        """
        if self.is_local:
            return self._managers.indexes.get_index_info(name)
        else:
            raise NotImplementedError("Remote index info not implemented")

    # Column convenience methods

    def add_column(self, table: str, column: "Column") -> None:
        """Add a new column to a table.

        Args:
            table: Table name
            column: Column definition

        Examples:
            from cinchdb.models import Column

            # Add nullable column
            db.add_column("users", Column(name="phone", type="TEXT"))

            # Add column with default
            db.add_column("users", Column(name="active", type="BOOLEAN", default="true"))
        """
        if self.is_local:
            self._managers.columns.add_column(table, column)
        else:
            raise NotImplementedError("Remote column addition not implemented")

    def drop_column(self, table: str, column: str) -> None:
        """Drop a column from a table.

        Args:
            table: Table name
            column: Column name

        Examples:
            # Drop column
            db.drop_column("users", "old_field")
        """
        if self.is_local:
            self._managers.columns.drop_column(table, column)
        else:
            raise NotImplementedError("Remote column dropping not implemented")

    def rename_column(self, table: str, old_name: str, new_name: str) -> None:
        """Rename a column.

        Args:
            table: Table name
            old_name: Current column name
            new_name: New column name

        Examples:
            # Rename column
            db.rename_column("users", "email_addr", "email")
        """
        if self.is_local:
            self._managers.columns.rename_column(table, old_name, new_name)
        else:
            raise NotImplementedError("Remote column renaming not implemented")

    def alter_column_nullable(self, table: str, column: str, nullable: bool, fill_value: Optional[str] = None) -> None:
        """Alter a column's nullable constraint.

        Args:
            table: Table name
            column: Column name
            nullable: Whether column should be nullable
            fill_value: Value to use for existing NULL values when making column NOT NULL

        Examples:
            # Make column nullable
            db.alter_column_nullable("users", "phone", True)

            # Make column NOT NULL with default value
            db.alter_column_nullable("users", "active", False, fill_value="true")
        """
        if self.is_local:
            self._managers.columns.alter_column_nullable(table, column, nullable, fill_value)
        else:
            raise NotImplementedError("Remote column altering not implemented")

    # View convenience methods

    def create_view(self, name: str, sql: str) -> "View":
        """Create a database view.

        Args:
            name: View name
            sql: SQL query defining the view

        Returns:
            Created View object

        Examples:
            # Create view
            view = db.create_view("active_users", "SELECT * FROM users WHERE active = true")
        """
        if self.is_local:
            return self._managers.views.create_view(name, sql)
        else:
            raise NotImplementedError("Remote view creation not implemented")

    def list_views(self) -> List["View"]:
        """List all views.

        Returns:
            List of View objects

        Examples:
            # List all views
            views = db.list_views()
            for view in views:
                print(f"View: {view.name}")
        """
        if self.is_local:
            return self._managers.views.list_views()
        else:
            raise NotImplementedError("Remote view listing not implemented")

    def update_view(self, name: str, sql: str, description: Optional[str] = None) -> "View":
        """Update an existing view.

        Args:
            name: View name
            sql: New SQL query defining the view
            description: Optional view description

        Returns:
            Updated View object

        Examples:
            # Update view SQL
            view = db.update_view("active_users", "SELECT * FROM users WHERE active = true AND created_at > '2024-01-01'")

            # Update with description
            view = db.update_view("recent_posts", "SELECT * FROM posts WHERE created_at > date('now', '-30 days')", "Posts from last 30 days")
        """
        if self.is_local:
            return self._managers.views.update_view(name, sql, description)
        else:
            raise NotImplementedError("Remote view updating not implemented")

    def drop_view(self, name: str) -> None:
        """Drop a view.

        Args:
            name: View name

        Examples:
            # Drop view
            db.drop_view("old_view")
        """
        if self.is_local:
            self._managers.views.delete_view(name)
        else:
            raise NotImplementedError("Remote view dropping not implemented")

    # Data convenience methods

    def select(self, model_class, limit: Optional[int] = None, offset: Optional[int] = None, **filters):
        """Select records using a Pydantic model class.

        Args:
            model_class: Pydantic model class representing the table
            limit: Maximum number of records
            offset: Number of records to skip
            **filters: Column filters (supports operators like column__gte, column__like)

        Returns:
            List of model instances

        Examples:
            from pydantic import BaseModel

            class User(BaseModel):
                id: str
                name: str
                email: str

                class Config:
                    json_schema_extra = {"table_name": "users"}

            # Select all users
            users = db.select(User)

            # With filters
            active_users = db.select(User, active=True, limit=10)
        """
        if self.is_local:
            return self._managers.data.select(model_class, limit=limit, offset=offset, **filters)
        else:
            raise NotImplementedError("Remote model-based select not implemented")

    def find_by_id(self, model_class, record_id: str):
        """Find a single record by ID using a Pydantic model class.

        Args:
            model_class: Pydantic model class
            record_id: Record ID

        Returns:
            Model instance or None

        Examples:
            # Find user by ID
            user = db.find_by_id(User, "user-123")
            if user:
                print(f"Found: {user.name}")
        """
        if self.is_local:
            return self._managers.data.find_by_id(model_class, record_id)
        else:
            raise NotImplementedError("Remote model-based find not implemented")

    def delete_model_by_id(self, model_class, record_id: str) -> bool:
        """Delete a record by ID using a Pydantic model class.

        Args:
            model_class: Pydantic model class representing the table
            record_id: Record ID to delete

        Returns:
            True if deleted, False if not found

        Examples:
            # Delete user by ID
            deleted = db.delete_model_by_id(User, "user-123")
            if deleted:
                print("User deleted successfully")
        """
        if self.is_local:
            return self._managers.data.delete_model_by_id(model_class, record_id)
        else:
            raise NotImplementedError("Remote model-based delete not implemented")

    # Codegen convenience methods

    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported code generation languages.

        Returns:
            List of language info dicts with 'name' and 'description'

        Examples:
            # Get available languages for code generation
            languages = db.get_supported_languages()
            for lang in languages:
                print(f"{lang['name']}: {lang['description']}")
        """
        if self.is_local:
            return self._managers.codegen.get_supported_languages()
        else:
            raise NotImplementedError("Remote code generation not implemented")

    def generate_models(self, language: str, output_dir: Optional[Path] = None,
                       include_tables: bool = True, include_views: bool = True) -> Dict[str, Any]:
        """Generate model code for the database schema.

        Args:
            language: Target language (e.g., 'python', 'typescript')
            output_dir: Directory to write generated files (optional)
            include_tables: Include table models (default: True)
            include_views: Include view models (default: True)

        Returns:
            Dict with 'files_generated' list and other metadata

        Examples:
            # Generate Python models to a directory
            from pathlib import Path
            output = Path("./models")
            result = db.generate_models("python", output_dir=output)
            print(f"Generated {len(result['files_generated'])} files")
        """
        if self.is_local:
            if output_dir is None:
                import tempfile
                output_dir = Path(tempfile.mkdtemp()) / "generated_models"
            return self._managers.codegen.generate_models(
                language, output_dir, include_tables, include_views
            )
        else:
            raise NotImplementedError("Remote code generation not implemented")

    # Table convenience methods

    def list_tables(self, include_system: bool = False) -> List["Table"]:
        """List all tables in the database.

        Args:
            include_system: If True, include system tables (sqlite_* and __*)

        Returns:
            List of Table objects

        Examples:
            # List all user tables
            tables = db.list_tables()
            for table in tables:
                print(f"Table: {table.name} ({len(table.columns)} columns)")

            # List all tables including system tables
            all_tables = db.list_tables(include_system=True)
        """
        if self.is_local:
            return self._managers.tables.list_tables(include_system=include_system)
        else:
            raise NotImplementedError("Remote table listing not implemented")

    def get_table(self, name: str) -> "Table":
        """Get detailed information about a table.

        Args:
            name: Table name

        Returns:
            Table object with columns and metadata

        Examples:
            # Get table details
            table = db.get_table("users")
            print(f"Table has {len(table.columns)} columns")
            for col in table.columns:
                print(f"  {col.name}: {col.type}")
        """
        if self.is_local:
            return self._managers.tables.get_table(name)
        else:
            raise NotImplementedError("Remote table details not implemented")

    def drop_table(self, name: str) -> None:
        """Drop a table and all its data.

        Args:
            name: Table name to drop

        Examples:
            # Drop table permanently
            db.drop_table("old_table")
        """
        if self.is_local:
            self._managers.tables.delete_table(name)
        else:
            raise NotImplementedError("Remote table dropping not implemented")

    def copy_table(self, source: str, target: str, copy_data: bool = True) -> None:
        """Copy a table structure and optionally its data.

        Args:
            source: Source table name
            target: Target table name
            copy_data: Whether to copy data (default: True)

        Examples:
            # Copy table with data
            db.copy_table("users", "users_backup")

            # Copy only structure
            db.copy_table("users", "users_template", copy_data=False)
        """
        if self.is_local:
            self._managers.tables.copy_table(source, target, copy_data)
        else:
            raise NotImplementedError("Remote table copying not implemented")

    def close(self):
        """Close any open connections."""
        if not self.is_local and self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def connect(
    database: str,
    branch: str = "main",
    tenant: str = "main",
    project_dir: Optional[Path] = None,
    encryption_key: Optional[str] = None,
) -> CinchDB:
    """Connect to a local CinchDB database.

    Args:
        database: Database name
        branch: Branch name (default: main)
        tenant: Tenant name (default: main)
        project_dir: Path to project directory (optional, will search for .cinchdb)
        encryption_key: Encryption key for encrypted tenant databases

    Returns:
        CinchDB connection instance

    Examples:
        # Connect using current directory
        db = connect("mydb")

        # Connect to specific branch
        db = connect("mydb", "feature-branch")

        # Connect to encrypted tenant
        db = connect("mydb", tenant="customer_a", encryption_key="my-secret-key")

        # Connect with explicit project directory
        db = connect("mydb", project_dir=Path("/path/to/project"))
    """
    if project_dir is None:
        try:
            project_dir = get_project_root(Path.cwd())
        except FileNotFoundError:
            raise ValueError("No .cinchdb directory found. Run 'cinchdb init' first.")

    return CinchDB(
        database=database, branch=branch, tenant=tenant, project_dir=project_dir,
        encryption_key=encryption_key
    )


def connect_api(
    api_url: str,
    api_key: str,
    database: str,
    branch: str = "main",
    tenant: str = "main",
) -> CinchDB:
    """Connect to a remote CinchDB API.

    Args:
        api_url: Base URL of the CinchDB API
        api_key: API authentication key
        database: Database name
        branch: Branch name (default: main)
        tenant: Tenant name (default: main)

    Returns:
        CinchDB connection instance for remote API
    """
    return CinchDB(
        database=database,
        branch=branch,
        tenant=tenant,
        api_url=api_url,
        api_key=api_key,
    )



"""Unified database connection interface for CinchDB."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from cinchdb.models import Column, Change
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
    def tables(self) -> "TableManager":
        """Access table operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._table_manager is None:
            from cinchdb.managers.table import TableManager

            self._table_manager = TableManager(
                self.project_dir, self.database, self.branch, self.tenant, self.encryption_manager
            )
        return self._table_manager

    @property
    def columns(self) -> "ColumnManager":
        """Access column operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._column_manager is None:
            from cinchdb.managers.column import ColumnManager

            self._column_manager = ColumnManager(
                self.project_dir, self.database, self.branch, self.tenant, self.encryption_manager
            )
        return self._column_manager

    @property
    def views(self) -> "ViewModel":
        """Access view operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._view_manager is None:
            from cinchdb.managers.view import ViewModel

            self._view_manager = ViewModel(
                self.project_dir, self.database, self.branch, self.tenant
            )
        return self._view_manager

    @property
    def branches(self) -> "BranchManager":
        """Access branch operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._branch_manager is None:
            from cinchdb.managers.branch import BranchManager

            self._branch_manager = BranchManager(self.project_dir, self.database)
        return self._branch_manager

    @property
    def tenants(self) -> "TenantManager":
        """Access tenant operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._tenant_manager is None:
            from cinchdb.managers.tenant import TenantManager

            self._tenant_manager = TenantManager(
                self.project_dir, self.database, self.branch, self.encryption_manager
            )
        return self._tenant_manager

    @property
    def data(self) -> "DataManager":
        """Access data operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._data_manager is None:
            from cinchdb.managers.data import DataManager

            self._data_manager = DataManager(
                self.project_dir, self.database, self.branch, self.tenant, self.encryption_manager
            )
        return self._data_manager

    @property
    def codegen(self) -> "CodegenManager":
        """Access code generation operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._codegen_manager is None:
            from cinchdb.managers.codegen import CodegenManager

            self._codegen_manager = CodegenManager(
                self.project_dir, self.database, self.branch, self.tenant
            )
        return self._codegen_manager

    @property
    def merge(self) -> "MergeManager":
        """Access merge operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._merge_manager is None:
            from cinchdb.managers.merge_manager import MergeManager

            self._merge_manager = MergeManager(self.project_dir, self.database)
        return self._merge_manager

    @property
    def indexes(self) -> "IndexManager":
        """Access index operations (local only)."""
        if not self.is_local:
            raise RuntimeError(
                "Direct manager access not available for remote connections"
            )
        if self._index_manager is None:
            from cinchdb.managers.index import IndexManager

            self._index_manager = IndexManager(
                self.project_dir, self.database, self.branch
            )
        return self._index_manager

    # Convenience methods for common operations

    def query(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        skip_validation: bool = False,
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query.

        Args:
            sql: SQL query to execute
            params: Query parameters (optional)
            skip_validation: Skip SQL validation (default: False)

        Returns:
            List of result rows as dictionaries

        Raises:
            SQLValidationError: If the query contains restricted operations
        """
        # Validate query unless explicitly skipped
        if not skip_validation:
            validate_query_safe(sql)

        if self.is_local:
            if self._query_manager is None:
                from cinchdb.managers.query import QueryManager

                self._query_manager = QueryManager(
                    self.project_dir, self.database, self.branch, self.tenant, self.encryption_manager
                )
            return self._query_manager.execute(sql, params, skip_validation)
        else:
            # Remote query
            data = {"sql": sql}
            if params:
                data["params"] = params
            result = self._make_request("POST", "/query", json=data)
            return result.get("data", [])

    def create_table(self, name: str, columns: List[Column]) -> None:
        """Create a new table.

        Args:
            name: Table name
            columns: List of column definitions
        """
        if self.is_local:
            self.tables.create_table(name, columns)
        else:
            # Remote table creation
            columns_data = [
                {"name": col.name, "type": col.type, "nullable": col.nullable}
                for col in columns
            ]
            self._make_request(
                "POST", "/tables", json={"name": name, "columns": columns_data}
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
            # Initialize data manager if needed
            if self._data_manager is None:
                from cinchdb.managers.data import DataManager
                self._data_manager = DataManager(
                    self.project_dir, self.database, self.branch, self.tenant
                )
            
            # Single record
            if len(data) == 1:
                return self._data_manager.create_from_dict(table, data[0])
            
            # Multiple records - use bulk insert
            return self._data_manager.bulk_create_from_dict(table, list(data))
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
                return self.data.update_by_id(table, record_id, update_data)
            
            # Multiple records - batch update
            results = []
            for update_data in updates:
                update_copy = update_data.copy()
                record_id = update_copy.pop('id')
                try:
                    result = self.data.update_by_id(table, record_id, update_copy)
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
                success = self.data.delete_by_id(table, ids[0])
                return 1 if success else 0
            
            # Multiple records - batch delete
            deleted_count = 0
            for record_id in ids:
                success = self.data.delete_by_id(table, record_id)
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
            return self.data.delete_where(table, operator=operator, **filters)
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
            return self.data.update_where(table, data, operator=operator, **filters)
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
            return self.indexes.create_index(table, index.columns, index.name, index.unique)
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
            - materialized: Whether tenant is materialized
            - size_bytes: Size in bytes (0 if lazy)
            - size_kb: Size in KB
            - size_mb: Size in MB
            - page_size: SQLite page size (if materialized)
            - page_count: Number of pages (if materialized)
            
        Examples:
            # Get size of current tenant
            size = db.get_tenant_size()
            print(f"Current tenant uses {size['size_mb']:.2f} MB")
            
            # Get size of specific tenant
            size = db.get_tenant_size("store_west")
            if size['materialized']:
                print(f"Page size: {size['page_size']} bytes")
        """
        if self.is_local:
            tenant_to_check = tenant_name or self.tenant
            return self.tenants.get_tenant_size(tenant_to_check)
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
            return self.tenants.vacuum_tenant(tenant_to_vacuum)
        else:
            raise NotImplementedError("Remote tenant vacuum not implemented")
    
    def get_storage_info(self) -> dict:
        """Get storage size information for all tenants in current branch.
        
        Returns:
            Dictionary with:
            - tenants: List of individual tenant size info (sorted by size)
            - total_size_bytes: Total size of all materialized tenants
            - total_size_mb: Total size in MB
            - lazy_count: Number of lazy tenants
            - materialized_count: Number of materialized tenants
            
        Examples:
            # Get storage overview
            info = db.get_storage_info()
            print(f"Total storage: {info['total_size_mb']:.2f} MB")
            print(f"Materialized tenants: {info['materialized_count']}")
            print(f"Lazy tenants: {info['lazy_count']}")
            
            # List largest tenants
            for tenant in info['tenants'][:5]:  # Top 5
                if tenant['materialized']:
                    print(f"{tenant['name']}: {tenant['size_mb']:.2f} MB")
        """
        if self.is_local:
            return self.tenants.get_all_tenant_sizes()
        else:
            raise NotImplementedError("Remote storage info not implemented")
    

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



"""Unified database connection interface for CinchDB."""

from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from cinchdb.models import Column, Change
from cinchdb.core.path_utils import get_project_root
from cinchdb.utils import validate_query_safe

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
    ):
        """Initialize CinchDB connection.

        Args:
            database: Database name
            branch: Branch name (default: main)
            tenant: Tenant name (default: main)
            project_dir: Path to project directory for local connection
            api_url: Base URL for remote API connection
            api_key: API key for remote connection

        Raises:
            ValueError: If neither local nor remote connection params provided
        """
        self.database = database
        self.branch = branch
        self.tenant = tenant

        # Determine connection type
        if project_dir is not None:
            # Local connection
            self.project_dir = Path(project_dir)
            self.api_url = None
            self.api_key = None
            self.is_local = True
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
                self.project_dir, self.database, self.branch, self.tenant
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
                self.project_dir, self.database, self.branch, self.tenant
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
                self.project_dir, self.database, self.branch
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
                self.project_dir, self.database, self.branch, self.tenant
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
                    self.project_dir, self.database, self.branch, self.tenant
                )
            return self._query_manager.execute(sql, params)
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

    def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into a table.

        Args:
            table: Table name
            data: Record data as dictionary

        Returns:
            Inserted record with generated fields (id, created_at, updated_at)

        Examples:
            # Simple insert
            db.insert("users", {"name": "John", "email": "john@example.com"})
            
            # Insert with custom ID
            db.insert("products", {"id": "prod-123", "name": "Widget", "price": 9.99})
        """
        if self.is_local:
            # Initialize data manager if needed
            if self._data_manager is None:
                from cinchdb.managers.data import DataManager
                self._data_manager = DataManager(
                    self.project_dir, self.database, self.branch, self.tenant
                )
            # Use the new create_from_dict method
            return self._data_manager.create_from_dict(table, data)
        else:
            # Remote insert - use new data CRUD endpoint
            result = self._make_request(
                "POST", f"/tables/{table}/data", json={"data": data}
            )
            return result

    def update(self, table: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record in a table.

        Args:
            table: Table name
            id: Record ID
            data: Updated data as dictionary

        Returns:
            Updated record
        """
        if self.is_local:
            return self.data.update(table, id, data)
        else:
            # Remote update - use new data CRUD endpoint
            result = self._make_request(
                "PUT", f"/tables/{table}/data/{id}", json={"data": data}
            )
            return result

    def delete(self, table: str, id: str) -> None:
        """Delete a record from a table.

        Args:
            table: Table name
            id: Record ID
        """
        if self.is_local:
            self.data.delete(table, id)
        else:
            # Remote delete
            self._make_request("DELETE", f"/tables/{table}/data/{id}")

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
) -> CinchDB:
    """Connect to a local CinchDB database.

    Args:
        database: Database name
        branch: Branch name (default: main)
        tenant: Tenant name (default: main)
        project_dir: Path to project directory (optional, will search for .cinchdb)

    Returns:
        CinchDB connection instance

    Examples:
        # Connect using current directory
        db = connect("mydb")

        # Connect to specific branch
        db = connect("mydb", "feature-branch")

        # Connect with explicit project directory
        db = connect("mydb", project_dir=Path("/path/to/project"))
    """
    if project_dir is None:
        try:
            project_dir = get_project_root(Path.cwd())
        except FileNotFoundError:
            raise ValueError("No .cinchdb directory found. Run 'cinchdb init' first.")

    return CinchDB(
        database=database, branch=branch, tenant=tenant, project_dir=project_dir
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

    Examples:
        # Connect to remote API
        db = connect_api("https://api.example.com", "your-api-key", "mydb")

        # Connect to specific branch
        db = connect_api("https://api.example.com", "your-api-key", "mydb", "dev")

        # Use with context manager
        with connect_api("https://api.example.com", "key", "mydb") as db:
            results = db.query("SELECT * FROM users")
    """
    return CinchDB(
        database=database,
        branch=branch,
        tenant=tenant,
        api_url=api_url,
        api_key=api_key,
    )

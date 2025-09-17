"""Query execution manager for CinchDB - handles SQL queries with type-safe returns."""

from pathlib import Path
from typing import List, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from cinchdb.core.connection import DatabaseConnection
from cinchdb.utils import validate_query_safe
from cinchdb.managers.tenant import TenantManager

T = TypeVar("T", bound=BaseModel)


class QueryManager:
    """Manages SQL query execution with support for typed returns."""

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main",
        encryption_manager=None
    ):
        """Initialize query manager.

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
        # Initialize tenant manager for lazy tenant handling
        self.tenant_manager = TenantManager(project_root, database, branch, encryption_manager)
    
    def _is_write_query(self, sql: str) -> bool:
        """Check if a SQL query is a write operation.
        
        Args:
            sql: SQL query string
            
        Returns:
            True if query performs writes, False otherwise
        """
        sql_upper = sql.strip().upper()
        write_keywords = [
            "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "TRUNCATE", "REPLACE", "MERGE"
        ]
        return any(sql_upper.startswith(keyword) for keyword in write_keywords)


    def query_typed(
        self,
        sql: str,
        model: Type[T],
        params: Optional[Union[tuple, dict]] = None,
        strict: bool = True,
    ) -> List[T]:
        """Execute a SELECT query and return results as typed model instances.

        Args:
            sql: SQL query to execute
            model: Pydantic model class to validate results against
            params: Optional query parameters
            strict: If True, raise on validation errors; if False, skip invalid rows

        Returns:
            List of model instances

        Raises:
            ValueError: If query is not a SELECT query
            ValidationError: If strict=True and validation fails
            Exception: If query execution fails
        """
        # Ensure this is a SELECT query
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("execute_typed can only be used with SELECT queries")

        # Execute query and get raw results
        # Validate query unless explicitly skipped
        validate_query_safe(sql)

        # Ensure this is a SELECT query
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("execute_typed can only be used with SELECT queries")

        # Get appropriate database path based on operation type (read for SELECT)
        db_path = self.tenant_manager.get_tenant_db_path_for_operation(
            self.tenant, is_write=False
        )

        with DatabaseConnection(db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, params)
            raw_rows = cursor.fetchall()
            rows = [dict(row) for row in raw_rows]

        # Convert to typed results
        typed_results = []
        validation_errors = []

        for i, row in enumerate(rows):
            try:
                instance = model(**row)
                typed_results.append(instance)
            except ValidationError as e:
                if strict:
                    # Re-raise with more context
                    raise ValueError(
                        f"Row {i} failed validation for {model.__name__}: {str(e)}"
                    )
                else:
                    validation_errors.append((i, str(e)))

        # If we had validation errors in non-strict mode, we could log them
        # For now, we'll just return the valid results

        return typed_results


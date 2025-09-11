"""Query execution manager for CinchDB - handles SQL queries with type-safe returns."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar, Union

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

    def execute(
        self,
        sql: str,
        params: Optional[Union[tuple, dict]] = None,
        skip_validation: bool = False,
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as dictionaries.

        Args:
            sql: SQL query to execute
            params: Optional query parameters (tuple for positional, dict for named)
            skip_validation: Skip SQL validation (default: False)

        Returns:
            List of dictionaries representing rows

        Raises:
            SQLValidationError: If query contains restricted operations
            Exception: If query execution fails
        """
        # Validate query unless explicitly skipped
        if not skip_validation:
            validate_query_safe(sql)

        # Note: The original code had SELECT-only validation, but we're now more permissive
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError(
                "execute() can only be used with SELECT queries. Use execute_non_query() for INSERT/UPDATE/DELETE operations."
            )

        # Get appropriate database path based on operation type (read for SELECT)
        db_path = self.tenant_manager.get_tenant_db_path_for_operation(
            self.tenant, is_write=False
        )
        
        with DatabaseConnection(db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_typed(
        self,
        sql: str,
        model: Type[T],
        params: Optional[Union[tuple, dict]] = None,
        strict: bool = True,
    ) -> List[T]:
        """Execute a SQL query and return results as typed model instances.

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
        rows = self.execute(sql, params)

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

    def execute_one(
        self, sql: str, params: Optional[Union[tuple, dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a SQL query and return at most one result as a dictionary.

        Args:
            sql: SQL query to execute
            params: Optional query parameters

        Returns:
            Dictionary representing a single row, or None if no results

        Raises:
            Exception: If query execution fails
        """
        results = self.execute(sql, params)
        return results[0] if results else None

    def execute_one_typed(
        self,
        sql: str,
        model: Type[T],
        params: Optional[Union[tuple, dict]] = None,
        strict: bool = True,
    ) -> Optional[T]:
        """Execute a SQL query and return at most one result as a typed model instance.

        Args:
            sql: SQL query to execute
            model: Pydantic model class to validate result against
            params: Optional query parameters
            strict: If True, raise on validation errors

        Returns:
            Model instance or None if no results

        Raises:
            ValueError: If query is not a SELECT query
            ValidationError: If strict=True and validation fails
            Exception: If query execution fails
        """
        results = self.execute_typed(sql, model, params, strict)
        return results[0] if results else None

    def execute_non_query(
        self,
        sql: str,
        params: Optional[Union[tuple, dict]] = None,
        skip_validation: bool = False,
    ) -> int:
        """Execute a non-SELECT SQL query (INSERT, UPDATE, DELETE, etc.).

        Args:
            sql: SQL query to execute
            params: Optional query parameters
            skip_validation: Skip SQL validation (default: False)

        Returns:
            Number of rows affected

        Raises:
            SQLValidationError: If query contains restricted operations
            Exception: If query execution fails
        """
        # Validate query unless explicitly skipped
        if not skip_validation:
            validate_query_safe(sql)

        # Get appropriate database path based on operation type (write for non-SELECT)
        db_path = self.tenant_manager.get_tenant_db_path_for_operation(
            self.tenant, is_write=True
        )

        with DatabaseConnection(db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, params)
            affected_rows = cursor.rowcount
            conn.commit()
            return affected_rows

    def execute_many(self, sql: str, params_list: List[Union[tuple, dict]]) -> int:
        """Execute the same SQL query multiple times with different parameters.

        Args:
            sql: SQL query to execute
            params_list: List of parameter sets

        Returns:
            Total number of rows affected

        Raises:
            Exception: If query execution fails
        """
        total_affected = 0

        # Determine if this is a write operation
        is_write = self._is_write_query(sql)
        
        # Get appropriate database path
        db_path = self.tenant_manager.get_tenant_db_path_for_operation(
            self.tenant, is_write=is_write
        )

        with DatabaseConnection(db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            try:
                for params in params_list:
                    cursor = conn.execute(sql, params)
                    total_affected += cursor.rowcount
                conn.commit()
                return total_affected
            except Exception:
                conn.rollback()
                raise

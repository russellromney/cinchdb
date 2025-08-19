"""Query execution manager for CinchDB - handles SQL queries with type-safe returns."""

from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.utils import validate_query_safe

T = TypeVar("T", bound=BaseModel)


class QueryManager:
    """Manages SQL query execution with support for typed returns."""

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main"
    ):
        """Initialize query manager.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
            tenant: Tenant name (default: main)
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.db_path = get_tenant_db_path(project_root, database, branch, tenant)

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

        with DatabaseConnection(self.db_path) as conn:
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

        with DatabaseConnection(self.db_path) as conn:
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

        with DatabaseConnection(self.db_path) as conn:
            try:
                for params in params_list:
                    cursor = conn.execute(sql, params)
                    total_affected += cursor.rowcount
                conn.commit()
                return total_affected
            except Exception:
                conn.rollback()
                raise

"""Query router for CinchDB API."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel

from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.connection import DatabaseConnection
from cinchdb.api.auth import (
    AuthContext,
    require_read_permission,
    require_write_permission,
)
from cinchdb.utils import validate_sql_query, SQLValidationError, SQLOperation


router = APIRouter()


class QueryRequest(BaseModel):
    """Request to execute a query."""

    sql: str
    limit: Optional[int] = None


class QueryResult(BaseModel):
    """Query execution result."""

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    affected_rows: Optional[int] = None


@router.post("/execute")
async def execute_query(
    request: QueryRequest,
    database: str = QueryParam(..., description="Database name"),
    branch: str = QueryParam(..., description="Branch name"),
    tenant: str = QueryParam(..., description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission),
) -> QueryResult:
    """Execute a SQL query.

    SELECT queries require read permission.
    INSERT/UPDATE/DELETE queries require write permission.
    """
    db_name = database
    branch_name = branch

    # Validate the SQL query first
    try:
        is_valid, error_msg, operation = validate_sql_query(request.sql)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if this is a write operation based on validated operation
    sql_upper = request.sql.strip().upper()
    is_write = operation in (SQLOperation.INSERT, SQLOperation.UPDATE, SQLOperation.DELETE)

    if is_write:
        # Require write permission for write operations
        await require_write_permission(auth, branch_name)
    else:
        # Check branch permissions for read
        await require_read_permission(auth, branch_name)

    # Add LIMIT if specified and not already present
    query_sql = request.sql
    if request.limit and "LIMIT" not in sql_upper:
        query_sql = f"{request.sql} LIMIT {request.limit}"

    # Get database path
    db_path = get_tenant_db_path(auth.project_dir, db_name, branch_name, tenant)

    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(query_sql)

            # Check if this is a SELECT query
            is_select = sql_upper.startswith("SELECT")

            if is_select:
                rows = cursor.fetchall()

                # Get column names
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )

                # Convert rows to lists (from sqlite3.Row objects)
                row_data = []
                for row in rows:
                    row_data.append(list(row))

                return QueryResult(
                    columns=columns,
                    rows=row_data,
                    row_count=len(rows),
                    affected_rows=None,
                )
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                affected = cursor.rowcount

                return QueryResult(
                    columns=[], rows=[], row_count=0, affected_rows=affected
                )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@router.get("/tables/{table}/data")
async def get_table_data(
    table: str,
    database: str = QueryParam(..., description="Database name"),
    branch: str = QueryParam(..., description="Branch name"),
    tenant: str = QueryParam(..., description="Tenant name"),
    limit: int = QueryParam(100, description="Maximum rows to return"),
    offset: int = QueryParam(0, description="Number of rows to skip"),
    auth: AuthContext = Depends(require_read_permission),
) -> QueryResult:
    """Get data from a specific table with pagination."""
    # Build query
    query = QueryRequest(
        sql=f"SELECT * FROM {table} LIMIT {limit} OFFSET {offset}",
        limit=None,  # Already included in SQL
    )

    return await execute_query(query, database, branch, tenant, auth)


@router.get("/tables/{table}/count")
async def get_table_count(
    table: str,
    database: str = QueryParam(..., description="Database name"),
    branch: str = QueryParam(..., description="Branch name"),
    tenant: str = QueryParam(..., description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission),
) -> Dict[str, int]:
    """Get the row count for a table."""
    # Build query
    query = QueryRequest(sql=f"SELECT COUNT(*) as count FROM {table}", limit=None)

    result = await execute_query(query, database, branch, tenant, auth)

    if result.rows and result.rows[0]:
        return {"count": result.rows[0][0]}
    return {"count": 0}

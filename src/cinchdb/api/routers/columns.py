"""Columns router for CinchDB API."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from cinchdb.core.database import CinchDB
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column
from cinchdb.api.auth import (
    AuthContext,
    require_write_permission,
    require_read_permission,
)


router = APIRouter()


class ColumnInfo(BaseModel):
    """Column information."""

    name: str
    type: str
    nullable: bool
    default: Optional[str]
    primary_key: bool
    unique: bool


class AddColumnRequest(BaseModel):
    """Request to add a column."""

    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None


class RenameColumnRequest(BaseModel):
    """Request to rename a column."""

    old_name: str
    new_name: str


@router.get("/{table}/columns", response_model=List[ColumnInfo])
async def list_columns(
    table: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission),
):
    """List all columns in a table."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_read_permission(auth, branch_name)

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        columns = db.columns.list_columns(table)

        result = []
        for col in columns:
            result.append(
                ColumnInfo(
                    name=col.name,
                    type=col.type,
                    nullable=col.nullable,
                    default=col.default,
                    primary_key=col.primary_key,
                    unique=col.unique,
                )
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{table}/columns")
async def add_column(
    table: str,
    request: AddColumnRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Add a new column to a table."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_write_permission(auth, branch_name)

    # Validate type
    if request.type.upper() not in ["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"]:
        raise HTTPException(
            status_code=400, detail=f"Invalid column type: {request.type}"
        )

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        column = Column(
            name=request.name,
            type=request.type.upper(),
            nullable=request.nullable,
            default=request.default,
        )
        db.columns.add_column(table, column)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        return {"message": f"Added column '{request.name}' to table '{table}'"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{table}/columns/{column}")
async def drop_column(
    table: str,
    column: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Drop a column from a table."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_write_permission(auth, branch_name)

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        db.columns.drop_column(table, column)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        return {"message": f"Dropped column '{column}' from table '{table}'"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{table}/columns/rename")
async def rename_column(
    table: str,
    request: RenameColumnRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Rename a column in a table."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_write_permission(auth, branch_name)

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        db.columns.rename_column(table, request.old_name, request.new_name)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        return {
            "message": f"Renamed column '{request.old_name}' to '{request.new_name}' in table '{table}'"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{table}/columns/{column}")
async def get_column_info(
    table: str,
    column: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission),
) -> ColumnInfo:
    """Get information about a specific column."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_read_permission(auth, branch_name)

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        col = db.columns.get_column_info(table, column)

        return ColumnInfo(
            name=col.name,
            type=col.type,
            nullable=col.nullable,
            default=col.default,
            primary_key=col.primary_key,
            unique=col.unique,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

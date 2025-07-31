"""Tables router for CinchDB API."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from cinchdb.core.database import CinchDB
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.models import Column, ForeignKeyRef
from cinchdb.api.auth import (
    AuthContext,
    require_write_permission,
    require_read_permission,
)


router = APIRouter()


class ForeignKeySchema(BaseModel):
    """Foreign key schema for requests."""
    
    table: str
    column: str = "id"
    on_delete: str = "RESTRICT"
    on_update: str = "RESTRICT"


class ColumnSchema(BaseModel):
    """Column schema for requests."""

    name: str
    type: str
    nullable: bool = False
    default: Optional[str] = None
    primary_key: bool = False
    unique: bool = False
    foreign_key: Optional[ForeignKeySchema] = None


class TableInfo(BaseModel):
    """Table information."""

    name: str
    column_count: int
    columns: List[ColumnSchema]


class CreateTableRequest(BaseModel):
    """Request to create a table."""

    name: str
    columns: List[ColumnSchema]


class CopyTableRequest(BaseModel):
    """Request to copy a table."""

    source: str
    target: str
    copy_data: bool = True


@router.get("/", response_model=List[TableInfo])
async def list_tables(
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission),
):
    """List all tables in a branch."""
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
        tables = db.tables.list_tables()

        result = []
        for table in tables:
            # Convert columns
            columns = []
            for col in table.columns:
                # Convert foreign key if present
                fk_schema = None
                if col.foreign_key:
                    fk_schema = ForeignKeySchema(
                        table=col.foreign_key.table,
                        column=col.foreign_key.column,
                        on_delete=col.foreign_key.on_delete,
                        on_update=col.foreign_key.on_update,
                    )
                
                columns.append(
                    ColumnSchema(
                        name=col.name,
                        type=col.type,
                        nullable=col.nullable,
                        default=col.default,
                        primary_key=col.primary_key,
                        unique=col.unique,
                        foreign_key=fk_schema,
                    )
                )

            # Count user-defined columns
            user_columns = [
                c
                for c in table.columns
                if c.name not in ["id", "created_at", "updated_at"]
            ]

            result.append(
                TableInfo(
                    name=table.name, column_count=len(user_columns), columns=columns
                )
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
async def create_table(
    request: CreateTableRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Create a new table."""
    db_name = database
    branch_name = branch

    # Check branch permissions
    await require_write_permission(auth, branch_name)

    # Convert columns
    columns = []
    for col_schema in request.columns:
        # Validate type
        if col_schema.type.upper() not in [
            "TEXT",
            "INTEGER",
            "REAL",
            "BLOB",
            "NUMERIC",
        ]:
            raise HTTPException(
                status_code=400, detail=f"Invalid column type: {col_schema.type}"
            )

        # Convert foreign key if present
        fk_ref = None
        if col_schema.foreign_key:
            # Validate FK action
            if col_schema.foreign_key.on_delete not in ["CASCADE", "SET NULL", "RESTRICT", "NO ACTION"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid on_delete action: {col_schema.foreign_key.on_delete}"
                )
            if col_schema.foreign_key.on_update not in ["CASCADE", "SET NULL", "RESTRICT", "NO ACTION"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid on_update action: {col_schema.foreign_key.on_update}"
                )
            
            fk_ref = ForeignKeyRef(
                table=col_schema.foreign_key.table,
                column=col_schema.foreign_key.column,
                on_delete=col_schema.foreign_key.on_delete,
                on_update=col_schema.foreign_key.on_update,
            )
        
        columns.append(
            Column(
                name=col_schema.name,
                type=col_schema.type.upper(),
                nullable=col_schema.nullable,
                default=col_schema.default,
                primary_key=col_schema.primary_key,
                unique=col_schema.unique,
                foreign_key=fk_ref,
            )
        )

    try:
        db = CinchDB(
            database=db_name,
            branch=branch_name,
            tenant="main",
            project_dir=auth.project_dir,
        )
        db.tables.create_table(request.name, columns)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        return {
            "message": f"Created table '{request.name}' with {len(columns)} columns"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def delete_table(
    name: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Delete a table."""
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
        db.tables.delete_table(name)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        return {"message": f"Deleted table '{name}'"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/copy")
async def copy_table(
    request: CopyTableRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Copy a table to a new table."""
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
        db.tables.copy_table(request.source, request.target, request.copy_data)

        # Apply to all tenants if requested
        if apply:
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applier.apply_all_unapplied()

        data_msg = "with data" if request.copy_data else "without data"
        return {
            "message": f"Copied table '{request.source}' to '{request.target}' {data_msg}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}")
async def get_table_info(
    name: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission),
) -> TableInfo:
    """Get information about a specific table."""
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
        table = db.tables.get_table(name)

        # Convert columns
        columns = []
        for col in table.columns:
            # Convert foreign key if present
            fk_schema = None
            if col.foreign_key:
                fk_schema = ForeignKeySchema(
                    table=col.foreign_key.table,
                    column=col.foreign_key.column,
                    on_delete=col.foreign_key.on_delete,
                    on_update=col.foreign_key.on_update,
                )
            
            columns.append(
                ColumnSchema(
                    name=col.name,
                    type=col.type,
                    nullable=col.nullable,
                    default=col.default,
                    primary_key=col.primary_key,
                    unique=col.unique,
                    foreign_key=fk_schema,
                )
            )

        # Count user-defined columns
        user_columns = [
            c for c in table.columns if c.name not in ["id", "created_at", "updated_at"]
        ]

        return TableInfo(
            name=table.name, column_count=len(user_columns), columns=columns
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

"""Views router for CinchDB API."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from cinchdb.config import Config
from cinchdb.managers.view import ViewModel
from cinchdb.managers.change_applier import ChangeApplier
from cinchdb.api.auth import AuthContext, require_write_permission, require_read_permission


router = APIRouter()


class ViewInfo(BaseModel):
    """View information."""
    name: str
    sql_statement: str
    sql_length: int
    description: Optional[str]


class CreateViewRequest(BaseModel):
    """Request to create a view."""
    name: str
    sql: str
    description: Optional[str] = None


class UpdateViewRequest(BaseModel):
    """Request to update a view."""
    sql: str
    description: Optional[str] = None


@router.get("/", response_model=List[ViewInfo])
async def list_views(
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    branch: Optional[str] = Query(None, description="Branch name (defaults to active)"),
    tenant: str = Query("main", description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """List all views in a branch."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    branch_name = branch or config_data.active_branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        view_mgr = ViewModel(auth.project_dir, db_name, branch_name, tenant)
        views = view_mgr.list_views()
        
        result = []
        for view in views:
            result.append(ViewInfo(
                name=view.name,
                sql_statement=view.sql_statement,
                sql_length=len(view.sql_statement) if view.sql_statement else 0,
                description=view.description
            ))
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
async def create_view(
    request: CreateViewRequest,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    branch: Optional[str] = Query(None, description="Branch name (defaults to active)"),
    tenant: str = Query("main", description="Tenant name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Create a new view."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    branch_name = branch or config_data.active_branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        view_mgr = ViewModel(auth.project_dir, db_name, branch_name, tenant)
        view = view_mgr.create_view(request.name, request.sql, request.description)
        
        # Apply to all tenants if requested
        if apply and tenant == "main":
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
        
        return {"message": f"Created view '{request.name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{name}")
async def update_view(
    name: str,
    request: UpdateViewRequest,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    branch: Optional[str] = Query(None, description="Branch name (defaults to active)"),
    tenant: str = Query("main", description="Tenant name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Update an existing view."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    branch_name = branch or config_data.active_branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        view_mgr = ViewModel(auth.project_dir, db_name, branch_name, tenant)
        view_mgr.update_view(name, request.sql, request.description)
        
        # Apply to all tenants if requested
        if apply and tenant == "main":
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
        
        return {"message": f"Updated view '{name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def delete_view(
    name: str,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    branch: Optional[str] = Query(None, description="Branch name (defaults to active)"),
    tenant: str = Query("main", description="Tenant name"),
    apply: bool = Query(True, description="Apply changes to all tenants"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Delete a view."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    branch_name = branch or config_data.active_branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        view_mgr = ViewModel(auth.project_dir, db_name, branch_name, tenant)
        view_mgr.delete_view(name)
        
        # Apply to all tenants if requested
        if apply and tenant == "main":
            applier = ChangeApplier(auth.project_dir, db_name, branch_name)
            applied = applier.apply_all_unapplied()
        
        return {"message": f"Deleted view '{name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}")
async def get_view_info(
    name: str,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    branch: Optional[str] = Query(None, description="Branch name (defaults to active)"),
    tenant: str = Query("main", description="Tenant name"),
    auth: AuthContext = Depends(require_read_permission)
) -> ViewInfo:
    """Get information about a specific view."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    branch_name = branch or config_data.active_branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        view_mgr = ViewModel(auth.project_dir, db_name, branch_name, tenant)
        view = view_mgr.get_view(name)
        
        return ViewInfo(
            name=view.name,
            sql_statement=view.sql_statement,
            sql_length=len(view.sql_statement) if view.sql_statement else 0,
            description=view.description
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
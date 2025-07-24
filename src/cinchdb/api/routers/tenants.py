"""Tenants router for CinchDB API."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from cinchdb.core.database import CinchDB
from cinchdb.api.auth import AuthContext, require_write_permission, require_read_permission


router = APIRouter()


class TenantInfo(BaseModel):
    """Tenant information."""
    name: str
    size_bytes: int
    is_protected: bool


class CreateTenantRequest(BaseModel):
    """Request to create a tenant."""
    name: str


class RenameTenantRequest(BaseModel):
    """Request to rename a tenant."""
    new_name: str


class CopyTenantRequest(BaseModel):
    """Request to copy a tenant."""
    source: str
    target: str
    copy_data: bool = True


@router.get("/", response_model=List[TenantInfo])
async def list_tenants(
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """List all tenants in a branch."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        tenants = db.tenants.list_tenants()
        
        result = []
        for tenant in tenants:
            # Get tenant size
            db_path = (auth.project_dir / ".cinchdb" / "databases" / db_name / 
                      "branches" / branch_name / "tenants" / f"{tenant}.db")
            size = db_path.stat().st_size if db_path.exists() else 0
            
            result.append(TenantInfo(
                name=tenant,
                size_bytes=size,
                is_protected=tenant == "main"
            ))
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
async def create_tenant(
    request: CreateTenantRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Create a new tenant."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        db.tenants.create_tenant(request.name)
        
        return {"message": f"Created tenant '{request.name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def delete_tenant(
    name: str,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Delete a tenant."""
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot delete the main tenant")
    
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        db.tenants.delete_tenant(name)
        
        return {"message": f"Deleted tenant '{name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{name}/rename")
async def rename_tenant(
    name: str,
    request: RenameTenantRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Rename a tenant."""
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot rename the main tenant")
    
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        db.tenants.rename_tenant(name, request.new_name)
        
        return {"message": f"Renamed tenant '{name}' to '{request.new_name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/copy")
async def copy_tenant(
    request: CopyTenantRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Copy a tenant to a new tenant."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_write_permission(auth, branch_name)
    
    try:
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        db.tenants.copy_tenant(request.source, request.target, request.copy_data)
        
        data_msg = "with data" if request.copy_data else "without data"
        return {"message": f"Copied tenant '{request.source}' to '{request.target}' {data_msg}"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
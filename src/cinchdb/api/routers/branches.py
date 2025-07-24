"""Branches router for CinchDB API."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from cinchdb.config import Config
from cinchdb.managers.branch import BranchManager
from cinchdb.api.auth import AuthContext, require_write_permission, require_read_permission


router = APIRouter()


class BranchInfo(BaseModel):
    """Branch information."""
    name: str
    parent: Optional[str]
    created_at: datetime
    is_active: bool
    tenant_count: int


class CreateBranchRequest(BaseModel):
    """Request to create a branch."""
    name: str
    source: str = "main"


@router.get("/", response_model=List[BranchInfo])
async def list_branches(
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    auth: AuthContext = Depends(require_read_permission)
):
    """List all branches in a database."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    
    try:
        branch_mgr = BranchManager(auth.project_dir, db_name)
        branches = branch_mgr.list_branches()
        
        result = []
        for branch in branches:
            # Count tenants
            tenants_dir = (auth.project_dir / ".cinchdb" / "databases" / 
                          db_name / "branches" / branch.name / "tenants")
            tenant_count = len(list(tenants_dir.glob("*.db"))) if tenants_dir.exists() else 0
            
            result.append(BranchInfo(
                name=branch.name,
                parent=branch.parent,
                created_at=branch.created_at,
                is_active=branch.name == config_data.active_branch,
                tenant_count=tenant_count
            ))
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
async def create_branch(
    request: CreateBranchRequest,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Create a new branch."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    
    # Check branch permissions
    if auth.api_key.branches and request.source not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied for source branch '{request.source}'"
        )
    
    if auth.api_key.branches and request.name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot create branch '{request.name}' - not in allowed branches"
        )
    
    try:
        branch_mgr = BranchManager(auth.project_dir, db_name)
        branch = branch_mgr.create_branch(request.name, request.source)
        
        return {
            "message": f"Created branch '{request.name}' from '{request.source}'",
            "branch": {
                "name": branch.name,
                "parent": branch.parent,
                "created_at": branch.created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def delete_branch(
    name: str,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Delete a branch."""
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot delete the main branch")
    
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    
    # Check branch permissions
    if auth.api_key.branches and name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied for branch '{name}'"
        )
    
    try:
        branch_mgr = BranchManager(auth.project_dir, db_name)
        branch_mgr.delete_branch(name)
        
        # If this was the active branch, switch to main
        if config_data.active_branch == name and config_data.active_database == db_name:
            config_data.active_branch = "main"
            config.save(config_data)
        
        return {"message": f"Deleted branch '{name}'"}
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/switch/{name}")
async def switch_branch(
    name: str,
    database: Optional[str] = Query(None, description="Database name (defaults to active)"),
    auth: AuthContext = Depends(require_write_permission)
):
    """Switch to a different branch."""
    config = Config(auth.project_dir)
    config_data = config.load()
    
    db_name = database or config_data.active_database
    
    # Check branch permissions
    if auth.api_key.branches and name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied for branch '{name}'"
        )
    
    try:
        branch_mgr = BranchManager(auth.project_dir, db_name)
        branch_mgr.switch_branch(name)
        
        return {
            "message": f"Switched to branch '{name}'",
            "active_database": db_name,
            "active_branch": name
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
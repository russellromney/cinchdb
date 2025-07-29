"""Branches router for CinchDB API."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from cinchdb.config import Config
from cinchdb.core.database import CinchDB
from cinchdb.managers.merge_manager import MergeError
from cinchdb.managers.change_comparator import ChangeComparator
from cinchdb.api.auth import (
    AuthContext,
    require_write_permission,
    require_read_permission,
)


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


class MergeBranchRequest(BaseModel):
    """Request to merge branches."""

    source: str
    target: str
    force: bool = False


class BranchComparisonResult(BaseModel):
    """Result of branch comparison."""

    source_branch: str
    target_branch: str
    source_only_changes: int
    target_only_changes: int
    common_ancestor: Optional[str]
    can_fast_forward: bool


class MergeCheckResult(BaseModel):
    """Result of merge feasibility check."""

    can_merge: bool
    reason: Optional[str] = None
    merge_type: Optional[str] = None
    changes_to_merge: Optional[int] = None
    target_changes: Optional[int] = None
    conflicts: Optional[List[Dict[str, Any]]] = None


@router.get("/", response_model=List[BranchInfo])
async def list_branches(
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_read_permission),
):
    """List all branches in a database."""
    config = Config(auth.project_dir)
    config_data = config.load()

    db_name = database

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        branches = db.branches.list_branches()

        result = []
        for branch in branches:
            # Count tenants
            tenants_dir = (
                auth.project_dir
                / ".cinchdb"
                / "databases"
                / db_name
                / "branches"
                / branch.name
                / "tenants"
            )
            tenant_count = (
                len(list(tenants_dir.glob("*.db"))) if tenants_dir.exists() else 0
            )

            result.append(
                BranchInfo(
                    name=branch.name,
                    parent=branch.parent_branch,
                    created_at=branch.metadata.get("created_at", "Unknown"),
                    is_active=branch.name == config_data.active_branch
                    and db_name == config_data.active_database,
                    tenant_count=tenant_count,
                )
            )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/")
async def create_branch(
    request: CreateBranchRequest,
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Create a new branch."""
    db_name = database

    # Check branch permissions
    if auth.api_key.branches and request.source not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied for source branch '{request.source}'",
        )

    if auth.api_key.branches and request.name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot create branch '{request.name}' - not in allowed branches",
        )

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        branch = db.branches.create_branch(request.name, request.source)

        return {
            "message": f"Created branch '{request.name}' from '{request.source}'",
            "branch": {
                "name": branch.name,
                "parent": branch.parent_branch,
                "created_at": branch.metadata.get("created_at","Unknown"),
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
async def delete_branch(
    name: str,
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Delete a branch."""
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot delete the main branch")

    config = Config(auth.project_dir)
    config_data = config.load()

    db_name = database

    # Check branch permissions
    if auth.api_key.branches and name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403, detail=f"Access denied for branch '{name}'"
        )

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        db.branches.delete_branch(name)

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
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Switch to a different branch."""
    db_name = database

    # Check branch permissions
    if auth.api_key.branches and name not in auth.api_key.branches:
        raise HTTPException(
            status_code=403, detail=f"Access denied for branch '{name}'"
        )

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        db.branches.switch_branch(name)

        return {
            "message": f"Switched to branch '{name}'",
            "active_database": db_name,
            "active_branch": name,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{source}/compare/{target}", response_model=BranchComparisonResult)
async def compare_branches(
    source: str,
    target: str,
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_read_permission),
):
    """Compare two branches to see their differences."""
    db_name = database

    # Check branch permissions
    await require_read_permission(auth, source)
    await require_read_permission(auth, target)

    try:
        comparator = ChangeComparator(auth.project_dir, db_name)

        # Get divergent changes
        source_only, target_only = comparator.get_divergent_changes(source, target)

        # Find common ancestor
        common_ancestor = comparator.find_common_ancestor(source, target)

        # Check if fast-forward merge is possible
        can_fast_forward = comparator.can_fast_forward_merge(source, target)

        return BranchComparisonResult(
            source_branch=source,
            target_branch=target,
            source_only_changes=len(source_only),
            target_only_changes=len(target_only),
            common_ancestor=common_ancestor,
            can_fast_forward=can_fast_forward,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{source}/can-merge/{target}", response_model=MergeCheckResult)
async def check_merge_feasibility(
    source: str,
    target: str,
    database: str = Query(..., description="Database name"),
    auth: AuthContext = Depends(require_read_permission),
):
    """Check if source branch can be merged into target branch."""
    db_name = database

    # Check branch permissions
    await require_read_permission(auth, source)
    await require_read_permission(auth, target)

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        result = db.merge.can_merge(source, target)

        return MergeCheckResult(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{source}/merge/{target}")
async def merge_branches(
    source: str,
    target: str,
    database: str = Query(..., description="Database name"),
    force: bool = Query(False, description="Force merge even with conflicts"),
    dry_run: bool = Query(False, description="Preview merge without executing"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Merge source branch into target branch."""
    db_name = database

    # Check branch permissions for both branches
    await require_write_permission(auth, source)
    await require_write_permission(auth, target)

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )

        if target == "main":
            # Use the merge_into_main method for main branch protection
            result = db.merge.merge_into_main(source, force=force, dry_run=dry_run)
        else:
            # Use internal merge method for non-main branches
            result = db.merge._merge_branches_internal(
                source, target, force=force, dry_run=dry_run
            )

        return result

    except MergeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{source}/merge-into-main")
async def merge_into_main_branch(
    source: str,
    database: str = Query(..., description="Database name"),
    force: bool = Query(False, description="Force merge even with conflicts"),
    dry_run: bool = Query(False, description="Preview merge without executing"),
    auth: AuthContext = Depends(require_write_permission),
):
    """Merge source branch into the main branch with additional protections."""
    db_name = database

    # Check branch permissions
    await require_write_permission(auth, source)
    await require_write_permission(auth, "main")

    try:
        db = CinchDB(
            database=db_name, branch="main", tenant="main", project_dir=auth.project_dir
        )
        result = db.merge.merge_into_main(source, force=force, dry_run=dry_run)

        return result

    except MergeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

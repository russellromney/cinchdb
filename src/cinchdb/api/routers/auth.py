"""Authentication router for CinchDB API."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cinchdb.api.auth import (
    APIKeyManager,
    AuthContext,
    verify_api_key,
    get_current_project,
)
from pathlib import Path


router = APIRouter()


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating API key."""

    name: str
    permissions: str = "read"  # "read" or "write"
    branches: List[str] = None


class APIKeyResponse(BaseModel):
    """Response model for API key."""

    key: str
    name: str
    created_at: str
    permissions: str
    branches: List[str] = None
    active: bool


@router.post("/keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    project_dir: Path = Depends(get_current_project),
    auth: AuthContext = Depends(verify_api_key),
):
    """Create a new API key (requires existing API key with write permission)."""
    # Only write permission can create new keys
    if auth.api_key.permissions != "write":
        raise HTTPException(
            status_code=403, detail="Write permission required to create API keys"
        )

    manager = APIKeyManager(project_dir)

    # Validate permissions
    if request.permissions not in ["read", "write"]:
        raise HTTPException(
            status_code=400, detail="Invalid permissions. Must be 'read' or 'write'"
        )

    api_key = manager.create_key(
        name=request.name, permissions=request.permissions, branches=request.branches
    )

    return APIKeyResponse(
        key=api_key.key,
        name=api_key.name,
        created_at=api_key.created_at.isoformat(),
        permissions=api_key.permissions,
        branches=api_key.branches,
        active=api_key.active,
    )


@router.get("/keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    project_dir: Path = Depends(get_current_project),
    auth: AuthContext = Depends(verify_api_key),
):
    """List all API keys (requires write permission)."""
    # Only write permission can list keys
    if auth.api_key.permissions != "write":
        raise HTTPException(
            status_code=403, detail="Write permission required to list API keys"
        )

    manager = APIKeyManager(project_dir)
    keys = manager.list_keys()

    return [
        APIKeyResponse(
            key=k.key,
            name=k.name,
            created_at=k.created_at.isoformat(),
            permissions=k.permissions,
            branches=k.branches,
            active=k.active,
        )
        for k in keys
    ]


@router.delete("/keys/{key}")
async def revoke_api_key(
    key: str,
    project_dir: Path = Depends(get_current_project),
    auth: AuthContext = Depends(verify_api_key),
):
    """Revoke an API key (requires write permission)."""
    # Only write permission can revoke keys
    if auth.api_key.permissions != "write":
        raise HTTPException(
            status_code=403, detail="Write permission required to revoke API keys"
        )

    # Cannot revoke your own key
    if auth.api_key.key == key:
        raise HTTPException(status_code=400, detail="Cannot revoke your own API key")

    manager = APIKeyManager(project_dir)
    if not manager.revoke_key(key):
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked"}


@router.get("/me")
async def get_current_key_info(auth: AuthContext = Depends(verify_api_key)):
    """Get information about the current API key."""
    return APIKeyResponse(
        key=auth.api_key.key,
        name=auth.api_key.name,
        created_at=auth.api_key.created_at.isoformat(),
        permissions=auth.api_key.permissions,
        branches=auth.api_key.branches,
        active=auth.api_key.active,
    )

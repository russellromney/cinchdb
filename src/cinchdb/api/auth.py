"""Authentication and API key management for CinchDB API."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Literal
from pathlib import Path

from fastapi import HTTPException, Security, Depends, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from cinchdb.config import Config
from cinchdb.core.path_utils import get_project_root


# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKey(BaseModel):
    """API key model."""

    key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    permissions: Literal["read", "write"] = "read"
    branches: Optional[List[str]] = None  # None means all branches
    active: bool = True


class APIKeyManager:
    """Manages API keys in the project configuration."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize API key manager.

        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir or Path.cwd()
        self.config = Config(self.project_dir)

    def create_key(
        self,
        name: str,
        permissions: Literal["read", "write"] = "read",
        branches: Optional[List[str]] = None,
    ) -> APIKey:
        """Create a new API key.

        Args:
            name: Name for the API key
            permissions: Permission level (read or write)
            branches: List of allowed branches (None for all)

        Returns:
            Created API key
        """
        api_key = APIKey(name=name, permissions=permissions, branches=branches)

        # Load config and add key
        config_data = self.config.load()
        if not config_data.api_keys:
            config_data.api_keys = {}

        config_data.api_keys[api_key.key] = {
            "name": api_key.name,
            "created_at": api_key.created_at.isoformat(),
            "permissions": api_key.permissions,
            "branches": api_key.branches,
            "active": api_key.active,
        }

        self.config.save(config_data)
        return api_key

    def get_key(self, key: str) -> Optional[APIKey]:
        """Get an API key by its value.

        Args:
            key: API key string

        Returns:
            API key if found and active, None otherwise
        """
        config_data = self.config.load()
        if not config_data.api_keys or key not in config_data.api_keys:
            return None

        key_data = config_data.api_keys[key]
        if not key_data.get("active", True):
            return None

        return APIKey(
            key=key,
            name=key_data["name"],
            created_at=datetime.fromisoformat(key_data["created_at"]),
            permissions=key_data.get("permissions", "read"),
            branches=key_data.get("branches"),
            active=key_data.get("active", True),
        )

    def list_keys(self) -> List[APIKey]:
        """List all API keys.

        Returns:
            List of API keys
        """
        config_data = self.config.load()
        if not config_data.api_keys:
            return []

        keys = []
        for key, key_data in config_data.api_keys.items():
            keys.append(
                APIKey(
                    key=key,
                    name=key_data["name"],
                    created_at=datetime.fromisoformat(key_data["created_at"]),
                    permissions=key_data.get("permissions", "read"),
                    branches=key_data.get("branches"),
                    active=key_data.get("active", True),
                )
            )

        return keys

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key.

        Args:
            key: API key to revoke

        Returns:
            True if revoked, False if not found
        """
        config_data = self.config.load()
        if not config_data.api_keys or key not in config_data.api_keys:
            return False

        config_data.api_keys[key]["active"] = False
        self.config.save(config_data)
        return True

    def delete_key(self, key: str) -> bool:
        """Delete an API key.

        Args:
            key: API key to delete

        Returns:
            True if deleted, False if not found
        """
        config_data = self.config.load()
        if not config_data.api_keys or key not in config_data.api_keys:
            return False

        del config_data.api_keys[key]
        self.config.save(config_data)
        return True


class AuthContext(BaseModel):
    """Authentication context for requests."""

    api_key: APIKey
    project_dir: Path


async def get_current_project(project_dir: Optional[str] = None) -> Path:
    """Get the current project directory.

    Args:
        project_dir: Optional project directory path

    Returns:
        Project directory path

    Raises:
        HTTPException: If project not found
    """
    if project_dir:
        path = Path(project_dir)
        if not path.exists() or not (path / ".cinchdb").exists():
            raise HTTPException(status_code=404, detail="Project not found")
        return path

    # Try to find project from current directory
    project_root = get_project_root(Path.cwd())
    if not project_root:
        raise HTTPException(
            status_code=404,
            detail="No CinchDB project found. Specify project_dir parameter.",
        )

    return project_root


async def verify_api_key(
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
    project_dir: Path = Depends(get_current_project),
) -> AuthContext:
    """Verify API key and return auth context.

    Args:
        api_key_header: API key from header
        api_key_query: API key from query parameter
        project_dir: Project directory

    Returns:
        Authentication context

    Raises:
        HTTPException: If authentication fails
    """
    # Check header first, then query parameter
    api_key = api_key_header or api_key_query
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    manager = APIKeyManager(project_dir)
    key_obj = manager.get_key(api_key)

    if not key_obj:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return AuthContext(api_key=key_obj, project_dir=project_dir)


async def require_write_permission(
    auth: AuthContext = Depends(verify_api_key), branch: Optional[str] = None
) -> AuthContext:
    """Require write permission for the request.

    Args:
        auth: Authentication context
        branch: Optional branch name to check

    Returns:
        Authentication context

    Raises:
        HTTPException: If permission denied
    """
    if auth.api_key.permissions != "write":
        raise HTTPException(status_code=403, detail="Write permission required")

    # Check branch-specific permissions
    if branch and auth.api_key.branches and branch not in auth.api_key.branches:
        raise HTTPException(
            status_code=403, detail=f"Access denied for branch '{branch}'"
        )

    return auth


async def require_read_permission(
    auth: AuthContext = Depends(verify_api_key), branch: Optional[str] = None
) -> AuthContext:
    """Require read permission for the request.

    Args:
        auth: Authentication context
        branch: Optional branch name to check

    Returns:
        Authentication context

    Raises:
        HTTPException: If permission denied
    """
    # All valid API keys have at least read permission

    # Check branch-specific permissions
    if branch and auth.api_key.branches and branch not in auth.api_key.branches:
        raise HTTPException(
            status_code=403, detail=f"Access denied for branch '{branch}'"
        )

    return auth

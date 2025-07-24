"""Projects router for CinchDB API."""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cinchdb.config import Config
from cinchdb.api.auth import (
    AuthContext,
    require_write_permission,
    require_read_permission,
)


router = APIRouter()


class ProjectInfo(BaseModel):
    """Project information response."""

    path: str
    active_database: str
    active_branch: str
    has_api_keys: bool


class InitProjectRequest(BaseModel):
    """Request to initialize a new project."""

    path: str


@router.post("/init")
async def init_project(
    request: InitProjectRequest, auth: AuthContext = Depends(require_write_permission)
):
    """Initialize a new CinchDB project."""
    project_path = Path(request.path)

    # Check if directory exists
    if not project_path.exists():
        try:
            project_path.mkdir(parents=True)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to create directory: {e}"
            )

    # Initialize project
    try:
        config = Config(project_path)
        config.init_project()
        return {"message": f"Initialized CinchDB project in {project_path}"}
    except FileExistsError:
        raise HTTPException(status_code=400, detail="Project already exists")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize project: {e}"
        )


@router.get("/info")
async def get_project_info(
    auth: AuthContext = Depends(require_read_permission),
) -> ProjectInfo:
    """Get information about the current project."""
    config = Config(auth.project_dir)

    try:
        config_data = config.load()
        has_keys = bool(config_data.api_keys)

        return ProjectInfo(
            path=str(auth.project_dir),
            active_database=config_data.active_database,
            active_branch=config_data.active_branch,
            has_api_keys=has_keys,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project configuration not found")


class SetActiveRequest(BaseModel):
    """Request to set active database or branch."""

    database: Optional[str] = None
    branch: Optional[str] = None


@router.put("/active")
async def set_active(
    request: SetActiveRequest, auth: AuthContext = Depends(require_write_permission)
):
    """Set the active database and/or branch."""
    config = Config(auth.project_dir)

    try:
        config_data = config.load()

        if request.database:
            # Verify database exists
            db_path = auth.project_dir / ".cinchdb" / "databases" / request.database
            if not db_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Database '{request.database}' not found"
                )
            config_data.active_database = request.database

        if request.branch:
            # Verify branch exists in active database
            branch_path = (
                auth.project_dir
                / ".cinchdb"
                / "databases"
                / config_data.active_database
                / "branches"
                / request.branch
            )
            if not branch_path.exists():
                raise HTTPException(
                    status_code=404, detail=f"Branch '{request.branch}' not found"
                )
            config_data.active_branch = request.branch

        config.save(config_data)

        return {
            "active_database": config_data.active_database,
            "active_branch": config_data.active_branch,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project configuration not found")

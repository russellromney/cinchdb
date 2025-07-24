"""Databases router for CinchDB API."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from cinchdb.config import Config
from cinchdb.core.path_utils import list_databases
from cinchdb.api.auth import (
    AuthContext,
    require_write_permission,
    require_read_permission,
)


router = APIRouter()


class DatabaseInfo(BaseModel):
    """Database information."""

    name: str
    is_active: bool
    is_protected: bool
    branch_count: int


class CreateDatabaseRequest(BaseModel):
    """Request to create a database."""

    name: str
    description: str = None
    switch: bool = False


@router.get("/", response_model=List[DatabaseInfo])
async def list_all_databases(auth: AuthContext = Depends(require_read_permission)):
    """List all databases in the project."""
    config = Config(auth.project_dir)
    config_data = config.load()

    databases = list_databases(auth.project_dir)

    result = []
    for db_name in databases:
        # Count branches
        branches_path = (
            auth.project_dir / ".cinchdb" / "databases" / db_name / "branches"
        )
        branch_count = (
            len(list(branches_path.iterdir())) if branches_path.exists() else 0
        )

        result.append(
            DatabaseInfo(
                name=db_name,
                is_active=db_name == config_data.active_database,
                is_protected=db_name == "main",
                branch_count=branch_count,
            )
        )

    return result


@router.post("/")
async def create_database(
    request: CreateDatabaseRequest,
    auth: AuthContext = Depends(require_write_permission),
):
    """Create a new database."""
    config = Config(auth.project_dir)

    # Create database directory structure
    db_path = auth.project_dir / ".cinchdb" / "databases" / request.name
    if db_path.exists():
        raise HTTPException(
            status_code=400, detail=f"Database '{request.name}' already exists"
        )

    try:
        # Create the database structure
        db_path.mkdir(parents=True)
        branches_dir = db_path / "branches"
        branches_dir.mkdir()

        # Create main branch
        main_branch = branches_dir / "main"
        main_branch.mkdir()

        # Create main tenant
        tenants_dir = main_branch / "tenants"
        tenants_dir.mkdir()
        main_tenant = tenants_dir / "main.db"
        main_tenant.touch()

        # Create branch metadata
        import json
        from datetime import datetime, timezone

        metadata = {
            "name": "main",
            "parent": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(main_branch / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Create empty changes file
        with open(main_branch / "changes.json", "w") as f:
            json.dump([], f)

        # Switch to new database if requested
        if request.switch:
            config_data = config.load()
            config_data.active_database = request.name
            config_data.active_branch = "main"
            config.save(config_data)

        return {"message": f"Created database '{request.name}'"}

    except Exception as e:
        # Clean up on failure
        if db_path.exists():
            import shutil

            shutil.rmtree(db_path)
        raise HTTPException(status_code=500, detail=f"Failed to create database: {e}")


@router.delete("/{name}")
async def delete_database(
    name: str, auth: AuthContext = Depends(require_write_permission)
):
    """Delete a database."""
    if name == "main":
        raise HTTPException(status_code=400, detail="Cannot delete the main database")

    config = Config(auth.project_dir)
    db_path = auth.project_dir / ".cinchdb" / "databases" / name

    if not db_path.exists():
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    try:
        # Delete the database
        import shutil

        shutil.rmtree(db_path)

        # If this was the active database, switch to main
        config_data = config.load()
        if config_data.active_database == name:
            config_data.active_database = "main"
            config_data.active_branch = "main"
            config.save(config_data)

        return {"message": f"Deleted database '{name}'"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete database: {e}")


@router.get("/{name}")
async def get_database_info(
    name: str, auth: AuthContext = Depends(require_read_permission)
) -> DatabaseInfo:
    """Get information about a specific database."""
    db_path = auth.project_dir / ".cinchdb" / "databases" / name
    if not db_path.exists():
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    config = Config(auth.project_dir)
    config_data = config.load()

    # Count branches
    branches_path = db_path / "branches"
    branch_count = len(list(branches_path.iterdir())) if branches_path.exists() else 0

    return DatabaseInfo(
        name=name,
        is_active=name == config_data.active_database,
        is_protected=name == "main",
        branch_count=branch_count,
    )

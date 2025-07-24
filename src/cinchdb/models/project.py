"""Project model for CinchDB."""

from pathlib import Path
from typing import List, Optional
from pydantic import Field
from .base import CinchDBBaseModel


class Project(CinchDBBaseModel):
    """Represents a CinchDB project."""

    name: str = Field(description="Project name")
    path: Path = Field(description="Path to project directory")
    databases: List[str] = Field(
        default_factory=list, description="List of database names"
    )
    active_database: str = Field(
        default="main", description="Currently active database"
    )
    description: Optional[str] = Field(default=None, description="Project description")

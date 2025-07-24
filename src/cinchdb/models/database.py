"""Database model for CinchDB."""

from typing import List, Optional
from pydantic import Field
from .base import CinchDBBaseModel


class Database(CinchDBBaseModel):
    """Represents a database within a CinchDB project."""

    name: str = Field(description="Database name")
    branches: List[str] = Field(
        default_factory=lambda: ["main"], description="List of branch names"
    )
    active_branch: str = Field(default="main", description="Currently active branch")
    description: Optional[str] = Field(default=None, description="Database description")

    def can_delete(self) -> bool:
        """Check if this database can be deleted."""
        return self.name != "main"

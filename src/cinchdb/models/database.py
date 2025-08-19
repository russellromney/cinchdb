"""Database model for CinchDB."""

from typing import List, Optional
from pydantic import Field, field_validator
from .base import CinchDBBaseModel
from ..utils.name_validator import validate_name


class Database(CinchDBBaseModel):
    """Represents a database within a CinchDB project."""

    name: str = Field(description="Database name")
    branches: List[str] = Field(
        default_factory=lambda: ["main"], description="List of branch names"
    )
    active_branch: str = Field(default="main", description="Currently active branch")
    description: Optional[str] = Field(default=None, description="Database description")

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """Validate database name meets naming requirements."""
        validate_name(v, "database")
        return v

    def can_delete(self) -> bool:
        """Check if this database can be deleted."""
        return self.name != "main"

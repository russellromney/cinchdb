"""Tenant model for CinchDB."""

from typing import Optional
from pydantic import Field
from .base import CinchDBBaseModel


class Tenant(CinchDBBaseModel):
    """Represents a tenant within a branch."""
    
    name: str = Field(description="Tenant name")
    branch: str = Field(description="Parent branch name")
    database: str = Field(description="Parent database name")
    description: Optional[str] = Field(default=None, description="Tenant description")
    is_main: bool = Field(default=False, description="Whether this is the main tenant")
    
    def can_delete(self) -> bool:
        """Check if this tenant can be deleted."""
        return self.name != "main" and not self.is_main
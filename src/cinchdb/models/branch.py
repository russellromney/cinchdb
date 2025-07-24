"""Branch model for CinchDB."""

from typing import List, Optional, Dict, Any
from pydantic import Field
from .base import CinchDBBaseModel


class Branch(CinchDBBaseModel):
    """Represents a branch within a database."""
    
    name: str = Field(description="Branch name")
    database: str = Field(description="Parent database name")
    parent_branch: Optional[str] = Field(default=None, description="Parent branch this was created from")
    tenants: List[str] = Field(default_factory=lambda: ["main"], description="List of tenant names")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Branch metadata")
    is_main: bool = Field(default=False, description="Whether this is the main branch")
    
    def can_delete(self) -> bool:
        """Check if this branch can be deleted."""
        return self.name != "main" and not self.is_main
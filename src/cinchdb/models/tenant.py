"""Tenant model for CinchDB."""

from typing import Optional
from pydantic import Field, field_validator
from .base import CinchDBBaseModel
from ..utils.name_validator import validate_name


class Tenant(CinchDBBaseModel):
    """Represents a tenant within a branch."""

    name: str = Field(description="Tenant name")
    branch: str = Field(description="Parent branch name")
    database: str = Field(description="Parent database name")
    description: Optional[str] = Field(default=None, description="Tenant description")
    is_main: bool = Field(default=False, description="Whether this is the main tenant")

    @field_validator("name")
    @classmethod
    def validate_name_field(cls, v: str) -> str:
        """Validate tenant name meets naming requirements."""
        validate_name(v, "tenant")
        return v

    def can_delete(self) -> bool:
        """Check if this tenant can be deleted."""
        return self.name != "main" and not self.is_main

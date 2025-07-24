"""View model for CinchDB."""

from typing import Optional
from pydantic import Field
from .base import CinchDBBaseModel


class View(CinchDBBaseModel):
    """Represents a SQL view in the database."""

    name: str = Field(description="View name")
    database: str = Field(description="Database name")
    branch: str = Field(description="Branch name")
    sql_statement: str = Field(description="SQL SELECT statement that defines the view")
    description: Optional[str] = Field(default=None, description="View description")

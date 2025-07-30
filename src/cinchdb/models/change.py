"""Change tracking models for CinchDB."""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import Field
from .base import CinchDBTableModel


class ChangeType(str, Enum):
    """Types of schema changes."""

    # Table changes
    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    RENAME_TABLE = "rename_table"

    # Column changes
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    RENAME_COLUMN = "rename_column"
    MODIFY_COLUMN = "modify_column"
    ALTER_COLUMN_NULLABLE = "alter_column_nullable"

    # View changes
    CREATE_VIEW = "create_view"
    DROP_VIEW = "drop_view"
    UPDATE_VIEW = "update_view"

    # Index changes
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"


class Change(CinchDBTableModel):
    """Represents a schema change in the database."""

    type: ChangeType = Field(description="Type of change")
    entity_type: str = Field(description="Type of entity affected (table, view, index)")
    entity_name: str = Field(description="Name of the affected entity")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Change-specific details"
    )
    sql: Optional[str] = Field(
        default=None, description="SQL statement that implements the change"
    )
    branch: str = Field(description="Branch where change was made")
    applied: bool = Field(default=False, description="Whether change has been applied")

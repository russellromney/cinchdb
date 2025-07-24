"""Base models for CinchDB."""

from datetime import datetime, timezone
from typing import Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class CinchDBTableModel(BaseModel):
    """Base model for entities that will be stored as database tables.

    Includes automatic id, created_at, and updated_at fields.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique identifier"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: Optional[datetime], _info: Any) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return dt.isoformat() if dt else None


class CinchDBBaseModel(BaseModel):
    """Base model for non-table entities (metadata, config, etc)."""

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        extra="forbid",  # Strict validation for metadata
    )

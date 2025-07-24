"""Generated model for users table."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Users(BaseModel):
    """Model for users table."""

    id: str = Field(description="id field")
    created_at: datetime = Field(description="created_at field", default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(description="updated_at field", default=None)
    name: str = Field(description="name field")
    email: str = Field(description="email field")
    age: int = Field(description="age field")

    class Config:
        from_attributes = True
        json_schema_extra = {"table_name": "users"}
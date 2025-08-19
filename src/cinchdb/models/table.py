"""Table and Column models for CinchDB."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from .base import CinchDBBaseModel


# SQLite column types
ColumnType = Literal["TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"]

# Foreign key actions
ForeignKeyAction = Literal["CASCADE", "SET NULL", "RESTRICT", "NO ACTION"]


class ForeignKeyRef(BaseModel):
    """Foreign key reference specification."""

    model_config = ConfigDict(extra="forbid")

    table: str = Field(description="Referenced table name")
    column: str = Field(default="id", description="Referenced column name")
    on_delete: ForeignKeyAction = Field(
        default="RESTRICT", description="Action on delete of referenced row"
    )
    on_update: ForeignKeyAction = Field(
        default="RESTRICT", description="Action on update of referenced row"
    )


class Column(BaseModel):
    """Represents a column in a table."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Column name")
    type: ColumnType = Field(description="SQLite column type")
    nullable: bool = Field(
        default=True, description="Whether column allows NULL values"
    )
    default: Optional[str] = Field(
        default=None, description="Default value SQL expression"
    )
    primary_key: bool = Field(
        default=False, description="Whether this is a primary key"
    )
    unique: bool = Field(default=False, description="Whether values must be unique")
    foreign_key: Optional[ForeignKeyRef] = Field(
        default=None, description="Foreign key constraint specification"
    )


class Table(CinchDBBaseModel):
    """Represents a table in the database."""

    name: str = Field(description="Table name")
    database: str = Field(description="Database name")
    branch: str = Field(description="Branch name")
    columns: List[Column] = Field(default_factory=list, description="Table columns")

    def __init__(self, **data):
        """Initialize table with default columns."""
        super().__init__(**data)

        # Add default columns if not present
        column_names = {col.name for col in self.columns}

        if "id" not in column_names:
            self.columns.insert(
                0,
                Column(
                    name="id",
                    type="TEXT",
                    nullable=False,
                    primary_key=True,
                    unique=True,
                ),
            )

        if "created_at" not in column_names:
            self.columns.append(Column(name="created_at", type="TEXT", nullable=False))

        if "updated_at" not in column_names:
            self.columns.append(Column(name="updated_at", type="TEXT", nullable=True))

"""Schema snapshot model for tracking table schemas."""

from typing import Dict, List, Optional
from cinchdb.models.base import CinchDBBaseModel
from cinchdb.models.table import Column


class SchemaSnapshot(CinchDBBaseModel):
    """Represents a complete schema snapshot for a branch.

    The schema snapshot stores the complete table schema state at a point in time,
    mapping table names to their column definitions.
    """

    tables: Dict[str, List[Dict]] = {}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, List[Dict]]]) -> Optional["SchemaSnapshot"]:
        """Create SchemaSnapshot from dict representation.

        Args:
            data: Dictionary mapping table names to column definitions

        Returns:
            SchemaSnapshot instance, or None if data is None
        """
        if data is None:
            return None
        return cls(tables=data)

    def to_dict(self) -> Dict[str, List[Dict]]:
        """Convert to dict representation for JSON serialization.

        Returns:
            Dictionary mapping table names to column definitions
        """
        return self.tables

    def get_table_schema(self, table_name: str) -> Optional[List[Column]]:
        """Get column definitions for a table.

        Args:
            table_name: Name of the table

        Returns:
            List of Column objects, or None if table doesn't exist
        """
        if table_name not in self.tables:
            return None
        return [Column(**col_dict) for col_dict in self.tables[table_name]]

    def has_table(self, table_name: str) -> bool:
        """Check if a table exists in the snapshot.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists
        """
        return table_name in self.tables

    def add_table(self, table_name: str, columns: List[Column]) -> None:
        """Add or update a table in the snapshot.

        Args:
            table_name: Name of the table
            columns: List of Column objects
        """
        self.tables[table_name] = [col.model_dump() for col in columns]

    def remove_table(self, table_name: str) -> None:
        """Remove a table from the snapshot.

        Args:
            table_name: Name of the table
        """
        if table_name in self.tables:
            del self.tables[table_name]

    def update_column(self, table_name: str, column_name: str, updated_column: Column) -> None:
        """Update a specific column in a table.

        Args:
            table_name: Name of the table
            column_name: Name of the column to update
            updated_column: New Column definition

        Raises:
            ValueError: If table or column doesn't exist
        """
        if table_name not in self.tables:
            raise ValueError(f"Table '{table_name}' not found in schema snapshot")

        columns = self.tables[table_name]
        updated = False
        for i, col_dict in enumerate(columns):
            if col_dict.get('name') == column_name:
                columns[i] = updated_column.model_dump()
                updated = True
                break

        if not updated:
            raise ValueError(f"Column '{column_name}' not found in table '{table_name}'")

    def add_column(self, table_name: str, column: Column) -> None:
        """Add a column to a table.

        Args:
            table_name: Name of the table
            column: Column to add

        Raises:
            ValueError: If table doesn't exist
        """
        if table_name not in self.tables:
            raise ValueError(f"Table '{table_name}' not found in schema snapshot")

        self.tables[table_name].append(column.model_dump())

    def deep_copy(self) -> "SchemaSnapshot":
        """Create a deep copy of this snapshot.

        Returns:
            New SchemaSnapshot instance with copied data
        """
        import copy
        return SchemaSnapshot(tables=copy.deepcopy(self.tables))

    def list_tables(self) -> List[str]:
        """Get list of all table names in the snapshot.

        Returns:
            List of table names
        """
        return list(self.tables.keys())

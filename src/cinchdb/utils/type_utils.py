"""Type utilities for normalizing and handling column types."""

from typing import Any, Optional

# Map various type representations to canonical CinchDB types
TYPE_MAPPING = {
    # Standard canonical names
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "REAL": "REAL",
    "BLOB": "BLOB",
    "NUMERIC": "NUMERIC",
    "BOOLEAN": "BOOLEAN",

    # Lowercase variations
    "text": "TEXT",
    "integer": "INTEGER",
    "real": "REAL",
    "blob": "BLOB",
    "numeric": "NUMERIC",
    "boolean": "BOOLEAN",

    # Mixed case variations
    "Text": "TEXT",
    "Integer": "INTEGER",
    "Real": "REAL",
    "Blob": "BLOB",
    "Numeric": "NUMERIC",
    "Boolean": "BOOLEAN",

    # Common aliases
    "int": "INTEGER",
    "INT": "INTEGER",
    "Int": "INTEGER",
    "bool": "BOOLEAN",
    "BOOL": "BOOLEAN",
    "Bool": "BOOLEAN",
    "float": "REAL",
    "FLOAT": "REAL",
    "Float": "REAL",
    "double": "REAL",
    "DOUBLE": "REAL",
    "Double": "REAL",
    "string": "TEXT",
    "STRING": "TEXT",
    "String": "TEXT",
    "str": "TEXT",
    "STR": "TEXT",
    "Str": "TEXT",
    "varchar": "TEXT",
    "VARCHAR": "TEXT",
    "char": "TEXT",
    "CHAR": "TEXT",
    "bytes": "BLOB",
    "BYTES": "BLOB",
    "binary": "BLOB",
    "BINARY": "BLOB",
}


def normalize_type(type_str: str) -> str:
    """
    Normalize a type string to its canonical CinchDB type.

    Args:
        type_str: The type string to normalize (case-insensitive, supports aliases)

    Returns:
        The canonical CinchDB type (TEXT, INTEGER, REAL, BLOB, NUMERIC, BOOLEAN)

    Raises:
        ValueError: If the type string is not recognized
    """
    if not type_str:
        raise ValueError("Type cannot be empty")

    normalized = TYPE_MAPPING.get(type_str)
    if not normalized:
        # Get unique valid types for error message
        valid_types = sorted(set(TYPE_MAPPING.values()))
        raise ValueError(
            f"Invalid type: '{type_str}'. "
            f"Valid types: {', '.join(valid_types)}"
        )
    return normalized


def prepare_value_for_storage(column_type: str, value: Any) -> Any:
    """
    Prepare a Python value for storage in SQLite based on column type.

    Args:
        column_type: The canonical column type
        value: The Python value to prepare

    Returns:
        The value prepared for SQLite storage
    """
    if value is None:
        return None

    if column_type == "BOOLEAN":
        # Convert Python bool to SQLite integer (0 or 1)
        return 1 if value else 0

    return value


def convert_value_from_storage(column_type: str, value: Any) -> Any:
    """
    Convert a value from SQLite storage to appropriate Python type.

    Args:
        column_type: The canonical column type
        value: The value from SQLite

    Returns:
        The value converted to appropriate Python type
    """
    if value is None:
        return None

    if column_type == "BOOLEAN":
        # Convert SQLite integer to Python bool
        return bool(value)

    return value
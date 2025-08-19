"""SQL Query Validator for CinchDB.

Validates SQL queries to ensure only safe DML operations are allowed,
preventing structural database changes.
"""

import re
from typing import Tuple, Optional
from enum import Enum


class SQLOperation(Enum):
    """Allowed SQL operations."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


# List of restricted DDL operations and keywords
RESTRICTED_OPERATIONS = {
    "CREATE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "ANALYZE",
    "VACUUM",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "REINDEX",
    "SAVEPOINT",
    "RELEASE",
}

# Additional restricted keywords that could modify schema
RESTRICTED_KEYWORDS = {
    "ADD COLUMN",
    "DROP COLUMN",
    "MODIFY COLUMN",
    "ADD CONSTRAINT",
    "DROP CONSTRAINT",
    "ADD INDEX",
    "DROP INDEX",
    "CREATE INDEX",
    "CREATE UNIQUE",
    "CREATE VIEW",
    "DROP VIEW",
    "CREATE TRIGGER",
    "DROP TRIGGER",
    "CREATE PROCEDURE",
    "DROP PROCEDURE",
    "CREATE FUNCTION",
    "DROP FUNCTION",
}


class SQLValidationError(Exception):
    """Raised when SQL query validation fails."""

    pass


def validate_sql_query(
    query: str, allow_multiple_statements: bool = False
) -> Tuple[bool, Optional[str], Optional[SQLOperation]]:
    """Validate a SQL query to ensure it only contains allowed operations.

    Allowed operations: SELECT, INSERT, UPDATE, DELETE
    Blocked operations: All DDL operations (CREATE, ALTER, DROP, etc.)

    Args:
        query: The SQL query to validate
        allow_multiple_statements: Whether to allow multiple SQL statements (default: False)

    Returns:
        Tuple of (is_valid, error_message, operation)
        - is_valid: True if query is valid
        - error_message: Error description if invalid, None if valid
        - operation: The SQL operation type if valid, None if invalid
    """
    if not query or not query.strip():
        return False, "Query cannot be empty", None

    # Normalize the query - remove comments and extra whitespace
    normalized_query = query
    # Remove single-line comments
    normalized_query = re.sub(r"--.*$", "", normalized_query, flags=re.MULTILINE)
    # Remove multi-line comments
    normalized_query = re.sub(r"/\*[\s\S]*?\*/", "", normalized_query)
    # Replace multiple spaces with single space
    normalized_query = re.sub(r"\s+", " ", normalized_query)
    normalized_query = normalized_query.strip().upper()

    if not normalized_query:
        return False, "Query cannot be empty after removing comments", None

    # Check for multiple statements (security risk)
    if not allow_multiple_statements:
        # Count semicolons that are not at the end
        semicolon_pos = normalized_query.find(";")
        if semicolon_pos != -1 and semicolon_pos < len(normalized_query) - 1:
            # Check if there's non-whitespace after the semicolon
            remaining = normalized_query[semicolon_pos + 1 :].strip()
            if remaining:
                return (
                    False,
                    "Multiple statements are not allowed. Please execute one query at a time.",
                    None,
                )

    # Extract the first word (operation)
    first_word = normalized_query.split()[0].rstrip(";")

    # Check if it's an allowed operation
    try:
        operation = SQLOperation(first_word)

        # Additional validation for UPDATE and DELETE
        if operation in (SQLOperation.UPDATE, SQLOperation.DELETE):
            # Warning if no WHERE clause (we don't block it, just log)
            if "WHERE" not in normalized_query:
                import logging

                logging.warning(
                    f"{operation.value} statement without WHERE clause detected"
                )

        return True, None, operation
    except ValueError:
        # Not a recognized allowed operation
        pass

    # Check for restricted operations
    for restricted in RESTRICTED_OPERATIONS:
        if normalized_query.startswith(restricted):
            return (
                False,
                f"{restricted} operations are not allowed. Only SELECT, INSERT, UPDATE, and DELETE queries are permitted.",
                None,
            )

    # Check for restricted keywords anywhere in the query
    for keyword in RESTRICTED_KEYWORDS:
        if keyword in normalized_query:
            return (
                False,
                f"Query contains restricted operation: {keyword}. Only SELECT, INSERT, UPDATE, and DELETE queries are permitted.",
                None,
            )

    # Check for WITH statements that might contain DDL
    if normalized_query.startswith("WITH"):
        # Check if the CTE contains any DDL operations
        for restricted in RESTRICTED_OPERATIONS:
            if restricted in normalized_query:
                return (
                    False,
                    f"CTE (WITH clause) containing {restricted} operations is not allowed.",
                    None,
                )

    # If we get here, it's an unrecognized operation
    return (
        False,
        "Unrecognized or restricted SQL operation. Only SELECT, INSERT, UPDATE, and DELETE queries are permitted.",
        None,
    )


def validate_query_safe(query: str, allow_multiple_statements: bool = False) -> None:
    """Validate a SQL query and raise an exception if invalid.

    Args:
        query: The SQL query to validate
        allow_multiple_statements: Whether to allow multiple SQL statements

    Raises:
        SQLValidationError: If the query is invalid
    """
    is_valid, error_message, _ = validate_sql_query(query, allow_multiple_statements)
    if not is_valid:
        raise SQLValidationError(error_message)

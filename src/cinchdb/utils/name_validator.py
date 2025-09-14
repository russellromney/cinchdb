"""Name validation utilities for CinchDB entities.

Ensures branch, database, and tenant names are safe for filesystem operations
and follow consistent naming conventions.
"""

import re


# Regex patterns for different entity types
# Database/branch/tenant names: can have hyphens and start with numbers
VALID_DB_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-_]*[a-z0-9]$|^[a-z0-9]$")

# Table/column names: no hyphens (to avoid SQL quoting), must start with letter
VALID_TABLE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*[a-z0-9]$|^[a-z]$")

# Reserved names that cannot be used
RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}


class InvalidNameError(ValueError):
    """Raised when a name doesn't meet validation requirements."""

    pass


def validate_name(name: str, entity_type: str = "entity") -> None:
    """Validate that a name meets CinchDB naming requirements.

    Valid names must:
    - Contain only lowercase letters (a-z), numbers (0-9), dash (-), and underscore (_)
    - Start and end with alphanumeric characters
    - Be at least 1 character long
    - Not exceed 255 characters (filesystem limit)
    - Not be a reserved name
    - Not contain path traversal sequences

    Args:
        name: The name to validate
        entity_type: Type of entity (branch, database, tenant) for error messages

    Raises:
        InvalidNameError: If the name is invalid
    """
    if not name:
        raise InvalidNameError(f"{entity_type.capitalize()} name cannot be empty")

    if len(name) > 63:
        raise InvalidNameError(
            f"{entity_type.capitalize()} name cannot exceed 63 characters"
        )
    
    # Critical: Check for path traversal attempts
    if ".." in name or "/" in name or "\\" in name or "~" in name:
        raise InvalidNameError(
            f"Security violation: {entity_type} name '{name}' contains "
            f"forbidden path traversal characters"
        )
    
    # Check for null bytes and other control characters
    if "\x00" in name or any(ord(c) < 32 for c in name):
        raise InvalidNameError(
            f"Security violation: {entity_type} name contains invalid control characters"
        )

    # Check for lowercase requirement
    if name != name.lower():
        raise InvalidNameError(
            f"{entity_type.capitalize()} name must be lowercase. "
            f"Use '{name.lower()}' instead of '{name}'"
        )

    # Check pattern based on entity type
    if entity_type in ["table", "column"]:
        # Tables and columns: no hyphens, must start with letter
        if not VALID_TABLE_NAME_PATTERN.match(name):
            raise InvalidNameError(
                f"Invalid {entity_type} name '{name}'. "
                f"{entity_type.capitalize()} names must contain only lowercase letters (a-z), "
                f"numbers (0-9), and underscore (_). "
                f"Names must start with a letter and end with a letter or number."
            )
    else:
        # Database/branch/tenant: can have hyphens, can start with numbers
        if not VALID_DB_NAME_PATTERN.match(name):
            raise InvalidNameError(
                f"Invalid {entity_type} name '{name}'. "
                f"Names must contain only lowercase letters (a-z), numbers (0-9), "
                f"dash (-), and underscore (_). "
                f"Names must start and end with alphanumeric characters."
            )

    # Check for consecutive special characters
    if (
        "--" in name
        or "__" in name
        or "-_" in name
        or "_-" in name
    ):
        raise InvalidNameError(
            f"Invalid {entity_type} name '{name}'. "
            f"Names cannot contain consecutive special characters."
        )

    # Check reserved names
    if name.lower() in RESERVED_NAMES:
        raise InvalidNameError(
            f"'{name}' is a reserved name and cannot be used as a {entity_type} name"
        )


def clean_name(name: str) -> str:
    """Clean a name to make it valid if possible.

    This performs basic cleaning:
    - Convert to lowercase
    - Replace spaces with dashes
    - Remove invalid characters

    Args:
        name: The name to clean

    Returns:
        Cleaned name

    Note:
        This is a best-effort cleaning. The result should still be validated
        with validate_name() before use.
    """
    # Convert to lowercase
    cleaned = name.lower()

    # Replace spaces with dashes
    cleaned = cleaned.replace(" ", "-")

    # Remove invalid characters (period no longer allowed)
    cleaned = re.sub(r"[^a-z0-9\-_]", "", cleaned)

    # Remove consecutive special characters
    cleaned = re.sub(r"[-_]{2,}", "-", cleaned)

    # Remove leading/trailing special characters
    cleaned = cleaned.strip("-_")

    return cleaned


def is_valid_name(name: str) -> bool:
    """Check if a name is valid without raising an exception.

    Args:
        name: The name to check

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_name(name)
        return True
    except InvalidNameError:
        return False

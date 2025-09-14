"""Tests for name validation functionality."""

import pytest
from cinchdb.utils.name_validator import (
    validate_name,
    clean_name,
    is_valid_name,
    InvalidNameError,
)


class TestNameValidator:
    """Test the name validation functions."""

    def test_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = [
            "main",
            "feature-branch",
            "test_db",
            "user-123",
            "2024-data",
            "a",  # Single character
            "test-branch_v2-1",  # Dashes and underscores allowed
        ]

        for name in valid_names:
            # Should not raise
            validate_name(name)
            assert is_valid_name(name) is True

    def test_empty_name(self):
        """Test that empty names are rejected."""
        with pytest.raises(InvalidNameError) as exc_info:
            validate_name("")
        assert "cannot be empty" in str(exc_info.value)

        assert is_valid_name("") is False

    def test_uppercase_names(self):
        """Test that uppercase names are rejected with helpful message."""
        test_cases = [
            ("MyBranch", "mybranch"),
            ("TEST", "test"),
            ("Feature-Branch", "feature-branch"),
        ]

        for invalid, suggested in test_cases:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(invalid)
            error_msg = str(exc_info.value)
            assert "must be lowercase" in error_msg
            assert f"Use '{suggested}'" in error_msg

            assert is_valid_name(invalid) is False

    def test_invalid_characters(self):
        """Test that names with invalid characters are rejected."""
        invalid_names = [
            "my branch",  # Space
            "feature/branch",  # Slash
            "test@db",  # At symbol
            "user#123",  # Hash
            "data$base",  # Dollar sign
            "test!",  # Exclamation
            "branch(1)",  # Parentheses
            "my[branch]",  # Brackets
            "test\\branch",  # Backslash
            "db:main",  # Colon
            "test;db",  # Semicolon
            "branch?",  # Question mark
            "test*",  # Asterisk
            "v1.2.3",  # Period (no longer allowed for security)
            "my_project.backup",  # Period
            "test-branch_v2.1",  # Period
        ]

        for name in invalid_names:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name)
            # Error message can be either "Invalid" or "Security violation"
            assert "Invalid" in str(exc_info.value) or "Security violation" in str(exc_info.value)
            assert is_valid_name(name) is False

    def test_invalid_start_end_characters(self):
        """Test that names must start and end with alphanumeric."""
        invalid_names = [
            "-branch",  # Starts with dash
            "branch-",  # Ends with dash
            "_test",  # Starts with underscore
            "test_",  # Ends with underscore
            ".backup",  # Starts with period
            "backup.",  # Ends with period
            "-test-",  # Both start and end
        ]

        for name in invalid_names:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name)
            assert "must start and end with alphanumeric" in str(exc_info.value)
            assert is_valid_name(name) is False

    def test_consecutive_special_characters(self):
        """Test that consecutive special characters are rejected."""
        invalid_names = [
            "test--branch",  # Double dash
            "my__db",  # Double underscore
            "test-_branch",  # Dash underscore
            "db_-test",  # Underscore dash
        ]

        for name in invalid_names:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name)
            assert "consecutive special characters" in str(exc_info.value) or "Invalid" in str(exc_info.value)
            assert is_valid_name(name) is False

    def test_length_limits(self):
        """Test name length validation."""
        # Max length name (63 chars)
        max_name = "a" + "b" * 61 + "c"  # 63 chars
        validate_name(max_name)  # Should pass

        # Too long name
        too_long = "a" * 64
        with pytest.raises(InvalidNameError) as exc_info:
            validate_name(too_long)
        assert "cannot exceed 63 characters" in str(exc_info.value)

    def test_reserved_names(self):
        """Test that reserved names are rejected."""
        reserved = ["con", "prn", "aux", "nul", "com1", "lpt1"]

        for name in reserved:
            with pytest.raises(InvalidNameError) as exc_info:
                validate_name(name)
            assert "reserved name" in str(exc_info.value)
            assert is_valid_name(name) is False

    def test_entity_type_in_errors(self):
        """Test that entity type appears in error messages."""
        with pytest.raises(InvalidNameError) as exc_info:
            validate_name("", "branch")
        assert "Branch name" in str(exc_info.value)

        with pytest.raises(InvalidNameError) as exc_info:
            validate_name("TEST", "database")
        assert "Database name" in str(exc_info.value)

        with pytest.raises(InvalidNameError) as exc_info:
            validate_name("-invalid", "tenant")
        assert "tenant name" in str(exc_info.value)

    def test_clean_name(self):
        """Test name cleaning functionality."""
        test_cases = [
            # (input, expected)
            ("My Branch", "my-branch"),
            ("TEST_DB", "test_db"),
            ("Feature  Branch", "feature-branch"),
            ("--test--", "test"),
            ("test@#$name", "testname"),
            ("my---branch", "my-branch"),
            ("_underscore_", "underscore"),
            ("123-test-456", "123-test-456"),
            ("UPPERCASE", "uppercase"),
            ("test.backup", "testbackup"),  # Periods removed
            ("v1.2.3", "v123"),  # Periods removed
        ]

        for input_name, expected in test_cases:
            assert clean_name(input_name) == expected

    def test_clean_name_edge_cases(self):
        """Test edge cases for name cleaning."""
        # All invalid characters
        assert clean_name("@#$%^&*()") == ""

        # Mixed valid/invalid
        assert clean_name("test@branch#123") == "testbranch123"

        # Already clean
        assert clean_name("valid-name") == "valid-name"

    def test_is_valid_name(self):
        """Test the is_valid_name helper."""
        # Valid names
        assert is_valid_name("test") is True
        assert is_valid_name("feature-branch") is True
        assert is_valid_name("db_123") is True

        # Invalid names
        assert is_valid_name("") is False
        assert is_valid_name("TEST") is False
        assert is_valid_name("-invalid") is False
        assert is_valid_name("my branch") is False
        assert is_valid_name("con") is False

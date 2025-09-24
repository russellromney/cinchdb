"""Tests for column masking functionality in query method."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from cinchdb.core.database import CinchDB
from cinchdb.core.initializer import init_project


class TestColumnMasking:
    """Test column masking functionality."""

    def test_mask_single_column(self, tmp_path):
        """Test masking a single column."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "Alice", "email": "alice@example.com"},
                    {"id": 2, "name": "Bob", "email": "bob@example.com"}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                result = db.query("SELECT * FROM users", mask_columns=["email"])

                assert result == [
                    {"id": 1, "name": "Alice", "email": "***REDACTED***"},
                    {"id": 2, "name": "Bob", "email": "***REDACTED***"}
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_mask_multiple_columns(self, tmp_path):
        """Test masking multiple columns."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "Alice", "email": "alice@example.com", "ssn": "123-45-6789", "phone": "555-1234"},
                    {"id": 2, "name": "Bob", "email": "bob@example.com", "ssn": "987-65-4321", "phone": "555-5678"}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                result = db.query(
                    "SELECT * FROM users",
                    mask_columns=["email", "ssn", "phone"]
                )

                assert result == [
                    {"id": 1, "name": "Alice", "email": "***REDACTED***", "ssn": "***REDACTED***", "phone": "***REDACTED***"},
                    {"id": 2, "name": "Bob", "email": "***REDACTED***", "ssn": "***REDACTED***", "phone": "***REDACTED***"}
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_preserve_null_values(self, tmp_path):
        """Test that NULL values are preserved (not masked)."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "Alice", "email": "alice@example.com", "phone": None},
                    {"id": 2, "name": "Bob", "email": None, "phone": "555-5678"},
                    {"id": 3, "name": "Charlie", "email": None, "phone": None}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                result = db.query(
                    "SELECT * FROM users",
                    mask_columns=["email", "phone"]
                )

                # NULL values should remain NULL, not be masked
                assert result == [
                    {"id": 1, "name": "Alice", "email": "***REDACTED***", "phone": None},
                    {"id": 2, "name": "Bob", "email": None, "phone": "***REDACTED***"},
                    {"id": 3, "name": "Charlie", "email": None, "phone": None}
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_mask_nonexistent_column(self, tmp_path):
        """Test masking columns that don't exist in results."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                # Try to mask columns that don't exist
                result = db.query(
                    "SELECT id, name FROM users",
                    mask_columns=["email", "ssn", "nonexistent"]
                )

                # Should not affect the results since columns don't exist
                assert result == [
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"}
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_empty_mask_columns(self, tmp_path):
        """Test with empty mask_columns list."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "name": "Alice", "email": "alice@example.com"}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                # Empty mask_columns list
                result = db.query("SELECT * FROM users", mask_columns=[])

                # No masking should occur
                assert result == [
                    {"id": 1, "name": "Alice", "email": "alice@example.com"}
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_mask_with_empty_results(self, tmp_path):
        """Test masking with empty query results."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = []  # Empty results
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                result = db.query(
                    "SELECT * FROM users WHERE id = 999",
                    mask_columns=["email", "ssn"]
                )

                # Should handle empty results gracefully
                assert result == []

            temp_db_path.unlink(missing_ok=True)

    def test_mask_various_data_types(self, tmp_path):
        """Test masking various data types."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {
                        "id": 1,
                        "string_col": "text_value",
                        "int_col": 42,
                        "float_col": 3.14,
                        "bool_col": True,
                        "null_col": None
                    }
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                result = db.query(
                    "SELECT * FROM mixed_types",
                    mask_columns=["string_col", "int_col", "float_col", "bool_col", "null_col"]
                )

                # All non-null values should be masked regardless of type
                assert result == [
                    {
                        "id": 1,
                        "string_col": "***REDACTED***",
                        "int_col": "***REDACTED***",
                        "float_col": "***REDACTED***",
                        "bool_col": "***REDACTED***",
                        "null_col": None  # NULL preserved
                    }
                ]

            temp_db_path.unlink(missing_ok=True)

    def test_case_sensitive_column_names(self, tmp_path):
        """Test that column masking is case-sensitive."""
        init_project(tmp_path)
        db = CinchDB(database="test_db", project_dir=tmp_path)

        with patch("cinchdb.managers.tenant.TenantManager.get_tenant_db_path_for_operation") as mock_get_path:
            temp_db_path = Path(tempfile.NamedTemporaryFile(suffix=".db", delete=False).name)
            mock_get_path.return_value = temp_db_path

            with patch("cinchdb.core.connection.DatabaseConnection") as mock_db_conn:
                mock_conn = Mock()
                mock_cursor = Mock()
                mock_cursor.fetchall.return_value = [
                    {"id": 1, "Email": "alice@example.com", "email": "bob@example.com"}
                ]
                mock_conn.execute.return_value = mock_cursor
                mock_db_conn.return_value.__enter__.return_value = mock_conn

                # Mask only lowercase 'email'
                result = db.query(
                    "SELECT * FROM users",
                    mask_columns=["email"]
                )

                # Only exact match should be masked
                assert result == [
                    {"id": 1, "Email": "alice@example.com", "email": "***REDACTED***"}
                ]

            temp_db_path.unlink(missing_ok=True)
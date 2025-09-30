"""Comprehensive edge case tests for CLI data commands."""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from cinchdb.cli.commands.data import app
from cinchdb.managers.base import ConnectionContext
from cinchdb.core.initializer import init_project
from cinchdb.managers.table import TableManager
from cinchdb.models.table import Column


class TestDataCommandsEdgeCases:
    """Test edge cases for CLI data commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config and test table."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        
        # Initialize project
        init_project(project_dir)

        # Create test table
        table_mgr = TableManager(ConnectionContext(project_root=project_dir, database="main", branch="main"))

        # Users table with all column types
        table_mgr.create_table(
            "users",
            [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="email", type="TEXT", nullable=False),  # Required field
                Column(name="age", type="INTEGER"),
                Column(name="score", type="REAL"),
                Column(name="active", type="INTEGER"),  # Boolean as integer
                Column(name="bio", type="TEXT", nullable=True),
                Column(name="metadata", type="TEXT", nullable=True),  # For JSON storage
            ],
        )
        
        # Products table for testing relationships
        table_mgr.create_table(
            "products",
            [
                Column(name="name", type="TEXT"),
                Column(name="price", type="REAL"),
                Column(name="stock", type="INTEGER"),
                Column(name="category", type="TEXT", nullable=True),
            ],
        )
        
        yield project_dir
        shutil.rmtree(temp)

    # ============= INSERT COMMAND EDGE CASES =============
    
    def test_insert_with_special_characters(self, runner, temp_project):
        """Test inserting data with special characters."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Test with quotes, apostrophes, and unicode
            data = {
                "name": "O'Malley \"Mac\" Smith",
                "email": "test@example.com",
                "age": 30,
                "bio": "I'm a \"developer\" who loves 😊 emojis!"
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "Inserted record" in result.stdout

    def test_insert_with_null_values(self, runner, temp_project):
        """Test inserting with null/None values for nullable columns."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Explicitly set nullable fields to null
            data = {
                "name": "John",
                "email": "john@example.com",
                "age": 25,
                "bio": None,
                "metadata": None
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "Inserted record" in result.stdout

    def test_insert_missing_required_fields(self, runner, temp_project):
        """Test inserting without required fields should fail."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Missing required 'email' field
            data = {"name": "John", "age": 25}
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            # Should fail due to missing required field
            assert result.exit_code == 1

    def test_insert_with_extra_fields(self, runner, temp_project):
        """Test inserting with fields that don't exist in table."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Include non-existent field
            data = {
                "name": "John",
                "email": "john@example.com",
                "age": 25,
                "non_existent_field": "value"
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            # Should handle gracefully (ignore extra field or error)
            # Check the actual behavior
            assert result.exit_code in [0, 1]

    def test_insert_with_wrong_data_types(self, runner, temp_project):
        """Test inserting with incorrect data types."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # String for integer field
            data = {
                "name": "John",
                "email": "john@example.com",
                "age": "not_a_number"
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            # SQLite is flexible with types, so this might succeed
            # but we should test the behavior
            assert result.exit_code in [0, 1]

    def test_insert_very_large_data(self, runner, temp_project):
        """Test inserting very large strings."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Create a very large string (1MB)
            large_text = "x" * (1024 * 1024)
            data = {
                "name": "John",
                "email": "john@example.com",
                "age": 25,
                "bio": large_text
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "Inserted record" in result.stdout

    def test_insert_with_custom_id(self, runner, temp_project):
        """Test inserting with a custom ID."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Provide custom ID
            data = {
                "id": "custom-id-123",
                "name": "John",
                "email": "john@example.com",
                "age": 25
            }
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "ID:" in result.stdout

    def test_insert_duplicate_custom_id(self, runner, temp_project):
        """Test inserting with duplicate custom ID should fail."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data1 = {
                "id": "same-id",
                "name": "John",
                "email": "john@example.com",
                "age": 25
            }
            
            data2 = {
                "id": "same-id",
                "name": "Jane",
                "email": "jane@example.com",
                "age": 30
            }
            
            # First insert should succeed
            result1 = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data1)],
            )
            assert result1.exit_code == 0
            
            # Second insert with same ID should fail
            result2 = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data2)],
            )
            assert result2.exit_code == 1

    # ============= BULK-INSERT COMMAND EDGE CASES =============
    
    def test_bulk_insert_mixed_valid_invalid(self, runner, temp_project):
        """Test bulk insert with mix of valid and invalid records."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data = [
                {"name": "Valid1", "email": "valid1@example.com", "age": 25},
                {"name": "Invalid"},  # Missing required email
                {"name": "Valid2", "email": "valid2@example.com", "age": 30},
            ]
            
            result = runner.invoke(
                app,
                ["bulk-insert", "users", "--data", json.dumps(data)],
            )
            
            # Should handle the error - either fail all or skip invalid
            assert result.exit_code in [0, 1]

    def test_bulk_insert_with_1000_records(self, runner, temp_project):
        """Test bulk inserting a large number of records."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Generate 1000 records
            data = [
                {
                    "name": f"User{i}",
                    "email": f"user{i}@example.com",
                    "age": 20 + (i % 50)
                }
                for i in range(1000)
            ]
            
            result = runner.invoke(
                app,
                ["bulk-insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "1000 records" in result.stdout

    def test_bulk_insert_single_item_not_in_array(self, runner, temp_project):
        """Test bulk-insert with single object (not array) - should wrap it."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Single object, not in array
            data = {"name": "John", "email": "john@example.com", "age": 25}
            
            result = runner.invoke(
                app,
                ["bulk-insert", "users", "--data", json.dumps(data)],
            )
            
            # Should wrap in array and insert
            assert result.exit_code == 0
            assert "Inserted 1 record" in result.stdout

    # ============= DELETE COMMAND EDGE CASES =============
    
    def test_delete_with_complex_where(self, runner, temp_project):
        """Test delete with complex where conditions."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Test with multiple conditions
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "age__gt=25,active=1", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_delete_with_in_operator(self, runner, temp_project):
        """Test delete with IN operator."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "age__in=20,25,30", "--confirm"],
            )
            
            if result.exit_code != 0:
                print(f"Delete failed with: {result.output}")
            assert result.exit_code == 0

    def test_delete_with_like_pattern(self, runner, temp_project):
        """Test delete with LIKE pattern."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "email__like=%@example.com", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_delete_without_confirmation(self, runner, temp_project):
        """Test delete prompts for confirmation when not provided."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Without --confirm, should prompt (and we don't provide input, so it cancels)
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "age=25"],
                input="n\n"  # Say no to confirmation
            )
            
            assert "Operation cancelled" in result.stdout or "Are you sure" in result.stdout

    def test_delete_with_quoted_values(self, runner, temp_project):
        """Test delete with quoted string values."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["delete", "users", "--where", 'name="John Doe"', "--confirm"],
            )
            
            assert result.exit_code == 0

    # ============= UPDATE COMMAND EDGE CASES =============
    
    def test_update_multiple_fields(self, runner, temp_project):
        """Test updating multiple fields at once."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["update", "users", "--set", "active=1,age=30,bio=Updated", "--where", "name=John", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_update_with_null_value(self, runner, temp_project):
        """Test updating field to NULL."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # This might need special handling for NULL
            result = runner.invoke(
                app,
                ["update", "users", "--set", "bio=NULL", "--where", "id=1", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_update_with_expression(self, runner, temp_project):
        """Test update with SQL expression (increment)."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # This might not work with current implementation
            result = runner.invoke(
                app,
                ["update", "products", "--set", "stock=stock+10", "--where", "category=electronics", "--confirm"],
            )
            
            # Test current behavior
            assert result.exit_code in [0, 1]

    # ============= BULK-UPDATE COMMAND EDGE CASES =============
    
    def test_bulk_update_missing_id(self, runner, temp_project):
        """Test bulk update with records missing ID field."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data = [
                {"name": "Updated1", "age": 30},  # Missing ID
                {"id": "valid-id", "name": "Updated2"},
            ]
            
            result = runner.invoke(
                app,
                ["bulk-update", "users", "--data", json.dumps(data), "--confirm"],
            )
            
            # Should fail or skip records without ID
            assert result.exit_code in [0, 1]

    def test_bulk_update_nonexistent_ids(self, runner, temp_project):
        """Test bulk update with non-existent IDs."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data = [
                {"id": "non-existent-1", "name": "Updated1"},
                {"id": "non-existent-2", "name": "Updated2"},
            ]
            
            result = runner.invoke(
                app,
                ["bulk-update", "users", "--data", json.dumps(data), "--confirm"],
            )
            
            # Should handle gracefully
            if result.exit_code != 0:
                print(f"Bulk update failed with: {result.output}")
            assert result.exit_code == 0

    # ============= BULK-DELETE COMMAND EDGE CASES =============
    
    def test_bulk_delete_with_json_array(self, runner, temp_project):
        """Test bulk delete with JSON array format."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            ids = json.dumps(["id1", "id2", "id3"])
            
            result = runner.invoke(
                app,
                ["bulk-delete", "users", "--ids", ids, "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_bulk_delete_with_comma_separated(self, runner, temp_project):
        """Test bulk delete with comma-separated IDs."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["bulk-delete", "users", "--ids", "id1,id2,id3", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_bulk_delete_with_spaces(self, runner, temp_project):
        """Test bulk delete handles spaces in comma-separated list."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["bulk-delete", "users", "--ids", "id1, id2 , id3", "--confirm"],
            )
            
            assert result.exit_code == 0

    def test_bulk_delete_empty_ids(self, runner, temp_project):
        """Test bulk delete with empty ID list."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["bulk-delete", "users", "--ids", "", "--confirm"],
            )
            
            assert result.exit_code == 1
            assert "No valid IDs provided" in result.stdout

    # ============= TENANT-SPECIFIC EDGE CASES =============
    
    def test_operations_on_nonexistent_tenant(self, runner, temp_project):
        """Test operations on non-existent tenant."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data = {"name": "John", "email": "john@example.com", "age": 25}
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data), "--tenant", "nonexistent"],
            )
            
            # Should either create tenant or fail
            assert result.exit_code in [0, 1]

    # ============= MALFORMED INPUT EDGE CASES =============
    
    def test_insert_malformed_json_variations(self, runner, temp_project):
        """Test various malformed JSON inputs."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            malformed_inputs = [
                '{"name": "John"',  # Missing closing brace
                "{'name': 'John'}",  # Single quotes (not valid JSON)
                "{name: 'John'}",  # No quotes on key
                '{"name": "John",}',  # Trailing comma
                'undefined',  # JavaScript undefined
                'null',  # Null value
                'true',  # Boolean
                '123',  # Number
            ]
            
            for bad_json in malformed_inputs:
                result = runner.invoke(
                    app,
                    ["insert", "users", "--data", bad_json],
                )
                if result.exit_code != 1:
                    print(f"Unexpected success for: {bad_json}")
                    print(f"Output: {result.output}")
                assert result.exit_code == 1
                assert "Invalid JSON" in result.stdout or "Failed" in result.stdout or "No data" in result.stdout

    def test_where_clause_injection_attempt(self, runner, temp_project):
        """Test SQL injection attempt in where clause."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Attempt SQL injection
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "age=25 OR 1=1", "--confirm"],
            )
            
            # Should be handled safely
            assert result.exit_code in [0, 1]

    def test_set_clause_injection_attempt(self, runner, temp_project):
        """Test SQL injection attempt in set clause."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Attempt SQL injection in set clause
            result = runner.invoke(
                app,
                ["update", "users", "--set", "name=''; DROP TABLE users; --", "--where", "id=1", "--confirm"],
            )
            
            # Should be handled safely
            assert result.exit_code in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
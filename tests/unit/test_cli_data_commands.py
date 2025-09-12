"""Tests for CLI data commands (insert, delete, update, etc.)."""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from cinchdb.cli.commands.data import app
from cinchdb.core.initializer import init_project
from cinchdb.managers.table import TableManager
from cinchdb.models.table import Column


class TestCLIDataCommands:
    """Test suite for CLI data commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)
        
        # Initialize project
        init_project(project_dir)
        
        # Create a test table
        table_mgr = TableManager(project_dir, "main", "main")
        table_mgr.create_table(
            "users",
            [
                Column(name="name", type="TEXT"),
                Column(name="email", type="TEXT"),
                Column(name="age", type="INTEGER"),
                Column(name="active", type="INTEGER"),  # SQLite uses INTEGER for boolean
            ],
        )
        
        yield project_dir
        shutil.rmtree(temp)

    def test_insert_single_record(self, runner, temp_project):
        """Test inserting a single record."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            # Mock config
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Test data
            data = {"name": "Alice", "email": "alice@example.com", "age": 30}
            
            # Run command
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "Inserted 1 record" in result.stdout
            assert "ID:" in result.stdout

    def test_insert_multiple_records(self, runner, temp_project):
        """Test inserting multiple records."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # Test data - array of records
            data = [
                {"name": "Bob", "email": "bob@example.com", "age": 25},
                {"name": "Charlie", "email": "charlie@example.com", "age": 35},
            ]
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data)],
            )
            
            assert result.exit_code == 0
            assert "Inserted 2 records" in result.stdout
            assert "IDs:" in result.stdout

    def test_insert_with_tenant(self, runner, temp_project):
        """Test inserting data for a specific tenant."""
        # Create the tenant first
        from cinchdb.managers.tenant import TenantManager
        tenant_mgr = TenantManager(temp_project, "main", "main")
        tenant_mgr.create_tenant("customer_a")
        
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            data = {"name": "Dave", "email": "dave@tenant.com"}
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", json.dumps(data), "--tenant", "customer_a"],
            )
            
            assert result.exit_code == 0
            assert "Inserted 1 record" in result.stdout

    def test_insert_invalid_json(self, runner, temp_project):
        """Test inserting with invalid JSON."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", "not valid json"],
            )
            
            assert result.exit_code == 1
            assert "Invalid JSON format" in result.stdout

    def test_insert_empty_data(self, runner, temp_project):
        """Test inserting with empty data."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            result = runner.invoke(
                app,
                ["insert", "users", "--data", "[]"],
            )
            
            assert result.exit_code == 1
            assert "No data provided" in result.stdout

    def test_delete_with_where(self, runner, temp_project):
        """Test deleting records with where clause."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # First insert some data
            from cinchdb.core.database import CinchDB
            db = CinchDB("main", project_dir=temp_project)
            db.insert("users", {"name": "Test", "email": "test@example.com", "age": 40})
            
            # Delete with confirmation
            result = runner.invoke(
                app,
                ["delete", "users", "--where", "age=40", "--confirm"],
            )
            
            assert result.exit_code == 0
            assert "Deleted" in result.stdout or "No records matched" in result.stdout

    def test_update_with_where(self, runner, temp_project):
        """Test updating records with where clause."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # First insert some data
            from cinchdb.core.database import CinchDB
            db = CinchDB("main", project_dir=temp_project)
            db.insert("users", {"name": "UpdateMe", "email": "update@example.com", "age": 25, "active": False})
            
            # Update with confirmation
            result = runner.invoke(
                app,
                ["update", "users", "--set", "active=true", "--where", "name=UpdateMe", "--confirm"],
            )
            
            assert result.exit_code == 0
            assert "Updated" in result.stdout or "No records matched" in result.stdout

    def test_bulk_update(self, runner, temp_project):
        """Test bulk updating records."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # First insert some data
            from cinchdb.core.database import CinchDB
            db = CinchDB("main", project_dir=temp_project)
            result1 = db.insert("users", {"name": "User1", "email": "user1@example.com", "age": 20})
            result2 = db.insert("users", {"name": "User2", "email": "user2@example.com", "age": 30})
            
            # Bulk update
            update_data = [
                {"id": result1["id"], "age": 21},
                {"id": result2["id"], "age": 31},
            ]
            
            result = runner.invoke(
                app,
                ["bulk-update", "users", "--data", json.dumps(update_data), "--confirm"],
            )
            
            assert result.exit_code == 0
            assert "Updated 2 record(s)" in result.stdout

    def test_bulk_delete(self, runner, temp_project):
        """Test bulk deleting records."""
        with patch("cinchdb.cli.commands.data.get_config_with_data") as mock_config:
            mock_config.return_value = (
                MagicMock(project_dir=temp_project),
                MagicMock(active_database="main", active_branch="main"),
            )
            
            # First insert some data
            from cinchdb.core.database import CinchDB
            db = CinchDB("main", project_dir=temp_project)
            result1 = db.insert("users", {"name": "Delete1", "email": "del1@example.com", "age": 20})
            result2 = db.insert("users", {"name": "Delete2", "email": "del2@example.com", "age": 30})
            
            # Bulk delete
            ids = f"{result1['id']},{result2['id']}"
            
            result = runner.invoke(
                app,
                ["bulk-delete", "users", "--ids", ids, "--confirm"],
            )
            
            assert result.exit_code == 0
            assert "Deleted" in result.stdout
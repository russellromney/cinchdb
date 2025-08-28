"""Tests for the query CLI command."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typer.testing import CliRunner

from cinchdb.core.initializer import init_project
from cinchdb.managers.table import TableManager
from cinchdb.models import Column
from cinchdb.cli.main import app


class TestQueryCommand:
    """Test query CLI command."""

    def run_query_command(self, args, temp_project):
        """Helper to run query command in correct working directory."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)
            runner = CliRunner()
            return runner.invoke(app, args)
        finally:
            os.chdir(original_cwd)

    @pytest.fixture
    def temp_project(self):
        """Create a temporary test project."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)

        # Initialize project
        init_project(project_path)

        # Create a test table with data
        table_mgr = TableManager(project_path, "main", "main", "main")
        table_mgr.create_table(
            "users",
            [
                Column(name="name", type="TEXT", nullable=False),
                Column(name="email", type="TEXT", unique=True),
            ],
        )

        # Add some test data
        from cinchdb.core.path_utils import get_tenant_db_path
        from cinchdb.core.connection import DatabaseConnection

        db_path = get_tenant_db_path(project_path, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, created_at, name, email) VALUES ('1', '2023-01-01', 'Alice', 'alice@example.com')"
            )
            conn.execute(
                "INSERT INTO users (id, created_at, name, email) VALUES ('2', '2023-01-02', 'Bob', 'bob@example.com')"
            )
            conn.commit()

        yield project_path

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_query_select_basic(self, temp_project):
        """Test basic SELECT query."""
        result = self.run_query_command(
            ["query", "SELECT name FROM users"], temp_project
        )

        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

    def test_query_select_with_tenant(self, temp_project):
        """Test SELECT query with specific tenant."""
        result = self.run_query_command(
            ["query", "SELECT name FROM users", "--tenant", "main"], temp_project
        )

        assert result.exit_code == 0
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

    def test_query_json_format(self, temp_project):
        """Test query with JSON output format."""
        result = self.run_query_command(
            ["query", "SELECT name FROM users", "--format", "json"], temp_project
        )

        assert result.exit_code == 0
        assert '"name": "Alice"' in result.stdout
        assert '"name": "Bob"' in result.stdout

    def test_query_csv_format(self, temp_project):
        """Test query with CSV output format."""
        result = self.run_query_command(
            ["query", "SELECT name FROM users", "--format", "csv"], temp_project
        )

        assert result.exit_code == 0
        assert "name" in result.stdout  # CSV header
        assert "Alice" in result.stdout
        assert "Bob" in result.stdout

    def test_query_with_limit(self, temp_project):
        """Test query with LIMIT parameter."""
        result = self.run_query_command(
            ["query", "SELECT name FROM users", "--limit", "1"], temp_project
        )

        assert result.exit_code == 0
        # Should only show one result
        lines = [
            line
            for line in result.stdout.split("\n")
            if "Alice" in line or "Bob" in line
        ]
        assert len(lines) == 1

    def test_query_insert(self, temp_project):
        """Test INSERT query."""
        result = self.run_query_command(
            [
                "query",
                "INSERT INTO users (id, created_at, name, email) VALUES ('3', '2023-01-03', 'Charlie', 'charlie@example.com')",
            ],
            temp_project,
        )

        assert result.exit_code == 0
        assert "Query executed successfully" in result.stdout
        assert "Rows affected: 1" in result.stdout

    def test_query_update(self, temp_project):
        """Test UPDATE query."""
        result = self.run_query_command(
            ["query", "UPDATE users SET name = 'Alice Updated' WHERE name = 'Alice'"],
            temp_project,
        )

        assert result.exit_code == 0
        assert "Query executed successfully" in result.stdout
        assert "Rows affected: 1" in result.stdout

    def test_query_invalid_sql(self, temp_project):
        """Test query with invalid SQL."""
        result = self.run_query_command(["query", "INVALID SQL QUERY"], temp_project)

        assert result.exit_code == 1
        assert "Query error" in result.stdout

    def test_query_no_results(self, temp_project):
        """Test query with no results."""
        result = self.run_query_command(
            ["query", "SELECT * FROM users WHERE name = 'NonExistent'"], temp_project
        )

        assert result.exit_code == 0
        assert "No results" in result.stdout

    def test_query_help(self):
        """Test query command help."""
        runner = CliRunner()
        result = runner.invoke(app, ["query", "--help"])

        assert result.exit_code == 0
        assert "Execute a SQL query" in result.stdout
        assert "--tenant" in result.stdout
        assert "--format" in result.stdout
        assert "--limit" in result.stdout

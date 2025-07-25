"""Fast integration tests for CLI commands using CliRunner."""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from typer.testing import CliRunner

# Import the app directly
from cinchdb.cli.main import app

runner = CliRunner()


class TestCLIIntegration:
    """Fast CLI integration tests using CliRunner."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        yield project_path
        shutil.rmtree(temp_dir)

    def run_in_project(self, command, temp_project):
        """Run a command in the project directory."""
        original_cwd = os.getcwd()
        os.chdir(temp_project)
        try:
            return runner.invoke(app, command)
        finally:
            os.chdir(original_cwd)

    def test_project_initialization(self, temp_project):
        """Test project initialization workflow."""
        # Initialize project
        result = self.run_in_project(["init"], temp_project)
        assert result.exit_code == 0
        assert "Initialized CinchDB project" in result.stdout

        # Verify project structure
        assert (temp_project / ".cinchdb").exists()
        assert (temp_project / ".cinchdb" / "config.toml").exists()
        assert (temp_project / ".cinchdb" / "databases" / "main").exists()

        # Check version
        result = self.run_in_project(["version"], temp_project)
        assert result.exit_code == 0
        assert "CinchDB version" in result.stdout

    def test_database_operations(self, temp_project):
        """Test database CRUD operations."""
        # Initialize project
        self.run_in_project(["init"], temp_project)

        # List databases (should show main)
        result = self.run_in_project(["db", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout

        # Create new database
        result = self.run_in_project(["db", "create", "test_db"], temp_project)
        assert result.exit_code == 0
        assert "Created database 'test_db'" in result.stdout

        # List databases again
        result = self.run_in_project(["db", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout
        assert "test_db" in result.stdout

        # Switch to new database
        result = self.run_in_project(["db", "switch", "test_db"], temp_project)
        assert result.exit_code == 0
        assert "Switched to database 'test_db'" in result.stdout

        # Get database info
        result = self.run_in_project(["db", "info"], temp_project)
        assert result.exit_code == 0
        assert "test_db" in result.stdout

    def test_branch_operations(self, temp_project):
        """Test branch operations."""
        # Initialize project
        self.run_in_project(["init"], temp_project)

        # List branches (should show main)
        result = self.run_in_project(["branch", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout

        # Create feature branch
        result = self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        assert result.exit_code == 0
        assert "Created branch 'feature'" in result.stdout

        # List branches again
        result = self.run_in_project(["branch", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout
        assert "feature" in result.stdout

        # Switch to feature branch
        result = self.run_in_project(["branch", "switch", "feature"], temp_project)
        assert result.exit_code == 0
        assert "Switched to branch 'feature'" in result.stdout

        # Get branch info
        result = self.run_in_project(["branch", "info"], temp_project)
        assert result.exit_code == 0
        assert "feature" in result.stdout

    def test_table_operations(self, temp_project):
        """Test table operations."""
        # Initialize and setup
        self.run_in_project(["init"], temp_project)
        self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        self.run_in_project(["branch", "switch", "feature"], temp_project)

        # List tables (should be empty)
        result = self.run_in_project(["table", "list"], temp_project)
        assert result.exit_code == 0

        # Create table
        result = self.run_in_project(
            ["table", "create", "users", "name:TEXT:NOT NULL", "email:TEXT:UNIQUE"],
            temp_project,
        )
        assert result.exit_code == 0
        assert "Created table 'users'" in result.stdout

        # List tables
        result = self.run_in_project(["table", "list"], temp_project)
        assert result.exit_code == 0
        assert "users" in result.stdout

        # Get table info
        result = self.run_in_project(["table", "info", "users"], temp_project)
        assert result.exit_code == 0
        assert "users" in result.stdout
        assert "name" in result.stdout
        assert "email" in result.stdout

    def test_column_operations(self, temp_project):
        """Test column operations."""
        # Initialize and setup
        self.run_in_project(["init"], temp_project)
        self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        self.run_in_project(["branch", "switch", "feature"], temp_project)

        # Create table
        self.run_in_project(
            ["table", "create", "users", "name:TEXT:NOT NULL"], temp_project
        )

        # List columns
        result = self.run_in_project(["column", "list", "users"], temp_project)
        assert result.exit_code == 0
        assert "name" in result.stdout

        # Add column
        result = self.run_in_project(
            ["column", "add", "users", "age", "INTEGER"], temp_project
        )
        assert result.exit_code == 0
        assert "Added column 'age'" in result.stdout

        # List columns again
        result = self.run_in_project(["column", "list", "users"], temp_project)
        assert result.exit_code == 0
        assert "name" in result.stdout
        assert "age" in result.stdout

        # Get column info
        result = self.run_in_project(["column", "info", "users", "age"], temp_project)
        assert result.exit_code == 0
        assert "age" in result.stdout
        assert "INTEGER" in result.stdout

    def test_merge_workflow(self, temp_project):
        """Test complete merge workflow."""
        # Initialize and setup
        self.run_in_project(["init"], temp_project)
        self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        self.run_in_project(["branch", "switch", "feature"], temp_project)

        # Make changes in feature branch
        self.run_in_project(
            [
                "table",
                "create",
                "products",
                "name:TEXT:NOT NULL",
                "price:REAL:NOT NULL",
            ],
            temp_project,
        )

        self.run_in_project(
            ["column", "add", "products", "description", "TEXT"], temp_project
        )

        # Preview merge
        result = self.run_in_project(
            ["branch", "merge", "feature", "--target", "main", "--preview"],
            temp_project,
        )
        assert result.exit_code == 0
        assert "Merge Preview" in result.stdout
        assert "feature → main" in result.stdout

        # Merge into main
        result = self.run_in_project(
            ["branch", "merge-into-main", "feature"], temp_project
        )
        assert result.exit_code == 0
        assert "Successfully merged" in result.stdout

        # Switch to main and verify changes
        self.run_in_project(["branch", "switch", "main"], temp_project)

        result = self.run_in_project(["table", "list"], temp_project)
        assert result.exit_code == 0
        assert "products" in result.stdout

        result = self.run_in_project(["column", "list", "products"], temp_project)
        assert result.exit_code == 0
        assert "description" in result.stdout

    def test_tenant_operations(self, temp_project):
        """Test tenant operations."""
        # Initialize and setup
        self.run_in_project(["init"], temp_project)
        self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        self.run_in_project(["branch", "switch", "feature"], temp_project)

        # Create table first
        self.run_in_project(
            ["table", "create", "items", "name:TEXT:NOT NULL"], temp_project
        )

        # List tenants (should show main)
        result = self.run_in_project(["tenant", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout

        # Create new tenant
        result = self.run_in_project(["tenant", "create", "test_tenant"], temp_project)
        assert result.exit_code == 0
        assert "Created tenant 'test_tenant'" in result.stdout

        # List tenants again
        result = self.run_in_project(["tenant", "list"], temp_project)
        assert result.exit_code == 0
        assert "main" in result.stdout
        assert "test_tenant" in result.stdout

        # Query from specific tenant
        result = self.run_in_project(
            ["query", "SELECT * FROM items", "--tenant", "test_tenant"], temp_project
        )
        assert result.exit_code == 0

    def test_view_operations(self, temp_project):
        """Test view operations."""
        # Initialize and setup
        self.run_in_project(["init"], temp_project)
        self.run_in_project(
            ["branch", "create", "feature", "--source", "main"], temp_project
        )
        self.run_in_project(["branch", "switch", "feature"], temp_project)

        # Create tables
        self.run_in_project(
            ["table", "create", "users", "name:TEXT:NOT NULL"], temp_project
        )

        self.run_in_project(
            [
                "table",
                "create",
                "posts",
                "title:TEXT:NOT NULL",
                "user_id:TEXT:NOT NULL",
            ],
            temp_project,
        )

        # Create view
        result = self.run_in_project(
            [
                "view",
                "create",
                "user_posts",
                "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id",
            ],
            temp_project,
        )
        assert result.exit_code == 0
        assert "Created view 'user_posts'" in result.stdout

        # List views
        result = self.run_in_project(["view", "list"], temp_project)
        assert result.exit_code == 0
        assert "user_posts" in result.stdout

        # Get view info
        result = self.run_in_project(["view", "info", "user_posts"], temp_project)
        assert result.exit_code == 0
        assert "user_posts" in result.stdout
        assert "SELECT" in result.stdout

    def test_error_handling(self, temp_project):
        """Test CLI error handling."""
        # Try to run command outside project
        result = self.run_in_project(["table", "list"], temp_project)
        assert result.exit_code != 0
        # Check if the error is captured in the exception output
        output = (
            result.stdout + result.stderr + str(result.exception)
            if result.exception
            else ""
        )
        assert "No CinchDB project found from" in output

        # Initialize project for other tests
        self.run_in_project(["init"], temp_project)

        # Try to create duplicate database
        result = self.run_in_project(["db", "create", "main"], temp_project)
        assert result.exit_code != 0
        output = (
            result.stdout + result.stderr + str(result.exception)
            if result.exception
            else ""
        )
        assert "already exists" in output

        # Try to create table without columns
        result = self.run_in_project(["table", "create", "empty"], temp_project)
        assert result.exit_code != 0

        # Try to operate on non-existent table
        result = self.run_in_project(
            ["column", "add", "nonexistent", "col", "TEXT"], temp_project
        )
        assert result.exit_code != 0
        output = (
            result.stdout + result.stderr + str(result.exception)
            if result.exception
            else ""
        )
        assert "does not exist" in output or "not found" in output

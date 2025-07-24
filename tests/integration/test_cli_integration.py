"""Integration tests for CLI commands."""

import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path


class TestCLIIntegration:
    """Test CLI command integration."""
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_path = Path(temp_dir)
        yield project_path
        shutil.rmtree(temp_dir)
    
    def run_command(self, command, cwd=None, check=True):
        """Run a CLI command."""
        cmd = ["uv", "run", "cinch"] + command
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        if check and result.returncode != 0:
            pytest.fail(f"Command failed: {' '.join(cmd)}\\nStdout: {result.stdout}\\nStderr: {result.stderr}")
        return result
    
    def test_project_initialization(self, temp_project):
        """Test project initialization workflow."""
        # Initialize project
        result = self.run_command(["init"], cwd=temp_project)
        assert result.returncode == 0
        assert "Initialized CinchDB project" in result.stdout
        
        # Verify project structure
        assert (temp_project / ".cinchdb").exists()
        assert (temp_project / ".cinchdb" / "config.toml").exists()
        assert (temp_project / ".cinchdb" / "databases" / "main").exists()
        
        # Check version
        result = self.run_command(["version"], cwd=temp_project)
        assert result.returncode == 0
        assert "CinchDB version" in result.stdout
    
    def test_database_operations(self, temp_project):
        """Test database CRUD operations."""
        # Initialize project
        self.run_command(["init"], cwd=temp_project)
        
        # List databases (should show main)
        result = self.run_command(["db", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        
        # Create new database
        result = self.run_command(["db", "create", "test_db"], cwd=temp_project)
        assert result.returncode == 0
        assert "Created database 'test_db'" in result.stdout
        
        # List databases again
        result = self.run_command(["db", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        assert "test_db" in result.stdout
        
        # Switch to new database
        result = self.run_command(["db", "switch", "test_db"], cwd=temp_project)
        assert result.returncode == 0
        assert "Switched to database 'test_db'" in result.stdout
        
        # Get database info
        result = self.run_command(["db", "info"], cwd=temp_project)
        assert result.returncode == 0
        assert "test_db" in result.stdout
    
    def test_branch_operations(self, temp_project):
        """Test branch operations."""
        # Initialize project
        self.run_command(["init"], cwd=temp_project)
        
        # List branches (should show main)
        result = self.run_command(["branch", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        
        # Create feature branch
        result = self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        assert result.returncode == 0
        assert "Created branch 'feature'" in result.stdout
        
        # List branches again
        result = self.run_command(["branch", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        assert "feature" in result.stdout
        
        # Switch to feature branch
        result = self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        assert result.returncode == 0
        assert "Switched to branch 'feature'" in result.stdout
        
        # Get branch info
        result = self.run_command(["branch", "info"], cwd=temp_project)
        assert result.returncode == 0
        assert "feature" in result.stdout
    
    def test_table_operations(self, temp_project):
        """Test table operations."""
        # Initialize and setup
        self.run_command(["init"], cwd=temp_project)
        self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        
        # List tables (should be empty)
        result = self.run_command(["table", "list"], cwd=temp_project)
        assert result.returncode == 0
        
        # Create table
        result = self.run_command([
            "table", "create", "users",
            "name:TEXT:NOT NULL",
            "email:TEXT:UNIQUE"
        ], cwd=temp_project)
        assert result.returncode == 0
        assert "Created table 'users'" in result.stdout
        
        # List tables
        result = self.run_command(["table", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "users" in result.stdout
        
        # Get table info
        result = self.run_command(["table", "info", "users"], cwd=temp_project)
        assert result.returncode == 0
        assert "users" in result.stdout
        assert "name" in result.stdout
        assert "email" in result.stdout
    
    def test_column_operations(self, temp_project):
        """Test column operations."""
        # Initialize and setup
        self.run_command(["init"], cwd=temp_project)
        self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        
        # Create table
        self.run_command([
            "table", "create", "users",
            "name:TEXT:NOT NULL"
        ], cwd=temp_project)
        
        # List columns
        result = self.run_command(["column", "list", "users"], cwd=temp_project)
        assert result.returncode == 0
        assert "name" in result.stdout
        
        # Add column
        result = self.run_command(["column", "add", "users", "age", "INTEGER"], cwd=temp_project)
        assert result.returncode == 0
        assert "Added column 'age'" in result.stdout
        
        # List columns again
        result = self.run_command(["column", "list", "users"], cwd=temp_project)
        assert result.returncode == 0
        assert "name" in result.stdout
        assert "age" in result.stdout
        
        # Get column info
        result = self.run_command(["column", "info", "users", "age"], cwd=temp_project)
        assert result.returncode == 0
        assert "age" in result.stdout
        assert "INTEGER" in result.stdout
    
    def test_merge_workflow(self, temp_project):
        """Test complete merge workflow."""
        # Initialize and setup
        self.run_command(["init"], cwd=temp_project)
        self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        
        # Make changes in feature branch
        self.run_command([
            "table", "create", "products",
            "name:TEXT:NOT NULL",
            "price:REAL:NOT NULL"
        ], cwd=temp_project)
        
        self.run_command(["column", "add", "products", "description", "TEXT"], cwd=temp_project)
        
        # Preview merge
        result = self.run_command(["branch", "merge", "feature", "--target", "main", "--preview"], cwd=temp_project)
        assert result.returncode == 0
        assert "Merge Preview" in result.stdout
        assert "feature → main" in result.stdout
        
        # Merge into main
        result = self.run_command(["branch", "merge-into-main", "feature"], cwd=temp_project)
        assert result.returncode == 0
        assert "Successfully merged" in result.stdout
        
        # Switch to main and verify changes
        self.run_command(["branch", "switch", "main"], cwd=temp_project)
        
        result = self.run_command(["table", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "products" in result.stdout
        
        result = self.run_command(["column", "list", "products"], cwd=temp_project)
        assert result.returncode == 0
        assert "description" in result.stdout
    
    def test_tenant_operations(self, temp_project):
        """Test tenant operations."""
        # Initialize and setup
        self.run_command(["init"], cwd=temp_project)
        self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        
        # Create table first
        self.run_command([
            "table", "create", "items",
            "name:TEXT:NOT NULL"
        ], cwd=temp_project)
        
        # List tenants (should show main)
        result = self.run_command(["tenant", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        
        # Create new tenant
        result = self.run_command(["tenant", "create", "test_tenant"], cwd=temp_project)
        assert result.returncode == 0
        assert "Created tenant 'test_tenant'" in result.stdout
        
        # List tenants again
        result = self.run_command(["tenant", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "main" in result.stdout
        assert "test_tenant" in result.stdout
        
        # Query from specific tenant
        result = self.run_command([
            "query", "SELECT * FROM items", "--tenant", "test_tenant"
        ], cwd=temp_project)
        assert result.returncode == 0
    
    def test_view_operations(self, temp_project):
        """Test view operations."""
        # Initialize and setup
        self.run_command(["init"], cwd=temp_project)
        self.run_command(["branch", "create", "feature", "--source", "main"], cwd=temp_project)
        self.run_command(["branch", "switch", "feature"], cwd=temp_project)
        
        # Create tables
        self.run_command([
            "table", "create", "users",
            "name:TEXT:NOT NULL"
        ], cwd=temp_project)
        
        self.run_command([
            "table", "create", "posts",
            "title:TEXT:NOT NULL",
            "user_id:TEXT:NOT NULL"
        ], cwd=temp_project)
        
        # Create view
        result = self.run_command([
            "view", "create", "user_posts",
            "SELECT u.name, p.title FROM users u JOIN posts p ON u.id = p.user_id"
        ], cwd=temp_project)
        assert result.returncode == 0
        assert "Created view 'user_posts'" in result.stdout
        
        # List views
        result = self.run_command(["view", "list"], cwd=temp_project)
        assert result.returncode == 0
        assert "user_posts" in result.stdout
        
        # Get view info
        result = self.run_command(["view", "info", "user_posts"], cwd=temp_project)
        assert result.returncode == 0
        assert "user_posts" in result.stdout
        assert "SELECT" in result.stdout
    
    def test_error_handling(self, temp_project):
        """Test CLI error handling."""
        # Try to run command outside project
        result = self.run_command(["table", "list"], cwd=temp_project, check=False)
        assert result.returncode != 0
        assert "Not in a CinchDB project directory" in result.stderr
        
        # Initialize project for other tests
        self.run_command(["init"], cwd=temp_project)
        
        # Try to create duplicate database
        result = self.run_command(["db", "create", "main"], cwd=temp_project, check=False)
        assert result.returncode != 0
        assert "already exists" in result.stdout
        
        # Try to create table without columns
        result = self.run_command(["table", "create", "empty"], cwd=temp_project, check=False)
        assert result.returncode != 0
        
        # Try to operate on non-existent table
        result = self.run_command(["column", "add", "nonexistent", "col", "TEXT"], cwd=temp_project, check=False)
        assert result.returncode != 0
        assert "does not exist" in result.stdout or "not found" in result.stdout
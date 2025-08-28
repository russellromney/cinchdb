"""Tests for CLI foreign key parsing."""

import pytest
from typer.testing import CliRunner
from cinchdb.cli.main import app
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.table import TableManager
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


class TestCLIForeignKeys:
    """Test CLI foreign key functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        # Change to project directory for CLI commands
        import os

        old_cwd = os.getcwd()
        os.chdir(temp)

        yield project_dir

        os.chdir(old_cwd)
        shutil.rmtree(temp)

    @pytest.fixture
    def runner(self):
        """Create a CLI runner."""
        return CliRunner()

    def test_cli_create_table_with_foreign_key_basic(self, runner, temp_project):
        """Test creating table with basic foreign key syntax."""
        # Create users table first
        result = runner.invoke(
            app, ["table", "create", "users", "username:TEXT", "email:TEXT"]
        )
        assert result.exit_code == 0

        # Create posts table with foreign key
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "content:TEXT",
                "author_id:TEXT:fk=users",
            ],
        )
        assert result.exit_code == 0
        assert "Created table 'posts'" in result.output

        # Verify foreign key was created
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            sql = cursor.fetchone()["sql"]
            assert "FOREIGN KEY (author_id) REFERENCES users(id)" in sql

    def test_cli_foreign_key_with_column(self, runner, temp_project):
        """Test foreign key with specific column."""
        # Create users table
        result = runner.invoke(
            app, ["table", "create", "users", "username:TEXT", "email:TEXT"]
        )
        assert result.exit_code == 0

        # Create posts with FK to specific column
        result = runner.invoke(
            app,
            ["table", "create", "posts", "title:TEXT", "author_id:TEXT:fk=users.id"],
        )
        assert result.exit_code == 0

        # Verify
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            sql = cursor.fetchone()["sql"]
            assert "FOREIGN KEY (author_id) REFERENCES users(id)" in sql

    def test_cli_foreign_key_with_cascade(self, runner, temp_project):
        """Test foreign key with cascade action."""
        # Create users table
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        # Create posts with CASCADE delete
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "author_id:TEXT:fk=users.cascade",
            ],
        )
        assert result.exit_code == 0

        # Verify CASCADE
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON DELETE CASCADE" in sql

    def test_cli_foreign_key_full_syntax(self, runner, temp_project):
        """Test foreign key with table.column.action syntax."""
        # Create users table
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        # Create posts with full FK syntax
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "author_id:TEXT:fk=users.id.cascade",
            ],
        )
        assert result.exit_code == 0

        # Verify
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            sql = cursor.fetchone()["sql"]
            assert (
                "FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE" in sql
            )

    def test_cli_nullable_with_foreign_key(self, runner, temp_project):
        """Test combining nullable and foreign key."""
        # Create users table
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        # Create posts with nullable FK
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "author_id:TEXT:nullable:fk=users",
            ],
        )
        assert result.exit_code == 0

        # Verify column is nullable and has FK
        table_mgr = TableManager(temp_project, "main", "main", "main")
        posts = table_mgr.get_table("posts")
        author_col = next(col for col in posts.columns if col.name == "author_id")
        assert author_col.nullable is True
        assert author_col.foreign_key is not None
        assert author_col.foreign_key.table == "users"

    def test_cli_multiple_foreign_keys(self, runner, temp_project):
        """Test table with multiple foreign keys."""
        # Create referenced tables
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["table", "create", "posts", "title:TEXT"])
        assert result.exit_code == 0

        # Create comments with multiple FKs
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "comments",
                "content:TEXT",
                "user_id:TEXT:fk=users",
                "post_id:TEXT:fk=posts",
            ],
        )
        assert result.exit_code == 0

        # Verify both FKs
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='comments'"
            )
            sql = cursor.fetchone()["sql"]
            assert "FOREIGN KEY (user_id) REFERENCES users(id)" in sql
            assert "FOREIGN KEY (post_id) REFERENCES posts(id)" in sql

    def test_cli_invalid_fk_action(self, runner, temp_project):
        """Test invalid foreign key action."""
        # Create users table
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        # Try invalid action
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "author_id:TEXT:fk=users.id.invalid",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid foreign key format" in result.output

    def test_cli_fk_to_nonexistent_table(self, runner, temp_project):
        """Test foreign key to non-existent table."""
        result = runner.invoke(
            app,
            ["table", "create", "posts", "title:TEXT", "author_id:TEXT:fk=nonexistent"],
        )
        assert result.exit_code == 1
        assert "non-existent table" in result.output

    def test_cli_set_null_action(self, runner, temp_project):
        """Test SET NULL action."""
        # Create users table
        result = runner.invoke(app, ["table", "create", "users", "username:TEXT"])
        assert result.exit_code == 0

        # Create posts with SET NULL
        result = runner.invoke(
            app,
            [
                "table",
                "create",
                "posts",
                "title:TEXT",
                "author_id:TEXT:nullable:fk=users.set null",
            ],
        )
        assert result.exit_code == 0

        # Verify
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON DELETE SET NULL" in sql

"""Tests for foreign key functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path
from cinchdb.core.initializer import init_project
from cinchdb.managers.table import TableManager
from cinchdb.models import Column, ForeignKeyRef
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path


class TestForeignKeys:
    """Test foreign key functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def table_manager(self, temp_project):
        """Create a TableManager instance."""
        return TableManager(temp_project, "main", "main", "main")

    def test_create_table_with_foreign_key(self, table_manager, temp_project):
        """Test creating a table with a foreign key."""
        # Create users table first
        user_columns = [
            Column(name="username", type="TEXT", nullable=False, unique=True),
            Column(name="email", type="TEXT", nullable=False),
        ]
        table_manager.create_table("users", user_columns)

        # Create posts table with foreign key
        post_columns = [
            Column(name="title", type="TEXT", nullable=False),
            Column(name="content", type="TEXT"),
            Column(
                name="author_id",
                type="TEXT",
                nullable=False,
                foreign_key=ForeignKeyRef(
                    table="users", column="id", on_delete="CASCADE"
                ),
            ),
        ]
        posts_table = table_manager.create_table("posts", post_columns)

        # Verify table was created
        assert posts_table.name == "posts"

        # Verify foreign key is tracked in column
        author_col = next(col for col in posts_table.columns if col.name == "author_id")
        assert author_col.foreign_key is not None
        assert author_col.foreign_key.table == "users"
        assert author_col.foreign_key.column == "id"
        assert author_col.foreign_key.on_delete == "CASCADE"

        # Verify SQL contains foreign key constraint
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            create_sql = cursor.fetchone()["sql"]
            assert (
                "FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE"
                in create_sql
            )

    def test_foreign_key_default_column(self, table_manager):
        """Test foreign key defaults to id column."""
        # Create users table
        table_manager.create_table("users", [Column(name="username", type="TEXT")])

        # Create posts table with FK that doesn't specify column
        post_columns = [
            Column(
                name="author_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="users"),
            ),
        ]
        posts_table = table_manager.create_table("posts", post_columns)

        # Verify default column is 'id'
        author_col = next(col for col in posts_table.columns if col.name == "author_id")
        assert author_col.foreign_key.column == "id"

    def test_foreign_key_actions(self, table_manager, temp_project):
        """Test different foreign key actions."""
        # Create parent table
        table_manager.create_table("categories", [Column(name="name", type="TEXT")])

        # Test CASCADE
        cascade_cols = [
            Column(
                name="category_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="categories", on_delete="CASCADE"),
            ),
        ]
        table_manager.create_table("products_cascade", cascade_cols)

        # Test SET NULL
        setnull_cols = [
            Column(
                name="category_id",
                type="TEXT",
                nullable=True,
                foreign_key=ForeignKeyRef(table="categories", on_delete="SET NULL"),
            ),
        ]
        table_manager.create_table("products_setnull", setnull_cols)

        # Test NO ACTION
        noaction_cols = [
            Column(
                name="category_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="categories", on_delete="NO ACTION"),
            ),
        ]
        table_manager.create_table("products_noaction", noaction_cols)

        # Verify SQL for each
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            # CASCADE
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='products_cascade'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON DELETE CASCADE" in sql

            # SET NULL
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='products_setnull'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON DELETE SET NULL" in sql

            # NO ACTION
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='products_noaction'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON DELETE NO ACTION" in sql

    def test_multiple_foreign_keys(self, table_manager):
        """Test table with multiple foreign keys."""
        # Create referenced tables
        table_manager.create_table("users", [Column(name="username", type="TEXT")])
        table_manager.create_table("posts", [Column(name="title", type="TEXT")])

        # Create comments table with multiple FKs
        comment_cols = [
            Column(name="content", type="TEXT"),
            Column(
                name="user_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="users"),
            ),
            Column(
                name="post_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="posts"),
            ),
        ]
        comments_table = table_manager.create_table("comments", comment_cols)

        # Verify both foreign keys
        fk_cols = [col for col in comments_table.columns if col.foreign_key]
        assert len(fk_cols) == 2
        assert any(col.foreign_key.table == "users" for col in fk_cols)
        assert any(col.foreign_key.table == "posts" for col in fk_cols)

    def test_self_referential_foreign_key(self, table_manager):
        """Test self-referential foreign key."""
        # Create employees table with manager reference
        emp_cols = [
            Column(name="name", type="TEXT"),
            Column(
                name="manager_id",
                type="TEXT",
                nullable=True,
                foreign_key=ForeignKeyRef(table="employees"),
            ),
        ]

        # This should fail because employees table doesn't exist yet
        with pytest.raises(ValueError) as exc:
            table_manager.create_table("employees", emp_cols)
        assert "non-existent table" in str(exc.value)

        # Create table without FK first
        table_manager.create_table("employees", [Column(name="name", type="TEXT")])

        # Then create another table with FK to employees
        dept_cols = [
            Column(name="name", type="TEXT"),
            Column(
                name="manager_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="employees"),
            ),
        ]
        table_manager.create_table("departments", dept_cols)

    def test_foreign_key_to_nonexistent_table(self, table_manager):
        """Test foreign key to non-existent table fails."""
        columns = [
            Column(
                name="user_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="nonexistent"),
            ),
        ]

        with pytest.raises(ValueError) as exc:
            table_manager.create_table("posts", columns)
        assert "non-existent table: 'nonexistent'" in str(exc.value)

    def test_foreign_key_to_nonexistent_column(self, table_manager):
        """Test foreign key to non-existent column fails."""
        # Create users table
        table_manager.create_table("users", [Column(name="username", type="TEXT")])

        # Try to reference non-existent column
        columns = [
            Column(
                name="user_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="users", column="nonexistent"),
            ),
        ]

        with pytest.raises(ValueError) as exc:
            table_manager.create_table("posts", columns)
        assert "non-existent column: 'users.nonexistent'" in str(exc.value)

    def test_foreign_key_on_update_actions(self, table_manager, temp_project):
        """Test foreign key ON UPDATE actions."""
        # Create parent table
        table_manager.create_table("users", [Column(name="username", type="TEXT")])

        # Create child table with ON UPDATE CASCADE
        columns = [
            Column(
                name="user_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(
                    table="users", on_delete="RESTRICT", on_update="CASCADE"
                ),
            ),
        ]
        table_manager.create_table("sessions", columns)

        # Verify SQL
        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            sql = cursor.fetchone()["sql"]
            assert "ON UPDATE CASCADE" in sql

    def test_foreign_key_enforcement(self, table_manager, temp_project):
        """Test that foreign key constraints are actually enforced."""
        # Create users table and add a user
        table_manager.create_table("users", [Column(name="username", type="TEXT")])

        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            # Add a user
            conn.execute(
                "INSERT INTO users (id, username, created_at) VALUES (?, ?, datetime('now'))",
                ("user1", "testuser"),
            )
            conn.commit()

        # Create posts table with foreign key
        columns = [
            Column(name="title", type="TEXT"),
            Column(
                name="author_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="users"),
            ),
        ]
        table_manager.create_table("posts", columns)

        with DatabaseConnection(db_path) as conn:
            # This should work - valid foreign key
            conn.execute(
                "INSERT INTO posts (id, title, author_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("post1", "Test Post", "user1"),
            )
            conn.commit()

            # This should fail - invalid foreign key
            with pytest.raises(Exception) as exc:
                conn.execute(
                    "INSERT INTO posts (id, title, author_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                    ("post2", "Bad Post", "nonexistent_user"),
                )
            assert "FOREIGN KEY constraint failed" in str(exc.value)

    def test_cascade_delete(self, table_manager, temp_project):
        """Test CASCADE delete action."""
        # Create users table
        table_manager.create_table("users", [Column(name="username", type="TEXT")])

        # Create posts table with CASCADE delete
        columns = [
            Column(name="title", type="TEXT"),
            Column(
                name="author_id",
                type="TEXT",
                foreign_key=ForeignKeyRef(table="users", on_delete="CASCADE"),
            ),
        ]
        table_manager.create_table("posts", columns)

        db_path = get_tenant_db_path(temp_project, "main", "main", "main")
        with DatabaseConnection(db_path) as conn:
            # Add a user and post
            conn.execute(
                "INSERT INTO users (id, username, created_at) VALUES (?, ?, datetime('now'))",
                ("user1", "testuser"),
            )
            conn.execute(
                "INSERT INTO posts (id, title, author_id, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("post1", "Test Post", "user1"),
            )
            conn.commit()

            # Verify post exists
            cursor = conn.execute("SELECT COUNT(*) as count FROM posts")
            assert cursor.fetchone()["count"] == 1

            # Delete user - should cascade delete posts
            conn.execute("DELETE FROM users WHERE id = ?", ("user1",))
            conn.commit()

            # Verify post was deleted
            cursor = conn.execute("SELECT COUNT(*) as count FROM posts")
            assert cursor.fetchone()["count"] == 0

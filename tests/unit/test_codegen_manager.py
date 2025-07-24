"""Tests for CodegenManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

from cinchdb.config import Config
from cinchdb.managers import TableManager, ViewModel, CodegenManager
from cinchdb.models import Column


class TestCodegenManager:
    """Test CodegenManager functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary test project."""
        temp = tempfile.mkdtemp()
        project_root = Path(temp)

        # Initialize project
        config = Config(project_root)
        config.init_project()

        yield project_root

        # Cleanup
        shutil.rmtree(temp)

    @pytest.fixture
    def codegen_manager(self, temp_project):
        """Create CodegenManager with test data."""
        # Create some test tables
        table_manager = TableManager(temp_project, "main", "main", "main")

        # Create users table
        users_columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False, unique=True),
            Column(name="age", type="INTEGER", nullable=True),
        ]
        table_manager.create_table("users", users_columns)

        # Create posts table
        posts_columns = [
            Column(name="title", type="TEXT", nullable=False),
            Column(name="content", type="TEXT", nullable=True),
            Column(name="user_id", type="TEXT", nullable=False),
        ]
        table_manager.create_table("posts", posts_columns)

        # Create a view
        view_manager = ViewModel(temp_project, "main", "main", "main")
        view_manager.create_view(
            "user_posts",
            "SELECT u.name, u.email, p.title FROM users u JOIN posts p ON u.id = p.user_id",
        )

        return CodegenManager(temp_project, "main", "main", "main")

    def test_get_supported_languages(self, codegen_manager):
        """Test getting supported languages."""
        languages = codegen_manager.get_supported_languages()

        assert isinstance(languages, list)
        assert "python" in languages
        assert "typescript" in languages
        assert len(languages) == 2

    def test_generate_python_models_tables_only(self, codegen_manager, temp_project):
        """Test generating Python models for tables only."""
        output_dir = temp_project / "generated_models"

        results = codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=True,
            include_views=False,
        )

        # Check results structure
        assert results["language"] == "python"
        assert results["output_dir"] == str(output_dir)
        assert (
            len(results["files_generated"]) == 4
        )  # users.py, posts.py, cinch_models.py, __init__.py
        assert len(results["tables_processed"]) == 2
        assert "users" in results["tables_processed"]
        assert "posts" in results["tables_processed"]
        assert len(results["views_processed"]) == 0

        # Check files exist
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "users.py").exists()
        assert (output_dir / "posts.py").exists()
        assert (output_dir / "cinch_models.py").exists()

        # Check users.py content
        users_content = (output_dir / "users.py").read_text()
        assert "class Users(BaseModel):" in users_content
        assert "name: str" in users_content
        assert "email: str" in users_content
        assert "age: Optional[int]" in users_content
        assert "id: Optional[str]" in users_content
        assert "created_at: Optional[datetime]" in users_content
        assert "updated_at: Optional[datetime]" in users_content

        # Check __init__.py content
        init_content = (output_dir / "__init__.py").read_text()
        assert "from .users import Users" in init_content
        assert "from .posts import Posts" in init_content
        assert '"Users"' in init_content
        assert '"Posts"' in init_content

    def test_generate_python_models_views_only(self, codegen_manager, temp_project):
        """Test generating Python models for views only."""
        output_dir = temp_project / "generated_views"

        results = codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=False,
            include_views=True,
        )

        # Check results
        assert results["language"] == "python"
        assert len(results["tables_processed"]) == 0
        assert len(results["views_processed"]) == 1
        assert "user_posts" in results["views_processed"]

        # Check files exist
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "user_posts_view.py").exists()

        # Check view content
        view_content = (output_dir / "user_posts_view.py").read_text()
        assert "class UserPostsView(BaseModel):" in view_content
        assert "readonly" in view_content

    def test_generate_python_models_both(self, codegen_manager, temp_project):
        """Test generating Python models for both tables and views."""
        output_dir = temp_project / "generated_all"

        results = codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=True,
            include_views=True,
        )

        # Check results
        assert len(results["tables_processed"]) == 2
        assert len(results["views_processed"]) == 1
        assert (
            len(results["files_generated"]) == 5
        )  # 2 tables + 1 view + cinch_models.py + __init__.py

        # Check all files exist
        assert (output_dir / "__init__.py").exists()
        assert (output_dir / "users.py").exists()
        assert (output_dir / "posts.py").exists()
        assert (output_dir / "user_posts_view.py").exists()
        assert (output_dir / "cinch_models.py").exists()

    def test_generate_typescript_placeholder(self, codegen_manager, temp_project):
        """Test TypeScript generation (currently placeholder)."""
        output_dir = temp_project / "generated_ts"

        results = codegen_manager.generate_models(
            language="typescript", output_dir=output_dir
        )

        # Should create placeholder file
        assert (output_dir / "typescript_generation_todo.md").exists()
        assert "typescript_generation_todo.md" in results["files_generated"]

    def test_invalid_language(self, codegen_manager, temp_project):
        """Test error handling for invalid language."""
        output_dir = temp_project / "generated_invalid"

        with pytest.raises(ValueError, match="Language 'java' not supported"):
            codegen_manager.generate_models(language="java", output_dir=output_dir)

    def test_output_directory_creation(self, codegen_manager, temp_project):
        """Test that output directory is created if it doesn't exist."""
        output_dir = temp_project / "deeply" / "nested" / "path"
        assert not output_dir.exists()

        codegen_manager.generate_models(language="python", output_dir=output_dir)

        assert output_dir.exists()
        assert (output_dir / "__init__.py").exists()

    def test_snake_case_conversion(self, codegen_manager):
        """Test snake_case conversion utility."""
        assert codegen_manager._to_snake_case("UserPosts") == "user_posts"
        assert codegen_manager._to_snake_case("user_posts") == "user_posts"
        assert (
            codegen_manager._to_snake_case("HTTPResponseCode") == "http_response_code"
        )
        assert codegen_manager._to_snake_case("simple") == "simple"

    def test_pascal_case_conversion(self, codegen_manager):
        """Test PascalCase conversion utility."""
        assert codegen_manager._to_pascal_case("user_posts") == "UserPosts"
        assert codegen_manager._to_pascal_case("UserPosts") == "UserPosts"
        assert (
            codegen_manager._to_pascal_case("http_response_code") == "HttpResponseCode"
        )
        assert codegen_manager._to_pascal_case("simple") == "Simple"

    def test_sqlite_to_python_type_mapping(self, codegen_manager):
        """Test SQLite to Python type mapping."""
        assert codegen_manager._sqlite_to_python_type("TEXT") == "str"
        assert codegen_manager._sqlite_to_python_type("VARCHAR(255)") == "str"
        assert codegen_manager._sqlite_to_python_type("INTEGER") == "int"
        assert codegen_manager._sqlite_to_python_type("REAL") == "float"
        assert codegen_manager._sqlite_to_python_type("FLOAT") == "float"
        assert codegen_manager._sqlite_to_python_type("BLOB") == "bytes"
        assert codegen_manager._sqlite_to_python_type("NUMERIC") == "float"

    def test_python_field_generation(self, codegen_manager):
        """Test Python field generation for different column types."""
        # Non-nullable string field
        col = Column(name="name", type="TEXT", nullable=False)
        field = codegen_manager._generate_python_field(col)
        assert "name: str" in field
        assert "Optional" not in field

        # Nullable integer field
        col = Column(name="age", type="INTEGER", nullable=True)
        field = codegen_manager._generate_python_field(col)
        assert "age: Optional[int]" in field
        assert "default=None" in field

        # ID field (special case - now Optional for CRUD operations)
        col = Column(name="id", type="TEXT", nullable=False, primary_key=True)
        field = codegen_manager._generate_python_field(col)
        assert "id: Optional[str]" in field
        assert "default=None" in field

        # Created at field (special case - now Optional for model creation)
        col = Column(name="created_at", type="TEXT", nullable=False)
        field = codegen_manager._generate_python_field(col)
        assert "created_at: Optional[datetime]" in field
        assert "default=None" in field

    def test_generated_model_imports(self, codegen_manager, temp_project):
        """Test that generated models have correct imports."""
        output_dir = temp_project / "test_imports"

        codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=True,
            include_views=False,
        )

        # Check users.py imports
        users_content = (output_dir / "users.py").read_text()
        assert "from typing import Optional" in users_content
        assert "from datetime import datetime" in users_content
        assert "from pydantic import BaseModel, Field" in users_content

    def test_generated_model_config(self, codegen_manager, temp_project):
        """Test that generated models have correct configuration."""
        output_dir = temp_project / "test_config"

        codegen_manager.generate_models(
            language="python",
            output_dir=output_dir,
            include_tables=True,
            include_views=False,
        )

        # Check model config
        users_content = (output_dir / "users.py").read_text()
        assert "model_config = ConfigDict(" in users_content
        assert "from_attributes=True" in users_content
        assert '"table_name": "users"' in users_content

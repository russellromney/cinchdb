"""Tests for unified codegen CLI functionality (local and remote)."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import responses

from cinchdb.cli.handlers import CodegenHandler
from cinchdb.config import Config
from cinchdb.core.initializer import init_project


class TestUnifiedCodegenCLI:
    """Test unified codegen CLI functionality."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create project structure
        cinchdb_dir = temp_dir / ".cinchdb"
        cinchdb_dir.mkdir()

        # Create config - initialize project first
        config = Config(temp_dir)
        init_project(temp_dir)  # This creates the config file
        config_data = config.load()
        config_data.active_database = "test_db"
        config_data.active_branch = "main"
        config.save(config_data)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_config_data(self):
        """Mock configuration data."""
        return {
            "active_database": "test_db",
            "active_branch": "main",
            "project_root": Path("/tmp/test"),
        }

    @pytest.fixture
    def mock_config_data_with_api(self):
        """Mock configuration data with API settings."""
        return {
            "active_database": "test_db",
            "active_branch": "main",
            "project_root": Path("/tmp/test"),
            "api": {"url": "https://api.example.com", "key": "test-api-key"},
        }

    def test_codegen_handler_local_mode(self, mock_config_data, temp_project):
        """Test CodegenHandler in local mode."""
        handler = CodegenHandler(mock_config_data)

        assert handler.is_remote is False
        assert handler.api_url is None
        assert handler.api_key is None

    def test_codegen_handler_remote_mode(self, mock_config_data_with_api):
        """Test CodegenHandler in remote mode."""
        handler = CodegenHandler(mock_config_data_with_api)

        assert handler.is_remote is True
        assert handler.api_url == "https://api.example.com"
        assert handler.api_key == "test-api-key"

    def test_codegen_handler_force_local(self, mock_config_data_with_api):
        """Test CodegenHandler forced to local mode."""
        handler = CodegenHandler(mock_config_data_with_api, force_local=True)

        assert handler.is_remote is False

    def test_codegen_handler_override_api_settings(self, mock_config_data):
        """Test CodegenHandler with overridden API settings."""
        handler = CodegenHandler(
            mock_config_data, api_url="https://override.com", api_key="override-key"
        )

        assert handler.is_remote is True
        assert handler.api_url == "https://override.com"
        assert handler.api_key == "override-key"

    @patch("cinchdb.cli.handlers.codegen_handler.CodegenManager")
    def test_local_generation(
        self, mock_codegen_manager, mock_config_data, temp_project
    ):
        """Test local model generation."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_manager_instance.generate_models.return_value = {
            "files_generated": ["user.py", "post.py"],
            "tables_processed": ["users", "posts"],
            "views_processed": [],
            "output_dir": "/tmp/output",
            "language": "python",
        }
        mock_codegen_manager.return_value = mock_manager_instance

        handler = CodegenHandler(mock_config_data)
        output_dir = temp_project / "models"

        result = handler.generate_models(
            language="python",
            output_dir=output_dir,
            database="test_db",
            branch="main",
            project_root=temp_project,
        )

        assert result["files_generated"] == ["user.py", "post.py"]
        assert result["tables_processed"] == ["users", "posts"]
        assert not result.get("remote", False)

        # Verify manager was called correctly
        mock_codegen_manager.assert_called_once()
        mock_manager_instance.generate_models.assert_called_once()

    @responses.activate
    def test_remote_generation(self, mock_config_data_with_api, temp_project):
        """Test remote model generation."""
        # Setup mock API response
        responses.add(
            responses.POST,
            "https://api.example.com/api/v1/codegen/generate/files",
            json={
                "files": [
                    {"filename": "user.py", "content": "class User: pass"},
                    {"filename": "post.py", "content": "class Post: pass"},
                ],
                "tables_processed": ["users", "posts"],
                "views_processed": [],
                "language": "python",
            },
            status=200,
        )

        handler = CodegenHandler(mock_config_data_with_api)
        output_dir = temp_project / "models"

        result = handler.generate_models(
            language="python", output_dir=output_dir, database="test_db", branch="main"
        )

        assert result["files_generated"] == ["user.py", "post.py"]
        assert result["tables_processed"] == ["users", "posts"]
        assert result["remote"] is True

        # Verify files were written
        assert (output_dir / "user.py").exists()
        assert (output_dir / "post.py").exists()
        assert (output_dir / "user.py").read_text() == "class User: pass"

    @responses.activate
    def test_remote_generation_api_error(self, mock_config_data_with_api, temp_project):
        """Test remote generation handles API errors."""
        # Setup mock API error response
        responses.add(
            responses.POST,
            "https://api.example.com/api/v1/codegen/generate/files",
            json={"error": "Database not found"},
            status=404,
        )

        handler = CodegenHandler(mock_config_data_with_api)
        output_dir = temp_project / "models"

        with pytest.raises(RuntimeError, match="Remote codegen failed"):
            handler.generate_models(
                language="python",
                output_dir=output_dir,
                database="test_db",
                branch="main",
            )

    @responses.activate
    def test_get_supported_languages_remote(self, mock_config_data_with_api):
        """Test getting supported languages from remote API."""
        # Setup mock API response
        responses.add(
            responses.GET,
            "https://api.example.com/api/v1/codegen/languages",
            json={
                "languages": [
                    {"name": "python", "description": "Python models"},
                    {"name": "typescript", "description": "TypeScript models"},
                ]
            },
            status=200,
        )

        handler = CodegenHandler(mock_config_data_with_api)
        languages = handler.get_supported_languages()

        assert languages == ["python", "typescript"]

    @patch("cinchdb.cli.handlers.codegen_handler.CodegenManager")
    def test_get_supported_languages_local_fallback(
        self, mock_codegen_manager, mock_config_data_with_api
    ):
        """Test fallback to local languages when remote fails."""
        # Setup mock manager
        mock_manager_instance = Mock()
        mock_manager_instance.get_supported_languages.return_value = ["python"]
        mock_codegen_manager.return_value = mock_manager_instance

        handler = CodegenHandler(mock_config_data_with_api)

        # Remote call will fail (no responses setup)
        languages = handler.get_supported_languages(project_root=Path("/tmp"))

        assert languages == ["python"]

    def test_get_supported_languages_no_project(self, mock_config_data):
        """Test getting supported languages without project root."""
        handler = CodegenHandler(mock_config_data)
        languages = handler.get_supported_languages()

        # Should return hardcoded list
        assert languages == ["python"]

    def test_cli_imports(self):
        """Test that unified CLI components can be imported."""
        from cinchdb.cli.handlers import CodegenHandler
        from cinchdb.cli.utils import get_config_dict

        assert CodegenHandler is not None
        assert get_config_dict is not None

    def test_cli_command_structure(self):
        """Test that CLI commands have proper structure."""
        from cinchdb.cli.commands.codegen import app, languages, generate

        # Check that the commands are registered with the app
        assert languages is not None
        assert generate is not None
        assert hasattr(app, "registered_commands")

        # The important thing is that these functions exist and are callable
        assert callable(languages)
        assert callable(generate)

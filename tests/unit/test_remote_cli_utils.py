"""Tests for remote CLI utilities."""

import pytest
from pathlib import Path
import tempfile
from unittest.mock import patch, MagicMock

from cinchdb.config import Config, ProjectConfig, RemoteConfig
from cinchdb.cli.utils import get_cinchdb_instance
from cinchdb.core.database import CinchDB


class TestRemoteCLIUtils:
    """Test remote CLI utility functions."""

    @pytest.fixture
    def temp_project_with_remotes(self, tmp_path):
        """Create a temporary project with remote configurations."""
        # Initialize project
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add remotes
        project_config.remotes["production"] = RemoteConfig(
            url="https://prod.example.com", key="prod-key"
        )
        project_config.remotes["staging"] = RemoteConfig(
            url="https://staging.example.com", key="staging-key"
        )

        # Save config
        config.save(project_config)
        config.init_project()

        return tmp_path

    @patch("cinchdb.cli.utils.get_config_with_data")
    def test_get_cinchdb_instance_local(self, mock_get_config):
        """Test getting local CinchDB instance."""
        # Mock config data
        config = MagicMock()
        config.project_dir = Path("/test/project")
        config_data = MagicMock()
        config_data.active_database = "testdb"
        config_data.active_branch = "main"
        config_data.active_remote = None
        config_data.remotes = {}

        mock_get_config.return_value = (config, config_data)

        # Get instance
        db = get_cinchdb_instance()

        # Verify local connection
        assert db.is_local is True
        assert db.project_dir == Path("/test/project")
        assert db.database == "testdb"
        assert db.branch == "main"

    @patch("cinchdb.cli.utils.get_config_with_data")
    def test_get_cinchdb_instance_remote_active(self, mock_get_config):
        """Test getting remote CinchDB instance with active remote."""
        # Mock config data
        config = MagicMock()
        config.project_dir = Path("/test/project")
        config_data = MagicMock()
        config_data.active_database = "testdb"
        config_data.active_branch = "main"
        config_data.active_remote = "production"
        config_data.remotes = {
            "production": RemoteConfig(url="https://prod.example.com", key="prod-key")
        }

        mock_get_config.return_value = (config, config_data)

        # Get instance
        db = get_cinchdb_instance()

        # Verify remote connection
        assert db.is_local is False
        assert db.api_url == "https://prod.example.com"
        assert db.api_key == "prod-key"
        assert db.database == "testdb"
        assert db.branch == "main"

    @patch("cinchdb.cli.utils.get_config_with_data")
    def test_get_cinchdb_instance_force_local(self, mock_get_config):
        """Test forcing local connection even with active remote."""
        # Mock config data
        config = MagicMock()
        config.project_dir = Path("/test/project")
        config_data = MagicMock()
        config_data.active_database = "testdb"
        config_data.active_branch = "main"
        config_data.active_remote = "production"
        config_data.remotes = {
            "production": RemoteConfig(url="https://prod.example.com", key="prod-key")
        }

        mock_get_config.return_value = (config, config_data)

        # Get instance with force_local
        db = get_cinchdb_instance(force_local=True)

        # Verify local connection
        assert db.is_local is True
        assert db.project_dir == Path("/test/project")

    @patch("cinchdb.cli.utils.get_config_with_data")
    def test_get_cinchdb_instance_specific_remote(self, mock_get_config):
        """Test using specific remote alias."""
        # Mock config data
        config = MagicMock()
        config.project_dir = Path("/test/project")
        config_data = MagicMock()
        config_data.active_database = "testdb"
        config_data.active_branch = "main"
        config_data.active_remote = "production"
        config_data.remotes = {
            "production": RemoteConfig(url="https://prod.example.com", key="prod-key"),
            "staging": RemoteConfig(
                url="https://staging.example.com", key="staging-key"
            ),
        }

        mock_get_config.return_value = (config, config_data)

        # Get instance with specific remote
        db = get_cinchdb_instance(remote_alias="staging")

        # Verify staging connection
        assert db.is_local is False
        assert db.api_url == "https://staging.example.com"
        assert db.api_key == "staging-key"

    @patch("cinchdb.cli.utils.get_config_with_data")
    def test_get_cinchdb_instance_custom_params(self, mock_get_config):
        """Test with custom database/branch/tenant parameters."""
        # Mock config data
        config = MagicMock()
        config.project_dir = Path("/test/project")
        config_data = MagicMock()
        config_data.active_database = "testdb"
        config_data.active_branch = "main"
        config_data.active_remote = None
        config_data.remotes = {}

        mock_get_config.return_value = (config, config_data)

        # Get instance with custom params
        db = get_cinchdb_instance(
            database="customdb", branch="feature", tenant="tenant1"
        )

        # Verify custom parameters
        assert db.database == "customdb"
        assert db.branch == "feature"
        assert db.tenant == "tenant1"

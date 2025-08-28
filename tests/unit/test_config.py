"""Tests for configuration management."""

import os
import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.config import Config, ProjectConfig, RemoteConfig
from cinchdb.core.initializer import init_project


class TestConfig:
    """Test configuration management."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp = tempfile.mkdtemp()
        yield Path(temp)
        shutil.rmtree(temp)

    def test_init_project(self, temp_dir):
        """Test initializing a new project."""
        config = Config(temp_dir)

        # Should not exist initially
        assert not config.exists

        # Initialize project using standalone function
        project_config = init_project(temp_dir)

        # Check defaults
        assert project_config.active_database == "main"
        assert project_config.active_branch == "main"
        assert project_config.api_keys == {}

        # Check files were created
        assert config.exists
        assert (
            temp_dir / ".cinchdb" / "databases" / "main" / "branches" / "main"
        ).exists()
        assert (
            temp_dir
            / ".cinchdb"
            / "databases"
            / "main"
            / "branches"
            / "main"
            / "metadata.json"
        ).exists()
        assert (
            temp_dir
            / ".cinchdb"
            / "databases"
            / "main"
            / "branches"
            / "main"
            / "changes.json"
        ).exists()
        assert (
            temp_dir
            / ".cinchdb"
            / "databases"
            / "main"
            / "branches"
            / "main"
            / "tenants"
        ).exists()

    def test_init_project_already_exists(self, temp_dir):
        """Test initializing when project already exists."""
        config = Config(temp_dir)
        init_project(temp_dir)

        # Should raise error on second init
        with pytest.raises(FileExistsError):
            init_project(temp_dir)

    def test_load_config(self, temp_dir):
        """Test loading configuration."""
        config = Config(temp_dir)
        original = init_project(temp_dir)

        # Load from disk
        loaded = config.load()
        assert loaded.active_database == original.active_database
        assert loaded.active_branch == original.active_branch

    def test_save_config(self, temp_dir):
        """Test saving configuration."""
        config = Config(temp_dir)
        init_project(temp_dir)

        # Modify and save
        project_config = config.load()
        project_config.active_database = "test_db"
        project_config.active_branch = "feature"
        config.save(project_config)

        # Reload and verify
        reloaded = config.load()
        assert reloaded.active_database == "test_db"
        assert reloaded.active_branch == "feature"

    def test_load_nonexistent(self, temp_dir):
        """Test loading when config doesn't exist."""
        config = Config(temp_dir)

        with pytest.raises(FileNotFoundError):
            config.load()

    def test_env_var_project_dir(self, monkeypatch, temp_dir):
        """Test CINCHDB_PROJECT_DIR environment variable."""
        # Set environment variable
        env_path = str(temp_dir / "env_project")
        monkeypatch.setenv("CINCHDB_PROJECT_DIR", env_path)

        # Initialize config without explicit project_dir
        config = Config()

        # Should use environment variable path
        assert config.project_dir == Path(env_path)

    def test_env_var_overrides(self, monkeypatch, temp_dir):
        """Test that environment variables override config values."""
        # Initialize project
        config = Config(temp_dir)
        init_project(temp_dir)

        # Set environment variables
        monkeypatch.setenv("CINCHDB_DATABASE", "env_db")
        monkeypatch.setenv("CINCHDB_BRANCH", "env_branch")

        # Load config
        project_config = config.load()

        # Verify overrides
        assert project_config.active_database == "env_db"
        assert project_config.active_branch == "env_branch"

    def test_env_var_remote_config(self, monkeypatch, temp_dir):
        """Test environment variables for remote configuration."""
        # Initialize project
        config = Config(temp_dir)
        init_project(temp_dir)

        # Set remote environment variables
        monkeypatch.setenv("CINCHDB_REMOTE_URL", "https://env.example.com")
        monkeypatch.setenv("CINCHDB_API_KEY", "env_key_123")

        # Load config
        project_config = config.load()

        # Verify remote was created
        assert "env" in project_config.remotes
        assert project_config.remotes["env"].url == "https://env.example.com"
        assert project_config.remotes["env"].key == "env_key_123"
        assert project_config.active_remote == "env"

    def test_env_var_remote_url_normalization(self, monkeypatch, temp_dir):
        """Test that remote URL from env var has trailing slash removed."""
        # Initialize project
        config = Config(temp_dir)
        init_project(temp_dir)

        # Set remote environment variables with trailing slash
        monkeypatch.setenv("CINCHDB_REMOTE_URL", "https://env.example.com/")
        monkeypatch.setenv("CINCHDB_API_KEY", "env_key_123")

        # Load config
        project_config = config.load()

        # Verify trailing slash was removed
        assert project_config.remotes["env"].url == "https://env.example.com"

    def test_env_var_partial_remote_config(self, monkeypatch, temp_dir):
        """Test that partial remote config (only URL or only KEY) doesn't create remote."""
        # Initialize project
        config = Config(temp_dir)
        init_project(temp_dir)

        # Set only URL (no key)
        monkeypatch.setenv("CINCHDB_REMOTE_URL", "https://env.example.com")

        # Load config
        project_config = config.load()

        # Should not create remote without both URL and KEY
        assert "env" not in project_config.remotes
        assert project_config.active_remote is None

        # Clear env and set only KEY (no URL)
        monkeypatch.delenv("CINCHDB_REMOTE_URL")
        monkeypatch.setenv("CINCHDB_API_KEY", "env_key_123")

        # Reload config
        project_config = config.load()

        # Should still not create remote
        assert "env" not in project_config.remotes
        assert project_config.active_remote is None

    def test_env_var_existing_remote_preserved(self, monkeypatch, temp_dir):
        """Test that existing remotes are preserved when env remote is added."""
        # Initialize project with existing remote
        config = Config(temp_dir)
        project_config = ProjectConfig()
        project_config.remotes["production"] = RemoteConfig(
            url="https://prod.example.com", key="prod-key"
        )
        project_config.active_remote = "production"
        config.save(project_config)

        # Set environment variables
        monkeypatch.setenv("CINCHDB_REMOTE_URL", "https://env.example.com")
        monkeypatch.setenv("CINCHDB_API_KEY", "env_key_123")

        # Load config
        loaded = config.load()

        # Both remotes should exist
        assert "production" in loaded.remotes
        assert "env" in loaded.remotes
        # Active remote should remain as production (env doesn't override if already set)
        assert loaded.active_remote == "production"

    def test_env_var_priority_order(self, monkeypatch, temp_dir):
        """Test that environment variables have correct priority."""
        # Initialize project with config values
        config = Config(temp_dir)
        project_config = ProjectConfig()
        project_config.active_database = "config_db"
        project_config.active_branch = "config_branch"
        config.save(project_config)

        # Set environment variables that should override
        monkeypatch.setenv("CINCHDB_DATABASE", "env_db")
        monkeypatch.setenv("CINCHDB_BRANCH", "env_branch")

        # Load config
        loaded = config.load()

        # Environment variables should override config file
        assert loaded.active_database == "env_db"
        assert loaded.active_branch == "env_branch"

    def test_env_var_all_variables(self, monkeypatch, temp_dir):
        """Test all environment variables working together."""
        # Set all environment variables
        env_project = str(temp_dir / "env_project")
        os.makedirs(env_project, exist_ok=True)

        monkeypatch.setenv("CINCHDB_PROJECT_DIR", env_project)
        monkeypatch.setenv("CINCHDB_DATABASE", "env_database")
        monkeypatch.setenv("CINCHDB_BRANCH", "env_branch")
        monkeypatch.setenv("CINCHDB_REMOTE_URL", "https://env.example.com")
        monkeypatch.setenv("CINCHDB_API_KEY", "env_api_key")

        # Initialize and load config
        config = Config()
        init_project(Path(env_project))
        project_config = config.load()

        # Verify all overrides
        assert config.project_dir == Path(env_project)
        assert project_config.active_database == "env_database"
        assert project_config.active_branch == "env_branch"
        assert "env" in project_config.remotes
        assert project_config.remotes["env"].url == "https://env.example.com"
        assert project_config.remotes["env"].key == "env_api_key"
        assert project_config.active_remote == "env"

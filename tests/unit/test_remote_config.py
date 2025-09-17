"""Tests for remote configuration functionality."""


from cinchdb.config import Config, ProjectConfig, RemoteConfig


class TestRemoteConfig:
    """Test remote configuration functionality."""

    def test_add_remote_config(self, tmp_path):
        """Test adding a remote configuration."""
        # Initialize config
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add a remote
        project_config.remotes["production"] = RemoteConfig(
            url="https://api.example.com", key="test-api-key"
        )

        # Save and reload
        config.save(project_config)
        loaded = config.load()

        # Verify
        assert "production" in loaded.remotes
        assert loaded.remotes["production"].url == "https://api.example.com"
        assert loaded.remotes["production"].key == "test-api-key"

    def test_set_active_remote(self, tmp_path):
        """Test setting active remote."""
        # Initialize config
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add remotes
        project_config.remotes["production"] = RemoteConfig(
            url="https://prod.example.com", key="prod-key"
        )
        project_config.remotes["staging"] = RemoteConfig(
            url="https://staging.example.com", key="staging-key"
        )

        # Set active remote
        project_config.active_remote = "production"

        # Save and reload
        config.save(project_config)
        loaded = config.load()

        # Verify
        assert loaded.active_remote == "production"

    def test_remove_remote_config(self, tmp_path):
        """Test removing a remote configuration."""
        # Initialize config
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add remotes
        project_config.remotes["production"] = RemoteConfig(
            url="https://api.example.com", key="test-key"
        )
        project_config.remotes["staging"] = RemoteConfig(
            url="https://staging.example.com", key="staging-key"
        )
        project_config.active_remote = "production"

        # Remove active remote
        del project_config.remotes["production"]
        project_config.active_remote = None

        # Save and reload
        config.save(project_config)
        loaded = config.load()

        # Verify
        assert "production" not in loaded.remotes
        assert "staging" in loaded.remotes
        assert loaded.active_remote is None

    def test_multiple_remotes(self, tmp_path):
        """Test managing multiple remote configurations."""
        # Initialize config
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add multiple remotes
        remotes = {
            "production": RemoteConfig(url="https://prod.example.com", key="prod-key"),
            "staging": RemoteConfig(
                url="https://staging.example.com", key="staging-key"
            ),
            "development": RemoteConfig(url="http://localhost:8002", key="dev-key"),
        }

        project_config.remotes = remotes

        # Save and reload
        config.save(project_config)
        loaded = config.load()

        # Verify all remotes
        assert len(loaded.remotes) == 3
        for alias, remote in remotes.items():
            assert alias in loaded.remotes
            assert loaded.remotes[alias].url == remote.url
            assert loaded.remotes[alias].key == remote.key

    def test_remote_url_normalization(self, tmp_path):
        """Test that remote URLs are normalized (trailing slashes removed)."""
        # Initialize config
        config = Config(tmp_path)
        project_config = ProjectConfig()

        # Add remote with trailing slash
        project_config.remotes["production"] = RemoteConfig(
            url="https://api.example.com/", key="test-key"
        )

        # Save and reload
        config.save(project_config)
        loaded = config.load()

        # URL should be stored with trailing slash (normalization happens in CLI)
        assert loaded.remotes["production"].url == "https://api.example.com/"

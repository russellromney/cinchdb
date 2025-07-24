"""Tests for configuration management."""

import pytest
from pathlib import Path
import tempfile
import shutil
from cinchdb.config import Config


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
        
        # Initialize project
        project_config = config.init_project()
        
        # Check defaults
        assert project_config.active_database == "main"
        assert project_config.active_branch == "main"
        assert project_config.api_keys == {}
        
        # Check files were created
        assert config.exists
        assert (temp_dir / ".cinchdb" / "databases" / "main" / "branches" / "main").exists()
        assert (temp_dir / ".cinchdb" / "databases" / "main" / "branches" / "main" / "metadata.json").exists()
        assert (temp_dir / ".cinchdb" / "databases" / "main" / "branches" / "main" / "changes.json").exists()
        assert (temp_dir / ".cinchdb" / "databases" / "main" / "branches" / "main" / "tenants").exists()
    
    def test_init_project_already_exists(self, temp_dir):
        """Test initializing when project already exists."""
        config = Config(temp_dir)
        config.init_project()
        
        # Should raise error on second init
        with pytest.raises(FileExistsError):
            config.init_project()
    
    def test_load_config(self, temp_dir):
        """Test loading configuration."""
        config = Config(temp_dir)
        original = config.init_project()
        
        # Load from disk
        loaded = config.load()
        assert loaded.active_database == original.active_database
        assert loaded.active_branch == original.active_branch
    
    def test_save_config(self, temp_dir):
        """Test saving configuration."""
        config = Config(temp_dir)
        config.init_project()
        
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
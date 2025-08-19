"""Configuration management for CinchDB projects."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import toml
from pydantic import BaseModel, Field, ConfigDict


class RemoteConfig(BaseModel):
    """Configuration for a remote CinchDB instance."""

    url: str = Field(description="Base URL of the remote CinchDB API")
    key: str = Field(description="API key for authentication")


class ProjectConfig(BaseModel):
    """Configuration for a CinchDB project stored in .cinchdb/config.toml."""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields for extensibility

    active_database: str = Field(
        default="main", description="Currently active database"
    )
    active_branch: str = Field(default="main", description="Currently active branch")
    active_remote: Optional[str] = Field(
        default=None, description="Currently active remote alias"
    )
    remotes: Dict[str, RemoteConfig] = Field(
        default_factory=dict, description="Remote configurations by alias"
    )
    api_keys: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, description="API key configurations (deprecated)"
    )


class Config:
    """Manages CinchDB project configuration."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize config manager.

        Args:
            project_dir: Path to project directory. If None, uses CINCHDB_PROJECT_DIR env var or current directory.
        """
        # Check environment variable first
        if project_dir is None:
            env_dir = os.environ.get("CINCHDB_PROJECT_DIR")
            if env_dir:
                project_dir = Path(env_dir)

        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.config_dir = self.project_dir / ".cinchdb"
        self.config_path = self.config_dir / "config.toml"
        self._config: Optional[ProjectConfig] = None

    @property
    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def load(self) -> ProjectConfig:
        """Load configuration from disk, with environment variable overrides."""
        if not self.exists:
            raise FileNotFoundError(f"Config file not found at {self.config_path}")

        with open(self.config_path, "r") as f:
            data = toml.load(f)

        # Apply environment variable overrides
        self._apply_env_overrides(data)

        # Convert remote dicts to RemoteConfig objects
        if "remotes" in data:
            for alias, remote_data in data["remotes"].items():
                if isinstance(remote_data, dict):
                    data["remotes"][alias] = RemoteConfig(**remote_data)

        self._config = ProjectConfig(**data)
        return self._config

    def _apply_env_overrides(self, data: Dict[str, Any]) -> None:
        """Apply environment variable overrides to configuration data."""
        # Override database and branch
        if env_db := os.environ.get("CINCHDB_DATABASE"):
            data["active_database"] = env_db

        if env_branch := os.environ.get("CINCHDB_BRANCH"):
            data["active_branch"] = env_branch

        # Override or create remote configuration
        env_url = os.environ.get("CINCHDB_REMOTE_URL")
        env_key = os.environ.get("CINCHDB_API_KEY")

        if env_url and env_key:
            # Create or update "env" remote
            if "remotes" not in data:
                data["remotes"] = {}

            data["remotes"]["env"] = {
                "url": env_url.rstrip("/"),  # Remove trailing slash
                "key": env_key,
            }

            # Make it active if no other remote is set
            if not data.get("active_remote"):
                data["active_remote"] = "env"

    def save(self, config: Optional[ProjectConfig] = None) -> None:
        """Save configuration to disk.

        Args:
            config: Configuration to save. If None, saves current config.
        """
        if config:
            self._config = config

        if not self._config:
            raise ValueError("No configuration to save")

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save to TOML - need to properly serialize RemoteConfig objects
        config_dict = self._config.model_dump()
        # Convert RemoteConfig objects to dicts for TOML serialization
        if "remotes" in config_dict:
            for alias, remote in config_dict["remotes"].items():
                if isinstance(remote, dict):
                    config_dict["remotes"][alias] = remote

        with open(self.config_path, "w") as f:
            toml.dump(config_dict, f)

    def init_project(self) -> ProjectConfig:
        """Initialize a new CinchDB project with default configuration.

        This method now delegates to the ProjectInitializer for the actual
        initialization logic.
        """
        from cinchdb.core.initializer import ProjectInitializer

        initializer = ProjectInitializer(self.project_dir)
        config = initializer.init_project()

        # Load the config into this instance
        self._config = config
        return config

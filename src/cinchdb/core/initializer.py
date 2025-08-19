"""Project initialization for CinchDB."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cinchdb.core.connection import DatabaseConnection
from cinchdb.config import ProjectConfig


class ProjectInitializer:
    """Handles initialization of CinchDB projects."""

    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize the project initializer.

        Args:
            project_dir: Path to project directory. If None, uses current directory.
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.config_dir = self.project_dir / ".cinchdb"
        self.config_path = self.config_dir / "config.toml"

    def init_project(
        self, database_name: str = "main", branch_name: str = "main"
    ) -> ProjectConfig:
        """Initialize a new CinchDB project with default configuration.

        Args:
            database_name: Name for the initial database (default: "main")
            branch_name: Name for the initial branch (default: "main")

        Returns:
            The created ProjectConfig

        Raises:
            FileExistsError: If project already exists at the location
        """
        if self.config_path.exists():
            raise FileExistsError(f"Project already exists at {self.config_dir}")

        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create default config
        config = ProjectConfig(active_database=database_name, active_branch=branch_name)

        # Save config
        self._save_config(config)

        # Create default database structure
        self._create_database_structure(database_name, branch_name)

        return config

    def init_database(
        self,
        database_name: str,
        branch_name: str = "main",
        description: Optional[str] = None,
    ) -> None:
        """Initialize a new database within an existing project.

        Args:
            database_name: Name for the database
            branch_name: Initial branch name (default: "main")
            description: Optional description for the database

        Raises:
            FileNotFoundError: If project doesn't exist
            FileExistsError: If database already exists
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"No CinchDB project found at {self.config_dir}")

        db_path = self.config_dir / "databases" / database_name
        if db_path.exists():
            raise FileExistsError(f"Database '{database_name}' already exists")

        # Create database structure
        self._create_database_structure(database_name, branch_name, description)

    def _create_database_structure(
        self,
        database_name: str,
        branch_name: str = "main",
        description: Optional[str] = None,
    ) -> None:
        """Create the directory structure for a database.

        Args:
            database_name: Name of the database
            branch_name: Name of the initial branch
            description: Optional description
        """
        # Create database branch path
        branch_path = (
            self.config_dir / "databases" / database_name / "branches" / branch_name
        )
        branch_path.mkdir(parents=True, exist_ok=True)

        # Create metadata file
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": branch_name,
            "parent": None,
            "description": description,
        }

        with open(branch_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Create empty changes file
        with open(branch_path / "changes.json", "w") as f:
            json.dump([], f, indent=2)

        # Create tenants directory
        tenant_dir = branch_path / "tenants"
        tenant_dir.mkdir(exist_ok=True)

        # Create and initialize main tenant database
        self._init_tenant_database(tenant_dir / "main.db")

    def _init_tenant_database(self, db_path: Path) -> None:
        """Initialize a tenant database with proper PRAGMAs.

        Args:
            db_path: Path to the database file
        """
        # Create the database file
        db_path.touch()

        # Initialize with proper PRAGMAs
        with DatabaseConnection(db_path):
            # The connection automatically sets up PRAGMAs in _connect():
            # - journal_mode = WAL
            # - synchronous = NORMAL
            # - wal_autocheckpoint = 0
            # - foreign_keys = ON
            pass

    def _save_config(self, config: ProjectConfig) -> None:
        """Save configuration to disk.

        Args:
            config: Configuration to save
        """
        import toml

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Convert to dict for TOML serialization
        config_dict = config.model_dump()

        # Convert RemoteConfig objects to dicts if present
        if "remotes" in config_dict:
            for alias, remote in config_dict["remotes"].items():
                if isinstance(remote, dict):
                    config_dict["remotes"][alias] = remote

        with open(self.config_path, "w") as f:
            toml.dump(config_dict, f)


def init_project(
    project_dir: Optional[Path] = None,
    database_name: str = "main",
    branch_name: str = "main",
) -> ProjectConfig:
    """Initialize a new CinchDB project.

    This is a convenience function that creates a ProjectInitializer
    and initializes a project.

    Args:
        project_dir: Directory to initialize in (default: current directory)
        database_name: Name for initial database (default: "main")
        branch_name: Name for initial branch (default: "main")

    Returns:
        The created ProjectConfig

    Raises:
        FileExistsError: If project already exists
    """
    initializer = ProjectInitializer(project_dir)
    return initializer.init_project(database_name, branch_name)


def init_database(
    project_dir: Optional[Path] = None,
    database_name: str = "main",
    branch_name: str = "main",
    description: Optional[str] = None,
) -> None:
    """Initialize a new database within an existing project.

    This is a convenience function that creates a ProjectInitializer
    and initializes a database.

    Args:
        project_dir: Project directory (default: current directory)
        database_name: Name for the database
        branch_name: Initial branch name (default: "main")
        description: Optional description

    Raises:
        FileNotFoundError: If project doesn't exist
        FileExistsError: If database already exists
    """
    initializer = ProjectInitializer(project_dir)
    initializer.init_database(database_name, branch_name, description)

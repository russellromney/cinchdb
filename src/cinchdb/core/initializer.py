"""Project initialization for CinchDB."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cinchdb.core.connection import DatabaseConnection
from cinchdb.config import ProjectConfig
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db
from cinchdb.core.path_utils import (
    calculate_shard,
    ensure_tenant_db_path,
    get_context_root,
    ensure_context_directory,
)


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
        self._metadata_db = None
    
    @property
    def metadata_db(self) -> MetadataDB:
        """Get metadata database connection (lazy-initialized from pool)."""
        if self._metadata_db is None:
            self._metadata_db = get_metadata_db(self.project_dir)
        return self._metadata_db

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
            InvalidNameError: If database name is invalid
        """
        from cinchdb.utils.name_validator import validate_name
        
        # Validate database name
        validate_name(database_name, "database")
        
        if self.config_path.exists():
            raise FileExistsError(f"Project already exists at {self.config_dir}")

        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create default config
        config = ProjectConfig(active_database=database_name, active_branch=branch_name)

        # Save config
        self._save_config(config)
        
        # Add initial database to metadata (metadata_db property will auto-initialize)
        database_id = str(uuid.uuid4())
        self.metadata_db.create_database(
            database_id, database_name, 
            description="Initial database",
            metadata={"initial_branch": branch_name}
        )
        
        # Add initial branch to metadata
        branch_id = str(uuid.uuid4())
        self.metadata_db.create_branch(
            branch_id, database_id, branch_name,
            parent_branch=None,
            schema_version="v1.0.0",
            metadata={"created_at": datetime.now(timezone.utc).isoformat()}
        )

        # Create default database structure (materialized by default for initial database)
        self._create_database_structure(database_name, branch_name, create_tenant_files=True)
        
        # Mark as materialized since we created the structure
        self.metadata_db.mark_database_materialized(database_id)
        self.metadata_db.mark_branch_materialized(branch_id)
        
        # Also create main tenant in metadata
        tenant_id = str(uuid.uuid4())
        main_shard = calculate_shard("main")
        self.metadata_db.create_tenant(
            tenant_id, branch_id, "main", main_shard,
            metadata={"created_at": datetime.now(timezone.utc).isoformat()}
        )
        self.metadata_db.mark_tenant_materialized(tenant_id)
        
        # Create __empty__ tenant in metadata (for lazy tenant reads)
        empty_tenant_id = str(uuid.uuid4())
        empty_shard = calculate_shard("__empty__")
        self.metadata_db.create_tenant(
            empty_tenant_id, branch_id, "__empty__", empty_shard,
            metadata={
                "system": True,
                "description": "Template for lazy tenants",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
        self.metadata_db.mark_tenant_materialized(empty_tenant_id)
        
        # Create physical __empty__ tenant with schema from main
        from cinchdb.managers.tenant import TenantManager
        tenant_mgr = TenantManager(self.project_dir, database_name, branch_name)
        tenant_mgr._ensure_empty_tenant()

        return config

    def init_database(
        self,
        database_name: str,
        branch_name: str = "main",
        description: Optional[str] = None,
        lazy: bool = True,
    ) -> None:
        """Initialize a new database within an existing project.

        Args:
            database_name: Name for the database
            branch_name: Initial branch name (default: "main")
            description: Optional description for the database
            lazy: If True, don't create actual database files until first use

        Raises:
            FileNotFoundError: If project doesn't exist
            FileExistsError: If database already exists
            InvalidNameError: If database name is invalid
        """
        from cinchdb.utils.name_validator import validate_name
        
        # Validate database name
        validate_name(database_name, "database")
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"No CinchDB project found at {self.config_dir}")
        
        # Check if database already exists in metadata
        existing_db = self.metadata_db.get_database(database_name)
        if existing_db:
            raise FileExistsError(f"Database '{database_name}' already exists")

        # Create database ID
        database_id = str(uuid.uuid4())
        
        # Create database in metadata
        metadata = {
            "description": description,
            "initial_branch": branch_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_db.create_database(database_id, database_name, description, metadata)
        
        # Create initial branch in metadata
        branch_id = str(uuid.uuid4())
        self.metadata_db.create_branch(
            branch_id, database_id, branch_name,
            parent_branch=None,
            schema_version="v1.0.0",
            metadata={"created_at": datetime.now(timezone.utc).isoformat()}
        )
        
        # Create main tenant entry in metadata (will be materialized if database is not lazy)
        main_tenant_id = str(uuid.uuid4())
        main_shard = calculate_shard("main")
        self.metadata_db.create_tenant(
            main_tenant_id, branch_id, "main", main_shard,
            metadata={"description": "Default tenant", "created_at": datetime.now(timezone.utc).isoformat()}
        )
        
        # Create __empty__ tenant entry in metadata (lazy)
        # This serves as a template for all lazy tenants in this branch
        empty_tenant_id = str(uuid.uuid4())
        empty_shard = calculate_shard("__empty__")
        self.metadata_db.create_tenant(
            empty_tenant_id, branch_id, "__empty__", empty_shard,
            metadata={"system": True, "description": "Template for lazy tenants"}
        )

        if not lazy:
            # Create actual database structure
            self._create_database_structure(database_name, branch_name, description)
            
            # Mark as materialized
            self.metadata_db.mark_database_materialized(database_id)
            self.metadata_db.mark_branch_materialized(branch_id)
            self.metadata_db.mark_tenant_materialized(main_tenant_id)

    def _create_database_structure(
        self,
        database_name: str,
        branch_name: str = "main",
        description: Optional[str] = None,
        create_tenant_files: bool = False,
    ) -> None:
        """Create the directory structure for a database using tenant-first storage.

        Args:
            database_name: Name of the database
            branch_name: Name of the initial branch
            description: Optional description
            create_tenant_files: Whether to create actual tenant files
        """
        # Use tenant-first structure: .cinchdb/{database}-{branch}/
        context_root = ensure_context_directory(self.project_dir, database_name, branch_name)
        
        # Create metadata file in context root
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database": database_name,
            "branch": branch_name,
            "parent": None,
            "description": description,
        }
        
        with open(context_root / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create empty changes file
        with open(context_root / "changes.json", "w") as f:
            json.dump([], f, indent=2)
        
        # Create main tenant database in sharded directory (only if requested)
        if create_tenant_files:
            main_db_path = ensure_tenant_db_path(self.project_dir, database_name, branch_name, "main")
            self._init_tenant_database(main_db_path)

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

    def materialize_database(self, database_name: str) -> None:
        """Materialize a lazy database into actual database structure.
        
        Args:
            database_name: Name of the database to materialize
            
        Raises:
            ValueError: If database doesn't exist or is already materialized
        """
        # Get database info from metadata
        db_info = self.metadata_db.get_database(database_name)
        if not db_info:
            raise ValueError(f"Database '{database_name}' does not exist")
            
        # Check if already materialized
        if db_info['materialized']:
            return  # Already materialized
            
        db_path = self.config_dir / "databases" / database_name
        if db_path.exists():
            # Mark as materialized in metadata if directory already exists
            self.metadata_db.mark_database_materialized(db_info['id'])
            return
            
        # Get metadata details
        metadata = json.loads(db_info['metadata']) if db_info['metadata'] else {}
        branch_name = metadata.get("initial_branch", "main")
        description = db_info.get('description')
        
        # Create the actual database structure (no tenant files - those are created when tables are added)
        self._create_database_structure(database_name, branch_name, description, create_tenant_files=False)
        
        # Mark database as materialized in metadata
        self.metadata_db.mark_database_materialized(db_info['id'])
        
        # Also mark the initial branch as materialized
        branch_info = self.metadata_db.get_branch(db_info['id'], branch_name)
        if branch_info:
            self.metadata_db.mark_branch_materialized(branch_info['id'])

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
    lazy: bool = True,
) -> None:
    """Initialize a new database within an existing project.

    This is a convenience function that creates a ProjectInitializer
    and initializes a database.

    Args:
        project_dir: Project directory (default: current directory)
        database_name: Name for the database
        branch_name: Initial branch name (default: "main")
        description: Optional description
        lazy: If True, don't create actual database files until first use

    Raises:
        FileNotFoundError: If project doesn't exist
        FileExistsError: If database already exists
    """
    initializer = ProjectInitializer(project_dir)
    initializer.init_database(database_name, branch_name, description, lazy)

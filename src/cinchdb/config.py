"""Configuration management for CinchDB projects."""

from pathlib import Path
from typing import Optional, Dict, Any
import toml
from pydantic import BaseModel, Field, ConfigDict


class ProjectConfig(BaseModel):
    """Configuration for a CinchDB project stored in .cinchdb/config.toml."""
    
    model_config = ConfigDict(extra="allow")  # Allow additional fields for extensibility
    
    active_database: str = Field(default="main", description="Currently active database")
    active_branch: str = Field(default="main", description="Currently active branch")
    api_keys: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="API key configurations")


class Config:
    """Manages CinchDB project configuration."""
    
    def __init__(self, project_dir: Optional[Path] = None):
        """Initialize config manager.
        
        Args:
            project_dir: Path to project directory. If None, uses current directory.
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.config_dir = self.project_dir / ".cinchdb"
        self.config_path = self.config_dir / "config.toml"
        self._config: Optional[ProjectConfig] = None
    
    @property
    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()
    
    def load(self) -> ProjectConfig:
        """Load configuration from disk."""
        if not self.exists:
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        
        with open(self.config_path, "r") as f:
            data = toml.load(f)
        
        self._config = ProjectConfig(**data)
        return self._config
    
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
        
        # Save to TOML
        with open(self.config_path, "w") as f:
            toml.dump(self._config.model_dump(), f)
    
    def init_project(self) -> ProjectConfig:
        """Initialize a new CinchDB project with default configuration."""
        if self.exists:
            raise FileExistsError(f"Project already exists at {self.config_dir}")
        
        # Create default config
        config = ProjectConfig()
        self.save(config)
        
        # Create default database structure
        self._create_default_structure()
        
        return config
    
    def _create_default_structure(self) -> None:
        """Create default project structure."""
        # Create main database with main branch
        db_path = self.config_dir / "databases" / "main" / "branches" / "main"
        db_path.mkdir(parents=True, exist_ok=True)
        
        # Create metadata files
        from datetime import datetime, timezone
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tables": {},
            "views": {}
        }
        
        import json
        with open(db_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create empty changes file
        with open(db_path / "changes.json", "w") as f:
            json.dump([], f, indent=2)
        
        # Create main tenant directory
        tenant_dir = db_path / "tenants"
        tenant_dir.mkdir(exist_ok=True)
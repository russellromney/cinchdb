"""Branch management for CinchDB."""

import json
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from cinchdb.models import Branch
from cinchdb.core.path_utils import (
    get_database_path,
    get_branch_path,
    list_branches,
)
from cinchdb.utils.name_validator import validate_name
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db


class BranchManager:
    """Manages branches within a database."""

    def __init__(self, project_root: Path, database: str):
        """Initialize branch manager.

        Args:
            project_root: Path to project root
            database: Database name
        """
        self.project_root = Path(project_root)
        self.database = database
        self.db_path = get_database_path(self.project_root, database)
        
        # Lazy-initialized pooled connection
        self._metadata_db = None
        self.database_id = None
    
    def _ensure_initialized(self) -> None:
        """Ensure metadata connection and IDs are initialized."""
        if self._metadata_db is None:
            self._metadata_db = get_metadata_db(self.project_root)
            
            # Initialize database ID on first access
            if self.database_id is None:
                db_info = self._metadata_db.get_database(self.database)
                if db_info:
                    self.database_id = db_info['id']

    @property
    def metadata_db(self) -> MetadataDB:
        """Get metadata database connection (lazy-initialized from pool)."""
        self._ensure_initialized()
        return self._metadata_db

    def list_branches(self) -> List[Branch]:
        """List all branches in the database.

        Returns:
            List of Branch objects
        """
        branch_names = list_branches(self.project_root, self.database)
        branches = []

        for name in branch_names:
            metadata = self.get_branch_metadata(name)
            branch = Branch(
                name=name,
                database=self.database,
                parent_branch=metadata.get("parent_branch"),
                is_main=(name == "main"),
                metadata=metadata,
            )
            branches.append(branch)

        return branches

    def create_branch(self, source_branch: str, new_branch_name: str) -> Branch:
        """Create a new branch from an existing branch.

        Args:
            source_branch: Name of branch to copy from
            new_branch_name: Name for the new branch

        Returns:
            Created Branch object

        Raises:
            ValueError: If source doesn't exist or new branch already exists
            InvalidNameError: If new branch name is invalid
        """
        # Validate new branch name
        validate_name(new_branch_name, "branch")
        
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.database_id:
            raise ValueError(f"Database '{self.database}' not found in metadata")

        # Validate source branch exists in metadata
        source_branch_info = self.metadata_db.get_branch(self.database_id, source_branch)
        if not source_branch_info:
            raise ValueError(f"Source branch '{source_branch}' does not exist")

        # Validate new branch doesn't exist
        existing_branch = self.metadata_db.get_branch(self.database_id, new_branch_name)
        if existing_branch:
            raise ValueError(f"Branch '{new_branch_name}' already exists")

        # Create branch ID
        branch_id = str(uuid.uuid4())
        
        # Get source branch schema version
        schema_version = source_branch_info['schema_version'] if source_branch_info else "v1.0.0"
        
        # Create branch in metadata
        metadata = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "copied_from": source_branch,
        }
        self.metadata_db.create_branch(
            branch_id, self.database_id, new_branch_name,
            parent_branch=source_branch,
            schema_version=schema_version,
            metadata=metadata
        )
        
        # Copy all tenant entries from source branch to new branch
        # Tenants are branch-specific, so each branch needs its own tenant entries
        source_tenants = self.metadata_db.list_tenants(source_branch_info['id'])
        for tenant in source_tenants:
            new_tenant_id = str(uuid.uuid4())
            tenant_metadata = json.loads(tenant['metadata']) if tenant['metadata'] else {}
            tenant_metadata['copied_from'] = source_branch
            
            # Create tenant in new branch, preserving materialization status and shard info
            self.metadata_db.create_tenant(
                new_tenant_id, branch_id, tenant['name'], tenant['shard'],
                metadata=tenant_metadata
            )
            
            # Preserve materialization status from source branch
            if tenant['materialized']:
                self.metadata_db.mark_tenant_materialized(new_tenant_id)
        
        # Ensure __empty__ tenant exists (in case source branch didn't have it)
        if not any(t['name'] == '__empty__' for t in source_tenants):
            import hashlib
            empty_shard = hashlib.sha256("__empty__".encode('utf-8')).hexdigest()[:2]
            empty_tenant_id = str(uuid.uuid4())
            self.metadata_db.create_tenant(
                empty_tenant_id, branch_id, "__empty__", empty_shard,
                metadata={"system": True, "description": "Template for lazy tenants"}
            )

        # Copy all changes from source branch to new branch
        # This ensures the new branch has all the change history from its parent
        self.metadata_db.copy_branch_changes(
            source_branch, new_branch_name,
            source_branch_id=source_branch_info['id'],
            target_branch_id=branch_id
        )

        # Copy entire branch directory (branches should copy ALL files including tenants)
        source_path = get_branch_path(self.project_root, self.database, source_branch)
        new_path = get_branch_path(self.project_root, self.database, new_branch_name)
        
        if source_path.exists():
            shutil.copytree(source_path, new_path)
            
            # Update branch metadata file
            fs_metadata = self.get_branch_metadata(new_branch_name)
            fs_metadata["parent_branch"] = source_branch
            fs_metadata["created_at"] = datetime.now(timezone.utc).isoformat()
            self.update_branch_metadata(new_branch_name, fs_metadata)
        
        # Mark branch as materialized (always true now)
        self.metadata_db.mark_branch_materialized(branch_id)

        return Branch(
            name=new_branch_name,
            database=self.database,
            parent_branch=source_branch,
            is_main=False,
            metadata=metadata,
        )

    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch.

        Args:
            branch_name: Name of branch to delete

        Raises:
            ValueError: If branch doesn't exist or is main branch
        """
        # Can't delete main branch
        if branch_name == "main":
            raise ValueError("Cannot delete the main branch")
        
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.database_id:
            raise ValueError(f"Database '{self.database}' not found in metadata")

        # Check if branch exists in metadata
        branch_info = self.metadata_db.get_branch(self.database_id, branch_name)
        if not branch_info:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        # NOTE: We delete from metadata first because it's better to have a scared, lost file than a zombie branch

        # Delete from metadata (cascade deletes will handle tenants)
        with self.metadata_db.conn:
            self.metadata_db.conn.execute(
                "DELETE FROM branches WHERE id = ?",
                (branch_info['id'],)
            )

        # Delete branch directory if it exists
        branch_path = get_branch_path(self.project_root, self.database, branch_name)
        if branch_path.exists():
            shutil.rmtree(branch_path)

    def get_branch_metadata(self, branch_name: str) -> Dict[str, Any]:
        """Get metadata for a branch.

        Args:
            branch_name: Branch name

        Returns:
            Metadata dictionary
        """
        metadata_path = (
            get_branch_path(self.project_root, self.database, branch_name)
            / "metadata.json"
        )

        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                return json.load(f)

        return {}

    def update_branch_metadata(
        self, branch_name: str, metadata: Dict[str, Any]
    ) -> None:
        """Update metadata for a branch.

        Args:
            branch_name: Branch name
            metadata: Metadata dictionary to save
        """
        metadata_path = (
            get_branch_path(self.project_root, self.database, branch_name)
            / "metadata.json"
        )

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists.

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch exists, False otherwise
        """
        return branch_name in list_branches(self.project_root, self.database)
    

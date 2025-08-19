"""Branch management for CinchDB."""

import json
import shutil
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

        # Validate source branch exists
        if source_branch not in list_branches(self.project_root, self.database):
            raise ValueError(f"Source branch '{source_branch}' does not exist")

        # Validate new branch doesn't exist
        if new_branch_name in list_branches(self.project_root, self.database):
            raise ValueError(f"Branch '{new_branch_name}' already exists")

        # Get paths
        source_path = get_branch_path(self.project_root, self.database, source_branch)
        new_path = get_branch_path(self.project_root, self.database, new_branch_name)

        # Copy entire branch directory
        shutil.copytree(source_path, new_path)

        # Update metadata for new branch
        metadata = self.get_branch_metadata(new_branch_name)
        metadata["parent_branch"] = source_branch
        metadata["created_at"] = datetime.now(timezone.utc).isoformat()
        self.update_branch_metadata(new_branch_name, metadata)

        # New branch inherits all changes from source branch
        # (changes.json is already copied by copytree, so nothing to do here)

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

        # Validate branch exists
        if branch_name not in list_branches(self.project_root, self.database):
            raise ValueError(f"Branch '{branch_name}' does not exist")

        # Delete branch directory
        branch_path = get_branch_path(self.project_root, self.database, branch_name)
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

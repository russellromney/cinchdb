"""Tenant management for CinchDB."""

import shutil
from pathlib import Path
from typing import List, Optional

from cinchdb.models import Tenant
from cinchdb.core.path_utils import (
    get_branch_path,
    get_tenant_db_path,
    list_tenants,
)
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance import check_maintenance_mode
from cinchdb.utils.name_validator import validate_name


class TenantManager:
    """Manages tenants within a branch."""

    def __init__(self, project_root: Path, database: str, branch: str):
        """Initialize tenant manager.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.branch_path = get_branch_path(self.project_root, database, branch)

    def list_tenants(self) -> List[Tenant]:
        """List all tenants in the branch.

        Returns:
            List of Tenant objects
        """
        tenant_names = list_tenants(self.project_root, self.database, self.branch)
        tenants = []

        for name in tenant_names:
            tenant = Tenant(
                name=name,
                database=self.database,
                branch=self.branch,
                is_main=(name == "main"),
            )
            tenants.append(tenant)

        return tenants

    def create_tenant(
        self, tenant_name: str, description: Optional[str] = None
    ) -> Tenant:
        """Create a new tenant by copying schema from main tenant.

        Args:
            tenant_name: Name for the new tenant
            description: Optional description

        Returns:
            Created Tenant object

        Raises:
            ValueError: If tenant already exists
            InvalidNameError: If tenant name is invalid
            MaintenanceError: If branch is in maintenance mode
        """
        # Validate tenant name
        validate_name(tenant_name, "tenant")

        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Validate tenant doesn't exist
        if tenant_name in list_tenants(self.project_root, self.database, self.branch):
            raise ValueError(f"Tenant '{tenant_name}' already exists")

        # Get paths
        main_db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, "main"
        )
        new_db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )

        # Copy main tenant database to new tenant
        shutil.copy2(main_db_path, new_db_path)

        # Clear any data from the copied database (keep schema only)
        with DatabaseConnection(new_db_path) as conn:
            # Get all tables
            result = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row["name"] for row in result.fetchall()]

            # Clear data from each table
            for table in tables:
                conn.execute(f"DELETE FROM {table}")

            conn.commit()

        return Tenant(
            name=tenant_name,
            database=self.database,
            branch=self.branch,
            description=description,
            is_main=False,
        )

    def delete_tenant(self, tenant_name: str) -> None:
        """Delete a tenant.

        Args:
            tenant_name: Name of tenant to delete

        Raises:
            ValueError: If tenant doesn't exist or is main tenant
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Can't delete main tenant
        if tenant_name == "main":
            raise ValueError("Cannot delete the main tenant")

        # Validate tenant exists
        if tenant_name not in list_tenants(
            self.project_root, self.database, self.branch
        ):
            raise ValueError(f"Tenant '{tenant_name}' does not exist")

        # Delete tenant database file and related files
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        db_path.unlink()

        # Also remove WAL and SHM files if they exist
        wal_path = db_path.with_suffix(".db-wal")
        shm_path = db_path.with_suffix(".db-shm")

        if wal_path.exists():
            wal_path.unlink()
        if shm_path.exists():
            shm_path.unlink()

    def copy_tenant(self, source_tenant: str, target_tenant: str) -> Tenant:
        """Copy a tenant to a new tenant.

        Args:
            source_tenant: Name of tenant to copy from
            target_tenant: Name for the new tenant

        Returns:
            Created Tenant object

        Raises:
            ValueError: If source doesn't exist or target already exists
            InvalidNameError: If target tenant name is invalid
            MaintenanceError: If branch is in maintenance mode
        """
        # Validate target tenant name
        validate_name(target_tenant, "tenant")

        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Validate source exists
        if source_tenant not in list_tenants(
            self.project_root, self.database, self.branch
        ):
            raise ValueError(f"Source tenant '{source_tenant}' does not exist")

        # Validate target doesn't exist
        if target_tenant in list_tenants(self.project_root, self.database, self.branch):
            raise ValueError(f"Tenant '{target_tenant}' already exists")

        # Get paths
        source_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, source_tenant
        )
        target_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, target_tenant
        )

        # Copy database file
        shutil.copy2(source_path, target_path)

        return Tenant(
            name=target_tenant,
            database=self.database,
            branch=self.branch,
            is_main=False,
        )

    def rename_tenant(self, old_name: str, new_name: str) -> None:
        """Rename a tenant.

        Args:
            old_name: Current tenant name
            new_name: New tenant name

        Raises:
            ValueError: If old doesn't exist, new already exists, or trying to rename main
            InvalidNameError: If new tenant name is invalid
        """
        # Validate new tenant name
        validate_name(new_name, "tenant")

        # Can't rename main tenant
        if old_name == "main":
            raise ValueError("Cannot rename the main tenant")

        # Validate old exists
        if old_name not in list_tenants(self.project_root, self.database, self.branch):
            raise ValueError(f"Tenant '{old_name}' does not exist")

        # Validate new doesn't exist
        if new_name in list_tenants(self.project_root, self.database, self.branch):
            raise ValueError(f"Tenant '{new_name}' already exists")

        # Get paths
        old_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, old_name
        )
        new_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, new_name
        )

        # Rename database file
        old_path.rename(new_path)

        # Also rename WAL and SHM files if they exist
        old_wal = old_path.with_suffix(".db-wal")
        old_shm = old_path.with_suffix(".db-shm")
        new_wal = new_path.with_suffix(".db-wal")
        new_shm = new_path.with_suffix(".db-shm")

        if old_wal.exists():
            old_wal.rename(new_wal)
        if old_shm.exists():
            old_shm.rename(new_shm)

    def get_tenant_connection(self, tenant_name: str) -> DatabaseConnection:
        """Get a database connection for a tenant.

        Args:
            tenant_name: Tenant name

        Returns:
            DatabaseConnection object

        Raises:
            ValueError: If tenant doesn't exist
        """
        if tenant_name not in list_tenants(
            self.project_root, self.database, self.branch
        ):
            raise ValueError(f"Tenant '{tenant_name}' does not exist")

        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        return DatabaseConnection(db_path)

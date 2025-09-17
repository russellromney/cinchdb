"""Tenant management for CinchDB."""

import hashlib
import logging
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from cinchdb.models import Tenant
from cinchdb.core.path_utils import (
    get_branch_path,
    get_tenant_db_path,
    list_tenants,
    # New tenant-first path utilities
    get_context_root,
    get_tenant_db_path_in_context,
    ensure_context_directory,
    ensure_tenant_db_path,
    calculate_shard,
    invalidate_cache,
)
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance_utils import check_maintenance_mode
from cinchdb.utils.name_validator import validate_name
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db

logger = logging.getLogger(__name__)


class TenantManager:
    """Manages tenants within a branch."""

    def __init__(self, project_root: Path, database: str, branch: str, encryption_manager=None):
        """Initialize tenant manager.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
            encryption_manager: EncryptionManager instance for encrypted connections
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.encryption_manager = encryption_manager
        
        # New tenant-first approach: use context root
        self.context_root = get_context_root(self.project_root, database, branch)
        
        # Legacy support: keep branch_path for backward compatibility
        self.branch_path = get_branch_path(self.project_root, database, branch)
        
        self._empty_tenant_name = "__empty__"  # Reserved name for lazy tenant template
        
        # Lazy-initialized pooled connection
        self._metadata_db = None
        self.database_id = None
        self.branch_id = None
        
    def _ensure_initialized(self) -> None:
        """Ensure metadata connection and IDs are initialized."""
        if self._metadata_db is None:
            self._metadata_db = get_metadata_db(self.project_root)
            
            # Initialize database and branch IDs on first access
            if self.database_id is None:
                db_info = self._metadata_db.get_database(self.database)
                if db_info:
                    self.database_id = db_info['id']
                    branch_info = self._metadata_db.get_branch(self.database_id, self.branch)
                    if branch_info:
                        self.branch_id = branch_info['id']

    @property
    def metadata_db(self) -> MetadataDB:
        """Get metadata database connection (lazy-initialized from pool)."""
        self._ensure_initialized()
        return self._metadata_db

    def list_tenants(self, include_system: bool = False) -> List[Tenant]:
        """List all tenants in the branch.

        Args:
            include_system: If True, include system tenants like __empty__

        Returns:
            List of Tenant objects
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return []
            
        # Get tenants from metadata database
        tenant_records = self.metadata_db.list_tenants(self.branch_id)
        tenants = []

        for record in tenant_records:
            # Filter out the __empty__ tenant from user-facing listings unless requested
            if not include_system and record['name'] == self._empty_tenant_name:
                continue
                
            tenant = Tenant(
                name=record['name'],
                database=self.database,
                branch=self.branch,
                is_main=(record['name'] == "main"),
            )
            tenants.append(tenant)

        return tenants

    def create_tenant(
        self, tenant_name: str, description: Optional[str] = None, lazy: bool = True,
        encrypt: bool = False, encryption_key: Optional[str] = None
    ) -> Tenant:
        """Create a new tenant by copying schema from main tenant.

        Args:
            tenant_name: Name for the new tenant
            description: Optional description
            lazy: If True, don't create database file until first use
            encrypt: If True, create encrypted tenant database
            encryption_key: Encryption key for encrypted tenant (required if encrypt=True)

        Returns:
            Created Tenant object

        Raises:
            ValueError: If tenant already exists or uses reserved name
            InvalidNameError: If tenant name is invalid
            MaintenanceError: If branch is in maintenance mode
        """
        # Validate encryption parameters
        if encrypt and not encryption_key:
            raise ValueError("encryption_key is required when encrypt=True")
        if encryption_key and not encrypt:
            raise ValueError("encrypt=True is required when providing encryption_key")
            
        # Check for reserved name
        if tenant_name == self._empty_tenant_name:
            raise ValueError(f"'{self._empty_tenant_name}' is a reserved tenant name")
            
        # Validate tenant name
        validate_name(tenant_name, "tenant")

        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")

        # Check if tenant already exists in metadata
        existing_tenant = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if existing_tenant:
            raise ValueError(f"Tenant '{tenant_name}' already exists")

        # Create tenant ID
        tenant_id = str(uuid.uuid4())
        
        # Calculate shard for tenant
        shard = calculate_shard(tenant_name)
        
        # Create tenant in metadata database
        metadata = {
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "encrypted": encrypt,
        }
        self.metadata_db.create_tenant(tenant_id, self.branch_id, tenant_name, shard, metadata)

        # Generate encryption key if plugged is available and encryption is enabled
        self._maybe_generate_tenant_key(tenant_name)

        if not lazy:
            # Create actual database file using sharded paths
            # Use ensure_tenant_db_path to create directories if needed
            new_db_path = ensure_tenant_db_path(
                self.project_root, self.database, self.branch, tenant_name
            )
            
            if encrypt:
                # Create encrypted database with schema from main tenant
                self._create_encrypted_tenant_database(new_db_path, encryption_key)
            else:
                # Ensure __empty__ tenant exists with current schema
                self._ensure_empty_tenant()
                
                # Copy __empty__ tenant database to new tenant
                # __empty__ already has 512-byte pages and no data
                empty_db_path = self._get_sharded_tenant_db_path(self._empty_tenant_name)
                shutil.copy2(empty_db_path, new_db_path)
            
            # Mark as materialized in metadata
            self.metadata_db.mark_tenant_materialized(tenant_id)

        return Tenant(
            name=tenant_name,
            database=self.database,
            branch=self.branch,
            description=description,
            is_main=False,
        )


    def _get_tenant_db_path(self, tenant_name: str) -> Path:
        """Get the database path for a tenant using new tenant-first approach.
        
        Args:
            tenant_name: Name of the tenant
            
        Returns:
            Path to the tenant database file in the context
        """
        # Ensure context directory exists
        ensure_context_directory(self.project_root, self.database, self.branch)
        
        # Use new tenant-first path resolution
        return get_tenant_db_path_in_context(self.context_root, tenant_name)

    def _get_sharded_tenant_db_path(self, tenant_name: str) -> Path:
        """Get the sharded database path for a tenant (legacy compatibility).
        
        This method is kept for backward compatibility but now uses the new
        tenant-first storage approach internally.
        
        Args:
            tenant_name: Name of the tenant
            
        Returns:
            Path to the tenant database file in its shard directory
        """
        return self._get_tenant_db_path(tenant_name)

    def _ensure_empty_tenant(self) -> None:
        """Ensure the __empty__ tenant exists with current schema.
        
        This tenant serves as a template for lazy tenants.
        It's created on-demand when first lazy tenant is read.
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return
            
        # Check if __empty__ exists in metadata
        empty_tenant = self.metadata_db.get_tenant(self.branch_id, self._empty_tenant_name)
        
        empty_db_path = self._get_sharded_tenant_db_path(self._empty_tenant_name)
        
        # Create in metadata if doesn't exist (should already be created during branch/database init)
        if not empty_tenant:
            tenant_id = str(uuid.uuid4())
            shard = calculate_shard(self._empty_tenant_name)
            self.metadata_db.create_tenant(
                tenant_id, self.branch_id, self._empty_tenant_name, shard,
                metadata={"system": True, "description": "Template for lazy tenants"}
            )
            # Don't mark as materialized yet - it will be when the file is created
            empty_tenant = {"id": tenant_id}
        
        # If __empty__ database doesn't exist, create it by copying from main tenant
        if not empty_db_path.exists():
            # Use centralized function to ensure directory exists
            ensure_tenant_db_path(
                self.project_root, self.database, self.branch, "__empty__"
            )
            
            # Get main tenant database path (may need to materialize it first)
            main_db_path = self._get_sharded_tenant_db_path("main")
            
            if main_db_path.exists():
                # Copy main tenant database to __empty__
                shutil.copy2(main_db_path, empty_db_path)
                
                # Clear all data from tables (keep schema only)
                with DatabaseConnection(empty_db_path, encryption_manager=self.encryption_manager) as conn:
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
            else:
                # If main doesn't exist either, create empty database
                empty_db_path.touch()
                with DatabaseConnection(empty_db_path, encryption_manager=self.encryption_manager):
                    pass  # Just initialize with PRAGMAs
            
            # Set reasonable default page size for template
            # We need to rebuild the database with new page size
            temp_path = empty_db_path.with_suffix('.tmp')
            
            # Create new database with 4KB pages (SQLite default, good balance for general use)
            vacuum_conn = sqlite3.connect(str(empty_db_path))
            vacuum_conn.isolation_level = None
            vacuum_conn.execute("PRAGMA page_size = 4096")
            vacuum_conn.execute(f"VACUUM INTO '{temp_path}'")
            vacuum_conn.close()
            
            # Replace original with default optimized version
            shutil.move(str(temp_path), str(empty_db_path))
            
            # Mark as materialized now that the file exists
            self.metadata_db.mark_tenant_materialized(empty_tenant['id'])
    

    def delete_tenant(self, tenant_name: str) -> None:
        """Delete a tenant.

        Args:
            tenant_name: Name of tenant to delete

        Raises:
            ValueError: If tenant doesn't exist, is main tenant, or is reserved
            InvalidNameError: If tenant name is invalid
            MaintenanceError: If branch is in maintenance mode
        """
        # Can't delete main or __empty__ tenants (check before validation)
        if tenant_name == "main":
            raise ValueError("Cannot delete the main tenant")
        if tenant_name == self._empty_tenant_name:
            raise ValueError(f"Cannot delete the reserved '{self._empty_tenant_name}' tenant")
        
        # Validate tenant name for security
        validate_name(tenant_name, "tenant")
        
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")

        # Get tenant info from metadata
        tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if not tenant_info:
            raise ValueError(f"Tenant '{tenant_name}' does not exist")

        # Delete from metadata database (this handles cascade delete)
        with self.metadata_db.conn:
            self.metadata_db.conn.execute(
                "DELETE FROM tenants WHERE id = ?", 
                (tenant_info['id'],)
            )

        # Delete tenant database file and related files (if they exist and it's materialized)
        if tenant_info['materialized']:
            db_path = get_tenant_db_path(
                self.project_root, self.database, self.branch, tenant_name
            )
            if db_path.exists():
                db_path.unlink()

                # Also remove WAL and SHM files if they exist
                wal_path = db_path.with_suffix(".db-wal")
                shm_path = db_path.with_suffix(".db-shm")

                if wal_path.exists():
                    wal_path.unlink()
                if shm_path.exists():
                    shm_path.unlink()
        
        # Invalidate cache for this tenant
        invalidate_cache(tenant=tenant_name)

    
    def materialize_tenant(self, tenant_name: str) -> None:
        """Materialize a lazy tenant into an actual database file.
        
        Args:
            tenant_name: Name of the tenant to materialize
            
        Raises:
            ValueError: If tenant doesn't exist or is already materialized
            InvalidNameError: If tenant name is invalid
        """
        # Validate tenant name first for security
        validate_name(tenant_name, "tenant")
        
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")
            
        # Get tenant info from metadata
        tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if not tenant_info:
            raise ValueError(f"Tenant '{tenant_name}' does not exist")
            
        # Check if already materialized
        if tenant_info['materialized']:
            return  # Already materialized
            
        # Use centralized function to get path and ensure directory exists
        db_path = ensure_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        
        # Ensure __empty__ tenant exists with current schema
        self._ensure_empty_tenant()
            
        # Get __empty__ tenant path for schema copy using new structure
        empty_db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, self._empty_tenant_name
        )
        
        # Copy __empty__ tenant database to new tenant
        shutil.copy2(empty_db_path, db_path)
        
        # No need to vacuum when copying from __empty__ since it's already optimized
        # The __empty__ template already has 512-byte pages and is vacuumed
        
        # Mark as materialized in metadata database
        self.metadata_db.mark_tenant_materialized(tenant_info['id'])


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
            
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")

        # Create tenant in metadata database first with shard
        tenant_id = str(uuid.uuid4())
        target_shard = calculate_shard(target_tenant)
        metadata = {
            "description": f"Copied from {source_tenant}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_db.create_tenant(tenant_id, self.branch_id, target_tenant, target_shard, metadata)

        # Get paths using sharded approach
        source_path = self._get_sharded_tenant_db_path(source_tenant)
        # Use ensure function to create directory if needed
        target_path = ensure_tenant_db_path(
            self.project_root, self.database, self.branch, target_tenant
        )

        # Copy database file
        shutil.copy2(source_path, target_path)
        
        # Mark as materialized since we copied a physical file
        self.metadata_db.mark_tenant_materialized(tenant_id)

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
            InvalidNameError: If either tenant name is invalid
        """
        # Validate both names for security (prevent path traversal)
        validate_name(old_name, "tenant")
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
            
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")
            
        # Get tenant info from metadata
        tenant_info = self.metadata_db.get_tenant(self.branch_id, old_name)
        if not tenant_info:
            raise ValueError(f"Tenant '{old_name}' does not exist in metadata")

        # Get old path before updating metadata (if materialized)
        old_path = None
        new_path = None
        if tenant_info['materialized']:
            # Calculate paths before metadata update
            old_shard = tenant_info['shard']
            new_shard = calculate_shard(new_name)
            
            context_root = get_context_root(self.project_root, self.database, self.branch)
            
            old_path = context_root / old_shard / f"{old_name}.db"
            # Use centralized function to ensure new directory exists
            new_path = ensure_tenant_db_path(
                self.project_root, self.database, self.branch, new_name
            )

        # Update metadata database
        new_shard = calculate_shard(new_name)
        with self.metadata_db.conn:
            self.metadata_db.conn.execute(
                "UPDATE tenants SET name = ?, shard = ? WHERE id = ?",
                (new_name, new_shard, tenant_info['id'])
            )

        # Rename physical files if tenant is materialized
        if tenant_info['materialized'] and old_path and new_path:

            # Rename database file if it exists
            if old_path.exists():
                # Directory already created by ensure_tenant_db_path above
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

    def get_tenant_size(self, tenant_name: str) -> dict:
        """Get storage size information for a tenant.
        
        Args:
            tenant_name: Name of the tenant
            
        Returns:
            Dictionary with size information:
            - name: Tenant name
            - size_bytes: Size in bytes (0 if no data)
            - size_kb: Size in KB
            - size_mb: Size in MB
            - page_size: SQLite page size (if available)
            - page_count: Number of pages (if available)
            
        Raises:
            ValueError: If tenant doesn't exist
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found")
            
        # Get tenant info from metadata
        tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if not tenant_info:
            raise ValueError(f"Tenant '{tenant_name}' does not exist")
            
        result = {
            "name": tenant_name,
            "size_bytes": 0,
            "size_kb": 0.0,
            "size_mb": 0.0,
            "page_size": None,
            "page_count": None
        }
        
        # If not materialized, return zeros
        if not tenant_info['materialized']:
            return result
            
        # Get actual file size
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            result["size_bytes"] = size_bytes
            result["size_kb"] = size_bytes / 1024
            result["size_mb"] = size_bytes / (1024 * 1024)
            
            # Get page information
            try:
                conn = sqlite3.connect(str(db_path))
                result["page_size"] = conn.execute("PRAGMA page_size").fetchone()[0]
                result["page_count"] = conn.execute("PRAGMA page_count").fetchone()[0]
                conn.close()
            except Exception:
                pass  # Ignore errors reading page info
                
        return result
    
    def get_all_tenant_sizes(self) -> dict:
        """Get storage size information for all tenants in the branch.
        
        Returns:
            Dictionary with:
            - tenants: List of individual tenant size info (sorted by size)
            - total_size_bytes: Total size of all tenants
            - total_size_mb: Total size in MB
            - tenant_count: Total number of tenants
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return {
                "tenants": [],
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "tenant_count": 0
            }
            
        # Get all tenants for this branch
        all_tenants = self.metadata_db.list_tenants(self.branch_id)
        
        result = {
            "tenants": [],
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "tenant_count": 0
        }

        for tenant_info in all_tenants:
            tenant_name = tenant_info['name']
            size_info = self.get_tenant_size(tenant_name)
            result["tenants"].append(size_info)
            result["tenant_count"] += 1
            result["total_size_bytes"] += size_info["size_bytes"]
                
        result["total_size_mb"] = result["total_size_bytes"] / (1024 * 1024)
        
        # Sort by size descending
        result["tenants"].sort(key=lambda x: x["size_bytes"], reverse=True)
        
        return result
    
    def is_tenant_lazy(self, tenant_name: str) -> bool:
        """Check if a tenant is lazy (not materialized).
        
        Args:
            tenant_name: Name of the tenant to check
            
        Returns:
            True if tenant is lazy, False if materialized
        """
        # Check if it's the __empty__ tenant (always materialized when exists)
        if tenant_name == self._empty_tenant_name:
            return False
            
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return False
            
        # Check metadata database
        tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if not tenant_info:
            return False
            
        # Tenant is lazy if it's not materialized
        return not tenant_info['materialized']
    
    def get_tenant_db_path_for_operation(self, tenant_name: str, is_write: bool = False) -> Path:
        """Get the appropriate database path for a tenant operation.
        
        For lazy tenants:
        - Read operations use __empty__ tenant
        - Write operations trigger materialization
        
        Args:
            tenant_name: Name of the tenant
            is_write: Whether this is for a write operation
            
        Returns:
            Path to the appropriate database file
            
        Raises:
            ValueError: If tenant doesn't exist
        """
        # Ensure initialization
        self._ensure_initialized()
        
        # Check if tenant exists in metadata
        if not self.branch_id:
            raise ValueError(f"Branch '{self.branch}' not found in metadata database")
            
        if tenant_name != self._empty_tenant_name:
            tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
            if not tenant_info:
                raise ValueError(f"Tenant '{tenant_name}' does not exist")
        
        # For lazy tenants
        if self.is_tenant_lazy(tenant_name):
            if is_write:
                # Materialize the tenant for writes
                self.materialize_tenant(tenant_name)
                return self._get_sharded_tenant_db_path(tenant_name)
            else:
                # Use __empty__ tenant for reads
                self._ensure_empty_tenant()
                return self._get_sharded_tenant_db_path(self._empty_tenant_name)
        else:
            # For materialized tenants, use their actual database
            return self._get_sharded_tenant_db_path(tenant_name)

    def get_tenant_connection(self, tenant_name: str, is_write: bool = False) -> DatabaseConnection:
        """Get a database connection for a tenant.

        IMPORTANT: The returned connection must be used with a context manager (with statement)
        to ensure proper resource cleanup and prevent file descriptor leaks.

        Args:
            tenant_name: Tenant name
            is_write: Whether this connection will be used for writes

        Returns:
            DatabaseConnection object (must be used with 'with' statement)

        Raises:
            ValueError: If tenant doesn't exist
            InvalidNameError: If tenant name is invalid
            
        Example:
            with tenant_manager.get_tenant_connection("main") as conn:
                conn.execute("SELECT * FROM table")
        """
        # Validate tenant name first for security (prevent path traversal)
        # Exception: __empty__ and main are system tenants
        if tenant_name not in ("__empty__", "main"):
            validate_name(tenant_name, "tenant")
        
        db_path = self.get_tenant_db_path_for_operation(tenant_name, is_write)
        return DatabaseConnection(db_path, tenant_id=tenant_name, encryption_manager=self.encryption_manager)

    def vacuum_tenant(self, tenant_name: str) -> dict:
        """Run VACUUM operation on a specific tenant to reclaim space and optimize performance.
        
        This performs SQLite's VACUUM command which:
        - Reclaims space from deleted records
        - Defragments the database file
        - Can improve query performance
        - Rebuilds database statistics
        
        Args:
            tenant_name: Name of the tenant to vacuum
            
        Returns:
            Dictionary with vacuum results:
            - success: Whether vacuum completed successfully
            - tenant: Name of the tenant
            - size_before: Size in bytes before vacuum
            - size_after: Size in bytes after vacuum
            - space_reclaimed: Bytes reclaimed by vacuum
            - duration_seconds: Time taken for vacuum operation
            
        Raises:
            ValueError: If tenant doesn't exist or is not materialized
        """
        import time
        
        # Ensure initialization
        self._ensure_initialized()
        
        # Check if tenant exists
        if tenant_name != self._empty_tenant_name:
            if not self.branch_id:
                raise ValueError(f"Branch '{self.branch}' not found")
                
            tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
            if not tenant_info:
                raise ValueError(f"Tenant '{tenant_name}' does not exist")
        
        # Check if tenant is materialized - return zero values for lazy tenants
        if self.is_tenant_lazy(tenant_name):
            return {
                "success": True,
                "tenant": tenant_name,
                "size_before": 0,
                "size_after": 0,
                "space_reclaimed": 0,
                "space_reclaimed_mb": 0.0,
                "duration_seconds": 0.0
            }
        
        # Get database path
        db_path = self._get_sharded_tenant_db_path(tenant_name)
        
        if not db_path.exists():
            raise ValueError(f"Database file for tenant '{tenant_name}' does not exist")
        
        # Get size before vacuum
        size_before = db_path.stat().st_size
        
        # Perform vacuum operation
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            with DatabaseConnection(db_path, tenant_id=tenant_name, encryption_manager=self.encryption_manager) as conn:
                # Run VACUUM command
                conn.execute("VACUUM")
            success = True
        except Exception as e:
            error_message = str(e)
        
        duration = time.time() - start_time
        
        # Get size after vacuum
        size_after = db_path.stat().st_size if db_path.exists() else 0
        space_reclaimed = max(0, size_before - size_after)
        
        result = {
            "success": success,
            "tenant": tenant_name,
            "size_before": size_before,
            "size_after": size_after,
            "space_reclaimed": space_reclaimed,
            "space_reclaimed_mb": round(space_reclaimed / (1024 * 1024), 2),
            "duration_seconds": round(duration, 2)
        }
        
        if not success:
            result["error"] = error_message
        
        return result
    
    def _maybe_generate_tenant_key(self, tenant_name: str) -> None:
        """Generate encryption key for tenant if plugged is available and encryption enabled."""
        try:
            # Try to import plugged TenantKeyManager
            from plugged.tenant_key_manager import TenantKeyManager
            
            # Create tenant ID for plugged (using same format as cinchdb)
            tenant_id = f"{self.database}-{self.branch}-{tenant_name}"
            
            # Initialize key manager with our metadata database
            key_manager = TenantKeyManager(self.metadata_db)
            
            # Generate encryption key for the new tenant
            encryption_key = key_manager.generate_tenant_key(tenant_id)
            
            logger.info(f"Generated encryption key for tenant {tenant_name} (version 1)")
            
        except ImportError:
            # Plugged not available - continue without encryption
            logger.debug(f"Plugged not available, skipping key generation for tenant {tenant_name}")
        except Exception as e:
            # Key generation failed - log warning but don't fail tenant creation
            logger.warning(f"Failed to generate encryption key for tenant {tenant_name}: {e}")
    
    def rotate_tenant_key(self, tenant_name: str) -> str:
        """Rotate encryption key for tenant if plugged is available."""
        try:
            from plugged.tenant_key_manager import TenantKeyManager
            
            tenant_id = f"{self.database}-{self.branch}-{tenant_name}"
            key_manager = TenantKeyManager(self.metadata_db)
            
            # Generate new key version
            new_key = key_manager.generate_tenant_key(tenant_id)
            
            logger.info(f"Rotated encryption key for tenant {tenant_name}")
            return new_key
            
        except ImportError:
            raise ValueError("Plugged extension not available - encryption key rotation requires plugged")
        except Exception as e:
            raise ValueError(f"Failed to rotate key for tenant {tenant_name}: {e}")
    
    def _create_encrypted_tenant_database(self, db_path: str, encryption_key: str) -> None:
        """Create an encrypted tenant database with current schema.
        
        Args:
            db_path: Path where the encrypted database should be created
            encryption_key: Encryption key for the database
        """
        try:
            # Import sqlite3 to check for SQLCipher support
            import sqlite3
            
            # Create encrypted database connection
            conn = sqlite3.connect(db_path)
            
            # Try to set encryption key (this will fail if SQLCipher is not available)
            try:
                conn.execute(f"PRAGMA key = '{encryption_key}'")
            except sqlite3.OperationalError as e:
                conn.close()
                # Remove the created file since it's not encrypted
                if os.path.exists(db_path):
                    os.remove(db_path)
                raise ValueError(
                    "SQLCipher is required for encryption but not available. "
                    "Please install pysqlcipher3 or sqlite3 with SQLCipher support."
                ) from e
            
            # Set SQLite optimization settings for new database
            conn.execute("PRAGMA page_size = 512")
            conn.execute("PRAGMA journal_mode = WAL")
            
            # Get schema from main tenant to replicate
            main_db_path = self._get_sharded_tenant_db_path("main")
            if os.path.exists(main_db_path):
                # Connect to main tenant to get schema
                main_conn = sqlite3.connect(main_db_path)
                
                # Get all table creation statements
                cursor = main_conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                
                # Create tables in encrypted database
                for (sql,) in cursor.fetchall():
                    if sql:  # Skip empty SQL statements
                        conn.execute(sql)
                
                # Get all index creation statements
                cursor = main_conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                )
                
                # Create indexes in encrypted database
                for (sql,) in cursor.fetchall():
                    if sql:  # Skip empty SQL statements
                        conn.execute(sql)
                
                main_conn.close()
            
            # Commit changes and close
            conn.commit()
            conn.close()
            
        except Exception as e:
            # Clean up on failure
            if os.path.exists(db_path):
                os.remove(db_path)
            raise ValueError(f"Failed to create encrypted database: {e}") from e

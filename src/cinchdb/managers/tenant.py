"""Tenant management for CinchDB."""

import hashlib
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
    get_database_path,
    list_tenants,
)
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance import check_maintenance_mode
from cinchdb.utils.name_validator import validate_name
from cinchdb.infrastructure.metadata_db import MetadataDB
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db


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
        self, tenant_name: str, description: Optional[str] = None, lazy: bool = True
    ) -> Tenant:
        """Create a new tenant by copying schema from main tenant.

        Args:
            tenant_name: Name for the new tenant
            description: Optional description
            lazy: If True, don't create database file until first use

        Returns:
            Created Tenant object

        Raises:
            ValueError: If tenant already exists or uses reserved name
            InvalidNameError: If tenant name is invalid
            MaintenanceError: If branch is in maintenance mode
        """
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
        shard = self._calculate_shard(tenant_name)
        
        # Create tenant in metadata database
        metadata = {
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_db.create_tenant(tenant_id, self.branch_id, tenant_name, shard, metadata)

        if not lazy:
            # Ensure __empty__ tenant exists with current schema
            self._ensure_empty_tenant()
            
            # Create actual database file using sharded paths
            new_db_path = self._get_sharded_tenant_db_path(tenant_name)
            empty_db_path = self._get_sharded_tenant_db_path(self._empty_tenant_name)
            
            # Directory creation is handled by _get_sharded_tenant_db_path
            
            # Copy __empty__ tenant database to new tenant
            # __empty__ already has 512-byte pages and no data
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

    def _calculate_shard(self, tenant_name: str) -> str:
        """Calculate the shard directory for a tenant using SHA256 hash.
        
        Args:
            tenant_name: Name of the tenant
            
        Returns:
            Two-character hex string (e.g., "a0", "ff")
        """
        hash_val = hashlib.sha256(tenant_name.encode('utf-8')).hexdigest()
        return hash_val[:2]

    def _get_sharded_tenant_db_path(self, tenant_name: str) -> Path:
        """Get the sharded database path for a tenant using metadata DB lookup.
        
        Args:
            tenant_name: Name of the tenant
            
        Returns:
            Path to the tenant database file in its shard directory
            
        Raises:
            ValueError: If tenant doesn't exist in metadata
        """
        # For __empty__ tenant, calculate shard directly
        if tenant_name == self._empty_tenant_name:
            shard = self._calculate_shard(tenant_name)
        else:
            # Look up shard from metadata DB
            tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
            if not tenant_info or not tenant_info.get('shard'):
                raise ValueError(f"Tenant '{tenant_name}' not found in metadata or missing shard info")
            shard = tenant_info['shard']
        
        # Build sharded path
        branch_path = get_branch_path(self.project_root, self.database, self.branch)
        tenants_dir = branch_path / "tenants"
        shard_dir = tenants_dir / shard
        
        # Ensure shard directory exists
        shard_dir.mkdir(parents=True, exist_ok=True)
        
        return shard_dir / f"{tenant_name}.db"

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
            shard = self._calculate_shard(self._empty_tenant_name)
            self.metadata_db.create_tenant(
                tenant_id, self.branch_id, self._empty_tenant_name, shard,
                metadata={"system": True, "description": "Template for lazy tenants"}
            )
            # Don't mark as materialized yet - it will be when the file is created
            empty_tenant = {"id": tenant_id}
        
        # If __empty__ database doesn't exist, create it by copying from main tenant
        if not empty_db_path.exists():
            empty_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get main tenant database path (may need to materialize it first)
            main_db_path = self._get_sharded_tenant_db_path("main")
            
            if main_db_path.exists():
                # Copy main tenant database to __empty__
                shutil.copy2(main_db_path, empty_db_path)
                
                # Clear all data from tables (keep schema only)
                with DatabaseConnection(empty_db_path) as conn:
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
                with DatabaseConnection(empty_db_path):
                    pass  # Just initialize with PRAGMAs
            
            # Optimize with small page size for empty template
            # We need to rebuild the database with new page size
            temp_path = empty_db_path.with_suffix('.tmp')
            
            # Create new database with 512-byte pages
            vacuum_conn = sqlite3.connect(str(empty_db_path))
            vacuum_conn.isolation_level = None
            vacuum_conn.execute("PRAGMA page_size = 512")
            vacuum_conn.execute(f"VACUUM INTO '{temp_path}'")
            vacuum_conn.close()
            
            # Replace original with optimized version
            shutil.move(str(temp_path), str(empty_db_path))
            
            # Mark as materialized now that the file exists
            self.metadata_db.mark_tenant_materialized(empty_tenant['id'])
    

    def delete_tenant(self, tenant_name: str) -> None:
        """Delete a tenant.

        Args:
            tenant_name: Name of tenant to delete

        Raises:
            ValueError: If tenant doesn't exist, is main tenant, or is reserved
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Can't delete main or __empty__ tenants
        if tenant_name == "main":
            raise ValueError("Cannot delete the main tenant")
        if tenant_name == self._empty_tenant_name:
            raise ValueError(f"Cannot delete the reserved '{self._empty_tenant_name}' tenant")

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

    def optimize_all_tenants(self, force: bool = False) -> dict:
        """Optimize storage for all materialized tenants in the branch.
        
        This is designed to be called periodically (e.g., every minute) to:
        - Reclaim unused space with VACUUM
        - Adjust page sizes as databases grow
        - Keep small databases compact
        
        Args:
            force: If True, optimize all tenants regardless of size
            
        Returns:
            Dictionary with optimization results:
            - optimized: List of tenant names that were optimized
            - skipped: List of tenant names that were skipped
            - errors: List of tuples (tenant_name, error_message)
        """
        results = {
            "optimized": [],
            "skipped": [],
            "errors": []
        }
        
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return results
            
        # Get all materialized tenants for this branch
        tenants = self.metadata_db.list_tenants(self.branch_id, materialized_only=True)
        
        for tenant in tenants:
            tenant_name = tenant['name']
            
            # Skip system tenants unless forced
            if not force and tenant_name in ["main", self._empty_tenant_name]:
                results["skipped"].append(tenant_name)
                continue
                
            try:
                optimized = self.optimize_tenant_storage(tenant_name, force=force)
                if optimized:
                    results["optimized"].append(tenant_name)
                else:
                    results["skipped"].append(tenant_name)
            except Exception as e:
                results["errors"].append((tenant_name, str(e)))
                
        return results
    
    def optimize_tenant_storage(self, tenant_name: str, force: bool = False) -> bool:
        """Optimize tenant database storage with VACUUM and optional page size adjustment.
        
        This performs:
        1. Always: VACUUM to reclaim unused space and defragment
        2. If needed: Rebuild with optimal page size based on database size
        
        Args:
            tenant_name: Name of tenant to optimize
            force: If True, always perform VACUUM even if page size is optimal
            
        Returns:
            True if optimization was performed, False if tenant doesn't exist
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return False
            
        # Skip system tenants
        if tenant_name in ["main", self._empty_tenant_name]:
            return False
            
        # Get tenant info
        tenant_info = self.metadata_db.get_tenant(self.branch_id, tenant_name)
        if not tenant_info or not tenant_info['materialized']:
            return False
            
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        
        if not db_path.exists():
            return False
            
        # Check current page size
        conn = sqlite3.connect(str(db_path))
        current_page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        conn.close()
        
        # Determine optimal page size
        optimal_page_size = self._get_optimal_page_size(db_path)
        
        # Decide if we need to rebuild with new page size
        needs_page_size_change = (current_page_size != optimal_page_size and 
                                  db_path.stat().st_size > 1024 * 1024)  # Only if > 1MB
        
        if needs_page_size_change:
            # Rebuild with new page size using VACUUM INTO
            temp_path = db_path.with_suffix('.tmp')
            conn = sqlite3.connect(str(db_path))
            conn.isolation_level = None
            conn.execute(f"PRAGMA page_size = {optimal_page_size}")
            conn.execute(f"VACUUM INTO '{temp_path}'")
            conn.close()
            
            # Replace original with optimized version
            shutil.move(str(temp_path), str(db_path))
            return True
        elif force or current_page_size == 512:
            # Just run regular VACUUM to defragment and reclaim space
            # Always vacuum 512-byte page databases to keep them compact
            conn = sqlite3.connect(str(db_path))
            conn.isolation_level = None
            conn.execute("VACUUM")
            conn.close()
            return True
            
        return False
    
    def _get_optimal_page_size(self, db_path: Path) -> int:
        """Determine optimal page size based on database file size.
        
        Args:
            db_path: Path to database file
            
        Returns:
            Optimal page size in bytes
        """
        if not db_path.exists():
            return 512  # Default for new/empty databases
            
        size_mb = db_path.stat().st_size / (1024 * 1024)
        
        if size_mb < 0.1:  # < 100KB
            return 512
        elif size_mb < 10:  # < 10MB
            return 4096  # 4KB - good balance for small-medium DBs
        elif size_mb < 100:  # < 100MB
            return 8192  # 8KB - better for larger rows
        else:  # >= 100MB
            return 16384  # 16KB - optimal for bulk operations
    
    def materialize_tenant(self, tenant_name: str) -> None:
        """Materialize a lazy tenant into an actual database file.
        
        Args:
            tenant_name: Name of the tenant to materialize
            
        Raises:
            ValueError: If tenant doesn't exist or is already materialized
        """
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
            
        db_path = get_tenant_db_path(
            self.project_root, self.database, self.branch, tenant_name
        )
        
        # Ensure tenants directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure __empty__ tenant exists with current schema
        self._ensure_empty_tenant()
            
        # Get __empty__ tenant path for schema copy
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
        target_shard = self._calculate_shard(target_tenant)
        metadata = {
            "description": f"Copied from {source_tenant}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata_db.create_tenant(tenant_id, self.branch_id, target_tenant, target_shard, metadata)

        # Get paths using sharded approach
        source_path = self._get_sharded_tenant_db_path(source_tenant)
        target_path = self._get_sharded_tenant_db_path(target_tenant)

        # Directory creation is handled by _get_sharded_tenant_db_path

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
            new_shard = self._calculate_shard(new_name)
            
            branch_path = get_branch_path(self.project_root, self.database, self.branch)
            tenants_dir = branch_path / "tenants"
            
            old_path = tenants_dir / old_shard / f"{old_name}.db"
            new_shard_dir = tenants_dir / new_shard
            new_shard_dir.mkdir(parents=True, exist_ok=True)
            new_path = new_shard_dir / f"{new_name}.db"

        # Update metadata database
        new_shard = self._calculate_shard(new_name)
        with self.metadata_db.conn:
            self.metadata_db.conn.execute(
                "UPDATE tenants SET name = ?, shard = ? WHERE id = ?",
                (new_name, new_shard, tenant_info['id'])
            )

        # Rename physical files if tenant is materialized
        if tenant_info['materialized'] and old_path and new_path:

            # Rename database file if it exists
            if old_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
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
            - materialized: Whether tenant is materialized
            - size_bytes: Size in bytes (0 if lazy)
            - size_kb: Size in KB
            - size_mb: Size in MB
            - page_size: SQLite page size (if materialized)
            - page_count: Number of pages (if materialized)
            
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
            "materialized": tenant_info['materialized'],
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
            - tenants: List of individual tenant size info
            - total_size_bytes: Total size of all materialized tenants
            - total_size_mb: Total size in MB
            - lazy_count: Number of lazy tenants
            - materialized_count: Number of materialized tenants
        """
        # Ensure initialization
        self._ensure_initialized()
        
        if not self.branch_id:
            return {
                "tenants": [],
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "lazy_count": 0,
                "materialized_count": 0
            }
            
        # Get all tenants for this branch
        all_tenants = self.metadata_db.list_tenants(self.branch_id)
        
        result = {
            "tenants": [],
            "total_size_bytes": 0,
            "total_size_mb": 0.0,
            "lazy_count": 0,
            "materialized_count": 0
        }
        
        for tenant_info in all_tenants:
            tenant_name = tenant_info['name']
            size_info = self.get_tenant_size(tenant_name)
            result["tenants"].append(size_info)
            
            if size_info["materialized"]:
                result["materialized_count"] += 1
                result["total_size_bytes"] += size_info["size_bytes"]
            else:
                result["lazy_count"] += 1
                
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
            
        Example:
            with tenant_manager.get_tenant_connection("main") as conn:
                conn.execute("SELECT * FROM table")
        """
        db_path = self.get_tenant_db_path_for_operation(tenant_name, is_write)
        return DatabaseConnection(db_path)

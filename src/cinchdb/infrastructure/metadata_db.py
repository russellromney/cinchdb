"""SQLite-based metadata storage for lazy resource tracking."""

import sqlite3
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
import json


class MetadataDB:
    """Manages SQLite database for project metadata."""
    
    def __init__(self, project_path: Path):
        """Initialize metadata database for a project."""
        self.db_path = project_path / ".cinchdb" / "metadata.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()
    
    def _connect(self):
        """Connect to the SQLite database."""
        # Check if this is a new database
        is_new_db = not self.db_path.exists()
        
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,  # Allow multi-threaded access
            timeout=30.0
        )
        self.conn.row_factory = sqlite3.Row
        
        # For new databases, set small page size before creating any tables
        if is_new_db:
            self.conn.execute("PRAGMA page_size = 1024")  # 1KB pages for metadata DB
        
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
    
    
    def _create_tables(self):
        """Create the metadata tables if they don't exist."""
        with self.conn:
            # Databases table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS databases (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    materialized BOOLEAN DEFAULT FALSE,
                    maintenance_mode BOOLEAN DEFAULT FALSE,
                    maintenance_reason TEXT,
                    maintenance_started_at TIMESTAMP,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Branches table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS branches (
                    id TEXT PRIMARY KEY,
                    database_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    parent_branch TEXT,
                    schema_version TEXT,
                    materialized BOOLEAN DEFAULT FALSE,
                    maintenance_mode BOOLEAN DEFAULT FALSE,
                    maintenance_reason TEXT,
                    maintenance_started_at TIMESTAMP,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (database_id) REFERENCES databases(id) ON DELETE CASCADE,
                    UNIQUE(database_id, name)
                )
            """)
            
            # Tenants table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    branch_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    shard TEXT,
                    materialized BOOLEAN DEFAULT FALSE,
                    metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
                    UNIQUE(branch_id, name)
                )
            """)
            
            # Create indexes for common queries
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_branches_database 
                ON branches(database_id)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenants_branch 
                ON tenants(branch_id)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_databases_materialized 
                ON databases(materialized)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_branches_materialized 
                ON branches(materialized)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenants_materialized 
                ON tenants(materialized)
            """)
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tenants_shard 
                ON tenants(shard)
            """)

            try:
                self.conn.execute("""
                    ALTER TABLE branches ADD COLUMN cdc_enabled BOOLEAN DEFAULT FALSE
                """)
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_branches_cdc_enabled 
                ON branches(cdc_enabled)
            """)
    
    # Database operations
    def create_database(self, database_id: str, name: str, 
                       description: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """Create a lazy database entry."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO databases (id, name, description, metadata)
                VALUES (?, ?, ?, ?)
            """, (database_id, name, description, 
                  json.dumps(metadata) if metadata else None))
    
    def get_database(self, name: str) -> Optional[Dict[str, Any]]:
        """Get database by name."""
        cursor = self.conn.execute("""
            SELECT * FROM databases WHERE name = ?
        """, (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_databases(self, materialized_only: bool = False) -> List[Dict[str, Any]]:
        """List all databases."""
        query = "SELECT * FROM databases"
        if materialized_only:
            query += " WHERE materialized = TRUE"
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_database_materialized(self, database_id: str) -> None:
        """Mark a database as materialized."""
        with self.conn:
            self.conn.execute("""
                UPDATE databases 
                SET materialized = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (database_id,))
    
    # Branch operations
    def create_branch(self, branch_id: str, database_id: str, name: str,
                     parent_branch: Optional[str] = None,
                     schema_version: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Create a lazy branch entry."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO branches (id, database_id, name, parent_branch, 
                                    schema_version, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (branch_id, database_id, name, parent_branch, schema_version,
                  json.dumps(metadata) if metadata else None))
    
    def get_branch(self, database_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get branch by database and name."""
        cursor = self.conn.execute("""
            SELECT * FROM branches 
            WHERE database_id = ? AND name = ?
        """, (database_id, name))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_branches(self, database_id: str, 
                     materialized_only: bool = False) -> List[Dict[str, Any]]:
        """List branches for a database."""
        query = "SELECT * FROM branches WHERE database_id = ?"
        params = [database_id]
        if materialized_only:
            query += " AND materialized = TRUE"
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_branch_materialized(self, branch_id: str) -> None:
        """Mark a branch as materialized."""
        with self.conn:
            self.conn.execute("""
                UPDATE branches 
                SET materialized = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (branch_id,))
    
    # Tenant operations
    def create_tenant(self, tenant_id: str, branch_id: str, name: str,
                     shard: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Create a lazy tenant entry."""
        with self.conn:
            self.conn.execute("""
                INSERT INTO tenants (id, branch_id, name, shard, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (tenant_id, branch_id, name, shard,
                  json.dumps(metadata) if metadata else None))
    
    def get_tenant(self, branch_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get tenant by branch and name."""
        cursor = self.conn.execute("""
            SELECT * FROM tenants 
            WHERE branch_id = ? AND name = ?
        """, (branch_id, name))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def list_tenants(self, branch_id: str,
                    materialized_only: bool = False) -> List[Dict[str, Any]]:
        """List tenants for a branch."""
        query = "SELECT * FROM tenants WHERE branch_id = ?"
        params = [branch_id]
        if materialized_only:
            query += " AND materialized = TRUE"
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_tenants_by_shard(self, branch_id: str, shard: str) -> List[Dict[str, Any]]:
        """Get all tenants in a specific shard for a branch."""
        cursor = self.conn.execute("""
            SELECT * FROM tenants 
            WHERE branch_id = ? AND shard = ?
        """, (branch_id, shard))
        return [dict(row) for row in cursor.fetchall()]
    
    def mark_tenant_materialized(self, tenant_id: str) -> None:
        """Mark a tenant as materialized."""
        with self.conn:
            self.conn.execute("""
                UPDATE tenants 
                SET materialized = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tenant_id,))
    
    def delete_database(self, database_id: str) -> None:
        """Delete a database and all its branches and tenants (cascading delete)."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM databases WHERE id = ?
            """, (database_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Database with id {database_id} not found")
    
    def delete_database_by_name(self, name: str) -> None:
        """Delete a database by name and all its branches and tenants (cascading delete)."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM databases WHERE name = ?
            """, (name,))
            if cursor.rowcount == 0:
                raise ValueError(f"Database '{name}' not found")
    
    def delete_branch(self, branch_id: str) -> None:
        """Delete a branch and all its tenants (cascading delete)."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM branches WHERE id = ?
            """, (branch_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Branch with id {branch_id} not found")
    
    def delete_branch_by_name(self, database_id: str, branch_name: str) -> None:
        """Delete a branch by name and all its tenants (cascading delete)."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM branches WHERE database_id = ? AND name = ?
            """, (database_id, branch_name))
            if cursor.rowcount == 0:
                raise ValueError(f"Branch '{branch_name}' not found in database")
    
    def delete_tenant(self, tenant_id: str) -> None:
        """Delete a tenant."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM tenants WHERE id = ?
            """, (tenant_id,))
            if cursor.rowcount == 0:
                raise ValueError(f"Tenant with id {tenant_id} not found")
    
    def delete_tenant_by_name(self, branch_id: str, tenant_name: str) -> None:
        """Delete a tenant by name."""
        with self.conn:
            cursor = self.conn.execute("""
                DELETE FROM tenants WHERE branch_id = ? AND name = ?
            """, (branch_id, tenant_name))
            if cursor.rowcount == 0:
                raise ValueError(f"Tenant '{tenant_name}' not found in branch")
    
    def tenant_exists(self, database_name: str, branch_name: str, 
                     tenant_name: str) -> bool:
        """Check if a tenant exists (lazy or materialized)."""
        cursor = self.conn.execute("""
            SELECT 1 FROM tenants t
            JOIN branches b ON t.branch_id = b.id
            JOIN databases d ON b.database_id = d.id
            WHERE d.name = ? AND b.name = ? AND t.name = ?
            LIMIT 1
        """, (database_name, branch_name, tenant_name))
        return cursor.fetchone() is not None
    
    def get_full_tenant_info(self, database_name: str, branch_name: str,
                            tenant_name: str) -> Optional[Dict[str, Any]]:
        """Get full tenant information including database and branch details."""
        cursor = self.conn.execute("""
            SELECT 
                t.*,
                b.name as branch_name,
                b.schema_version,
                b.materialized as branch_materialized,
                d.name as database_name,
                d.materialized as database_materialized
            FROM tenants t
            JOIN branches b ON t.branch_id = b.id
            JOIN databases d ON b.database_id = d.id
            WHERE d.name = ? AND b.name = ? AND t.name = ?
        """, (database_name, branch_name, tenant_name))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # Utility methods
    def copy_tenants_to_branch(self, source_branch_id: str, target_branch_id: str, 
                               as_lazy: bool = True) -> int:
        """Copy all tenants from source branch to target branch.
        
        Args:
            source_branch_id: ID of source branch
            target_branch_id: ID of target branch  
            as_lazy: If True, copied tenants are marked as not materialized
            
        Returns:
            Number of tenants copied
        """
        with self.conn:
            # Get all tenants from source branch
            cursor = self.conn.execute("""
                SELECT name, metadata FROM tenants 
                WHERE branch_id = ?
            """, (source_branch_id,))
            
            tenants = cursor.fetchall()
            
            for tenant in tenants:
                tenant_id = str(uuid.uuid4())
                self.conn.execute("""
                    INSERT INTO tenants (id, branch_id, name, materialized, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (tenant_id, target_branch_id, tenant['name'], 
                      not as_lazy, tenant['metadata']))
            
            return len(tenants)
    
    # Maintenance Mode Methods
    
    def set_database_maintenance(self, database_name: str, enabled: bool, reason: Optional[str] = None) -> None:
        """Set maintenance mode for a database."""
        with self.conn:
            if enabled:
                self.conn.execute("""
                    UPDATE databases 
                    SET maintenance_mode = TRUE, 
                        maintenance_reason = ?, 
                        maintenance_started_at = CURRENT_TIMESTAMP 
                    WHERE name = ?
                """, (reason, database_name))
            else:
                self.conn.execute("""
                    UPDATE databases 
                    SET maintenance_mode = FALSE, 
                        maintenance_reason = NULL, 
                        maintenance_started_at = NULL 
                    WHERE name = ?
                """, (database_name,))
    
    def set_branch_maintenance(self, database_name: str, branch_name: str, enabled: bool, reason: Optional[str] = None) -> None:
        """Set maintenance mode for a branch."""
        with self.conn:
            if enabled:
                self.conn.execute("""
                    UPDATE branches 
                    SET maintenance_mode = TRUE, 
                        maintenance_reason = ?, 
                        maintenance_started_at = CURRENT_TIMESTAMP 
                    WHERE database_id = (SELECT id FROM databases WHERE name = ?) 
                    AND name = ?
                """, (reason, database_name, branch_name))
            else:
                self.conn.execute("""
                    UPDATE branches 
                    SET maintenance_mode = FALSE, 
                        maintenance_reason = NULL, 
                        maintenance_started_at = NULL 
                    WHERE database_id = (SELECT id FROM databases WHERE name = ?) 
                    AND name = ?
                """, (database_name, branch_name))
    
    def is_database_in_maintenance(self, database_name: str) -> bool:
        """Check if database is in maintenance mode."""
        cursor = self.conn.execute("""
            SELECT maintenance_mode FROM databases WHERE name = ?
        """, (database_name,))
        row = cursor.fetchone()
        return bool(row and row['maintenance_mode'])
    
    def is_branch_in_maintenance(self, database_name: str, branch_name: str) -> bool:
        """Check if branch is in maintenance mode."""
        cursor = self.conn.execute("""
            SELECT maintenance_mode FROM branches 
            WHERE database_id = (SELECT id FROM databases WHERE name = ?) 
            AND name = ?
        """, (database_name, branch_name))
        row = cursor.fetchone()
        return bool(row and row['maintenance_mode'])
    
    def get_maintenance_info(self, database_name: str, branch_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get maintenance mode information."""
        if branch_name:
            # Check branch maintenance
            cursor = self.conn.execute("""
                SELECT maintenance_mode, maintenance_reason, maintenance_started_at 
                FROM branches 
                WHERE database_id = (SELECT id FROM databases WHERE name = ?) 
                AND name = ?
            """, (database_name, branch_name))
        else:
            # Check database maintenance
            cursor = self.conn.execute("""
                SELECT maintenance_mode, maintenance_reason, maintenance_started_at 
                FROM databases WHERE name = ?
            """, (database_name,))
        
        row = cursor.fetchone()
        if row and row['maintenance_mode']:
            return {
                'enabled': True,
                'reason': row['maintenance_reason'],
                'started_at': row['maintenance_started_at']
            }
        return None
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
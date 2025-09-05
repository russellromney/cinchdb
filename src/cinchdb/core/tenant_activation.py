"""Tenant activation and caching.

This module handles local caching of tenant databases with
LRU eviction and TTL management. WAL streaming is handled
at the api-server layer, not in the core library.
"""

import os
import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from cinchdb.core.connection import DatabaseConnection


class TenantCache:
    """Manages local cache of activated tenant databases.
    
    This implements an LRU cache with TTL for tenant SQLite files.
    Tenants are activated on-demand from WAL replay and cached locally.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, max_size_gb: float = 10.0):
        """Initialize tenant cache.
        
        Args:
            cache_dir: Directory for cached tenant databases
            max_size_gb: Maximum cache size in GB before eviction
        """
        self.cache_dir = cache_dir or Path("/var/cache/cinchdb/tenants")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        
        # Track cached tenants: tenant_key -> (path, version, last_access)
        self.cache_index: Dict[str, Dict[str, Any]] = {}
    
    def _get_cache_path(self, database: str, branch: str, tenant: str) -> Path:
        """Get cache path for a tenant database.
        
        Uses sharding to avoid too many files in one directory.
        """
        # Create tenant key
        tenant_key = f"{database}_{branch}_{tenant}"
        
        # Calculate shard (2-level sharding like production)
        hash_val = hashlib.sha256(tenant_key.encode()).hexdigest()
        shard1 = hash_val[:2]
        shard2 = hash_val[2:4]
        
        # Build path
        cache_path = self.cache_dir / database / branch / shard1 / shard2
        cache_path.mkdir(parents=True, exist_ok=True)
        
        return cache_path / f"{tenant}.db"
    
    def get_tenant_connection(
        self,
        database: str,
        branch: str,
        tenant: str,
        wal_capture=None
    ) -> DatabaseConnection:
        """Get a database connection for a tenant.
        
        If the tenant is not cached, activates it from WAL replay.
        
        Args:
            database: Database name
            branch: Branch name
            tenant: Tenant name
            wal_capture: Optional WAL capture for streaming
            
        Returns:
            DatabaseConnection to the tenant database
        """
        tenant_key = f"{database}_{branch}_{tenant}"
        cache_path = self._get_cache_path(database, branch, tenant)
        
        # Check if already cached
        if cache_path.exists():
            # Update last access time
            if tenant_key in self.cache_index:
                self.cache_index[tenant_key]["last_access"] = datetime.now()
            
            return DatabaseConnection(cache_path, wal_capture=wal_capture)
        
        # Not cached - create empty database
        # WAL streaming/activation happens at api-server layer if enabled
        return self._create_empty_database(cache_path, wal_capture)
    
    def _create_empty_database(
        self,
        cache_path: Path,
        wal_capture=None
    ) -> DatabaseConnection:
        """Create an empty database (for lazy tenants or non-streaming mode).
        
        Args:
            cache_path: Path where database should be created
            wal_capture: Optional WAL capture
            
        Returns:
            DatabaseConnection to the new database
        """
        # Create empty SQLite database
        conn = sqlite3.connect(str(cache_path))
        
        # Set up WAL mode
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.commit()
        conn.close()
        
        return DatabaseConnection(cache_path, wal_capture=wal_capture)
    
    
    def _evict_if_needed(self):
        """Evict least recently used tenants if cache is too large."""
        # Calculate total cache size
        total_size = sum(
            info["size_bytes"] for info in self.cache_index.values()
        )
        
        if total_size <= self.max_size_bytes:
            return  # Cache is within limits
        
        # Sort by last access time (LRU)
        sorted_tenants = sorted(
            self.cache_index.items(),
            key=lambda x: x[1]["last_access"]
        )
        
        # Evict until under limit
        for tenant_key, info in sorted_tenants:
            if total_size <= self.max_size_bytes:
                break
            
            # Delete cached database
            cache_path = info["path"]
            if cache_path.exists():
                # Delete SQLite files (main, WAL, SHM)
                for suffix in ["", "-wal", "-shm"]:
                    file_path = Path(str(cache_path) + suffix)
                    if file_path.exists():
                        file_path.unlink()
                
                print(f"Evicted cached tenant: {tenant_key}")
            
            # Remove from index
            total_size -= info["size_bytes"]
            del self.cache_index[tenant_key]
    
    def invalidate_tenant(self, database: str, branch: str, tenant: str):
        """Invalidate a cached tenant (force re-activation on next access).
        
        Args:
            database: Database name
            branch: Branch name
            tenant: Tenant name
        """
        tenant_key = f"{database}_{branch}_{tenant}"
        
        if tenant_key in self.cache_index:
            info = self.cache_index[tenant_key]
            cache_path = info["path"]
            
            # Delete cached files
            if cache_path.exists():
                for suffix in ["", "-wal", "-shm"]:
                    file_path = Path(str(cache_path) + suffix)
                    if file_path.exists():
                        file_path.unlink()
            
            # Remove from index
            del self.cache_index[tenant_key]
            print(f"Invalidated cached tenant: {tenant_key}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_size = sum(
            info["size_bytes"] for info in self.cache_index.values()
        )
        
        return {
            "cached_tenants": len(self.cache_index),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_gb": self.max_size_bytes / (1024 * 1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }


# Global cache instance (singleton)
_tenant_cache: Optional[TenantCache] = None


def get_tenant_cache() -> TenantCache:
    """Get the global tenant cache instance.
    
    Returns:
        TenantCache singleton
    """
    global _tenant_cache
    
    if _tenant_cache is None:
        cache_dir = os.getenv("TENANT_CACHE_DIR", "/var/cache/cinchdb")
        cache_size_gb = float(os.getenv("TENANT_CACHE_SIZE_GB", "10.0"))
        _tenant_cache = TenantCache(Path(cache_dir), cache_size_gb)
    
    return _tenant_cache
"""Path utilities for CinchDB."""

import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from cinchdb.infrastructure.metadata_connection_pool import get_metadata_db
from cinchdb.utils.name_validator import validate_name

# Cache for path calculations to avoid repeated string operations
_path_cache: Dict[Tuple[str, str, str], Path] = {}
_shard_cache: Dict[str, str] = {}
_MAX_CACHE_SIZE = 10000  # Limit cache size to prevent unbounded growth


def get_project_root(start_path: Path) -> Path:
    """Find the project root by looking for .cinchdb directory.

    Args:
        start_path: Path to start searching from

    Returns:
        Path to project root

    Raises:
        FileNotFoundError: If no project root found
    """
    current = Path(start_path).resolve()

    while current != current.parent:
        if (current / ".cinchdb").exists():
            return current
        current = current.parent

    raise FileNotFoundError(f"No CinchDB project found from {start_path}")


def get_database_path(project_root: Path, database: str) -> Path:
    """Get path to a database directory.

    Args:
        project_root: Project root directory
        database: Database name

    Returns:
        Path to database directory
    """
    return project_root / ".cinchdb" / "databases" / database


def get_branch_path(project_root: Path, database: str, branch: str) -> Path:
    """Get path to a branch directory (now uses context root).

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name

    Returns:
        Path to branch directory (context root in tenant-first structure)
    """
    # In tenant-first structure, branch path is the context root
    return get_context_root(project_root, database, branch)


def get_tenant_path(
    project_root: Path, database: str, branch: str, tenant: str
) -> Path:
    """Get path to tenant directory (deprecated, use get_context_root instead).

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name

    Returns:
        Path to context root (no longer has /tenants subfolder)
    """
    return get_branch_path(project_root, database, branch)


def get_tenant_db_path(
    project_root: Path, database: str, branch: str, tenant: str
) -> Path:
    """Get path to tenant database file using hash-based sharding.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name

    Returns:
        Path to tenant database file in sharded directory structure
        
    Raises:
        InvalidNameError: If any name contains path traversal characters
    """
    # Validate all names to prevent path traversal
    # Exception: __empty__ is a system tenant and exempt from validation
    validate_name(database, "database")
    validate_name(branch, "branch")
    if tenant != "__empty__":  # System tenant exempt from validation
        validate_name(tenant, "tenant")
    
    context_root = get_context_root(project_root, database, branch)
    shard = calculate_shard(tenant)
    return context_root / shard / f"{tenant}.db"


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists
    """
    path.mkdir(parents=True, exist_ok=True)


def list_databases(project_root: Path) -> List[str]:
    """List all databases in a project.

    Args:
        project_root: Project root directory

    Returns:
        List of database names
    """
    metadata_db_path = project_root / ".cinchdb" / "metadata.db"
    if not metadata_db_path.exists():
        return []
    
    metadata_db = get_metadata_db(project_root)
    db_records = metadata_db.list_databases()
    return sorted(record['name'] for record in db_records)


def list_branches(project_root: Path, database: str) -> List[str]:
    """List all branches in a database.

    Args:
        project_root: Project root directory
        database: Database name

    Returns:
        List of branch names
    """
    metadata_db_path = project_root / ".cinchdb" / "metadata.db"
    if not metadata_db_path.exists():
        return []
    
    metadata_db = get_metadata_db(project_root)
    db_info = metadata_db.get_database(database)
    if not db_info:
        return []
    branch_records = metadata_db.list_branches(db_info['id'])
    return sorted(record['name'] for record in branch_records)


def list_tenants(project_root: Path, database: str, branch: str) -> List[str]:
    """List all tenants in a branch.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name

    Returns:
        List of tenant names
    """
    metadata_db_path = project_root / ".cinchdb" / "metadata.db"
    if not metadata_db_path.exists():
        return []
    
    metadata_db = get_metadata_db(project_root)
    db_info = metadata_db.get_database(database)
    if not db_info:
        return []
    branch_info = metadata_db.get_branch(db_info['id'], branch)
    if not branch_info:
        return []
    tenant_records = metadata_db.list_tenants(branch_info['id'])
    return sorted(record['name'] for record in tenant_records)


# New tenant-first path utilities

def get_context_root(project_root: Path, database: str, branch: str) -> Path:
    """Get root directory for a database-branch context with caching.
    
    This is the new tenant-first approach where each database-branch combination
    gets its own isolated directory with tenants stored as a flat hierarchy.
    
    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        
    Returns:
        Path to context root directory (e.g., .cinchdb/prod-main/)
    """
    cache_key = (str(project_root), database, branch)
    
    if cache_key not in _path_cache:
        # Check cache size and clear if needed
        if len(_path_cache) >= _MAX_CACHE_SIZE:
            _path_cache.clear()
        
        _path_cache[cache_key] = project_root / ".cinchdb" / f"{database}-{branch}"
    
    return _path_cache[cache_key]


def calculate_shard(tenant_name: str) -> str:
    """Calculate the shard directory for a tenant using SHA256 hash with caching.
    
    Args:
        tenant_name: Name of the tenant
        
    Returns:
        Two-character hex string (e.g., "a0", "ff")
    """
    if tenant_name not in _shard_cache:
        # Check cache size and clear if needed
        if len(_shard_cache) >= _MAX_CACHE_SIZE:
            _shard_cache.clear()
        
        hash_val = hashlib.sha256(tenant_name.encode('utf-8')).hexdigest()
        _shard_cache[tenant_name] = hash_val[:2]
    
    return _shard_cache[tenant_name]


def get_tenant_db_path_in_context(context_root: Path, tenant: str) -> Path:
    """Get tenant DB path within a context root.
    
    Uses the tenant-first storage approach where tenants are stored as:
    {context_root}/{shard}/{tenant}.db
    
    Args:
        context_root: Context root directory (from get_context_root)
        tenant: Tenant name
        
    Returns:
        Path to tenant database file within the context
    """
    shard = calculate_shard(tenant)
    return context_root / shard / f"{tenant}.db"




def ensure_context_directory(project_root: Path, database: str, branch: str) -> Path:
    """Ensure context root directory exists and return it.
    
    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        
    Returns:
        Path to context root directory (created if necessary)
    """
    context_root = get_context_root(project_root, database, branch)
    context_root.mkdir(parents=True, exist_ok=True)
    
    return context_root


def ensure_tenant_db_path(project_root: Path, database: str, branch: str, tenant: str) -> Path:
    """Ensure tenant database path exists (creates shard directory if needed).
    
    This is the ONLY place where tenant shard directories should be created,
    ensuring we have a single source of truth for the directory structure.
    
    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name
        
    Returns:
        Path to tenant database file (directory created if necessary)
        
    Raises:
        InvalidNameError: If any name contains path traversal characters
    """
    # Validation happens inside get_tenant_db_path
    db_path = get_tenant_db_path(project_root, database, branch, tenant)
    
    # Ensure the shard directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return db_path


def invalidate_cache(database: Optional[str] = None, 
                    branch: Optional[str] = None, 
                    tenant: Optional[str] = None) -> None:
    """Invalidate cache entries (write-through on delete operations).
    
    This function is called when databases, branches, or tenants are deleted
    to ensure cached paths don't point to non-existent resources.
    
    Args:
        database: Database name to invalidate (invalidates all branches/tenants if provided)
        branch: Branch name to invalidate (requires database)
        tenant: Tenant name to invalidate (only invalidates shard cache)
    """
    global _path_cache, _shard_cache
    
    if database:
        # Remove all cache entries for this database
        keys_to_remove = []
        for key in _path_cache:
            # key is (project_root, database, branch)
            if key[1] == database:
                if branch is None or key[2] == branch:
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del _path_cache[key]
    
    if tenant and tenant in _shard_cache:
        del _shard_cache[tenant]


def clear_all_caches() -> None:
    """Clear all path and shard caches.
    
    Useful for testing or when major structural changes occur.
    """
    global _path_cache, _shard_cache
    _path_cache.clear()
    _shard_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """Get statistics about cache usage.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        "path_cache_size": len(_path_cache),
        "shard_cache_size": len(_shard_cache),
        "max_cache_size": _MAX_CACHE_SIZE
    }

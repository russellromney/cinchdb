"""Path utilities for CinchDB."""

from pathlib import Path
from typing import List, Optional


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
    """Get path to a branch directory.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name

    Returns:
        Path to branch directory
    """
    return get_database_path(project_root, database) / "branches" / branch


def get_tenant_path(
    project_root: Path, database: str, branch: str, tenant: str
) -> Path:
    """Get path to tenant directory.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name

    Returns:
        Path to tenant directory
    """
    return get_branch_path(project_root, database, branch) / "tenants"


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
    """
    import hashlib
    
    # Calculate shard using SHA256 hash (same as TenantManager)
    hash_val = hashlib.sha256(tenant.encode('utf-8')).hexdigest()
    shard = hash_val[:2]
    
    # Build sharded path: /tenants/{shard}/{tenant}.db
    tenants_dir = get_tenant_path(project_root, database, branch, tenant)
    shard_dir = tenants_dir / shard
    
    return shard_dir / f"{tenant}.db"


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
    
    from cinchdb.infrastructure.metadata_db import MetadataDB
    with MetadataDB(project_root) as metadata_db:
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
    
    from cinchdb.infrastructure.metadata_db import MetadataDB
    with MetadataDB(project_root) as metadata_db:
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
    
    from cinchdb.infrastructure.metadata_db import MetadataDB
    with MetadataDB(project_root) as metadata_db:
        db_info = metadata_db.get_database(database)
        if not db_info:
            return []
        branch_info = metadata_db.get_branch(db_info['id'], branch)
        if not branch_info:
            return []
        tenant_records = metadata_db.list_tenants(branch_info['id'])
        return sorted(record['name'] for record in tenant_records)

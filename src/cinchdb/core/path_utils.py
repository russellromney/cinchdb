"""Path utilities for CinchDB."""

from pathlib import Path
from typing import List


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
    """Get path to tenant database file.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name

    Returns:
        Path to tenant database file
    """
    return get_tenant_path(project_root, database, branch, tenant) / f"{tenant}.db"


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
    db_dir = project_root / ".cinchdb" / "databases"
    if not db_dir.exists():
        return []

    return sorted([d.name for d in db_dir.iterdir() if d.is_dir()])


def list_branches(project_root: Path, database: str) -> List[str]:
    """List all branches in a database.

    Args:
        project_root: Project root directory
        database: Database name

    Returns:
        List of branch names
    """
    branches_dir = get_database_path(project_root, database) / "branches"
    if not branches_dir.exists():
        return []

    return sorted([b.name for b in branches_dir.iterdir() if b.is_dir()])


def list_tenants(project_root: Path, database: str, branch: str) -> List[str]:
    """List all tenants in a branch.

    Args:
        project_root: Project root directory
        database: Database name
        branch: Branch name

    Returns:
        List of tenant names
    """
    tenants_dir = get_branch_path(project_root, database, branch) / "tenants"
    if not tenants_dir.exists():
        return []

    # Only list .db files, not WAL or SHM files
    tenants = []
    for f in tenants_dir.iterdir():
        if f.is_file() and f.suffix == ".db":
            tenants.append(f.stem)

    return sorted(tenants)

"""Base manager class and shared context for all CinchDB managers."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class ConnectionContext:
    """Shared connection context for all managers.

    This eliminates parameter duplication across manager constructors and provides
    a single source of truth for connection information.

    Attributes:
        project_root: Path to project root directory
        database: Database name
        branch: Branch name
        tenant: Tenant name (default: main)
        encryption_manager: Optional encryption manager for encrypted tenants
    """
    project_root: Path
    database: str
    branch: str
    tenant: str = "main"
    encryption_manager: Optional[object] = None

    def __post_init__(self):
        """Ensure project_root is a Path object."""
        if not isinstance(self.project_root, Path):
            self.project_root = Path(self.project_root)

    # Manager properties for convenient access
    # These use lazy imports to avoid circular dependencies

    @property
    def tables(self) -> "TableManager":
        """Access TableManager for this context."""
        from cinchdb.managers.table import TableManager
        return TableManager(self)

    @property
    def columns(self) -> "ColumnManager":
        """Access ColumnManager for this context."""
        from cinchdb.managers.column import ColumnManager
        return ColumnManager(self)

    @property
    def views(self) -> "ViewModel":
        """Access ViewModel for this context."""
        from cinchdb.managers.view import ViewModel
        return ViewModel(self)

    @property
    def indexes(self) -> "IndexManager":
        """Access IndexManager for this context."""
        from cinchdb.managers.index import IndexManager
        return IndexManager(self)

    @property
    def data(self) -> "DataManager":
        """Access DataManager for this context."""
        from cinchdb.managers.data import DataManager
        return DataManager(self)

    @property
    def query(self) -> "QueryManager":
        """Access QueryManager for this context."""
        from cinchdb.managers.query import QueryManager
        return QueryManager(self)

    @property
    def branches(self) -> "BranchManager":
        """Access BranchManager for this context."""
        from cinchdb.managers.branch import BranchManager
        return BranchManager(self)

    @property
    def tenants(self) -> "TenantManager":
        """Access TenantManager for this context."""
        from cinchdb.managers.tenant import TenantManager
        return TenantManager(self)

    @property
    def codegen(self) -> "CodegenManager":
        """Access CodegenManager for this context."""
        from cinchdb.managers.codegen import CodegenManager
        return CodegenManager(self)

    @property
    def kv(self) -> "KVManager":
        """Access KVManager for this context."""
        from cinchdb.managers.kv import KVManager
        return KVManager(self)

    @property
    def change_tracker(self) -> "ChangeTracker":
        """Access ChangeTracker for this context."""
        from cinchdb.managers.change_tracker import ChangeTracker
        return ChangeTracker(self.project_root, self.database, self.branch)

    @property
    def change_applier(self) -> "ChangeApplier":
        """Access ChangeApplier for this context."""
        from cinchdb.managers.change_applier import ChangeApplier
        return ChangeApplier(self.project_root, self.database, self.branch)

    @property
    def merge(self) -> "MergeManager":
        """Access MergeManager for this context."""
        from cinchdb.managers.merge_manager import MergeManager
        return MergeManager(self)


class BaseManager:
    """Base class for all CinchDB managers.

    Provides shared initialization, lazy change tracker loading, and common utilities.
    Eliminates ~200 lines of duplicated code across 14+ manager classes.
    """

    def __init__(self, context: ConnectionContext):
        """Initialize base manager with connection context.

        Args:
            context: ConnectionContext with all connection parameters
        """
        self.context = context
        self.project_root = context.project_root
        self.database = context.database
        self.branch = context.branch
        self.tenant = context.tenant
        self.encryption_manager = context.encryption_manager

        # Compute db_path (most managers need this)
        from cinchdb.core.path_utils import get_tenant_db_path
        self.db_path = get_tenant_db_path(
            context.project_root,
            context.database,
            context.branch,
            context.tenant
        )

        # Lazy-loaded change tracker
        self._change_tracker = None

    @property
    def change_tracker(self):
        """Lazy load change tracker only when needed for actual changes.

        Returns:
            ChangeTracker instance or None if database/branch doesn't exist yet
        """
        if self._change_tracker is None:
            try:
                from cinchdb.managers.change_tracker import ChangeTracker
                self._change_tracker = ChangeTracker(
                    self.project_root,
                    self.database,
                    self.branch
                )
            except ValueError:
                # Database/branch doesn't exist yet - this is fine for read operations
                return None
        return self._change_tracker

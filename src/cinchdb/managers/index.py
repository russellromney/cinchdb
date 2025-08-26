"""Index management for CinchDB."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3
from datetime import datetime, timezone
import uuid

from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.models.change import Change, ChangeType


class IndexManager:
    """Manages database indexes for CinchDB tables at the branch level."""

    def __init__(
        self, project_dir: Path, database: str, branch: str
    ):
        """Initialize IndexManager.

        Args:
            project_dir: Path to the project directory
            database: Database name
            branch: Branch name
        """
        self.project_dir = Path(project_dir)
        self.database = database
        self.branch = branch

    def create_index(
        self,
        table: str,
        columns: List[str],
        name: Optional[str] = None,
        unique: bool = False,
        if_not_exists: bool = True,
    ) -> str:
        """Create an index on a table.

        Args:
            table: Table name
            columns: List of column names to index
            name: Optional index name (auto-generated if not provided)
            unique: Whether to create a unique index
            if_not_exists: Whether to use IF NOT EXISTS clause

        Returns:
            str: Name of the created index

        Raises:
            ValueError: If table doesn't exist or columns are invalid
        """
        # Convert parameters to Index model for validation
        from cinchdb.models import Index
        index = Index(columns=columns, name=name, unique=unique)
        
        if not index.columns:
            raise ValueError("At least one column must be specified for the index")

        # Generate index name if not provided
        if not index.name:
            column_str = "_".join(index.columns)
            unique_prefix = "uniq_" if index.unique else "idx_"
            index.name = f"{unique_prefix}{table}_{column_str}"

        # Get connection to main tenant database (indexes are branch-level)
        db_path = get_tenant_db_path(
            self.project_dir, self.database, self.branch, "main"
        )
        
        with DatabaseConnection(db_path) as conn:
            # Verify table exists
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                [table]
            )
            if not result.fetchone():
                raise ValueError(f"Table '{table}' does not exist")
            
            # Verify columns exist
            result = conn.execute(f"PRAGMA table_info({table})")
            existing_columns = {row[1] for row in result.fetchall()}
            
            invalid_columns = set(index.columns) - existing_columns
            if invalid_columns:
                raise ValueError(
                    f"Columns {invalid_columns} do not exist in table '{table}'"
                )
            
            # Build and execute CREATE INDEX statement
            unique_clause = "UNIQUE " if index.unique else ""
            if_not_exists_clause = "IF NOT EXISTS " if if_not_exists else ""
            column_list = ", ".join(index.columns)
            
            sql = f"CREATE {unique_clause}INDEX {if_not_exists_clause}{index.name} ON {table} ({column_list})"
            
            try:
                result = conn.execute(sql)
                conn.commit()
            except sqlite3.Error as e:
                if "already exists" in str(e):
                    if not if_not_exists:
                        raise ValueError(f"Index '{index.name}' already exists")
                else:
                    raise
        
        # Track the change
        self._track_change(
            ChangeType.CREATE_INDEX,
            index.name,
            {"table": table, "columns": index.columns, "unique": index.unique}
        )
        
        return index.name

    def drop_index(self, name: str, if_exists: bool = True) -> None:
        """Drop an index.

        Args:
            name: Index name
            if_exists: Whether to use IF EXISTS clause

        Raises:
            ValueError: If index doesn't exist and if_exists is False
        """
        # Get connection to main tenant database (indexes are branch-level)
        db_path = get_tenant_db_path(
            self.project_dir, self.database, self.branch, "main"
        )
        
        with DatabaseConnection(db_path) as conn:
            
            # Check if index exists
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
                [name]
            )
            exists = result.fetchone() is not None
            
            if not exists and not if_exists:
                raise ValueError(f"Index '{name}' does not exist")
            
            if exists:
                if_exists_clause = "IF EXISTS " if if_exists else ""
                sql = f"DROP INDEX {if_exists_clause}{name}"
                
                result = conn.execute(sql)
                conn.commit()
                
                # Track the change
                self._track_change(ChangeType.DROP_INDEX, name, {})

    def list_indexes(self, table: Optional[str] = None) -> List[Dict[str, Any]]:
        """List indexes for a table or all tables.

        Args:
            table: Optional table name to filter indexes

        Returns:
            List of index information dictionaries
        """
        # Get connection to main tenant database (indexes are branch-level)
        db_path = get_tenant_db_path(
            self.project_dir, self.database, self.branch, "main"
        )
        
        indexes = []
        
        with DatabaseConnection(db_path) as conn:
            
            # Get all indexes (excluding SQLite internal indexes)
            if table:
                result = conn.execute(
                    """
                    SELECT name, tbl_name, sql 
                    FROM sqlite_master 
                    WHERE type='index' 
                    AND tbl_name=? 
                    AND sql IS NOT NULL
                    """,
                    [table]
                )
            else:
                result = conn.execute(
                    """
                    SELECT name, tbl_name, sql 
                    FROM sqlite_master 
                    WHERE type='index' 
                    AND sql IS NOT NULL
                    """
                )
            
            for row in result.fetchall():
                index_name, table_name, sql = row
                
                # Parse unique from SQL
                is_unique = "CREATE UNIQUE INDEX" in sql.upper()
                
                # Get indexed columns
                pragma_result = conn.execute(f"PRAGMA index_info({index_name})")
                columns = [info[2] for info in pragma_result.fetchall()]
                
                indexes.append({
                    "name": index_name,
                    "table": table_name,
                    "columns": columns,
                    "unique": is_unique,
                    "sql": sql
                })
        
        return indexes

    def get_index_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a specific index.

        Args:
            name: Index name

        Returns:
            Dictionary with index information

        Raises:
            ValueError: If index doesn't exist
        """
        # Get connection to main tenant database (indexes are branch-level)
        db_path = get_tenant_db_path(
            self.project_dir, self.database, self.branch, "main"
        )
        
        with DatabaseConnection(db_path) as conn:
            
            # Get index info
            result = conn.execute(
                """
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type='index' 
                AND name=?
                """,
                [name]
            )
            
            row = result.fetchone()
            if not row:
                raise ValueError(f"Index '{name}' does not exist")
            
            index_name, table_name, sql = row
            
            # Parse unique from SQL
            is_unique = "CREATE UNIQUE INDEX" in (sql or "").upper()
            
            # Get indexed columns with more details
            pragma_result = conn.execute(f"PRAGMA index_info({index_name})")
            columns_info = []
            for info in pragma_result.fetchall():
                columns_info.append({
                    "position": info[0],
                    "column_id": info[1],
                    "column_name": info[2]
                })
            
            # Get index statistics
            xinfo_result = conn.execute(f"PRAGMA index_xinfo({index_name})")
            xinfo_result.fetchall()
            
            return {
                "name": index_name,
                "table": table_name,
                "columns": [col["column_name"] for col in columns_info],
                "columns_info": columns_info,
                "unique": is_unique,
                "sql": sql,
                "partial": sql and "WHERE" in sql.upper() if sql else False
            }

    def _track_change(
        self, change_type: ChangeType, entity_name: str, metadata: Dict[str, Any]
    ) -> None:
        """Track a change for this branch.

        Args:
            change_type: Type of change
            entity_name: Name of the entity being changed
            metadata: Additional metadata about the change
        """
        # Import here to avoid circular dependency
        from cinchdb.managers.change_tracker import ChangeTracker
        
        tracker = ChangeTracker(self.project_dir, self.database, self.branch)
        
        change = Change(
            id=str(uuid.uuid4()),
            type=change_type,
            entity_type="index",
            entity_name=entity_name,
            branch=self.branch,
            metadata=metadata,
            applied=True,
            created_at=datetime.now(timezone.utc),
        )
        
        tracker.add_change(change)
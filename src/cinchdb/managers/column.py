"""Column management for CinchDB."""

from pathlib import Path
from typing import List

from cinchdb.models import Column, Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.maintenance import check_maintenance_mode
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.table import TableManager


class ColumnManager:
    """Manages columns within tables."""
    
    # Protected column names that cannot be modified
    PROTECTED_COLUMNS = {"id", "created_at", "updated_at"}
    
    def __init__(self, project_root: Path, database: str, branch: str, tenant: str = "main"):
        """Initialize column manager.
        
        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
            tenant: Tenant name (default: main)
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.db_path = get_tenant_db_path(project_root, database, branch, tenant)
        self.change_tracker = ChangeTracker(project_root, database, branch)
        self.table_manager = TableManager(project_root, database, branch, tenant)
    
    def list_columns(self, table_name: str) -> List[Column]:
        """List all columns in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of Column objects
            
        Raises:
            ValueError: If table doesn't exist
        """
        table = self.table_manager.get_table(table_name)
        return table.columns
    
    def add_column(self, table_name: str, column: Column) -> None:
        """Add a column to a table.
        
        Args:
            table_name: Name of the table
            column: Column to add
            
        Raises:
            ValueError: If table doesn't exist, column exists, or uses protected name
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Validate table exists
        if not self.table_manager._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Check for protected column names
        if column.name in self.PROTECTED_COLUMNS:
            raise ValueError(f"Column name '{column.name}' is protected and cannot be used")
        
        # Check if column already exists
        existing_columns = self.list_columns(table_name)
        if any(col.name == column.name for col in existing_columns):
            raise ValueError(f"Column '{column.name}' already exists in table '{table_name}'")
        
        # Build ALTER TABLE SQL
        col_def = f"{column.name} {column.type}"
        if not column.nullable:
            col_def += " NOT NULL"
        if column.default is not None:
            col_def += f" DEFAULT {column.default}"
        
        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
        
        # Track the change first (as unapplied)
        change = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name=column.name,
            branch=self.branch,
            details={
                "table": table_name,
                "column_def": column.model_dump()
            },
            sql=alter_sql
        )
        self.change_tracker.add_change(change)
        
        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier
        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)
    
    def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column from a table.
        
        SQLite doesn't support DROP COLUMN directly, so we need to:
        1. Create a new table without the column
        2. Copy data from old table
        3. Drop old table
        4. Rename new table
        
        Args:
            table_name: Name of the table
            column_name: Name of column to drop
            
        Raises:
            ValueError: If table/column doesn't exist or column is protected
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Validate table exists
        if not self.table_manager._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Check if column is protected
        if column_name in self.PROTECTED_COLUMNS:
            raise ValueError(f"Cannot drop protected column '{column_name}'")
        
        # Get existing columns
        existing_columns = self.list_columns(table_name)
        if not any(col.name == column_name for col in existing_columns):
            raise ValueError(f"Column '{column_name}' does not exist in table '{table_name}'")
        
        # Filter out the column to drop
        new_columns = [col for col in existing_columns if col.name != column_name]
        
        # Build SQL statements
        temp_table = f"{table_name}_temp"
        
        # Create new table without the column
        col_defs = []
        for col in new_columns:
            col_def = f"{col.name} {col.type}"
            if col.primary_key:
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)
        
        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"
        
        # Column names for copying
        col_names = [col.name for col in new_columns]
        col_list = ", ".join(col_names)
        copy_sql = f"INSERT INTO {temp_table} ({col_list}) SELECT {col_list} FROM {table_name}"
        drop_sql = f"DROP TABLE {table_name}"
        rename_sql = f"ALTER TABLE {temp_table} RENAME TO {table_name}"
        
        # Track the change with individual SQL statements
        change = Change(
            type=ChangeType.DROP_COLUMN,
            entity_type="column",
            entity_name=column_name,
            branch=self.branch,
            details={
                "table": table_name,
                "temp_table": temp_table,
                "statements": [
                    ("CREATE", create_sql),
                    ("COPY", copy_sql),
                    ("DROP", drop_sql),
                    ("RENAME", rename_sql)
                ],
                "remaining_columns": [col.model_dump() for col in new_columns]
            },
            sql=f"-- DROP COLUMN {column_name} FROM {table_name}"
        )
        self.change_tracker.add_change(change)
        
        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier
        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)
    
    def rename_column(self, table_name: str, old_name: str, new_name: str) -> None:
        """Rename a column in a table.
        
        Args:
            table_name: Name of the table
            old_name: Current column name
            new_name: New column name
            
        Raises:
            ValueError: If table/column doesn't exist or names are protected
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Validate table exists
        if not self.table_manager._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        # Check if old column is protected
        if old_name in self.PROTECTED_COLUMNS:
            raise ValueError(f"Cannot rename protected column '{old_name}'")
        
        # Check if new name is protected
        if new_name in self.PROTECTED_COLUMNS:
            raise ValueError(f"Cannot use protected name '{new_name}'")
        
        # Get existing columns
        existing_columns = self.list_columns(table_name)
        
        # Check old column exists
        if not any(col.name == old_name for col in existing_columns):
            raise ValueError(f"Column '{old_name}' does not exist in table '{table_name}'")
        
        # Check new name doesn't exist
        if any(col.name == new_name for col in existing_columns):
            raise ValueError(f"Column '{new_name}' already exists in table '{table_name}'")
        
        # Try using ALTER TABLE RENAME COLUMN (SQLite 3.25.0+)
        rename_sql = f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"
        
        # Check if we need fallback SQL for older SQLite versions
        fallback_sqls = self._get_rename_column_fallback_sqls(table_name, old_name, new_name, existing_columns)
        
        # Track the change
        change = Change(
            type=ChangeType.RENAME_COLUMN,
            entity_type="column",
            entity_name=new_name,
            branch=self.branch,
            details={
                "table": table_name,
                "old_name": old_name,
                "fallback_sqls": fallback_sqls
            },
            sql=rename_sql
        )
        self.change_tracker.add_change(change)
        
        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier
        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)
    
    def get_column_info(self, table_name: str, column_name: str) -> Column:
        """Get information about a specific column.
        
        Args:
            table_name: Name of the table
            column_name: Name of the column
            
        Returns:
            Column object
            
        Raises:
            ValueError: If table/column doesn't exist
        """
        columns = self.list_columns(table_name)
        
        for col in columns:
            if col.name == column_name:
                return col
        
        raise ValueError(f"Column '{column_name}' does not exist in table '{table_name}'")
    
    def _get_rename_column_fallback_sqls(self, table_name: str, old_name: str, new_name: str, 
                                        existing_columns: List[Column]) -> dict:
        """Generate fallback SQL for rename column operation (for older SQLite versions).
        
        Args:
            table_name: Name of the table
            old_name: Current column name
            new_name: New column name
            existing_columns: List of existing columns
            
        Returns:
            Dictionary with all SQL statements needed for fallback
        """
        temp_table = f"{table_name}_temp"
        
        # Build new column list with renamed column
        new_columns = []
        old_col_names = []
        new_col_names = []
        
        for col in existing_columns:
            old_col_names.append(col.name)
            if col.name == old_name:
                new_col = Column(
                    name=new_name,
                    type=col.type,
                    nullable=col.nullable,
                    default=col.default,
                    primary_key=col.primary_key,
                    unique=col.unique
                )
                new_columns.append(new_col)
                new_col_names.append(new_name)
            else:
                new_columns.append(col)
                new_col_names.append(col.name)
        
        # Create new table
        col_defs = []
        for col in new_columns:
            col_def = f"{col.name} {col.type}"
            if col.primary_key:
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)
        
        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"
        
        # Copy data with column mapping
        old_list = ", ".join(old_col_names)
        new_list = ", ".join(new_col_names)
        copy_sql = f"INSERT INTO {temp_table} ({new_list}) SELECT {old_list} FROM {table_name}"
        drop_sql = f"DROP TABLE {table_name}"
        rename_sql = f"ALTER TABLE {temp_table} RENAME TO {table_name}"
        
        return {
            "temp_table": temp_table,
            "create_sql": create_sql,
            "copy_sql": copy_sql,
            "drop_sql": drop_sql,
            "rename_sql": rename_sql,
            "new_columns": [col.model_dump() for col in new_columns]
        }
    
    def _rename_column_via_recreate(self, table_name: str, old_name: str, new_name: str, 
                                   existing_columns: List[Column]) -> None:
        """Rename column by recreating the table (for older SQLite versions).
        
        Args:
            table_name: Name of the table
            old_name: Current column name
            new_name: New column name
            existing_columns: List of existing columns
        """
        temp_table = f"{table_name}_temp"
        
        # Build new column list with renamed column
        new_columns = []
        old_col_names = []
        new_col_names = []
        
        for col in existing_columns:
            old_col_names.append(col.name)
            if col.name == old_name:
                new_col = Column(
                    name=new_name,
                    type=col.type,
                    nullable=col.nullable,
                    default=col.default,
                    primary_key=col.primary_key,
                    unique=col.unique
                )
                new_columns.append(new_col)
                new_col_names.append(new_name)
            else:
                new_columns.append(col)
                new_col_names.append(col.name)
        
        # Create new table
        col_defs = []
        for col in new_columns:
            col_def = f"{col.name} {col.type}"
            if col.primary_key:
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)
        
        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"
        
        with DatabaseConnection(self.db_path) as conn:
            # Create new table
            conn.execute(create_sql)
            
            # Copy data with column mapping
            old_list = ", ".join(old_col_names)
            new_list = ", ".join(new_col_names)
            copy_sql = f"INSERT INTO {temp_table} ({new_list}) SELECT {old_list} FROM {table_name}"
            conn.execute(copy_sql)
            
            # Drop old table
            conn.execute(f"DROP TABLE {table_name}")
            
            # Rename new table
            conn.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
            conn.commit()
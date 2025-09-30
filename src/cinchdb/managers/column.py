"""Column management for CinchDB."""

from typing import List, Any, Optional

from cinchdb.models import Column, Change, ChangeType, SchemaSnapshot
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance_utils import check_maintenance_mode
from cinchdb.managers.base import BaseManager, ConnectionContext
from cinchdb.utils.type_utils import normalize_type


class ColumnManager(BaseManager):
    """Manages columns within tables."""

    # Protected column names that cannot be modified
    PROTECTED_COLUMNS = {"id", "created_at", "updated_at"}

    def __init__(self, context: ConnectionContext):
        """Initialize column manager.

        Args:
            context: ConnectionContext with all connection parameters
        """
        super().__init__(context)

        # Lazy-loaded table manager
        self._table_manager = None

    @property
    def table_manager(self):
        """Lazy load table manager to avoid circular dependencies."""
        if self._table_manager is None:
            from cinchdb.managers.table import TableManager
            self._table_manager = TableManager(self.context)
        return self._table_manager

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
            raise ValueError(
                f"Column name '{column.name}' is protected and cannot be used"
            )

        # Check if column already exists
        existing_columns = self.list_columns(table_name)
        if any(col.name == column.name for col in existing_columns):
            raise ValueError(
                f"Column '{column.name}' already exists in table '{table_name}'"
            )

        # Normalize column type
        normalized_column = Column(
            name=column.name,
            type=normalize_type(column.type),
            nullable=column.nullable,
            default=column.default,
            unique=column.unique,
            foreign_key=column.foreign_key
        )

        # Build ALTER TABLE SQL
        # Handle BOOLEAN type specially (store as INTEGER with CHECK constraint)
        if normalized_column.type == "BOOLEAN":
            col_def = f"{normalized_column.name} INTEGER CHECK ({normalized_column.name} IN (0, 1))"
        else:
            col_def = f"{normalized_column.name} {normalized_column.type}"

        if not normalized_column.nullable:
            col_def += " NOT NULL"
        if normalized_column.default is not None:
            col_def += f" DEFAULT {normalized_column.default}"

        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"

        # Build schema snapshot: get current schema + add this column
        schema_snapshot = None
        if self.change_tracker:
            # Get existing schema from latest snapshot
            existing_snapshot = self.change_tracker.metadata_db.get_latest_schema_snapshot(
                self.change_tracker.branch_id
            )
            if existing_snapshot:
                snapshot = existing_snapshot.deep_copy()
            else:
                snapshot = SchemaSnapshot()

            # Add this column to the table in the snapshot
            if snapshot.has_table(table_name):
                snapshot.add_column(table_name, normalized_column)
            else:
                # Table exists but not in snapshot yet (backwards compat)
                # Get current table schema and add it
                table = self.table_manager.get_table(table_name)
                snapshot.add_table(table_name, table.columns)
                snapshot.add_column(table_name, normalized_column)

            schema_snapshot = snapshot

        # Track the change first (as unapplied)
        change = Change(
            type=ChangeType.ADD_COLUMN,
            entity_type="column",
            entity_name=normalized_column.name,
            branch=self.branch,
            details={"table": table_name, "column_def": normalized_column.model_dump()},
            sql=alter_sql,
        )
        if self.change_tracker:
            self.change_tracker.add_change(change, schema_snapshot=schema_snapshot)

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
            raise ValueError(
                f"Column '{column_name}' does not exist in table '{table_name}'"
            )

        # Filter out the column to drop
        new_columns = [col for col in existing_columns if col.name != column_name]

        # Build SQL statements
        temp_table = f"{table_name}_temp"

        # Create new table without the column
        col_defs = []
        for col in new_columns:
            col_def = f"{col.name} {col.type}"
            # Primary keys are handled at table creation, not as a column attribute
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)

        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"

        # Column names for copying
        col_names = [col.name for col in new_columns]
        col_list = ", ".join(col_names)
        copy_sql = (
            f"INSERT INTO {temp_table} ({col_list}) SELECT {col_list} FROM {table_name}"
        )
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
                    ("RENAME", rename_sql),
                ],
                "remaining_columns": [col.model_dump() for col in new_columns],
            },
            sql=f"-- DROP COLUMN {column_name} FROM {table_name}",
        )
        if self.change_tracker:
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
            raise ValueError(
                f"Column '{old_name}' does not exist in table '{table_name}'"
            )

        # Check new name doesn't exist
        if any(col.name == new_name for col in existing_columns):
            raise ValueError(
                f"Column '{new_name}' already exists in table '{table_name}'"
            )

        # Try using ALTER TABLE RENAME COLUMN (SQLite 3.25.0+)
        rename_sql = f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"

        # Check if we need fallback SQL for older SQLite versions
        fallback_sqls = self._get_rename_column_fallback_sqls(
            table_name, old_name, new_name, existing_columns
        )

        # Track the change
        change = Change(
            type=ChangeType.RENAME_COLUMN,
            entity_type="column",
            entity_name=new_name,
            branch=self.branch,
            details={
                "table": table_name,
                "old_name": old_name,
                "fallback_sqls": fallback_sqls,
            },
            sql=rename_sql,
        )
        if self.change_tracker:
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

        raise ValueError(
            f"Column '{column_name}' does not exist in table '{table_name}'"
        )

    def _get_rename_column_fallback_sqls(
        self,
        table_name: str,
        old_name: str,
        new_name: str,
        existing_columns: List[Column],
    ) -> dict:
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
                    unique=col.unique,
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
            # Primary keys are handled at table creation, not as a column attribute
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)

        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"

        # Copy data with column mapping
        old_list = ", ".join(old_col_names)
        new_list = ", ".join(new_col_names)
        copy_sql = (
            f"INSERT INTO {temp_table} ({new_list}) SELECT {old_list} FROM {table_name}"
        )
        drop_sql = f"DROP TABLE {table_name}"
        rename_sql = f"ALTER TABLE {temp_table} RENAME TO {table_name}"

        return {
            "temp_table": temp_table,
            "create_sql": create_sql,
            "copy_sql": copy_sql,
            "drop_sql": drop_sql,
            "rename_sql": rename_sql,
            "new_columns": [col.model_dump() for col in new_columns],
        }

    def _rename_column_via_recreate(
        self,
        table_name: str,
        old_name: str,
        new_name: str,
        existing_columns: List[Column],
    ) -> None:
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
                    unique=col.unique,
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
            # Primary keys are handled at table creation, not as a column attribute
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)

        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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

    def alter_column_nullable(
        self,
        table_name: str,
        column_name: str,
        nullable: bool,
        fill_value: Optional[Any] = None,
    ) -> None:
        """Change the nullable constraint on a column.

        Args:
            table_name: Name of the table
            column_name: Name of the column to modify
            nullable: Whether the column should allow NULL values
            fill_value: Value to use for existing NULL values when making column NOT NULL

        Raises:
            ValueError: If table/column doesn't exist or column is protected
            ValueError: If making NOT NULL and column has NULL values without fill_value
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Validate table exists
        if not self.table_manager._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")

        # Check if column is protected
        if column_name in self.PROTECTED_COLUMNS:
            raise ValueError(f"Cannot modify protected column '{column_name}'")

        # Get existing columns
        existing_columns = self.list_columns(table_name)
        column_found = False
        old_column = None

        for col in existing_columns:
            if col.name == column_name:
                column_found = True
                old_column = col
                break

        if not column_found:
            raise ValueError(
                f"Column '{column_name}' does not exist in table '{table_name}'"
            )

        # Check if already has the desired nullable state
        if old_column.nullable == nullable:
            raise ValueError(
                f"Column '{column_name}' is already {'nullable' if nullable else 'NOT NULL'}"
            )

        # If making NOT NULL, check for NULL values
        if not nullable:
            with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} IS NULL"
                )
                null_count = cursor.fetchone()[0]

                if null_count > 0 and fill_value is None:
                    raise ValueError(
                        f"Column '{column_name}' has {null_count} NULL values. "
                        "Provide a fill_value to replace them."
                    )

        # Build SQL statements for table recreation
        temp_table = f"{table_name}_temp"

        # Create new table with modified column
        col_defs = []
        for col in existing_columns:
            col_def = f"{col.name} {col.type}"
            # Primary keys are handled at table creation, not as a column attribute
            # Apply nullable change to target column
            if col.name == column_name:
                if not nullable:
                    col_def += " NOT NULL"
            else:
                # Keep original nullable state for other columns
                if not col.nullable:
                    col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            col_defs.append(col_def)

        create_sql = f"CREATE TABLE {temp_table} ({', '.join(col_defs)})"

        # Column names for copying
        col_names = [col.name for col in existing_columns]
        col_list = ", ".join(col_names)

        # Build copy SQL with COALESCE if needed
        if not nullable and fill_value is not None:
            # Build select list with COALESCE for the target column
            select_cols = []
            for col_name in col_names:
                if col_name == column_name:
                    # Properly quote string values
                    if isinstance(fill_value, str):
                        select_cols.append(f"COALESCE({col_name}, '{fill_value}')")
                    else:
                        select_cols.append(f"COALESCE({col_name}, {fill_value})")
                else:
                    select_cols.append(col_name)
            select_list = ", ".join(select_cols)
            copy_sql = f"INSERT INTO {temp_table} ({col_list}) SELECT {select_list} FROM {table_name}"
        else:
            copy_sql = f"INSERT INTO {temp_table} ({col_list}) SELECT {col_list} FROM {table_name}"

        drop_sql = f"DROP TABLE {table_name}"
        rename_sql = f"ALTER TABLE {temp_table} RENAME TO {table_name}"

        # Track the change with individual SQL statements
        change = Change(
            type=ChangeType.ALTER_COLUMN_NULLABLE,
            entity_type="column",
            entity_name=column_name,
            branch=self.branch,
            details={
                "table": table_name,
                "nullable": nullable,
                "fill_value": fill_value,
                "old_nullable": old_column.nullable,
                "temp_table": temp_table,
                "statements": [
                    ("CREATE", create_sql),
                    ("COPY", copy_sql),
                    ("DROP", drop_sql),
                    ("RENAME", rename_sql),
                ],
            },
            sql=f"-- ALTER COLUMN {column_name} {'NULL' if nullable else 'NOT NULL'}",
        )

        # Get updated schema snapshot after this change
        schema_snapshot = None
        if self.change_tracker:
            # Build updated schema by getting all tables and updating the modified column
            snapshot = SchemaSnapshot()
            tables = self.table_manager.list_tables(include_system=False)
            for tbl in tables:
                if tbl.name == table_name:
                    # Update the nullable value for the target column in the snapshot
                    updated_columns = []
                    for col in existing_columns:
                        if col.name == column_name:
                            # Create updated column with new nullable value
                            updated_col = Column(
                                name=col.name,
                                type=col.type,
                                nullable=nullable,
                                default=col.default,
                                unique=col.unique,
                                foreign_key=col.foreign_key
                            )
                            updated_columns.append(updated_col)
                        else:
                            updated_columns.append(col)
                    snapshot.add_table(table_name, updated_columns)
                else:
                    # Keep other tables as-is
                    snapshot.add_table(tbl.name, tbl.columns)

            schema_snapshot = snapshot
            self.change_tracker.add_change(change, schema_snapshot=schema_snapshot)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

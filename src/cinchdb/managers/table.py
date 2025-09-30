"""Table management for CinchDB."""

from typing import List, Optional, TYPE_CHECKING

from cinchdb.models import Table, Column, Change, ChangeType, SchemaSnapshot
from cinchdb.managers.base import BaseManager, ConnectionContext

if TYPE_CHECKING:
    from cinchdb.models import Index
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance_utils import check_maintenance_mode
from cinchdb.utils.name_validator import validate_name


class TableManager(BaseManager):
    """Manages tables within a database."""

    # Protected column names that users cannot use
    PROTECTED_COLUMNS = {"id", "created_at", "updated_at"}

    # Protected table name prefixes that users cannot use
    PROTECTED_TABLE_PREFIXES = ("__", "sqlite_")

    def list_tables(self, include_system: bool = False) -> List[Table]:
        """List all tables in the tenant.

        Args:
            include_system: If True, include system tables (sqlite_* and __*)

        Returns:
            List of Table objects
        """
        tables = []

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            # Get all tables first, then filter in Python (more reliable than SQL LIKE)
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
                """
            )

            # Filter system tables unless requested
            all_table_names = [row["name"] for row in cursor.fetchall()]
            if include_system:
                filtered_table_names = all_table_names
            else:
                filtered_table_names = [
                    name for name in all_table_names
                    if not name.startswith('sqlite_') and not name.startswith('__')
                ]

            for table_name in filtered_table_names:
                table = self.get_table(table_name)
                tables.append(table)

        return tables

    def create_table(self, table_name: str, columns: List[Column], indexes: Optional[List["Index"]] = None) -> Table:
        """Create a new table with optional foreign key constraints and indexes.

        Args:
            table_name: Name of the table
            columns: List of Column objects defining the schema
            indexes: Optional list of Index objects to create on the table

        Returns:
            Created Table object

        Raises:
            ValueError: If table already exists, uses protected column names,
                       or has invalid foreign key references
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Validate table name doesn't use protected prefixes (check this FIRST)
        for prefix in self.PROTECTED_TABLE_PREFIXES:
            if table_name.startswith(prefix):
                raise ValueError(
                    f"Table name '{table_name}' is not allowed. "
                    f"Table names cannot start with '{prefix}' as these are reserved for system use."
                )
        
        # Validate table name format (after checking protected prefixes)
        validate_name(table_name, "table")

        # Validate table doesn't exist
        if self._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' already exists")

        # Check for protected column names and validate column names
        for column in columns:
            # Validate column name format
            validate_name(column.name, "column")
            
            if column.name in self.PROTECTED_COLUMNS:
                raise ValueError(
                    f"Column name '{column.name}' is protected and cannot be used"
                )

        # Validate foreign key references
        foreign_key_constraints = []
        for column in columns:
            if column.foreign_key:
                fk = column.foreign_key

                # Validate referenced table exists
                if not self._table_exists(fk.table):
                    raise ValueError(
                        f"Foreign key reference to non-existent table: '{fk.table}'"
                    )

                # Validate referenced column exists
                ref_table = self.get_table(fk.table)
                ref_col_names = [col.name for col in ref_table.columns]
                if fk.column not in ref_col_names:
                    raise ValueError(
                        f"Foreign key reference to non-existent column: '{fk.table}.{fk.column}'"
                    )

                # Build foreign key constraint
                fk_constraint = (
                    f"FOREIGN KEY ({column.name}) REFERENCES {fk.table}({fk.column})"
                )
                if fk.on_delete != "RESTRICT":
                    fk_constraint += f" ON DELETE {fk.on_delete}"
                if fk.on_update != "RESTRICT":
                    fk_constraint += f" ON UPDATE {fk.on_update}"
                foreign_key_constraints.append(fk_constraint)

        # Build automatic columns (id is always the primary key and unique)
        auto_columns = [
            Column(name="id", type="TEXT", nullable=False, unique=True),
            Column(name="created_at", type="TEXT", nullable=False),
            Column(name="updated_at", type="TEXT", nullable=True),
        ]

        # Combine all columns
        all_columns = auto_columns + columns

        # Build CREATE TABLE SQL
        sql_parts = []
        for col in all_columns:
            col_def = f"{col.name} {col.type}"

            # id column is always the primary key
            if col.name == "id":
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            if col.unique and col.name != "id":  # id is already unique via PRIMARY KEY
                col_def += " UNIQUE"

            sql_parts.append(col_def)

        # Add foreign key constraints
        sql_parts.extend(foreign_key_constraints)

        create_sql = f"CREATE TABLE {table_name} ({', '.join(sql_parts)})"

        # Track the change first (as unapplied)
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name=table_name,
            branch=self.branch,
            details={"columns": [col.model_dump() for col in all_columns]},
            sql=create_sql,
        )

        # Build schema snapshot with this new table
        schema_snapshot = None
        if self.change_tracker:
            snapshot = SchemaSnapshot()
            # Get existing tables
            existing_tables = self.list_tables(include_system=False)
            for tbl in existing_tables:
                snapshot.add_table(tbl.name, tbl.columns)
            # Add the new table
            snapshot.add_table(table_name, all_columns)
            schema_snapshot = snapshot

            self.change_tracker.add_change(change, schema_snapshot=schema_snapshot)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

        # Create indexes if specified
        if indexes:
            from cinchdb.managers.index import IndexManager
            index_manager = IndexManager(self.context)
            
            for index in indexes:
                index_manager.create_index(
                    table=table_name,
                    columns=index.columns,
                    name=index.name,
                    unique=index.unique,
                    if_not_exists=True
                )

        # Return the created table
        return Table(
            name=table_name,
            database=self.database,
            branch=self.branch,
            columns=all_columns,
        )

    def get_table(self, table_name: str) -> Table:
        """Get table information.

        Args:
            table_name: Name of the table

        Returns:
            Table object with schema information

        Raises:
            ValueError: If table doesn't exist
        """
        if not self._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")

        # Get schema from snapshot - this should ALWAYS be available
        if not self.change_tracker:
            raise RuntimeError(
                f"Cannot get table schema: change_tracker not initialized. "
                f"This indicates a critical bug in the metadata system."
            )

        schema_snapshot = self.change_tracker.metadata_db.get_latest_schema_snapshot(
            self.change_tracker.branch_id
        )

        if not schema_snapshot:
            raise RuntimeError(
                f"No schema snapshot found for branch. "
                f"This indicates a critical bug in the metadata/change tracking system."
            )

        if not schema_snapshot.has_table(table_name):
            raise RuntimeError(
                f"Table '{table_name}' exists in database but not in schema snapshot. "
                f"This indicates schema snapshot is out of sync - a critical bug."
            )

        # Build columns from snapshot (preserves BOOLEAN and other type info)
        columns = schema_snapshot.get_table_schema(table_name)

        return Table(
            name=table_name, database=self.database, branch=self.branch, columns=columns
        )

    def delete_table(self, table_name: str) -> None:
        """Delete a table.

        Args:
            table_name: Name of the table to delete

        Raises:
            ValueError: If table doesn't exist
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        if not self._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")

        # Build DROP TABLE SQL
        drop_sql = f"DROP TABLE {table_name}"

        # Track the change
        change = Change(
            type=ChangeType.DROP_TABLE,
            entity_type="table",
            entity_name=table_name,
            branch=self.branch,
            sql=drop_sql,
        )
        if self.change_tracker:
            self.change_tracker.add_change(change)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

    def copy_table(
        self, source_table: str, target_table: str, copy_data: bool = True
    ) -> Table:
        """Copy a table to a new table.

        Args:
            source_table: Name of the source table
            target_table: Name of the target table
            copy_data: Whether to copy data (default: True)

        Returns:
            Created Table object

        Raises:
            ValueError: If source doesn't exist or target already exists
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)
        
        # Validate target table name doesn't use protected prefixes (check this FIRST)
        for prefix in self.PROTECTED_TABLE_PREFIXES:
            if target_table.startswith(prefix):
                raise ValueError(
                    f"Table name '{target_table}' is not allowed. "
                    f"Table names cannot start with '{prefix}' as these are reserved for system use."
                )
        
        # Validate target table name format (after checking protected prefixes)
        validate_name(target_table, "table")

        if not self._table_exists(source_table):
            raise ValueError(f"Source table '{source_table}' does not exist")

        if self._table_exists(target_table):
            raise ValueError(f"Target table '{target_table}' already exists")

        # Get source table structure
        source = self.get_table(source_table)

        # Create SQL for new table
        sql_parts = []
        for col in source.columns:
            col_def = f"{col.name} {col.type}"

            # id column is always the primary key
            if col.name == "id":
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"

            sql_parts.append(col_def)

        create_sql = f"CREATE TABLE {target_table} ({', '.join(sql_parts)})"

        # Build copy data SQL if requested
        copy_sql = None
        if copy_data:
            col_names = [col.name for col in source.columns]
            col_list = ", ".join(col_names)
            copy_sql = f"INSERT INTO {target_table} ({col_list}) SELECT {col_list} FROM {source_table}"

        # Track the change
        change = Change(
            type=ChangeType.CREATE_TABLE,
            entity_type="table",
            entity_name=target_table,
            branch=self.branch,
            details={
                "columns": [col.model_dump() for col in source.columns],
                "copied_from": source_table,
                "with_data": copy_data,
                "copy_sql": copy_sql,
            },
            sql=create_sql,
        )

        # Build schema snapshot with the copied table
        schema_snapshot = None
        if self.change_tracker:
            snapshot = SchemaSnapshot()
            # Get existing tables
            existing_tables = self.list_tables(include_system=False)
            for tbl in existing_tables:
                snapshot.add_table(tbl.name, tbl.columns)
            # Add the new copied table
            snapshot.add_table(target_table, source.columns)
            schema_snapshot = snapshot

            self.change_tracker.add_change(change, schema_snapshot=schema_snapshot)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

        # Return the new table
        return Table(
            name=target_table,
            database=self.database,
            branch=self.branch,
            columns=source.columns,
        )

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists using schema snapshot.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists
        """
        if not self.change_tracker:
            # If no change tracker, we can't check the snapshot
            # This should only happen during initialization
            with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,),
                )
                return cursor.fetchone() is not None

        # Use schema snapshot for consistency
        schema_snapshot = self.change_tracker.metadata_db.get_latest_schema_snapshot(
            self.change_tracker.branch_id
        )
        return schema_snapshot is not None and schema_snapshot.has_table(table_name)

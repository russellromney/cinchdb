"""Table management for CinchDB."""

from pathlib import Path
from typing import List

from cinchdb.models import Table, Column, Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.maintenance import check_maintenance_mode
from cinchdb.managers.change_tracker import ChangeTracker
from cinchdb.managers.tenant import TenantManager


class TableManager:
    """Manages tables within a database."""

    # Protected column names that users cannot use
    PROTECTED_COLUMNS = {"id", "created_at", "updated_at"}

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main"
    ):
        """Initialize table manager.

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
        self.tenant_manager = TenantManager(project_root, database, branch)

    def list_tables(self) -> List[Table]:
        """List all tables in the tenant.

        Returns:
            List of Table objects
        """
        tables = []

        with DatabaseConnection(self.db_path) as conn:
            # Get all user tables (exclude sqlite internal tables)
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )

            for row in cursor.fetchall():
                table = self.get_table(row["name"])
                tables.append(table)

        return tables

    def create_table(self, table_name: str, columns: List[Column]) -> Table:
        """Create a new table with optional foreign key constraints.

        Args:
            table_name: Name of the table
            columns: List of Column objects defining the schema

        Returns:
            Created Table object

        Raises:
            ValueError: If table already exists, uses protected column names,
                       or has invalid foreign key references
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Validate table doesn't exist
        if self._table_exists(table_name):
            raise ValueError(f"Table '{table_name}' already exists")

        # Check for protected column names
        for column in columns:
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

        # Build automatic columns
        auto_columns = [
            Column(name="id", type="TEXT", primary_key=True, nullable=False),
            Column(name="created_at", type="TEXT", nullable=False),
            Column(name="updated_at", type="TEXT", nullable=True),
        ]

        # Combine all columns
        all_columns = auto_columns + columns

        # Build CREATE TABLE SQL
        sql_parts = []
        for col in all_columns:
            col_def = f"{col.name} {col.type}"

            if col.primary_key:
                col_def += " PRIMARY KEY"
            if not col.nullable:
                col_def += " NOT NULL"
            if col.default is not None:
                col_def += f" DEFAULT {col.default}"
            if col.unique and not col.primary_key:
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
        self.change_tracker.add_change(change)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

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

        columns = []
        foreign_keys = {}

        with DatabaseConnection(self.db_path) as conn:
            # Get foreign key information first
            fk_cursor = conn.execute(f"PRAGMA foreign_key_list({table_name})")
            for fk_row in fk_cursor.fetchall():
                from_col = fk_row["from"]
                to_table = fk_row["table"]
                to_col = fk_row["to"]
                on_update = fk_row["on_update"]
                on_delete = fk_row["on_delete"]

                # Create ForeignKeyRef
                from cinchdb.models import ForeignKeyRef

                foreign_keys[from_col] = ForeignKeyRef(
                    table=to_table,
                    column=to_col,
                    on_update=on_update,
                    on_delete=on_delete,
                )

            # Get column information
            cursor = conn.execute(f"PRAGMA table_info({table_name})")

            for row in cursor.fetchall():
                # Map SQLite types
                sqlite_type = row["type"].upper()
                if "INT" in sqlite_type:
                    col_type = "INTEGER"
                elif (
                    "REAL" in sqlite_type
                    or "FLOAT" in sqlite_type
                    or "DOUBLE" in sqlite_type
                ):
                    col_type = "REAL"
                elif "BLOB" in sqlite_type:
                    col_type = "BLOB"
                elif "NUMERIC" in sqlite_type:
                    col_type = "NUMERIC"
                else:
                    col_type = "TEXT"

                # Check if this column has a foreign key
                foreign_key = foreign_keys.get(row["name"])

                column = Column(
                    name=row["name"],
                    type=col_type,
                    nullable=(row["notnull"] == 0),
                    default=row["dflt_value"],
                    primary_key=(row["pk"] == 1),
                    foreign_key=foreign_key,
                )
                columns.append(column)

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

            if col.primary_key:
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
        self.change_tracker.add_change(change)

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
        """Check if a table exists.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists
        """
        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return cursor.fetchone() is not None

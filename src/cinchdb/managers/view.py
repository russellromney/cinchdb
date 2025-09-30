"""View/Model management for CinchDB."""

from typing import List

from cinchdb.managers.base import BaseManager, ConnectionContext
from cinchdb.models import View, Change, ChangeType
from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.maintenance_utils import check_maintenance_mode


class ViewModel(BaseManager):
    """Manages SQL views (models) in the database."""

    def __init__(self, context: ConnectionContext):
        """Initialize view manager.

        Args:
            context: ConnectionContext with all connection parameters
        """
        super().__init__(context)

    def list_views(self) -> List[View]:
        """List all views in the database.

        Returns:
            List of View objects
        """
        views = []

        with DatabaseConnection(self.db_path) as conn:
            # Get all views
            cursor = conn.execute(
                """
                SELECT name, sql FROM sqlite_master 
                WHERE type='view' 
                ORDER BY name
                """
            )

            for row in cursor.fetchall():
                view = View(
                    name=row["name"],
                    database=self.database,
                    branch=self.branch,
                    sql_statement=row["sql"],
                )
                views.append(view)

        return views

    def create_view(self, view_name: str, sql_statement: str) -> View:
        """Create a new view.

        Args:
            view_name: Name of the view
            sql_statement: SQL SELECT statement defining the view

        Returns:
            Created View object

        Raises:
            ValueError: If view already exists
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Check if view already exists
        if self._view_exists(view_name):
            raise ValueError(f"View '{view_name}' already exists")

        # Create the view
        create_sql = f"CREATE VIEW {view_name} AS {sql_statement}"

        # Track the change
        change = Change(
            type=ChangeType.CREATE_VIEW,
            entity_type="view",
            entity_name=view_name,
            branch=self.branch,
            details={"sql_statement": sql_statement},
            sql=create_sql,
        )
        if self.change_tracker:
            self.change_tracker.add_change(change)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

        # Return the created view
        return View(
            name=view_name,
            database=self.database,
            branch=self.branch,
            sql_statement=sql_statement,
        )

    def update_view(self, view_name: str, sql_statement: str) -> View:
        """Update an existing view's SQL.

        Args:
            view_name: Name of the view to update
            sql_statement: New SQL SELECT statement

        Returns:
            Updated View object

        Raises:
            ValueError: If view doesn't exist
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Check if view exists
        if not self._view_exists(view_name):
            raise ValueError(f"View '{view_name}' does not exist")

        # SQLite doesn't support CREATE OR REPLACE VIEW, so we need to drop and recreate
        create_sql = f"CREATE VIEW {view_name} AS {sql_statement}"

        # Track the change
        change = Change(
            type=ChangeType.UPDATE_VIEW,
            entity_type="view",
            entity_name=view_name,
            branch=self.branch,
            details={
                "sql_statement": sql_statement,
                "drop_sql": f"DROP VIEW {view_name}",
            },
            sql=create_sql,
        )
        if self.change_tracker:
            self.change_tracker.add_change(change)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

        # Return the updated view
        return View(
            name=view_name,
            database=self.database,
            branch=self.branch,
            sql_statement=sql_statement,
        )

    def delete_view(self, view_name: str) -> None:
        """Delete a view.

        Args:
            view_name: Name of the view to delete

        Raises:
            ValueError: If view doesn't exist
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Check if view exists
        if not self._view_exists(view_name):
            raise ValueError(f"View '{view_name}' does not exist")

        # Drop the view
        drop_sql = f"DROP VIEW {view_name}"

        # Track the change
        change = Change(
            type=ChangeType.DROP_VIEW,
            entity_type="view",
            entity_name=view_name,
            branch=self.branch,
            sql=drop_sql,
        )
        if self.change_tracker:
            self.change_tracker.add_change(change)

        # Apply to all tenants in the branch
        from cinchdb.managers.change_applier import ChangeApplier

        applier = ChangeApplier(self.project_root, self.database, self.branch)
        applier.apply_change(change.id)

    def get_view(self, view_name: str) -> View:
        """Get information about a specific view.

        Args:
            view_name: Name of the view

        Returns:
            View object

        Raises:
            ValueError: If view doesn't exist
        """
        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='view' AND name=?",
                (view_name,),
            )
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"View '{view_name}' does not exist")

            # Extract the SQL statement (remove CREATE VIEW ... AS prefix)
            sql = row["sql"]
            # Find the AS keyword and get everything after it
            as_index = sql.upper().find(" AS ")
            if as_index != -1:
                sql_statement = sql[as_index + 4 :].strip()
            else:
                sql_statement = sql

            return View(
                name=view_name,
                database=self.database,
                branch=self.branch,
                sql_statement=sql_statement,
            )

    def _view_exists(self, view_name: str) -> bool:
        """Check if a view exists.

        Args:
            view_name: Name of the view

        Returns:
            True if view exists
        """
        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name=?",
                (view_name,),
            )
            return cursor.fetchone() is not None

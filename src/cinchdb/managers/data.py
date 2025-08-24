"""Data management for CinchDB - handles CRUD operations on table data."""

import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar
from datetime import datetime

from pydantic import BaseModel

from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.maintenance import check_maintenance_mode
from cinchdb.managers.table import TableManager
from cinchdb.managers.query import QueryManager

T = TypeVar("T", bound=BaseModel)


class DataManager:
    """Manages data operations within a database tenant."""

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main"
    ):
        """Initialize data manager.

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
        self.table_manager = TableManager(project_root, database, branch, tenant)
        self.query_manager = QueryManager(project_root, database, branch, tenant)

    def select(
        self,
        model_class: Type[T],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters,
    ) -> List[T]:
        """Select records from a table with optional filtering.

        Args:
            model_class: Pydantic model class representing the table
            limit: Maximum number of records to return
            offset: Number of records to skip
            **filters: Column filters (exact match or special operators)

        Returns:
            List of model instances

        Raises:
            ValueError: If table doesn't exist or filters are invalid
        """
        table_name = self._get_table_name(model_class)

        # Build WHERE clause from filters
        where_clause, params = self._build_where_clause(filters)

        # Build query
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Convert rows to model instances
            return [model_class(**dict(row)) for row in rows]

    def find_by_id(self, model_class: Type[T], record_id: str) -> Optional[T]:
        """Find a single record by ID.

        Args:
            model_class: Pydantic model class representing the table
            record_id: The record ID to find

        Returns:
            Model instance or None if not found
        """
        results = self.select(model_class, limit=1, id=record_id)
        return results[0] if results else None

    def create_from_dict(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record from a dictionary.

        Args:
            table_name: Name of the table to insert into
            data: Dictionary containing the record data

        Returns:
            Dictionary with created record including generated ID and timestamps

        Raises:
            ValueError: If record with same ID already exists
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Make a copy to avoid modifying the original
        record_data = data.copy()

        # Generate ID if not provided
        if not record_data.get("id"):
            record_data["id"] = str(uuid.uuid4())

        # Set timestamps
        now = datetime.now()
        record_data["created_at"] = now
        record_data["updated_at"] = now

        # Build INSERT query
        columns = list(record_data.keys())
        placeholders = [f":{col}" for col in columns]
        query = f"""
            INSERT INTO {table_name} ({", ".join(columns)}) 
            VALUES ({", ".join(placeholders)})
        """

        with DatabaseConnection(self.db_path) as conn:
            try:
                conn.execute(query, record_data)
                conn.commit()

                # Return the created record data
                return record_data
            except Exception as e:
                conn.rollback()
                if "UNIQUE constraint failed" in str(e):
                    raise ValueError(f"Record with ID {record_data['id']} already exists")
                raise

    def create(self, instance: T) -> T:
        """Create a new record from a model instance.

        Args:
            instance: Model instance to create

        Returns:
            Created model instance with populated ID and timestamps

        Raises:
            ValueError: If record with same ID already exists
            MaintenanceError: If branch is in maintenance mode
        """
        table_name = self._get_table_name(type(instance))
        data = instance.model_dump()
        
        # Use the new create_from_dict method
        created_data = self.create_from_dict(table_name, data)
        
        # Return updated instance
        return type(instance)(**created_data)

    def save(self, instance: T) -> T:
        """Save (upsert) a record - insert if new, update if exists.

        Args:
            instance: Model instance to save

        Returns:
            Saved model instance with updated timestamps

        Raises:
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        data = instance.model_dump()

        # Generate ID if not provided
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())

        # Check if record exists
        existing = self.find_by_id(type(instance), data["id"])

        if existing:
            # Update existing record
            return self.update(instance)
        else:
            # Create new record
            return self.create(instance)

    def update(self, instance: T) -> T:
        """Update an existing record.

        Args:
            instance: Model instance to update

        Returns:
            Updated model instance

        Raises:
            ValueError: If record doesn't exist
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        table_name = self._get_table_name(type(instance))
        data = instance.model_dump()

        if not data.get("id"):
            raise ValueError("Cannot update record without ID")

        # Check if record exists
        existing = self.find_by_id(type(instance), data["id"])
        if not existing:
            raise ValueError(f"Record with ID {data['id']} not found")

        # Update timestamp
        data["updated_at"] = datetime.now()

        # Build UPDATE query (exclude id and created_at)
        update_data = {k: v for k, v in data.items() if k not in ["id", "created_at"]}
        set_clause = ", ".join([f"{col} = :{col}" for col in update_data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = :id"

        params = {**update_data, "id": data["id"]}

        with DatabaseConnection(self.db_path) as conn:
            try:
                conn.execute(query, params)
                conn.commit()

                # Return updated instance
                return type(instance)(**data)
            except Exception:
                conn.rollback()
                raise

    def delete(self, model_class: Type[T], **filters) -> int:
        """Delete records matching filters.

        Args:
            model_class: Pydantic model class representing the table
            **filters: Column filters to identify records to delete

        Returns:
            Number of records deleted

        Raises:
            ValueError: If no filters provided or table doesn't exist
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        if not filters:
            raise ValueError(
                "Delete requires at least one filter to prevent accidental deletion of all records"
            )

        table_name = self._get_table_name(model_class)

        # Build WHERE clause from filters
        where_clause, params = self._build_where_clause(filters)

        query = f"DELETE FROM {table_name} WHERE {where_clause}"

        with DatabaseConnection(self.db_path) as conn:
            try:
                cursor = conn.execute(query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
            except Exception:
                conn.rollback()
                raise

    def delete_by_id(self, model_class: Type[T], record_id: str) -> bool:
        """Delete a single record by ID.

        Args:
            model_class: Pydantic model class representing the table
            record_id: The record ID to delete

        Returns:
            True if record was deleted, False if not found

        Raises:
            MaintenanceError: If branch is in maintenance mode
        """
        deleted_count = self.delete(model_class, id=record_id)
        return deleted_count > 0

    def bulk_create(self, instances: List[T]) -> List[T]:
        """Create multiple records in a single transaction.

        Args:
            instances: List of model instances to create

        Returns:
            List of created model instances with populated IDs and timestamps

        Raises:
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        if not instances:
            return []

        table_name = self._get_table_name(type(instances[0]))
        created_instances = []

        with DatabaseConnection(self.db_path) as conn:
            try:
                for instance in instances:
                    data = instance.model_dump()

                    # Generate ID if not provided
                    if not data.get("id"):
                        data["id"] = str(uuid.uuid4())

                    # Set timestamps
                    now = datetime.now()
                    data["created_at"] = now
                    data["updated_at"] = now

                    # Build INSERT query
                    columns = list(data.keys())
                    placeholders = [f":{col}" for col in columns]
                    query = f"""
                        INSERT INTO {table_name} ({", ".join(columns)}) 
                        VALUES ({", ".join(placeholders)})
                    """

                    conn.execute(query, data)
                    created_instances.append(type(instance)(**data))

                conn.commit()
                return created_instances
            except Exception:
                conn.rollback()
                raise

    def count(self, model_class: Type[T], **filters) -> int:
        """Count records with optional filtering.

        Args:
            model_class: Pydantic model class representing the table
            **filters: Column filters

        Returns:
            Number of matching records
        """
        table_name = self._get_table_name(model_class)

        # Build WHERE clause from filters
        where_clause, params = self._build_where_clause(filters)

        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.execute(query, params)
            result = cursor.fetchone()
            return result["count"] if result else 0

    def _get_table_name(self, model_class: Type[BaseModel]) -> str:
        """Extract table name from model class.

        Args:
            model_class: Pydantic model class

        Returns:
            Table name

        Raises:
            ValueError: If model doesn't have table name configuration
        """
        # Try to get table name from model config (Pydantic v2 style)
        if hasattr(model_class, "model_config"):
            model_config = model_class.model_config
            if hasattr(model_config, "get"):
                # ConfigDict is a dict-like object
                json_schema_extra = model_config.get("json_schema_extra", {})
                if (
                    isinstance(json_schema_extra, dict)
                    and "table_name" in json_schema_extra
                ):
                    return json_schema_extra["table_name"]

        # Try to get table name from Config class (Pydantic v1 style)
        if hasattr(model_class, "Config"):
            config = getattr(model_class, "Config")
            if hasattr(config, "json_schema_extra"):
                json_schema_extra = getattr(config, "json_schema_extra", {})
                if (
                    isinstance(json_schema_extra, dict)
                    and "table_name" in json_schema_extra
                ):
                    return json_schema_extra["table_name"]

        # Fallback to class name in snake_case
        class_name = model_class.__name__
        # Convert PascalCase to snake_case
        import re

        snake_case = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        snake_case = re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_case).lower()
        return snake_case

    def _build_where_clause(
        self, filters: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Build WHERE clause and parameters from filters.

        Args:
            filters: Dictionary of column filters

        Returns:
            Tuple of (where_clause, parameters)
        """
        if not filters:
            return "", {}

        conditions = []
        params = {}

        for key, value in filters.items():
            # Handle special operators (column__operator format)
            if "__" in key:
                column, operator = key.split("__", 1)
                param_key = f"{column}_{operator}"

                if operator == "gte":
                    conditions.append(f"{column} >= :{param_key}")
                    params[param_key] = value
                elif operator == "lte":
                    conditions.append(f"{column} <= :{param_key}")
                    params[param_key] = value
                elif operator == "gt":
                    conditions.append(f"{column} > :{param_key}")
                    params[param_key] = value
                elif operator == "lt":
                    conditions.append(f"{column} < :{param_key}")
                    params[param_key] = value
                elif operator == "like":
                    conditions.append(f"{column} LIKE :{param_key}")
                    params[param_key] = value
                elif operator == "in":
                    if not isinstance(value, (list, tuple)):
                        raise ValueError(
                            f"'in' operator requires list or tuple, got {type(value)}"
                        )
                    placeholders = [f":{param_key}_{i}" for i in range(len(value))]
                    conditions.append(f"{column} IN ({', '.join(placeholders)})")
                    for i, v in enumerate(value):
                        params[f"{param_key}_{i}"] = v
                else:
                    raise ValueError(f"Unsupported operator: {operator}")
            else:
                # Exact match
                conditions.append(f"{key} = :{key}")
                params[key] = value

        return " AND ".join(conditions), params

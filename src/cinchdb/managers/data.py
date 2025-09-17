"""Data management for CinchDB - handles CRUD operations on table data."""

import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, TypeVar
from datetime import datetime

from pydantic import BaseModel

from cinchdb.core.connection import DatabaseConnection
from cinchdb.core.path_utils import get_tenant_db_path
from cinchdb.core.maintenance_utils import check_maintenance_mode
from cinchdb.managers.table import TableManager
from cinchdb.managers.query import QueryManager

T = TypeVar("T", bound=BaseModel)


class DataManager:
    """Manages data operations within a database tenant."""

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main",
        encryption_manager=None
    ):
        """Initialize data manager.

        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name
            tenant: Tenant name (default: main)
            encryption_manager: EncryptionManager instance for encrypted connections
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.encryption_manager = encryption_manager
        self.db_path = get_tenant_db_path(project_root, database, branch, tenant)
        self.table_manager = TableManager(project_root, database, branch, tenant, encryption_manager)
        self.query_manager = QueryManager(project_root, database, branch, tenant, encryption_manager)

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

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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

        # Auto-materialize lazy tenant if needed
        self._ensure_tenant_materialized()

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

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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

    def bulk_create_from_dict(self, table_name: str, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Bulk create multiple records from dictionaries using executemany.

        Args:
            table_name: Name of the table to insert into
            data_list: List of dictionaries containing record data

        Returns:
            List of dictionaries with created records including generated IDs and timestamps

        Raises:
            ValueError: If any record has duplicate ID
            MaintenanceError: If branch is in maintenance mode
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Auto-materialize lazy tenant if needed
        self._ensure_tenant_materialized()

        if not data_list:
            return []

        # Prepare all records
        records = []
        now = datetime.now()
        
        for data in data_list:
            record_data = data.copy()
            
            # Generate ID if not provided
            if not record_data.get("id"):
                record_data["id"] = str(uuid.uuid4())
            
            # Set timestamps
            record_data["created_at"] = now
            record_data["updated_at"] = now
            
            records.append(record_data)
        
        # Get columns from first record (all should have same structure)
        columns = list(records[0].keys())
        placeholders = [f":{col}" for col in columns]
        query = f"""
            INSERT INTO {table_name} ({", ".join(columns)}) 
            VALUES ({", ".join(placeholders)})
        """

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            try:
                # Use executemany for bulk insert
                conn.executemany(query, records)
                conn.commit()
                return records
            except Exception as e:
                conn.rollback()
                if "UNIQUE constraint failed" in str(e):
                    raise ValueError(f"Duplicate ID found in bulk insert")
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

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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

        # Return 0 if tenant is not materialized (no records to delete)
        if not self._is_tenant_materialized():
            return 0

        if not filters:
            raise ValueError(
                "Delete requires at least one filter to prevent accidental deletion of all records"
            )

        table_name = self._get_table_name(model_class)

        # Build WHERE clause from filters
        where_clause, params = self._build_where_clause(filters)

        query = f"DELETE FROM {table_name} WHERE {where_clause}"

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            try:
                cursor = conn.execute(query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count
            except Exception:
                conn.rollback()
                raise

    def delete_model_by_id(self, model_class: Type[T], record_id: str) -> bool:
        """Delete a single record by ID using model class.

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

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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

        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
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
        self, filters: Dict[str, Any], operator: str = "AND"
    ) -> tuple[str, Dict[str, Any]]:
        """Build WHERE clause and parameters from filters.

        Args:
            filters: Dictionary of column filters
            operator: Logical operator to combine conditions - "AND" (default) or "OR"

        Returns:
            Tuple of (where_clause, parameters)
        """
        if not filters:
            return "", {}

        if operator not in ("AND", "OR"):
            raise ValueError(f"Operator must be 'AND' or 'OR', got: {operator}")

        conditions = []
        params = {}

        for key, value in filters.items():
            # Handle special operators (column__operator format)
            if "__" in key:
                column, op = key.split("__", 1)
                param_key = f"{column}_{op}"

                if op == "gte":
                    conditions.append(f"{column} >= :{param_key}")
                    params[param_key] = value
                elif op == "lte":
                    conditions.append(f"{column} <= :{param_key}")
                    params[param_key] = value
                elif op == "gt":
                    conditions.append(f"{column} > :{param_key}")
                    params[param_key] = value
                elif op == "lt":
                    conditions.append(f"{column} < :{param_key}")
                    params[param_key] = value
                elif op == "like":
                    conditions.append(f"{column} LIKE :{param_key}")
                    params[param_key] = value
                elif op == "in":
                    if not isinstance(value, (list, tuple)):
                        raise ValueError(
                            f"'in' operator requires list or tuple, got {type(value)}"
                        )
                    placeholders = [f":{param_key}_{i}" for i in range(len(value))]
                    conditions.append(f"{column} IN ({', '.join(placeholders)})")
                    for i, v in enumerate(value):
                        params[f"{param_key}_{i}"] = v
                else:
                    raise ValueError(f"Unsupported operator: {op}")
            else:
                # Exact match
                conditions.append(f"{key} = :{key}")
                params[key] = value

        return f" {operator} ".join(conditions), params

    def delete_where(self, table: str, operator: str = "AND", **filters) -> int:
        """Delete records from a table based on filter criteria.
        
        Args:
            table: Table name
            operator: Logical operator to combine conditions - "AND" (default) or "OR"
            **filters: Filter criteria (supports operators like __gt, __lt, __in, __like, __not)
                      Multiple conditions are combined with the specified operator
            
        Returns:
            Number of records deleted
            
        Examples:
            # Delete records where status = 'inactive'
            count = dm.delete_where('users', status='inactive')
            
            # Delete records where status = 'inactive' AND age > 65 (default AND)
            count = dm.delete_where('users', status='inactive', age__gt=65)
            
            # Delete records where status = 'inactive' OR age > 65
            count = dm.delete_where('users', operator='OR', status='inactive', age__gt=65)
            
            # Delete records where age > 65
            count = dm.delete_where('users', age__gt=65)
            
            # Delete records where id in [1, 2, 3]
            count = dm.delete_where('users', id__in=[1, 2, 3])
            
            # Delete records where name like 'test%'
            count = dm.delete_where('users', name__like='test%')
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Return 0 if tenant is not materialized (no records to delete)
        if not self._is_tenant_materialized():
            return 0

        if not filters:
            raise ValueError("delete_where requires at least one filter condition")
        
        # Build WHERE clause
        where_clause, params = self._build_where_clause(filters, operator)
        
        sql = f"DELETE FROM {table} WHERE {where_clause}"
        
        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def update_where(self, table: str, data: Dict[str, Any], operator: str = "AND", **filters) -> int:
        """Update records in a table based on filter criteria.
        
        Args:
            table: Table name
            data: Dictionary of column-value pairs to update
            operator: Logical operator to combine conditions - "AND" (default) or "OR"
            **filters: Filter criteria (supports operators like __gt, __lt, __in, __like, __not)
                      Multiple conditions are combined with the specified operator
            
        Returns:
            Number of records updated
            
        Examples:
            # Update status for all users with age > 65
            count = dm.update_where('users', {'status': 'senior'}, age__gt=65)
            
            # Update status where age > 65 AND status = 'active' (default AND)
            count = dm.update_where('users', {'status': 'senior'}, age__gt=65, status='active')
            
            # Update status where age > 65 OR status = 'pending'
            count = dm.update_where('users', {'status': 'senior'}, operator='OR', age__gt=65, status='pending')
            
            # Update multiple fields where id in specific list
            count = dm.update_where(
                'users', 
                {'status': 'inactive', 'updated_at': datetime.now()},
                id__in=[1, 2, 3]
            )
            
            # Update where name like pattern
            count = dm.update_where('users', {'category': 'test'}, name__like='test%')
        """
        # Check maintenance mode
        check_maintenance_mode(self.project_root, self.database, self.branch)

        # Return 0 if tenant is not materialized (no records to update)
        if not self._is_tenant_materialized():
            return 0

        if not filters:
            raise ValueError("update_where requires at least one filter condition")
            
        if not data:
            raise ValueError("update_where requires data to update")
        
        # Build WHERE clause
        where_clause, where_params = self._build_where_clause(filters, operator)
        
        # Build SET clause
        set_clauses = []
        update_params = {}
        
        for key, value in data.items():
            param_key = f"update_{key}"
            set_clauses.append(f"{key} = :{param_key}")
            update_params[param_key] = value
        
        # Combine parameters (update params first to avoid conflicts)
        all_params = {**update_params, **where_params}
        
        sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"
        
        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, all_params)
            conn.commit()
            return cursor.rowcount

    def update_by_id(self, table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a single record by ID.

        Args:
            table: Table name
            record_id: Record ID to update
            data: Dictionary of column-value pairs to update

        Returns:
            Updated record

        Raises:
            ValueError: If tenant is not materialized or record not found
        """
        # Raise error if tenant is not materialized (record doesn't exist)
        if not self._is_tenant_materialized():
            raise ValueError(f"Record not found: {record_id}")

        # Build SET clause
        set_parts = []
        params = []
        
        for key, value in data.items():
            set_parts.append(f"{key} = ?")
            params.append(value)
        
        if not set_parts:
            raise ValueError("No data provided for update")
        
        set_clause = ", ".join(set_parts)
        sql = f"UPDATE {table} SET {set_clause} WHERE id = ?"
        params.append(record_id)
        
        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            
            if cursor.rowcount == 0:
                raise ValueError(f"No record found with id: {record_id}")
            
            # Return the updated record
            result = conn.execute(f"SELECT * FROM {table} WHERE id = ?", [record_id])
            row = result.fetchone()
            if row:
                return dict(row)
            else:
                raise ValueError(f"Record not found after update: {record_id}")
    
    def delete_by_id(self, table: str, record_id: str) -> bool:
        """Delete a single record by ID using table name.

        This method is used by the high-level database API.

        Args:
            table: Table name
            record_id: Record ID to delete

        Returns:
            True if record was deleted, False if not found
        """
        # Return False if tenant is not materialized (no records to delete)
        if not self._is_tenant_materialized():
            return False

        sql = f"DELETE FROM {table} WHERE id = ?"
        
        with DatabaseConnection(self.db_path, tenant_id=self.tenant, encryption_manager=self.encryption_manager) as conn:
            cursor = conn.execute(sql, [record_id])
            conn.commit()
            return cursor.rowcount > 0

    def _ensure_tenant_materialized(self) -> None:
        """Ensure the tenant is materialized before performing data operations.

        Materializes lazy tenants on their first data operation.
        """
        # Only materialize if we're not dealing with the main tenant
        # The main tenant is always materialized
        if self.tenant == "main":
            return

        # Check if tenant database file exists
        if not self.db_path.exists():
            # Tenant is lazy - materialize it
            from cinchdb.managers.tenant import TenantManager
            tenant_mgr = TenantManager(self.project_root, self.database, self.branch)
            tenant_mgr.materialize_tenant(self.tenant)

    def _is_tenant_materialized(self) -> bool:
        """Check if the tenant is materialized (has a database file).

        Returns:
            True if tenant is materialized, False if lazy
        """
        # Main tenant is always materialized
        if self.tenant == "main":
            return True

        # Check if database file exists
        return self.db_path.exists()


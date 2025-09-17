"""Tests for QueryManager - type-safe SQL query execution."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from cinchdb.core.initializer import init_project
from cinchdb.core.database import CinchDB
from cinchdb.managers.query import QueryManager
from cinchdb.managers.table import TableManager
from cinchdb.managers.data import DataManager
from cinchdb.models import Column


# Test model for query operations
class QueryTestUser(BaseModel):
    """Test model representing a user table."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"table_name": "users"}
    )

    id: Optional[str] = Field(default=None, description="id field")
    created_at: Optional[datetime] = Field(default=None, description="created_at field")
    updated_at: Optional[datetime] = Field(default=None, description="updated_at field")
    name: str = Field(description="name field")
    email: str = Field(description="email field")
    age: int = Field(description="age field")
    active: Optional[int] = Field(default=1, description="active field")


class TestQueryManager:
    """Test suite for QueryManager type-safe query operations."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project with config."""
        temp = tempfile.mkdtemp()
        project_dir = Path(temp)

        # Initialize project
        init_project(project_dir)

        yield project_dir
        shutil.rmtree(temp)

    @pytest.fixture
    def query_manager(self, temp_project):
        """Create a QueryManager instance with test data."""
        project_root = temp_project
        database = "main"
        branch = "main"
        tenant = "main"

        # Create table manager and test table
        table_manager = TableManager(project_root, database, branch, tenant)

        # Create users table
        columns = [
            Column(name="name", type="TEXT", nullable=False),
            Column(name="email", type="TEXT", nullable=False),
            Column(name="age", type="INTEGER", nullable=False),
            Column(name="active", type="INTEGER", nullable=True),
        ]
        table_manager.create_table("users", columns)

        # Create data manager and add test data
        data_manager = DataManager(project_root, database, branch, tenant)

        # Insert test users
        users = [
            QueryTestUser(
                name="Alice Smith", email="alice@example.com", age=30, active=1
            ),
            QueryTestUser(
                name="Bob Johnson", email="bob@example.com", age=25, active=1
            ),
            QueryTestUser(
                name="Carol Davis", email="carol@example.com", age=35, active=0
            ),
            QueryTestUser(
                name="David Wilson", email="david@example.com", age=28, active=1
            ),
        ]

        for user in users:
            data_manager.create(user)

        # Create and return query manager
        return QueryManager(project_root, database, branch, tenant)

    def test_query_typed_basic(self, query_manager):
        """Test executing a typed SELECT query returning model instances."""
        results = query_manager.query_typed(
            "SELECT * FROM users WHERE age >= 30", QueryTestUser
        )

        assert len(results) == 2
        assert all(isinstance(r, QueryTestUser) for r in results)

        # Check that model instances have correct data
        ages = [user.age for user in results]
        assert all(age >= 30 for age in ages)

        names = [user.name for user in results]
        assert "Alice Smith" in names
        assert "Carol Davis" in names

    def test_query_typed_with_validation_error(self, query_manager):
        """Test that query_typed raises ValueError in strict mode."""
        # Query that will return data missing required fields
        with pytest.raises(ValueError, match="failed validation"):
            query_manager.query_typed(
                "SELECT id, name FROM users",  # Missing required 'email' and 'age'
                QueryTestUser,
                strict=True,
            )

    def test_query_typed_non_strict_mode(self, query_manager):
        """Test that query_typed skips invalid rows in non-strict mode."""
        # This would normally fail validation
        results = query_manager.query_typed(
            "SELECT id, name, email, age FROM users WHERE 1=0",  # No results
            QueryTestUser,
            strict=False,
        )

        assert results == []

    def test_query_typed_non_select_query(self, query_manager):
        """Test that query_typed rejects non-SELECT queries."""
        with pytest.raises(
            ValueError, match="execute_typed can only be used with SELECT queries"
        ):
            query_manager.query_typed("UPDATE users SET active = 0", QueryTestUser)

    def test_query_typed_with_parameters(self, query_manager):
        """Test typed parameterized queries."""
        results = query_manager.query_typed(
            "SELECT * FROM users WHERE name LIKE ?", QueryTestUser, ("%Smith",)
        )

        assert len(results) == 1
        assert results[0].name == "Alice Smith"

    def test_query_typed_null_handling(self, query_manager):
        """Test handling of NULL values in typed queries."""
        # Insert a record with NULL active field
        db = CinchDB(database="main", project_dir=query_manager.project_root, tenant="main")
        db.insert("users", {
            "id": "null-test",
            "name": "Null User",
            "email": "null@example.com",
            "age": 99,
            "active": None,
        })

        # Test with typed query
        typed_results = query_manager.query_typed(
            "SELECT * FROM users WHERE active IS NULL", QueryTestUser
        )
        assert len(typed_results) == 1
        assert typed_results[0].active is None
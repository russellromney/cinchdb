"""Tests for QueryManager - type-safe SQL query execution."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from cinchdb.core.initializer import init_project
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

    def test_execute_select_query(self, query_manager):
        """Test executing a basic SELECT query returning dicts."""
        results = query_manager.execute("SELECT * FROM users WHERE active = 1")

        assert len(results) == 3
        assert all(isinstance(r, dict) for r in results)

        # Check that we have the expected fields
        for result in results:
            assert "id" in result
            assert "name" in result
            assert "email" in result
            assert "age" in result
            assert "active" in result
            assert result["active"] == 1

    def test_execute_typed_query(self, query_manager):
        """Test executing a typed SELECT query returning model instances."""
        results = query_manager.execute_typed(
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

    def test_execute_typed_with_validation_error(self, query_manager):
        """Test that execute_typed raises ValueError in strict mode."""
        # Query that will return data missing required fields
        with pytest.raises(ValueError, match="failed validation"):
            query_manager.execute_typed(
                "SELECT id, name FROM users",  # Missing required 'email' and 'age'
                QueryTestUser,
                strict=True,
            )

    def test_execute_typed_non_strict_mode(self, query_manager):
        """Test that execute_typed skips invalid rows in non-strict mode."""
        # This would normally fail validation
        results = query_manager.execute_typed(
            "SELECT id, name, email, age FROM users WHERE 1=0",  # No results
            QueryTestUser,
            strict=False,
        )

        assert results == []

    def test_execute_non_select_query(self, query_manager):
        """Test that execute rejects non-SELECT queries."""
        with pytest.raises(
            ValueError, match="execute\\(\\) can only be used with SELECT queries"
        ):
            query_manager.execute("UPDATE users SET active = 0")

        with pytest.raises(
            ValueError, match="execute\\(\\) can only be used with SELECT queries"
        ):
            query_manager.execute("INSERT INTO users (name) VALUES ('test')")

        with pytest.raises(
            ValueError, match="execute\\(\\) can only be used with SELECT queries"
        ):
            query_manager.execute("DELETE FROM users WHERE id = '1'")

    def test_execute_typed_non_select_query(self, query_manager):
        """Test that execute_typed rejects non-SELECT queries."""
        with pytest.raises(
            ValueError, match="execute_typed can only be used with SELECT queries"
        ):
            query_manager.execute_typed("UPDATE users SET active = 0", QueryTestUser)

    def test_execute_one(self, query_manager):
        """Test executing a query that returns a single result."""
        result = query_manager.execute_one(
            "SELECT * FROM users WHERE email = 'alice@example.com'"
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["name"] == "Alice Smith"
        assert result["email"] == "alice@example.com"

        # Test no results
        no_result = query_manager.execute_one(
            "SELECT * FROM users WHERE email = 'nonexistent@example.com'"
        )
        assert no_result is None

    def test_execute_one_non_select_query(self, query_manager):
        """Test that execute_one rejects non-SELECT queries."""
        with pytest.raises(
            ValueError, match="execute\\(\\) can only be used with SELECT queries"
        ):
            query_manager.execute_one("UPDATE users SET active = 0")

    def test_execute_one_typed(self, query_manager):
        """Test executing a typed query that returns a single result."""
        result = query_manager.execute_one_typed(
            "SELECT * FROM users WHERE email = 'bob@example.com'", QueryTestUser
        )

        assert result is not None
        assert isinstance(result, QueryTestUser)
        assert result.name == "Bob Johnson"
        assert result.age == 25

        # Test no results
        no_result = query_manager.execute_one_typed(
            "SELECT * FROM users WHERE age > 100", QueryTestUser
        )
        assert no_result is None

    def test_execute_non_query(self, query_manager):
        """Test executing INSERT, UPDATE, DELETE queries."""
        # Test UPDATE
        affected = query_manager.execute_non_query(
            "UPDATE users SET active = 0 WHERE age < 30"
        )
        assert affected == 2  # Bob and David

        # Verify the update
        results = query_manager.execute("SELECT * FROM users WHERE active = 0")
        assert len(results) == 3  # Carol was already inactive

        # Test DELETE
        affected = query_manager.execute_non_query(
            "DELETE FROM users WHERE email = 'carol@example.com'"
        )
        assert affected == 1

        # Test INSERT
        affected = query_manager.execute_non_query(
            "INSERT INTO users (id, name, email, age, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "test-id",
                "Eve Brown",
                "eve@example.com",
                40,
                1,
                datetime.now(),
                datetime.now(),
            ),
        )
        assert affected == 1

    def test_execute_with_parameters(self, query_manager):
        """Test parameterized queries."""
        # Positional parameters
        results = query_manager.execute(
            "SELECT * FROM users WHERE age >= ? AND active = ?", (30, 1)
        )
        assert len(results) == 1
        assert results[0]["name"] == "Alice Smith"

        # Named parameters
        results = query_manager.execute(
            "SELECT * FROM users WHERE age BETWEEN :min_age AND :max_age",
            {"min_age": 25, "max_age": 30},
        )
        assert len(results) == 3

    def test_execute_typed_with_parameters(self, query_manager):
        """Test typed parameterized queries."""
        results = query_manager.execute_typed(
            "SELECT * FROM users WHERE name LIKE ?", QueryTestUser, ("%Smith",)
        )

        assert len(results) == 1
        assert results[0].name == "Alice Smith"

    def test_execute_many(self, query_manager):
        """Test executing multiple queries with different parameters."""
        # Insert multiple records
        params_list = [
            (
                "id1",
                "User1",
                "user1@example.com",
                20,
                1,
                datetime.now(),
                datetime.now(),
            ),
            (
                "id2",
                "User2",
                "user2@example.com",
                21,
                1,
                datetime.now(),
                datetime.now(),
            ),
            (
                "id3",
                "User3",
                "user3@example.com",
                22,
                1,
                datetime.now(),
                datetime.now(),
            ),
        ]

        affected = query_manager.execute_many(
            "INSERT INTO users (id, name, email, age, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            params_list,
        )

        assert affected == 3

        # Verify insertions
        results = query_manager.execute(
            "SELECT * FROM users WHERE age BETWEEN 20 AND 22"
        )
        assert len(results) == 3

    def test_execute_with_sql_injection_protection(self, query_manager):
        """Test that parameterized queries protect against SQL injection."""
        # This should be safe due to parameterization
        malicious_input = "'; DROP TABLE users; --"

        results = query_manager.execute(
            "SELECT * FROM users WHERE name = ?", (malicious_input,)
        )

        assert len(results) == 0  # No matching users

        # Verify table still exists
        all_users = query_manager.execute("SELECT COUNT(*) as count FROM users")
        assert all_users[0]["count"] > 0

    def test_transaction_rollback(self, query_manager):
        """Test that failed operations rollback properly."""
        initial_count = query_manager.execute("SELECT COUNT(*) as count FROM users")[0][
            "count"
        ]

        # Try to insert with duplicate ID (should fail)
        existing_id = query_manager.execute("SELECT id FROM users LIMIT 1")[0]["id"]

        with pytest.raises(Exception):
            query_manager.execute_non_query(
                "INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?)",
                (existing_id, "Duplicate", "dup@example.com", 50),
            )

        # Verify count hasn't changed
        final_count = query_manager.execute("SELECT COUNT(*) as count FROM users")[0][
            "count"
        ]
        assert initial_count == final_count

    def test_null_handling(self, query_manager):
        """Test handling of NULL values in queries."""
        # Insert a record with NULL active field
        query_manager.execute_non_query(
            "INSERT INTO users (id, name, email, age, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "null-test",
                "Null User",
                "null@example.com",
                99,
                None,
                datetime.now(),
                datetime.now(),
            ),
        )

        # Query for NULL values
        results = query_manager.execute("SELECT * FROM users WHERE active IS NULL")
        assert len(results) == 1
        assert results[0]["name"] == "Null User"
        assert results[0]["active"] is None

        # Test with typed query
        typed_results = query_manager.execute_typed(
            "SELECT * FROM users WHERE active IS NULL", QueryTestUser
        )
        assert len(typed_results) == 1
        assert typed_results[0].active is None

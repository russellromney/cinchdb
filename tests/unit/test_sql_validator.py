"""Tests for SQL query validator."""

import pytest
from cinchdb.utils.sql_validator import (
    validate_sql_query,
    validate_query_safe,
    SQLValidationError,
    SQLOperation,
)


class TestSQLValidator:
    """Test SQL query validation functionality."""

    def test_allowed_select_queries(self):
        """Test that SELECT queries are allowed."""
        queries = [
            "SELECT * FROM users",
            "select id, name from products",
            "SELECT COUNT(*) FROM orders WHERE status = 'pending'",
            "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is True
            assert error is None
            assert operation == SQLOperation.SELECT

    def test_allowed_insert_queries(self):
        """Test that INSERT queries are allowed."""
        queries = [
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')",
            "insert into products (name, price) values ('Widget', 9.99)",
            "INSERT INTO logs SELECT * FROM temp_logs",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is True
            assert error is None
            assert operation == SQLOperation.INSERT

    def test_allowed_update_queries(self):
        """Test that UPDATE queries are allowed."""
        queries = [
            "UPDATE users SET name = 'John' WHERE id = 1",
            "update products set price = 100 where category = 'electronics'",
            "UPDATE orders SET status = 'completed'",  # Without WHERE - should still be valid
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is True
            assert error is None
            assert operation == SQLOperation.UPDATE

    def test_allowed_delete_queries(self):
        """Test that DELETE queries are allowed."""
        queries = [
            "DELETE FROM users WHERE id = 1",
            "delete from products where stock = 0",
            "DELETE FROM logs",  # Without WHERE - should still be valid
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is True
            assert error is None
            assert operation == SQLOperation.DELETE

    def test_blocked_create_operations(self):
        """Test that CREATE operations are blocked."""
        queries = [
            "CREATE TABLE users (id INTEGER PRIMARY KEY)",
            "CREATE INDEX idx_users_name ON users(name)",
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1",
            "CREATE TRIGGER update_timestamp BEFORE UPDATE ON users",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False
            assert "CREATE" in error
            assert operation is None

    def test_blocked_alter_operations(self):
        """Test that ALTER operations are blocked."""
        queries = [
            "ALTER TABLE users ADD COLUMN email TEXT",
            "ALTER TABLE products DROP COLUMN description",
            "ALTER TABLE orders RENAME TO order_history",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False
            assert "ALTER" in error
            assert operation is None

    def test_blocked_drop_operations(self):
        """Test that DROP operations are blocked."""
        queries = [
            "DROP TABLE users",
            "DROP INDEX idx_users_name",
            "DROP VIEW active_users",
            "DROP DATABASE mydb",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False
            assert "DROP" in error
            assert operation is None

    def test_blocked_truncate_operations(self):
        """Test that TRUNCATE operations are blocked."""
        is_valid, error, operation = validate_sql_query("TRUNCATE TABLE users")
        assert is_valid is False
        assert "TRUNCATE" in error
        assert operation is None

    def test_queries_with_comments(self):
        """Test handling of queries with comments."""
        queries = [
            "-- This is a comment\nSELECT * FROM users",
            "/* Multi-line\n   comment */\nSELECT * FROM products",
            "SELECT * FROM users -- WHERE id = 1",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is True
            assert operation == SQLOperation.SELECT

    def test_blocked_multiple_statements(self):
        """Test that multiple statements are blocked by default."""
        query = "SELECT * FROM users; DROP TABLE users;"
        is_valid, error, operation = validate_sql_query(query)
        assert is_valid is False
        assert "Multiple statements" in error
        assert operation is None

    def test_allow_multiple_statements_flag(self):
        """Test that multiple statements can be allowed with flag."""
        query = "SELECT * FROM users; SELECT * FROM products;"
        # With allow_multiple_statements=True, each statement should still be validated
        # but multiple statements are allowed
        is_valid, error, operation = validate_sql_query(
            query, allow_multiple_statements=True
        )
        # This should still fail because we don't have logic to validate each statement separately
        # For now, we just test that the flag is respected
        assert is_valid is True  # First statement is SELECT

    def test_empty_queries(self):
        """Test handling of empty queries."""
        queries = ["", "   ", "\n\t", "-- only comment"]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False
            assert "empty" in error.lower()
            assert operation is None

    def test_blocked_keywords_in_subqueries(self):
        """Test that restricted keywords are blocked even in subqueries."""
        # These queries should be blocked because they contain DDL operations
        queries = [
            "WITH temp AS (SELECT * FROM users) CREATE TABLE new_users AS SELECT * FROM temp",
            "CREATE TABLE temp AS SELECT * FROM users",
        ]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False

        # But SELECT queries that mention CREATE in string literals or column names should be allowed
        valid_query = "SELECT * FROM users WHERE description LIKE '%CREATE TABLE%'"
        is_valid, error, operation = validate_sql_query(valid_query)
        assert is_valid is True

    def test_blocked_cte_with_ddl(self):
        """Test that CTEs with DDL operations are blocked."""
        query = (
            "WITH temp AS (CREATE TABLE test AS SELECT * FROM users) SELECT * FROM temp"
        )
        is_valid, error, operation = validate_sql_query(query)
        assert is_valid is False
        assert "CTE" in error

    def test_validate_query_safe_raises_exception(self):
        """Test that validate_query_safe raises exception for invalid queries."""
        with pytest.raises(SQLValidationError) as exc_info:
            validate_query_safe("DROP TABLE users")
        assert "DROP" in str(exc_info.value)

    def test_validate_query_safe_passes_valid_queries(self):
        """Test that validate_query_safe doesn't raise for valid queries."""
        # Should not raise
        validate_query_safe("SELECT * FROM users")
        validate_query_safe("UPDATE users SET name = 'test' WHERE id = 1")
        validate_query_safe("DELETE FROM users WHERE id = 1")

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        queries = [
            ("CrEaTe TaBlE users (id INT)", False),
            ("SeLeCt * FrOm users", True),
            ("DeLeTe FrOm users", True),
        ]

        for query, expected_valid in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid == expected_valid

    def test_unrecognized_operations(self):
        """Test handling of unrecognized SQL operations."""
        queries = ["EXPLAIN SELECT * FROM users", "SHOW TABLES", "DESCRIBE users"]

        for query in queries:
            is_valid, error, operation = validate_sql_query(query)
            assert is_valid is False
            assert "Unrecognized" in error or "restricted" in error.lower()
            assert operation is None

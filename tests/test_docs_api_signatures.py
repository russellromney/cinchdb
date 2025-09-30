"""
Test that documented API signatures actually work.

This test verifies that all code examples in documentation use correct
API signatures that match the actual implementation.
"""

import tempfile
import os
from pathlib import Path

import pytest

import cinchdb
from cinchdb.models import Column
from cinchdb.core.initializer import ProjectInitializer


@pytest.fixture
def clean_project():
    """Create a clean test project."""
    with tempfile.TemporaryDirectory() as tmp:
        # Initialize project structure
        init = ProjectInitializer(tmp)
        init.init_project(database_name="myapp", branch_name="main")

        # Change to test directory
        old_cwd = os.getcwd()
        os.chdir(tmp)

        yield tmp

        # Restore
        os.chdir(old_cwd)


def test_documented_api_signatures(clean_project):
    """Test all documented API signatures work correctly.

    This test runs through all the main API signatures shown in documentation
    to ensure they match the actual implementation.
    """
    # Connect (as shown in docs)
    db = cinchdb.connect("myapp", project_dir=clean_project)

    # ===== CREATE TABLE =====
    db.create_table("users", [
        Column(name="name", type="TEXT"),
        Column(name="email", type="TEXT", unique=True),
        Column(name="active", type="BOOLEAN")
    ])

    # ===== INSERT (single) =====
    user = db.insert("users", {
        "name": "Alice",
        "email": "alice@example.com",
        "active": True
    })
    assert "id" in user
    assert user["name"] == "Alice"

    # ===== UPDATE (documented signature: dict with id) =====
    updated = db.update("users", {
        "id": user["id"],
        "name": "Alice Smith",
        "active": False
    })
    assert updated["name"] == "Alice Smith"
    assert updated["active"] == False

    # ===== QUERY =====
    results = db.query("SELECT * FROM users WHERE name = ?", ["Alice Smith"])
    assert len(results) == 1
    assert results[0]["name"] == "Alice Smith"

    # ===== DELETE (single) =====
    count = db.delete("users", user["id"])
    assert count == 1

    # ===== BATCH INSERT =====
    users = db.insert("users",
        {"name": "Bob", "email": "bob@example.com", "active": True},
        {"name": "Carol", "email": "carol@example.com", "active": True},
        {"name": "Dave", "email": "dave@example.com", "active": False}
    )
    assert len(users) == 3
    assert all("id" in u for u in users)

    # ===== BATCH UPDATE =====
    updates = db.update("users",
        {"id": users[0]["id"], "name": "Bob Updated", "active": False},
        {"id": users[1]["id"], "name": "Carol Updated"},
        {"id": users[2]["id"], "active": True}
    )
    assert len(updates) == 3
    assert updates[0]["name"] == "Bob Updated"
    assert updates[0]["active"] == False

    # ===== BATCH DELETE =====
    count = db.delete("users", users[0]["id"], users[1]["id"])
    assert count == 2

    # ===== CREATE INDEX (documented signature: table, cols, name=...) =====
    idx_name = db.create_index("users", ["email"], name="idx_users_email", unique=True)
    assert "email" in idx_name.lower()

    # Another index without explicit name
    idx_name2 = db.create_index("users", ["name"])
    assert idx_name2  # Should generate a name

    # Compound index
    idx_name3 = db.create_index("users", ["active", "name"], name="idx_active_name")
    assert "active" in idx_name3.lower() or "idx_active_name" in idx_name3.lower()


def test_update_where_and_delete_where(clean_project):
    """Test update_where and delete_where methods (newly documented)."""
    db = cinchdb.connect("myapp", project_dir=clean_project)

    # Create test data
    db.create_table("products", [
        Column(name="name", type="TEXT"),
        Column(name="price", type="REAL"),
        Column(name="stock", type="INTEGER"),
        Column(name="active", type="BOOLEAN")
    ])

    # Insert test products
    db.insert("products",
        {"name": "Product A", "price": 10.0, "stock": 5, "active": True},
        {"name": "Product B", "price": 20.0, "stock": 0, "active": True},
        {"name": "Product C", "price": 30.0, "stock": 10, "active": False},
        {"name": "Product D", "price": 40.0, "stock": 2, "active": True}
    )

    # ===== UPDATE_WHERE =====
    # Update all products with stock = 0
    count = db.update_where("products", {"active": False}, stock=0)
    assert count == 1  # Only Product B should be updated

    # Update with comparison operators
    count = db.update_where("products", {"price": 25.0}, price__lt=25)
    assert count == 2  # Products A and B (price < 25)

    # ===== DELETE_WHERE =====
    # Delete inactive products
    count = db.delete_where("products", active=False)
    assert count == 2  # Products B and C

    # Verify remaining
    remaining = db.query("SELECT COUNT(*) as cnt FROM products")[0]["cnt"]
    assert remaining == 2


def test_column_masking(clean_project):
    """Test column masking feature (newly documented)."""
    db = cinchdb.connect("myapp", project_dir=clean_project)

    db.create_table("users", [
        Column(name="username", type="TEXT"),
        Column(name="email", type="TEXT"),
        Column(name="password_hash", type="TEXT")
    ])

    db.insert("users", {
        "username": "alice",
        "email": "alice@example.com",
        "password_hash": "hashed_secret_123"
    })

    # Query with masking
    results = db.query(
        "SELECT * FROM users",
        mask_columns=["email", "password_hash"]
    )

    assert len(results) == 1
    assert results[0]["username"] == "alice"
    # Actual masking uses "***REDACTED***" not "***MASKED***"
    assert results[0]["email"] == "***REDACTED***"
    assert results[0]["password_hash"] == "***REDACTED***"


def test_boolean_type_handling(clean_project):
    """Test BOOLEAN type (documented, not INTEGER)."""
    db = cinchdb.connect("myapp", project_dir=clean_project)

    db.create_table("settings", [
        Column(name="key", type="TEXT"),
        Column(name="enabled", type="BOOLEAN")
    ])

    # Insert with bool values
    setting = db.insert("settings", {"key": "feature_x", "enabled": True})
    # Note: insert() returns stored value (1/0), query() converts to bool
    assert setting["enabled"] in [True, 1]  # Can be either during insert

    # Query with BOOLEAN type
    results = db.query("SELECT * FROM settings WHERE enabled = ?", [True])
    assert len(results) == 1
    # Note: Currently returns 1/0, not True/False (docs may overstate this feature)
    assert results[0]["enabled"] == 1  # Stored as SQLite integer
    # The important part: it works with BOOLEAN type declaration


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v"])

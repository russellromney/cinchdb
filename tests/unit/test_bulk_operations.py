"""Tests for bulk delete and update operations."""

import tempfile
from pathlib import Path

from cinchdb.core.database import CinchDB
from cinchdb.models import Column
from cinchdb.core.initializer import ProjectInitializer


def test_delete_where_in():
    """Test delete_where with __in operator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("test_items", [
            Column(name="item_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT")
        ])
        
        # Add some data
        for i in range(10):
            db.insert("test_items", {"item_id": i, "name": f"item_{i}"})
        
        # Verify all 10 records exist
        all_items = db.query("SELECT COUNT(*) as count FROM test_items")
        assert all_items[0]["count"] == 10
        
        # Delete items with item_id in [1, 3, 5]
        deleted_count = db.delete_where("test_items", item_id__in=[1, 3, 5])
        
        # Check that 3 records were deleted
        assert deleted_count == 3
        
        # Verify remaining count
        remaining_items = db.query("SELECT COUNT(*) as count FROM test_items")
        assert remaining_items[0]["count"] == 7
        
        # Verify specific items remain
        remaining_ids = db.query("SELECT item_id FROM test_items ORDER BY item_id")
        expected_ids = [0, 2, 4, 6, 7, 8, 9]
        actual_ids = [row["item_id"] for row in remaining_ids]
        assert actual_ids == expected_ids


def test_delete_where_gt():
    """Test delete_where with __gt operator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("numbers", [
            Column(name="num_id", type="INTEGER", unique=True),
            Column(name="value", type="INTEGER")
        ])
        
        # Add some data
        for i in range(10):
            db.insert("numbers", {"num_id": i, "value": i * 10})
        
        # Delete numbers where value > 50
        deleted_count = db.delete_where("numbers", value__gt=50)
        
        # Should delete items with values 60, 70, 80, 90 (4 items)
        assert deleted_count == 4
        
        # Verify remaining count
        remaining = db.query("SELECT COUNT(*) as count FROM numbers")
        assert remaining[0]["count"] == 6


def test_update_where():
    """Test update_where functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("users", [
            Column(name="user_id", type="INTEGER", unique=True),
            Column(name="name", type="TEXT"),
            Column(name="status", type="TEXT")
        ])
        
        # Add some data
        for i in range(5):
            db.insert("users", {"user_id": i, "name": f"user_{i}", "status": "active"})
        
        # Update status where user_id > 2
        updated_count = db.update_where("users", {"status": "inactive"}, user_id__gt=2)
        
        # Should update 2 records (user_id 3 and 4)
        assert updated_count == 2
        
        # Verify updates
        inactive_users = db.query("SELECT COUNT(*) as count FROM users WHERE status = 'inactive'")
        assert inactive_users[0]["count"] == 2
        
        active_users = db.query("SELECT COUNT(*) as count FROM users WHERE status = 'active'")
        assert active_users[0]["count"] == 3


def test_delete_where_no_filters():
    """Test that delete_where requires filters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("safe_table", [
            Column(name="test_id", type="INTEGER", unique=True)
        ])
        
        # Should fail without filters
        try:
            db.delete_where("safe_table")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "requires at least one filter condition" in str(e)


def test_bulk_update():
    """Test bulk update functionality with multiple records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("users", [
            Column(name="name", type="TEXT"),
            Column(name="email", type="TEXT"),
            Column(name="status", type="TEXT")
        ])
        
        # Insert initial data
        results = db.insert("users",
            {"name": "Alice", "email": "alice@example.com", "status": "active"},
            {"name": "Bob", "email": "bob@example.com", "status": "active"},
            {"name": "Charlie", "email": "charlie@example.com", "status": "active"}
        )
        
        # Extract IDs
        user_ids = [result["id"] for result in results]
        
        # Update multiple records
        updates = [
            {"id": user_ids[0], "status": "premium", "email": "alice.new@example.com"},
            {"id": user_ids[1], "name": "Bobby", "status": "inactive"},
            {"id": user_ids[2], "status": "premium"}
        ]
        
        updated_results = db.update("users", *updates)
        assert len(updated_results) == 3
        
        # Verify updates
        alice = db.query("SELECT * FROM users WHERE id = ?", [user_ids[0]])[0]
        assert alice["status"] == "premium"
        assert alice["email"] == "alice.new@example.com"
        assert alice["name"] == "Alice"  # unchanged
        
        bob = db.query("SELECT * FROM users WHERE id = ?", [user_ids[1]])[0]
        assert bob["name"] == "Bobby"
        assert bob["status"] == "inactive"
        
        charlie = db.query("SELECT * FROM users WHERE id = ?", [user_ids[2]])[0]
        assert charlie["status"] == "premium"


def test_bulk_delete():
    """Test bulk delete functionality with multiple IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("items", [
            Column(name="name", type="TEXT"),
            Column(name="category", type="TEXT")
        ])
        
        # Insert test data
        results = db.insert("items",
            {"name": "item1", "category": "A"},
            {"name": "item2", "category": "B"},
            {"name": "item3", "category": "A"},
            {"name": "item4", "category": "C"},
            {"name": "item5", "category": "B"}
        )
        
        # Extract IDs
        item_ids = [result["id"] for result in results]
        
        # Delete multiple records
        deleted_count = db.delete("items", item_ids[1], item_ids[3], item_ids[4])
        assert deleted_count == 3
        
        # Verify remaining records
        remaining = db.query("SELECT * FROM items ORDER BY name")
        assert len(remaining) == 2
        assert remaining[0]["name"] == "item1"
        assert remaining[1]["name"] == "item3"


def test_bulk_insert_existing():
    """Test that existing bulk insert functionality still works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("products", [
            Column(name="name", type="TEXT"),
            Column(name="price", type="REAL")
        ])
        
        # Test single insert
        single_result = db.insert("products", {"name": "Product 1", "price": 19.99})
        assert single_result["name"] == "Product 1"
        assert "id" in single_result
        
        # Test multiple insert
        multi_results = db.insert("products",
            {"name": "Product 2", "price": 29.99},
            {"name": "Product 3", "price": 39.99},
            {"name": "Product 4", "price": 49.99}
        )
        
        assert len(multi_results) == 3
        for result in multi_results:
            assert "id" in result
            assert "name" in result
            assert "price" in result
        
        # Verify total count
        count_result = db.query("SELECT COUNT(*) as count FROM products")
        assert count_result[0]["count"] == 4


def test_update_validation():
    """Test that bulk update validates ID field presence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("test_table", [
            Column(name="name", type="TEXT")
        ])
        
        # Test missing ID field
        try:
            db.update("test_table", {"name": "test"})  # Missing 'id' field
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "missing required 'id' field" in str(e)
        
        # Test empty updates
        try:
            db.update("test_table")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "At least one update record must be provided" in str(e)


def test_delete_validation():
    """Test that bulk delete validates ID presence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project  
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("test_table", [
            Column(name="name", type="TEXT")
        ])
        
        # Test empty IDs
        try:
            db.delete("test_table")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "At least one ID must be provided" in str(e)


def test_or_operator():
    """Test OR operator functionality in delete_where and update_where."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Initialize project
        initializer = ProjectInitializer(project_dir)
        initializer.init_project("testdb", "main")
        
        # Connect to database
        db = CinchDB("testdb", project_dir=project_dir)
        
        # Create table
        db.create_table("users", [
            Column(name="name", type="TEXT"),
            Column(name="age", type="INTEGER"),
            Column(name="status", type="TEXT")
        ])
        
        # Add test data
        db.insert("users", 
            {"name": "Alice", "age": 25, "status": "active"},
            {"name": "Bob", "age": 70, "status": "inactive"}, 
            {"name": "Charlie", "age": 30, "status": "pending"},
            {"name": "David", "age": 75, "status": "active"}
        )
        
        # Test update with OR operator - update where age > 65 OR status = 'pending'
        updated_count = db.update_where(
            "users", 
            {"status": "senior"}, 
            operator="OR", 
            age__gt=65, 
            status="pending"
        )
        
        # Should update Bob (age 70), Charlie (status pending), and David (age 75) = 3 records
        assert updated_count == 3
        
        # Verify results
        seniors = db.query("SELECT COUNT(*) as count FROM users WHERE status = 'senior'")
        assert seniors[0]["count"] == 3
        
        # Reset data for delete test - update all records to active
        # First get all user IDs, then update them individually
        all_user_ids = db.query("SELECT id FROM users")
        user_ids = [user["id"] for user in all_user_ids]
        updates = [{"id": uid, "status": "active"} for uid in user_ids] 
        db.update("users", *updates)
        db.insert("users", {"name": "Eve", "age": 80, "status": "inactive"})
        
        # Test delete with OR operator - delete where age > 70 OR status = 'inactive'
        deleted_count = db.delete_where("users", operator="OR", age__gt=70, status="inactive")
        
        # Should delete:
        # - David (age 75 > 70) - from the original data after status reset
        # - Eve (age 80 > 70 OR status = 'inactive')
        # Should NOT delete:
        # - Alice (age 25, status active) - neither condition matches
        # - Bob (age 70, status active) - 70 is not > 70, status is not inactive
        # - Charlie (age 30, status active) - neither condition matches
        assert deleted_count == 2
        
        # Verify remaining records
        remaining_count = db.query("SELECT COUNT(*) as count FROM users")[0]["count"]
        assert remaining_count == 3  # Alice, Bob, Charlie should remain
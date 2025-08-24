#!/usr/bin/env python3
"""
Branch workflow example.

This example demonstrates:
- Creating feature branches
- Making schema changes safely
- Testing on branches
- Merging changes to main
"""

import cinchdb
from cinchdb.models import Column
import json
from datetime import datetime


def create_initial_schema(db):
    """Create the initial schema on main branch."""
    print("Setting up initial schema...")

    try:
        # Users table
        db.create_table(
            "users",
            [
                Column(name="email", type="TEXT"),
                Column(name="name", type="TEXT"),
                Column(name="role", type="TEXT"),
            ],
        )

        # Products table
        db.create_table(
            "products",
            [
                Column(name="name", type="TEXT"),
                Column(name="price", type="REAL"),
                Column(name="stock", type="INTEGER"),
            ],
        )

        print("✓ Initial schema created")
    except:
        print("✓ Schema already exists")


def feature_add_reviews(db):
    """Add product reviews feature on a branch."""
    print("\n--- Feature: Product Reviews ---")

    if not db.is_local:
        print("Branch operations require local access")
        return

    # Create feature branch
    feature_branch = "feature.product-reviews"
    print(f"Creating branch: {feature_branch}")

    try:
        db.branches.create_branch(feature_branch)
    except:
        print("Branch already exists")

    # Create new instance for feature branch
    feature_db = cinchdb.connect(db.database, branch=feature_branch)
    print(f"Connected to branch: {feature_branch}")

    # Add reviews table
    print("Adding reviews table...")
    feature_db.create_table(
        "reviews",
        [
            Column(name="product_id", type="TEXT"),
            Column(name="user_id", type="TEXT"),
            Column(name="rating", type="INTEGER"),
            Column(name="comment", type="TEXT", nullable=True),
            Column(name="verified_purchase", type="BOOLEAN"),
        ],
    )

    # Add review count to products
    print("Adding review_count column to products...")
    if feature_db.is_local:
        feature_db.columns.add_column(
            "products", Column(name="review_count", type="INTEGER", nullable=True)
        )
        feature_db.columns.add_column(
            "products", Column(name="average_rating", type="REAL", nullable=True)
        )

    # Test the feature
    print("\nTesting on feature branch...")

    # Insert test data
    user = feature_db.insert(
        "users",
        {"email": "reviewer@example.com", "name": "Test Reviewer", "role": "customer"},
    )

    product = feature_db.insert(
        "products",
        {
            "name": "Test Product",
            "price": 29.99,
            "stock": 100,
            "review_count": 0,
            "average_rating": None,
        },
    )

    # Add reviews
    reviews = [
        {"rating": 5, "comment": "Excellent product!", "verified": True},
        {"rating": 4, "comment": "Good value", "verified": True},
        {"rating": 5, "comment": "Highly recommend", "verified": False},
    ]

    for r in reviews:
        feature_db.insert(
            "reviews",
            {
                "product_id": product["id"],
                "user_id": user["id"],
                "rating": r["rating"],
                "comment": r["comment"],
                "verified_purchase": r["verified"],
            },
        )

    # Update product stats
    stats = feature_db.query(
        """
        SELECT COUNT(*) as count, AVG(rating) as avg_rating
        FROM reviews
        WHERE product_id = ?
    """,
        [product["id"]],
    )[0]

    feature_db.update(
        "products",
        product["id"],
        {"review_count": stats["count"], "average_rating": stats["avg_rating"]},
    )

    # Verify
    updated_product = feature_db.query(
        "SELECT * FROM products WHERE id = ?", [product["id"]]
    )[0]

    print(f"✓ Product has {updated_product['review_count']} reviews")
    print(f"✓ Average rating: {updated_product['average_rating']:.1f}")

    return feature_branch


def feature_add_inventory(db):
    """Add inventory tracking feature."""
    print("\n--- Feature: Inventory Tracking ---")

    if not db.is_local:
        print("Branch operations require local access")
        return

    # Create feature branch
    feature_branch = "feature.inventory-tracking"
    print(f"Creating branch: {feature_branch}")

    try:
        db.branches.create_branch(feature_branch)
    except:
        print("Branch already exists")

    # Create new instance for feature branch
    feature_db = cinchdb.connect(db.database, branch=feature_branch)
    print(f"Connected to branch: {feature_branch}")

    # Add inventory movements table
    print("Adding inventory_movements table...")
    feature_db.create_table(
        "inventory_movements",
        [
            Column(name="product_id", type="TEXT"),
            Column(name="quantity", type="INTEGER"),
            Column(name="movement_type", type="TEXT"),  # 'in' or 'out'
            Column(name="reason", type="TEXT"),
            Column(name="reference_id", type="TEXT", nullable=True),
        ],
    )

    # Add trigger view for low stock
    print("Creating low_stock_products view...")
    feature_db.query("""
        CREATE VIEW low_stock_products AS
        SELECT * FROM products
        WHERE stock < 10
        ORDER BY stock ASC
    """)

    # Test the feature
    print("\nTesting inventory tracking...")

    # Add some movements
    product = feature_db.query("SELECT * FROM products LIMIT 1")[0]

    movements = [
        {"qty": 50, "type": "in", "reason": "Purchase Order #123"},
        {"qty": -10, "type": "out", "reason": "Sale Order #456"},
        {"qty": -5, "type": "out", "reason": "Sale Order #457"},
    ]

    for m in movements:
        feature_db.insert(
            "inventory_movements",
            {
                "product_id": product["id"],
                "quantity": abs(m["qty"]),
                "movement_type": m["type"],
                "reason": m["reason"],
            },
        )

        # Update stock
        new_stock = product["stock"] + m["qty"]
        feature_db.update("products", product["id"], {"stock": new_stock})
        product["stock"] = new_stock

    print(f"✓ Recorded {len(movements)} inventory movements")
    print(f"✓ Final stock: {product['stock']}")

    return feature_branch


def show_branch_changes(db, branch_name):
    """Display changes made in a branch."""
    if not db.is_local:
        return

    print(f"\nChanges in {branch_name}:")

    # Get changes file
    changes_path = (
        db.project_dir
        / ".cinchdb"
        / "databases"
        / db.database
        / "branches"
        / branch_name
        / "changes.json"
    )

    if changes_path.exists():
        with open(changes_path) as f:
            changes = json.load(f)

        for i, change in enumerate(changes, 1):
            change_type = change["type"]
            if change_type == "CREATE_TABLE":
                print(f"  {i}. Created table '{change['details']['table']}'")
            elif change_type == "ADD_COLUMN":
                print(
                    f"  {i}. Added column '{change['details']['column']['name']}' to '{change['details']['table']}'"
                )
            elif change_type == "CREATE_VIEW":
                print(f"  {i}. Created view '{change['details']['view']}'")


def merge_features(db):
    """Merge feature branches to main."""
    print("\n--- Merging Features ---")

    if not db.is_local:
        print("Merge operations require local access")
        return

    # Show current main schema
    main_db = cinchdb.connect(db.database, branch="main")
    tables = main_db.query("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"Tables on main: {[t['name'] for t in tables]}")

    # Merge product reviews
    print("\nMerging feature.product-reviews...")
    try:
        db.merge.merge_branches("feature.product-reviews", "main")
        print("✓ Successfully merged product reviews feature")
    except Exception as e:
        print(f"✗ Merge failed: {e}")

    # Merge inventory tracking
    print("\nMerging feature.inventory-tracking...")
    try:
        db.merge.merge_branches("feature.inventory-tracking", "main")
        print("✓ Successfully merged inventory tracking feature")
    except Exception as e:
        print(f"✗ Merge failed: {e}")

    # Verify main now has all features
    tables = main_db.query("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"\nTables on main after merge: {[t['name'] for t in tables]}")

    # Check columns
    columns = main_db.query("PRAGMA table_info(products)")
    column_names = [c["name"] for c in columns]
    print(f"Product columns: {column_names}")


def main():
    print("Branch Workflow Example")
    print("=" * 50)

    # Connect to database
    db = cinchdb.connect("branch_example")

    # Set up initial schema
    create_initial_schema(db)

    # Work on features in parallel
    reviews_branch = feature_add_reviews(db)
    inventory_branch = feature_add_inventory(db)

    # Show what changed
    if db.is_local:
        show_branch_changes(db, reviews_branch)
        show_branch_changes(db, inventory_branch)

    # Merge features
    merge_features(db)

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()

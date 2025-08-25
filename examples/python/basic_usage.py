#!/usr/bin/env python3
"""
Basic CinchDB usage example.

This example demonstrates:
- Connecting to a database
- Creating tables
- Inserting data
- Querying data
- Updating records
- Working with branches
"""

import cinchdb
from cinchdb.models import Column
from datetime import datetime


def main():
    # Connect to local database
    db = cinchdb.connect("example_app")

    # Create a users table
    print("Creating users table...")
    db.create_table(
        "users",
        [
            Column(name="username", type="TEXT"),
            Column(name="email", type="TEXT"),
            Column(name="full_name", type="TEXT", nullable=True),
            Column(name="active", type="BOOLEAN"),
        ],
    )

    # Insert some users
    print("\nInserting users...")
    users = [
        {
            "username": "alice",
            "email": "alice@example.com",
            "full_name": "Alice Smith",
            "active": True,
        },
        {
            "username": "bob",
            "email": "bob@example.com",
            "full_name": "Bob Jones",
            "active": True,
        },
        {"username": "charlie", "email": "charlie@example.com", "active": False},
    ]

    # Insert all users at once using batch insert
    inserted_users = db.insert("users", *users)
    for user in inserted_users:
        print(f"Created user: {user['username']} with ID: {user['id']}")

    # Query all users
    print("\nAll users:")
    all_users = db.query("SELECT * FROM users")
    for user in all_users:
        print(f"- {user['username']}: {user['email']} (Active: {user['active']})")

    # Query active users
    print("\nActive users:")
    active_users = db.query("SELECT * FROM users WHERE active = ?", [True])
    for user in active_users:
        print(f"- {user['username']}")

    # Update a user
    print("\nUpdating charlie's status...")
    charlie = db.query("SELECT * FROM users WHERE username = ?", ["charlie"])[0]
    updated = db.update(
        "users", charlie["id"], {"active": True, "full_name": "Charlie Brown"}
    )
    print(f"Updated: {updated['username']} is now active")

    # Create a branch for new features
    print("\nCreating feature branch...")
    if db.is_local:
        db.branches.create_branch("feature.add-profiles")

    # Create instance for feature branch
    feature_db = cinchdb.connect("example_app", branch="feature.add-profiles")

    # Add profiles table on feature branch
    print("Adding profiles table on feature branch...")
    feature_db.create_table(
        "profiles",
        [
            Column(name="user_id", type="TEXT"),
            Column(name="bio", type="TEXT", nullable=True),
            Column(name="website", type="TEXT", nullable=True),
            Column(name="joined_date", type="TEXT"),
        ],
    )

    # Add sample profile
    profile = feature_db.insert(
        "profiles",
        {
            "user_id": alice["id"],
            "bio": "Software developer and coffee enthusiast",
            "website": "https://alice.example.com",
            "joined_date": datetime.now().isoformat(),
        },
    )
    print(f"Created profile for user: {alice['username']}")

    # Query joined data on feature branch
    print("\nUsers with profiles (feature branch):")
    user_profiles = feature_db.query("""
        SELECT u.username, u.email, p.bio
        FROM users u
        LEFT JOIN profiles p ON u.id = p.user_id
    """)

    for row in user_profiles:
        bio = row["bio"] or "No profile"
        print(f"- {row['username']}: {bio}")

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()

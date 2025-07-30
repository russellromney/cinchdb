#!/bin/bash
# CinchDB CLI Getting Started Example

echo "CinchDB CLI Getting Started"
echo "==========================="
echo

# Initialize a new project
echo "1. Initializing new CinchDB project..."
cinch init example_project
cd example_project

# Show project structure
echo -e "\n2. Project structure:"
ls -la .cinchdb/

# Create a users table
echo -e "\n3. Creating users table..."
cinch table create users \
  username:TEXT \
  email:TEXT \
  full_name:TEXT? \
  is_active:BOOLEAN

# List tables
echo -e "\n4. Tables in database:"
cinch table list

# Show table info
echo -e "\n5. Users table structure:"
cinch table info users

# Insert some data
echo -e "\n6. Inserting users..."
cinch query "INSERT INTO users (username, email, full_name, is_active) VALUES ('alice', 'alice@example.com', 'Alice Smith', true)"
cinch query "INSERT INTO users (username, email, full_name, is_active) VALUES ('bob', 'bob@example.com', 'Bob Jones', true)"
cinch query "INSERT INTO users (username, email, is_active) VALUES ('charlie', 'charlie@example.com', false)"

# Query data
echo -e "\n7. All users:"
cinch query "SELECT * FROM users"

# Query with condition
echo -e "\n8. Active users only:"
cinch query "SELECT username, email FROM users WHERE is_active = true"

# Create a branch for new features
echo -e "\n9. Creating feature branch..."
cinch branch create feature.add-profiles

# Switch to feature branch
echo -e "\n10. Switching to feature branch..."
cinch branch switch feature.add-profiles

# Add profiles table on branch
echo -e "\n11. Creating profiles table on feature branch..."
cinch table create profiles \
  user_id:TEXT \
  bio:TEXT? \
  website:TEXT? \
  twitter:TEXT? \
  github:TEXT?

# Add column to existing table
echo -e "\n12. Adding column to users table..."
cinch column add users last_login:TEXT?

# Show branch changes
echo -e "\n13. Changes in feature branch:"
cinch branch changes

# Switch back to main
echo -e "\n14. Switching back to main branch..."
cinch branch switch main

# Verify profiles table doesn't exist on main
echo -e "\n15. Tables on main branch:"
cinch table list

# Merge feature branch
echo -e "\n16. Merging feature branch..."
cinch branch merge feature.add-profiles main

# Verify tables after merge
echo -e "\n17. Tables on main after merge:"
cinch table list

# Create a view
echo -e "\n18. Creating active users view..."
cinch view create active_users "SELECT username, email, last_login FROM users WHERE is_active = true"

# Query the view
echo -e "\n19. Querying active users view:"
cinch query "SELECT * FROM active_users"

# Multi-tenant example
echo -e "\n20. Creating tenants..."
cinch tenant create customer_a
cinch tenant create customer_b

# Insert tenant-specific data
echo -e "\n21. Adding data to customer_a tenant..."
cinch query "INSERT INTO users (username, email, is_active) VALUES ('customer_a_user', 'user@customer-a.com', true)" --tenant customer_a

# Query tenant data
echo -e "\n22. Users in customer_a tenant:"
cinch query "SELECT * FROM users" --tenant customer_a

echo -e "\n23. Users in main tenant (original data):"
cinch query "SELECT * FROM users" --tenant main

echo -e "\nGetting started example completed!"
echo "Try these next:"
echo "  - cinch table create <name> <columns...>"
echo "  - cinch branch create <name>"
echo "  - cinch remote add <alias> --url <url> --key <key>"
echo "  - cinch codegen generate python"
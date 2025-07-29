#!/bin/bash
# CinchDB Branch Workflow Example

echo "CinchDB Branch Workflow Example"
echo "==============================="
echo

# Function to pause between steps
pause() {
    echo -e "\nPress Enter to continue..."
    read
}

# Initialize project
echo "Setting up project..."
cinch init branch_demo
cd branch_demo

# Create initial schema on main
echo -e "\n1. Creating initial schema on main branch..."
cinch table create users \
  email:TEXT \
  name:TEXT \
  role:TEXT

cinch table create products \
  name:TEXT \
  price:REAL \
  stock:INTEGER \
  category:TEXT

echo "Initial tables created:"
cinch table list

pause

# Feature 1: Add user authentication
echo -e "\n2. Feature 1: Adding user authentication..."
cinch branch create feature/user-auth
cinch branch switch feature/user-auth

echo "Creating auth tables..."
cinch table create sessions \
  user_id:TEXT \
  token:TEXT \
  expires_at:TEXT \
  ip_address:TEXT?

cinch table create password_resets \
  user_id:TEXT \
  token:TEXT \
  expires_at:TEXT \
  used:BOOLEAN

cinch column add users password_hash:TEXT
cinch column add users email_verified:BOOLEAN

echo -e "\nTables on feature/user-auth branch:"
cinch table list

pause

# Feature 2: Add product reviews (parallel development)
echo -e "\n3. Feature 2: Adding product reviews (parallel to auth)..."
cinch branch switch main
cinch branch create feature/product-reviews
cinch branch switch feature/product-reviews

echo "Creating reviews table..."
cinch table create reviews \
  product_id:TEXT \
  user_id:TEXT \
  rating:INTEGER \
  title:TEXT \
  comment:TEXT? \
  helpful_count:INTEGER \
  verified_purchase:BOOLEAN

cinch column add products avg_rating:REAL?
cinch column add products review_count:INTEGER?

echo -e "\nCreating review summary view..."
cinch view create product_review_summary \
  "SELECT p.name, p.avg_rating, p.review_count, COUNT(r.id) as total_reviews \
   FROM products p \
   LEFT JOIN reviews r ON p.id = r.product_id \
   GROUP BY p.id"

echo -e "\nChanges in feature/product-reviews:"
cinch branch changes

pause

# Show branch status
echo -e "\n4. Current branch status..."
echo "All branches:"
cinch branch list

echo -e "\nMain branch tables:"
cinch branch switch main
cinch table list

echo -e "\nFeature branches have additional tables"

pause

# Merge first feature
echo -e "\n5. Merging user authentication feature..."
cinch branch merge feature/user-auth main

echo "Tables on main after first merge:"
cinch table list

pause

# Merge second feature
echo -e "\n6. Merging product reviews feature..."
cinch branch merge feature/product-reviews main

echo "Tables on main after second merge:"
cinch table list

echo -e "\nAll views:"
cinch view list

pause

# Hotfix example
echo -e "\n7. Hotfix example..."
cinch branch create hotfix/security-patch
cinch branch switch hotfix/security-patch

echo "Adding security fields..."
cinch column add users failed_login_attempts:INTEGER?
cinch column add users locked_until:TEXT?

echo "Creating security audit table..."
cinch table create security_audit \
  user_id:TEXT? \
  action:TEXT \
  ip_address:TEXT \
  user_agent:TEXT? \
  success:BOOLEAN

echo -e "\nHotfix changes:"
cinch branch changes

echo -e "\nMerging hotfix..."
cinch branch switch main
cinch branch merge hotfix/security-patch main

pause

# Clean up merged branches
echo -e "\n8. Cleaning up merged branches..."
echo "Deleting completed feature branches..."
cinch branch delete feature/user-auth --force
cinch branch delete feature/product-reviews --force
cinch branch delete hotfix/security-patch --force

echo -e "\nRemaining branches:"
cinch branch list

# Final schema
echo -e "\n9. Final schema on main branch:"
echo -e "\nTables:"
cinch table list

echo -e "\nUsers table structure:"
cinch table info users

echo -e "\nProducts table structure:"
cinch table info products

echo -e "\nBranch workflow example completed!"
echo -e "\nKey takeaways:"
echo "  - Branches allow parallel feature development"
echo "  - Changes are isolated until merge"
echo "  - Multiple developers can work without conflicts"
echo "  - Hotfixes can be applied quickly"
echo "  - Clean up branches after merging"
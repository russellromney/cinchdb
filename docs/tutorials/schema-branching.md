# Schema Branching Workflow

Learn how to use CinchDB's branching system for safe schema evolution.

## Overview

Schema branching allows you to:
- Develop schema changes in isolation
- Test changes before deployment
- Collaborate on database design
- Roll back if needed

## Basic Branching Workflow

### 1. Create Feature Branch
```bash
# Start from main
cinch branch switch main

# Create feature branch
cinch branch create feature.add-user-profiles

# Switch to new branch
cinch branch switch feature.add-user-profiles
```

### 2. Make Schema Changes
```bash
# Add new table
cinch table create user_profiles \
  user_id:TEXT \
  bio:TEXT? \
  website:TEXT? \
  location:TEXT? \
  avatar_url:TEXT?

# Add column to existing table
cinch column add users profile_complete:BOOLEAN
```

### 3. Test Changes
```bash
# Insert test data
cinch query "INSERT INTO user_profiles (user_id, bio) \
  VALUES ('123', 'Software developer')"

# Verify schema
cinch table info user_profiles
```

### 4. Merge to Main
```bash
# Review changes
cinch branch changes

# Merge when ready
cinch branch merge-into-main
```

## Advanced Patterns

### Parallel Development

Multiple developers can work on different features simultaneously:

```python
import cinchdb

# Developer A: Working on user features
dev_a_db = cinchdb.connect("myapp", branch="feature.user-enhancements")
dev_a_db.create_table("user_preferences", [
    Column(name="user_id", type="TEXT"),
    Column(name="theme", type="TEXT"),
    Column(name="notifications", type="BOOLEAN")
])

# Developer B: Working on product features
dev_b_db = cinchdb.connect("myapp", branch="feature.product-catalog")
dev_b_db.create_table("product_categories", [
    Column(name="name", type="TEXT"),
    Column(name="parent_id", type="TEXT", nullable=True),
    Column(name="active", type="BOOLEAN")
])

# Both can merge independently when ready
```

### Feature Flags with Branches

Test new schemas with feature flags:

```python
class FeatureBranchManager:
    def __init__(self, base_db):
        self.base_db = base_db
        self.feature_flags = {}
    
    def enable_feature(self, feature_name: str, branch_name: str):
        """Enable a feature branch for testing."""
        self.feature_flags[feature_name] = branch_name
    
    def get_db_for_feature(self, feature_name: str):
        """Get database connection for feature."""
        if feature_name in self.feature_flags:
            branch = self.feature_flags[feature_name]
            return cinchdb.connect(self.base_db.database, branch=branch)
        return self.base_db
    
    def query_with_feature(self, feature_name: str, sql: str, params=None):
        """Execute query on appropriate branch."""
        db = self.get_db_for_feature(feature_name)
        return db.query(sql, params)

# Usage
manager = FeatureBranchManager(cinchdb.connect("myapp"))
manager.enable_feature("new_analytics", "feature.analytics-v2")

# Queries use feature branch if enabled
data = manager.query_with_feature("new_analytics", 
    "SELECT * FROM analytics_events")
```

## Schema Migration Patterns

### 1. Additive Changes (Safe)

Always safe to merge:

```bash
# Add new tables
cinch table create audit_logs event:TEXT user_id:TEXT data:TEXT?

# Add nullable columns
cinch column add users last_seen:TEXT?

# Add indexes
cinch query "CREATE INDEX idx_users_email ON users(email)"
```

### 2. Breaking Changes (Careful Planning)

Require migration strategy:

```python
import cinchdb

def migrate_column_type(db, branch_name: str):
    """Example: Change column type safely."""
    # Create branch
    if db.is_local:
        db.branches.create_branch(branch_name)
    
    branch_db = cinchdb.connect(db.database, branch=branch_name)
    
    # Step 1: Add new column
    branch_db.query("ALTER TABLE products ADD COLUMN price_new REAL")
    
    # Step 2: Migrate data
    branch_db.query("""
        UPDATE products 
        SET price_new = CAST(price AS REAL)
    """)
    
    # Step 3: Drop old column (if possible)
    # Note: SQLite doesn't support DROP COLUMN directly
    
    # Step 4: Test thoroughly before merge
    test_results = branch_db.query("SELECT * FROM products LIMIT 10")
    validate_migration(test_results)
```

### 3. Renaming Strategy

```bash
# Create branch for rename
cinch branch create refactor.rename-columns

# Add new column
cinch column add users display_name:TEXT?

# Copy data
cinch query "UPDATE users SET display_name = name"

# Update application to use new column
# Later: remove old column in another branch
```

## Testing on Branches

### Automated Testing

```python
import pytest
import cinchdb

class TestSchemaChanges:
    def test_new_user_profiles_table(self):
        # Connect to feature branch
        db = cinchdb.connect("myapp", branch="feature.add-user-profiles")
        
        # Test table exists
        tables = db.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'"
        )
        assert len(tables) == 1
        
        # Test operations
        profile = db.insert("user_profiles", {
            "user_id": "test-123",
            "bio": "Test bio"
        })
        assert profile["id"] is not None
        
        # Test constraints
        with pytest.raises(Exception):
            # user_id should be required
            db.insert("user_profiles", {"bio": "No user"})

def run_branch_tests(branch_name: str):
    """Run all tests against a branch."""
    db = cinchdb.connect("myapp", branch=branch_name)
    
    # Run schema validation
    validate_schema(db)
    
    # Run data integrity checks
    check_data_integrity(db)
    
    # Run performance tests
    test_query_performance(db)
    
    return True
```

### Manual Testing Checklist

```python
import cinchdb

def branch_testing_checklist(db, branch_name: str):
    """Complete testing checklist for branch."""
    branch_db = cinchdb.connect(db.database, branch=branch_name)
    checklist = {
        "schema_valid": False,
        "queries_work": False,
        "performance_ok": False,
        "data_integrity": False,
        "backwards_compatible": False
    }
    
    # 1. Schema validation
    try:
        tables = branch_db.query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        checklist["schema_valid"] = len(tables) > 0
    except:
        pass
    
    # 2. Query testing
    try:
        # Test main queries
        branch_db.query("SELECT * FROM users LIMIT 1")
        checklist["queries_work"] = True
    except:
        pass
    
    # 3. Performance testing
    import time
    start = time.time()
    branch_db.query("SELECT COUNT(*) FROM users")
    elapsed = time.time() - start
    checklist["performance_ok"] = elapsed < 1.0
    
    # 4. Data integrity
    try:
        result = branch_db.query("""
            SELECT COUNT(*) as orphans
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            WHERE u.id IS NULL
        """)
        checklist["data_integrity"] = result[0]["orphans"] == 0
    except:
        pass
    
    # 5. Backwards compatibility
    try:
        # Check if old queries still work
        main_db = cinchdb.connect(db.database, branch="main")
        main_queries = get_application_queries()
        
        all_work = True
        for query in main_queries:
            try:
                branch_db.query(query)
            except:
                all_work = False
                break
        
        checklist["backwards_compatible"] = all_work
    except:
        pass
    
    return checklist
```

## Merge Strategies

### 1. Fast-Forward Merge

When branch has all changes from main:

```bash
# No conflicts - direct merge
cinch branch merge feature.simple-addition main
```

### 2. Review Before Merge

```python
def review_branch_changes(db, source_branch: str, target_branch: str = "main"):
    """Review changes before merge."""
    if not db.is_local:
        print("Review requires local access")
        return
    
    # Get change list
    changes = db.branches.get_branch_changes(source_branch)
    
    print(f"Changes to merge from {source_branch}:")
    for i, change in enumerate(changes, 1):
        print(f"{i}. {change.type}: {change.description}")
    
    # Check for risks
    risks = []
    for change in changes:
        if change.type == "DROP_TABLE":
            risks.append(f"⚠️  Dropping table: {change.table_name}")
        elif change.type == "DROP_COLUMN":
            risks.append(f"⚠️  Dropping column: {change.column_name}")
    
    if risks:
        print("\nPotential risks:")
        for risk in risks:
            print(risk)
    
    # Confirm
    response = input("\nProceed with merge? (y/n): ")
    return response.lower() == 'y'

# Usage
if review_branch_changes(db, "feature.risky-change"):
    db.merge.merge_branches("feature.risky-change", "main")
```

### 3. Staged Rollout

```python
import cinchdb

def staged_branch_rollout(db, branch_name: str, tenant_groups: dict):
    """Roll out branch changes in stages."""
    # Stage 1: Internal testing
    test_tenants = tenant_groups["test"]
    for tenant in test_tenants:
        print(f"Testing on tenant: {tenant}")
        test_db = cinchdb.connect(db.database, branch=branch_name, tenant=tenant)
        # Run tests...
    
    # Stage 2: Beta customers
    if input("Proceed to beta? (y/n): ") == 'y':
        beta_tenants = tenant_groups["beta"]
        for tenant in beta_tenants:
            # Apply to beta tenants
            pass
    
    # Stage 3: Full rollout
    if input("Proceed to production? (y/n): ") == 'y':
        db.merge.merge_branches(branch_name, "main")
```

## Rollback Procedures

### Branch Deletion

```bash
# If merge hasn't happened, just delete branch
cinch branch delete feature.bad-idea --force
```

### Post-Merge Rollback

```python
import cinchdb
import time

def create_rollback_branch(db, changes_to_reverse):
    """Create branch to reverse changes."""
    if not db.is_local:
        raise RuntimeError("Rollback requires local access")
    
    # Create rollback branch
    rollback_branch = f"rollback/{int(time.time())}"
    db.branches.create_branch(rollback_branch)
    
    rollback_db = cinchdb.connect(db.database, branch=rollback_branch)
    
    # Reverse each change
    for change in reversed(changes_to_reverse):
        if change.type == "CREATE_TABLE":
            rollback_db.query(f"DROP TABLE IF EXISTS {change.table_name}")
        elif change.type == "ADD_COLUMN":
            # SQLite doesn't support DROP COLUMN easily
            print(f"Warning: Cannot drop column {change.column_name}")
        # ... handle other change types
    
    return rollback_branch
```

## Best Practices

### 1. Branch Naming
```bash
feature.description    # New features
bugfix.issue-123      # Bug fixes  
hotfix.urgent-fix     # Urgent production fixes
refactor.cleanup      # Code improvements
experiment.idea       # Experimental changes
```

### 2. Small, Focused Changes
```bash
# Good: Single purpose
cinch branch create feature.add-user-avatars

# Bad: Too many changes
cinch branch create feature.everything-update
```

### 3. Document Changes
```python
import json
from datetime import datetime

# Create change documentation
def document_branch(branch_name: str, description: str, changes: list):
    doc = {
        "branch": branch_name,
        "created": datetime.now().isoformat(),
        "description": description,
        "changes": changes,
        "testing": "Tested on dev environment",
        "rollback": "Drop new tables if needed"
    }
    
    with open(f"docs/branches/{branch_name}.json", "w") as f:
        json.dump(doc, f, indent=2)
```

### 4. Clean Up Merged Branches
```bash
# After successful merge
cinch branch delete feature.completed-feature

# List old branches
cinch branch list | grep feature.
```

## Next Steps

- Build a [Multi-Tenant App](multi-tenant-app.md)
- Set up [Remote Deployment](remote-deployment.md)
- Learn about [Branching Concepts](../concepts/branching.md)
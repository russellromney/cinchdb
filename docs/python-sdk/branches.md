# Branch Operations

Database branching with the Python SDK.

## Problem → Solution

**Problem**: Need to develop schema changes safely without breaking production  
**Solution**: CinchDB branches isolate changes, enable testing, and allow safe merging

## Quick Reference

| Operation | Method | Example |
|-----------|--------|---------|
| Connect to branch | `cinchdb.connect()` | `cinchdb.connect("myapp", branch="dev")` |
| List branches | `db.list_branches()` | `db.list_branches()` |
| Create branch | `db.create_branch()` | `db.create_branch("feature-1")` |
| Merge branches | `db.merge_branches()` | `db.merge_branches("feature-1", "main")` |

## Connecting to Branches

```python
# Connect to different branches
main_db = cinchdb.connect("myapp", branch="main")
dev_db = cinchdb.connect("myapp", branch="development")
feature_db = cinchdb.connect("myapp", branch="feature.new-schema")

# Compare schemas between branches
main_tables = set(t["name"] for t in main_db.query("SELECT name FROM sqlite_master WHERE type='table'"))
feature_tables = set(t["name"] for t in feature_db.query("SELECT name FROM sqlite_master WHERE type='table'"))
new_tables = feature_tables - main_tables
print(f"New tables in feature branch: {new_tables}")
```

## Branch Management

```python
db = cinchdb.connect("myapp")

# List all branches
branches = db.list_branches()
for branch in branches:
    print(f"Branch: {branch.name} (created: {branch.created_at})")

# Create new branch
db.create_branch("feature.add-products")

# Create from specific source
db.create_branch("hotfix.bug-123", source_branch="main")

# Delete old branch (cannot delete main or active branch)
db.delete_branch("old-feature")
```

## Tracking Changes

```python
# Make changes on feature branch
feature_db = cinchdb.connect("myapp", branch="feature.new-schema")
feature_db.create_table("products", [Column(name="name", type="TEXT"), Column(name="price", type="REAL")])

# View changes
changes = feature_db.get_branch_changes("feature.new-schema")
for change in changes:
    print(f"{change.type}: {change.description}")

# Compare schemas between branches
def compare_schemas(db1, db2):
    tables1 = set(row["name"] for row in db1.query("SELECT name FROM sqlite_master WHERE type='table'"))
    tables2 = set(row["name"] for row in db2.query("SELECT name FROM sqlite_master WHERE type='table'"))
    
    return {
        "only_in_first": tables1 - tables2,
        "only_in_second": tables2 - tables1,
        "in_both": tables1 & tables2
    }

# Usage
main_db = cinchdb.connect("myapp", branch="main")
feature_db = cinchdb.connect("myapp", branch="feature.new")
diff = compare_schemas(main_db, feature_db)
print(f"New in feature: {diff['only_in_second']}")
```

## Merging Branches

```python
# Simple merge
db = cinchdb.connect("myapp")
db.merge_branches("feature.add-users", "main")

# Safe merge with validation
def safe_merge(db, source_branch: str, target_branch: str = "main"):
    """Safely merge with validation."""
    # Check if merge is possible
    if not db.can_merge(source_branch, target_branch):
        print("Cannot merge - branches have diverged")
        return False
    
    # Review changes first
    changes = db.get_branch_changes(source_branch)
    print(f"Changes to merge: {len(changes)}")
    for change in changes:
        print(f"  - {change.description}")
    
    # Perform merge
    try:
        db.merge_branches(source_branch, target_branch)
        print(f"Successfully merged {source_branch} into {target_branch}")
        return True
    except Exception as e:
        print(f"Merge failed: {e}")
        return False
```

## Common Workflows

### Feature Development
```python
# Standard feature workflow
db = cinchdb.connect("myapp")
# 1. Create feature branch
db.create_branch("feature.shopping-cart")

# 2. Make changes
feature_db = cinchdb.connect("myapp", branch="feature.shopping-cart")
feature_db.create_table("cart_items", [
    Column(name="user_id", type="TEXT"),
    Column(name="product_id", type="TEXT"),
    Column(name="quantity", type="INTEGER")
])

# 3. Test changes
test_data = feature_db.insert("cart_items", {"user_id": "test-user", "product_id": "test-product", "quantity": 2})

# 4. Merge when ready
db.merge_branches("feature.shopping-cart", "main")
```

### Hotfix Workflow
```python
# Quick production fix
db = cinchdb.connect("myapp")
# 1. Create hotfix branch
db.create_branch("hotfix.critical-bug", source_branch="main")

# 2. Apply fix
hotfix_db = cinchdb.connect("myapp", branch="hotfix.critical-bug")
hotfix_db.add_column("users", Column(name="email_verified", type="BOOLEAN", default=False))

# 3. Merge immediately
db.merge_branches("hotfix.critical-bug", "main")
```

### Experimental Development
```python
# Safe experimentation
db = cinchdb.connect("myapp")
db.create_branch("experimental.new-algorithm")
exp_db = cinchdb.connect("myapp", branch="experimental.new-algorithm")

try:
    # Try risky changes
    exp_db.create_table("experimental_data", [Column(name="result", type="TEXT")])
    results = exp_db.query("SELECT * FROM experimental_data")
    
    # Merge if successful, delete if not
    if validate_experiment(results):
        db.merge_branches("experimental.new-algorithm", "main")
    else:
        db.delete_branch("experimental.new-algorithm")
except Exception as e:
    print(f"Experiment failed: {e}")
    db.delete_branch("experimental.new-algorithm")
```

## Multi-Tenant Branching

**Schema changes apply to all tenants**: Branches affect schema, tenants isolate data.

```python
# Schema changes affect all tenants
db = cinchdb.connect("myapp")
db.create_branch("feature.tenant-settings")

# Make schema changes on branch
feature_db = cinchdb.connect("myapp", branch="feature.tenant-settings")
feature_db.create_table("tenant_settings", [Column(name="key", type="TEXT"), Column(name="value", type="TEXT")])

# Verify schema exists for all tenants on this branch
for tenant in ["main", "customer_a", "customer_b"]:
    tenant_db = cinchdb.connect("myapp", branch="feature.tenant-settings", tenant=tenant)
    tables = tenant_db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='tenant_settings'")
    assert len(tables) == 1  # Schema exists for all tenants
    
    # But data is isolated
    tenant_db.insert("tenant_settings", {"key": f"theme_{tenant}", "value": "dark"})
```

## Best Practices

### Naming Convention
- `feature.description` - New functionality
- `bugfix.issue-name` - Bug fixes
- `hotfix.urgent-fix` - Production emergencies
- `release.v1.2.3` - Release preparation
- `experimental.idea` - Risky experiments

**Include ticket numbers**: `feature.PROJ-123-add-payments`

### Standard Lifecycle
```python
def feature_lifecycle(db, feature_name: str, implement_func):
    """Complete feature development lifecycle."""
    branch_name = f"feature.{feature_name}"
    
    # Create → Implement → Test → Merge → Clean up
    db.create_branch(branch_name)
    feature_db = cinchdb.connect(db.database, branch=branch_name)
    
    try:
        implement_func(feature_db)
        print(f"Testing {feature_name}...")
        
        # Merge if successful
        db.merge_branches(branch_name, "main")
        db.delete_branch(branch_name)
        print(f"Feature {feature_name} completed")
    except Exception as e:
        print(f"Feature {feature_name} failed: {e}")
        # Branch remains for debugging
```

### Parallel Development
**Benefit**: Multiple developers work independently without conflicts.

```python
# Team can work on separate features simultaneously
branches = ["feature.auth", "feature.payments", "feature.shipping"]

for branch in branches:
    branch_db = cinchdb.connect("myapp", branch=branch)
    # Independent development, merge when ready
```


## Next Steps

- [Tenants](tenants.md) - Multi-tenant operations
- [Merge Concepts](../concepts/branching.md) - Understanding merges
- [Branch CLI](../cli/branch.md) - CLI branch commands
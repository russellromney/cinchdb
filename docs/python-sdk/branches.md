# Branch Operations

Work with database branches using the Python SDK.

## Switching Branches

### Create Branch Connection
```python
# Connect to specific branch
dev_db = cinchdb.connect("myapp", branch="development")

# Switch from existing connection
main_db = cinchdb.connect("myapp")
dev_db = main_db.switch_branch("development")
```

### Temporary Branch Context
```python
# Work with multiple branches
main_db = cinchdb.connect("myapp", branch="main")
feature_db = main_db.switch_branch("feature.new-schema")

# Compare schemas
main_tables = main_db.query("SELECT name FROM sqlite_master WHERE type='table'")
feature_tables = feature_db.query("SELECT name FROM sqlite_master WHERE type='table'")

new_tables = set(t["name"] for t in feature_tables) - set(t["name"] for t in main_tables)
print(f"New tables in feature branch: {new_tables}")
```

## Branch Management (Local Only)

### List Branches
```python
db = cinchdb.connect("myapp")

if db.is_local:
    branches = db.branches.list_branches()
    for branch in branches:
        print(f"Branch: {branch.name}")
        print(f"Created: {branch.created_at}")
```

### Create Branch
```python
if db.is_local:
    # Create from current branch
    db.branches.create_branch("feature.add-products")
    
    # Create from specific branch
    db.branches.create_branch("hotfix.bug-123", source_branch="main")
```

### Delete Branch
```python
if db.is_local:
    # Cannot delete main or active branch
    db.branches.delete_branch("old-feature")
```

## Working with Branch Changes

### Track Changes
```python
# Make changes on feature branch
feature_db = db.switch_branch("feature.new-schema")
feature_db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="price", type="REAL")
])

# View changes
if feature_db.is_local:
    changes = feature_db.branches.get_branch_changes("feature.new-schema")
    for change in changes:
        print(f"Change: {change.type} - {change.description}")
```

### Compare Branches
```python
def compare_schemas(db1, db2):
    """Compare schemas between two database connections."""
    # Get tables from both branches
    tables1 = set(row["name"] for row in db1.query(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ))
    tables2 = set(row["name"] for row in db2.query(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ))
    
    return {
        "only_in_first": tables1 - tables2,
        "only_in_second": tables2 - tables1,
        "in_both": tables1 & tables2
    }

# Compare main and feature branch
main_db = cinchdb.connect("myapp", branch="main")
feature_db = cinchdb.connect("myapp", branch="feature.new")
diff = compare_schemas(main_db, feature_db)
```

## Merging Branches (Local Only)

### Simple Merge
```python
if db.is_local:
    # Merge feature into main
    db.merge.merge_branches("feature.add-users", "main")
```

### Merge Workflow
```python
def safe_merge(db, source_branch: str, target_branch: str = "main"):
    """Safely merge branches with validation."""
    if not db.is_local:
        raise RuntimeError("Merging requires local connection")
    
    # Check if merge is possible
    can_merge = db.merge.can_merge(source_branch, target_branch)
    if not can_merge:
        print("Cannot merge - branches have diverged")
        return False
    
    # Review changes
    changes = db.branches.get_branch_changes(source_branch)
    print(f"Changes to merge: {len(changes)}")
    for change in changes:
        print(f"  - {change.description}")
    
    # Perform merge
    try:
        db.merge.merge_branches(source_branch, target_branch)
        print(f"Successfully merged {source_branch} into {target_branch}")
        return True
    except Exception as e:
        print(f"Merge failed: {e}")
        return False
```

## Branch Patterns

### Feature Development
```python
# 1. Create feature branch
db = cinchdb.connect("myapp")
feature_db = db.switch_branch("main").switch_branch("feature.shopping-cart")

# 2. Make changes
feature_db.create_table("cart_items", [
    Column(name="user_id", type="TEXT"),
    Column(name="product_id", type="TEXT"),
    Column(name="quantity", type="INTEGER")
])

# 3. Test changes
test_data = feature_db.insert("cart_items", {
    "user_id": "test-user",
    "product_id": "test-product",
    "quantity": 2
})

# 4. Merge when ready
if db.is_local:
    db.merge.merge_branches("feature.shopping-cart", "main")
```

### Hotfix Workflow
```python
# 1. Create hotfix from main
main_db = cinchdb.connect("myapp", branch="main")
if main_db.is_local:
    main_db.branches.create_branch("hotfix.critical-bug")

# 2. Switch to hotfix
hotfix_db = main_db.switch_branch("hotfix.critical-bug")

# 3. Apply fix
hotfix_db.query("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false")

# 4. Quick merge back
if main_db.is_local:
    main_db.merge.merge_branches("hotfix.critical-bug", "main")
```

### Experimental Features
```python
# Create experimental branch
exp_db = db.switch_branch("experimental.new-feature")

# Try risky changes
try:
    exp_db.create_table("experimental_data", [...])
    exp_db.query("CREATE TRIGGER ...")
    
    # Test thoroughly
    results = exp_db.query("SELECT * FROM experimental_data")
    
    if validate_results(results):
        # Merge if successful
        if db.is_local:
            db.merge.merge_branches("experimental.new-feature", "main")
    else:
        # Abandon if not working
        if db.is_local:
            db.branches.delete_branch("experimental.new-feature")
except Exception as e:
    print(f"Experiment failed: {e}")
    # Branch can be deleted without affecting main
```

## Multi-Tenant Branches

Branches apply to all tenants:

```python
# Create branch
feature_db = db.switch_branch("feature.multi-tenant-update")

# Changes apply to all tenants
feature_db.create_table("tenant_settings", [
    Column(name="key", type="TEXT"),
    Column(name="value", type="TEXT")
])

# Verify across tenants
for tenant in ["main", "customer_a", "customer_b"]:
    tenant_db = feature_db.switch_tenant(tenant)
    tables = tenant_db.query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tenant_settings'"
    )
    assert len(tables) == 1
```

## Best Practices

### 1. Branch Naming
```python
# Good branch names
"feature.user-authentication"
"bugfix.login-error"
"hotfix.security-patch"
"release.v2.0"
"experimental.new-algorithm"

# Include ticket numbers
"feature.PROJ-123-add-payments"
"bugfix.BUG-456-fix-crash"
```

### 2. Branch Lifecycle
```python
def feature_lifecycle(db, feature_name: str, implement_func):
    """Standard feature branch lifecycle."""
    branch_name = f"feature.{feature_name}"
    
    # Create branch
    if db.is_local:
        db.branches.create_branch(branch_name)
    
    # Switch to branch
    feature_db = db.switch_branch(branch_name)
    
    try:
        # Implement feature
        implement_func(feature_db)
        
        # Test (you would add real tests here)
        print(f"Testing {feature_name}...")
        
        # Merge if successful
        if db.is_local:
            db.merge.merge_branches(branch_name, "main")
            print(f"Merged {branch_name} to main")
            
            # Clean up
            db.branches.delete_branch(branch_name)
    except Exception as e:
        print(f"Feature {feature_name} failed: {e}")
        # Branch remains for debugging
```

### 3. Parallel Development
```python
# Multiple developers can work on separate branches
branches = ["feature.auth", "feature.payments", "feature.shipping"]

for branch in branches:
    branch_db = db.switch_branch(branch)
    # Each developer works independently
    # Merge when ready without conflicts
```

## Remote Branch Operations

With remote connections, use CLI or API:

```python
# Remote connections can switch branches
remote_db = cinchdb.connect_api(...)
prod_db = remote_db.switch_branch("production")
staging_db = remote_db.switch_branch("staging")

# But cannot create/merge branches
# Use CLI for remote branch management:
# cinch branch create feature.new --remote production
```

## Next Steps

- [Tenants](tenants.md) - Multi-tenant operations
- [Merge Concepts](../concepts/branching.md) - Understanding merges
- [Branch CLI](../cli/branch.md) - CLI branch commands
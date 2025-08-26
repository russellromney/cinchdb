# Tenant Operations

Multi-tenant data isolation with the Python SDK.

## Problem → Solution

**Problem**: Need to isolate customer data while sharing schema and infrastructure  
**Solution**: CinchDB tenants provide complete data isolation with automatic schema inheritance

## Quick Reference

| Operation | Method | Example |
|-----------|--------|---------|
| Connect to tenant | `cinchdb.connect()` | `cinchdb.connect("myapp", tenant="acme")` |
| List tenants | `db.tenants.list_tenants()` | Local only |
| Create tenant | `db.tenants.create_tenant()` | Local only |
| Delete tenant | `db.tenants.delete_tenant()` | Local only |

## Connecting to Tenants

```python
# Connect to specific tenant
tenant_db = cinchdb.connect("myapp", tenant="customer_a")
users = tenant_db.query("SELECT * FROM users")  # Only customer_a data

# Switch between tenants
customer_a = cinchdb.connect("myapp", tenant="customer_a")
customer_b = cinchdb.connect("myapp", tenant="customer_b")

customer_a.insert("users", {"name": "Alice", "email": "alice@customer-a.com"})
customer_b.insert("users", {"name": "Bob", "email": "bob@customer-b.com"})
```

## Tenant Management

```python
db = cinchdb.connect("myapp")

# List all tenants
tenants = db.tenants.list_tenants()
for tenant in tenants:
    print(f"Tenant: {tenant.name} at {tenant.db_path}")

# Create new tenant
db.tenants.create_tenant("customer_b")
customer_db = cinchdb.connect(db.database, tenant="customer_b")

# Copy tenant (with or without data)
db.tenants.copy_tenant("template", "new_customer", copy_data=True)

# Delete tenant (⚠️ Destroys all data)
db.tenants.delete_tenant("old_customer")
```

## Data Isolation

**Complete isolation**: Each tenant sees only their own data, shared schema.

```python
# Perfect isolation
tenant_a = cinchdb.connect("myapp", tenant="customer_a")
tenant_b = cinchdb.connect("myapp", tenant="customer_b")

tenant_a.insert("users", {"name": "Alice", "email": "alice@a.com"})
tenant_b.insert("users", {"name": "Bob", "email": "bob@b.com"})

# Each tenant sees only their data
a_users = tenant_a.query("SELECT * FROM users")  # Only Alice
b_users = tenant_b.query("SELECT * FROM users")  # Only Bob
assert len(a_users) == 1 and len(b_users) == 1

# Cross-tenant aggregation
def count_all_users(database, tenant_names):
    total = 0
    for tenant in tenant_names:
        tenant_db = cinchdb.connect(database, tenant=tenant)
        count = tenant_db.query("SELECT COUNT(*) as count FROM users")[0]["count"]
        total += count
    return total

total_users = count_all_users("myapp", ["customer_a", "customer_b"])
```

## Tenant Templates

**Pattern**: Create template tenant with default data, copy to new tenants.

```python
def setup_template(database):
    """Create template tenant with defaults."""
    template_db = cinchdb.connect(database, tenant="_template")
    
    # Add default settings (assuming settings table exists)
    defaults = [{"key": "theme", "value": "light"}, {"key": "timezone", "value": "UTC"}]
    for setting in defaults:
        template_db.insert("settings", setting)
    
    return template_db

def create_from_template(db, tenant_name):
    """Copy template to new tenant."""
    db.tenants.copy_tenant("_template", tenant_name)
    
    # Customize new tenant
    tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
    tenant_db.insert("settings", {"key": "company_name", "value": tenant_name})
    return tenant_db
```

## SaaS Customer Onboarding

**Pattern**: Create tenant, add admin user, initialize settings.

```python
def onboard_customer(database, customer_name, admin_email):
    """Complete customer onboarding."""
    db = cinchdb.connect(database)
    
    # Create isolated tenant
    db.tenants.create_tenant(customer_name)
    
    # Setup tenant
    tenant_db = cinchdb.connect(database, tenant=customer_name)
    
    # Create admin user
    admin = tenant_db.insert("users", {"email": admin_email, "role": "admin", "active": True})
    
    # Initialize company settings
    tenant_db.insert("company_settings", {
        "name": customer_name,
        "admin_user_id": admin["id"],
        "plan": "trial",
        "trial_ends": "datetime('now', '+30 days')"
    })
    
    return tenant_db

def get_tenant_stats(database, tenant_name):
    """Get tenant usage metrics."""
    tenant_db = cinchdb.connect(database, tenant=tenant_name)
    
    stats = {
        "user_count": tenant_db.query("SELECT COUNT(*) as count FROM users")[0]["count"],
        "storage_mb": 0  # Could calculate from file size if local
    }
    
    return stats

# Usage
customer_db = onboard_customer("myapp", "acme_corp", "admin@acme.com")
stats = get_tenant_stats("myapp", "acme_corp")
```


## Testing with Tenants

**Pattern**: Create temporary tenant, run tests, clean up.

```python
import time

def create_test_tenant(database, test_name):
    """Create isolated test tenant."""
    tenant_name = f"test_{test_name}_{int(time.time())}"
    db = cinchdb.connect(database)
    
    db.tenants.create_tenant(tenant_name)
    
    return cinchdb.connect(database, tenant=tenant_name), tenant_name

def cleanup_test_tenant(database, tenant_name):
    """Clean up after tests."""
    db = cinchdb.connect(database)
    if tenant_name.startswith("test_"):
        db.tenants.delete_tenant(tenant_name)

# Test pattern
def test_user_operations():
    test_db, tenant_name = create_test_tenant("myapp", "user_ops")
    
    try:
        # Isolated test environment
        user = test_db.insert("users", {"name": "Test User"})
        assert user["id"] is not None
        
        users = test_db.query("SELECT * FROM users")
        assert len(users) == 1
    finally:
        cleanup_test_tenant("myapp", tenant_name)
```

## Schema Synchronization

**Automatic**: Schema changes apply to all tenants automatically.

```python
# Schema changes made at branch level affect all tenants
db = cinchdb.connect("myapp")  # Default tenant
# Add column - applies to ALL tenants automatically
db.tables.add_column("users", Column(name="phone", type="TEXT", nullable=True))

# Verify across tenants
for tenant_name in ["customer_a", "customer_b"]:
    tenant_db = cinchdb.connect("myapp", tenant=tenant_name)
    columns = tenant_db.query("PRAGMA table_info(users)")
    column_names = [col["name"] for col in columns]
    assert "phone" in column_names  # New column exists everywhere
```

## Performance Benefits

**Isolation**: Each tenant's queries are completely independent.

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_tenant_queries(database, tenant_list):
    """Query multiple tenants in parallel - no cross-tenant interference."""
    def query_tenant(tenant_name):
        tenant_db = cinchdb.connect(database, tenant=tenant_name)
        return tenant_db.query("SELECT COUNT(*) FROM users")[0]["count"]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(query_tenant, tenant_list)
    
    return dict(zip(tenant_list, results))

# Connection pooling
class TenantConnectionPool:
    def __init__(self, database):
        self.database = database
        self.connections = {}
    
    def get_connection(self, tenant_name):
        if tenant_name not in self.connections:
            self.connections[tenant_name] = cinchdb.connect(self.database, tenant=tenant_name)
        return self.connections[tenant_name]
```

## Best Practices

### Naming Convention
- Use consistent patterns: `customer_12345`, `acme_corp`  
- Lowercase with underscores only
- Avoid special characters

### Security Validation
```python
def validate_tenant_access(user_tenant, requested_tenant):
    """Prevent cross-tenant access."""
    if user_tenant != requested_tenant:
        raise PermissionError(f"Access denied to tenant {requested_tenant}")

def get_user_data(database, user_id, user_tenant):
    validate_tenant_access(user_tenant, user_tenant)
    tenant_db = cinchdb.connect(database, tenant=user_tenant)
    return tenant_db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

### Lifecycle Management
```python
def create_with_audit(database, tenant_name):
    """Create tenant with audit trail."""
    db = cinchdb.connect(database)
    db.tenants.create_tenant(tenant_name)
    
    tenant_db = cinchdb.connect(database, tenant=tenant_name)
    tenant_db.insert("audit_log", {"event": "tenant_created", "timestamp": "datetime('now')"})
    return tenant_db

def archive_before_delete(database, tenant_name):
    """Export data before deletion."""
    tenant_db = cinchdb.connect(database, tenant=tenant_name)
    data = tenant_db.query("SELECT * FROM users")
    
    # Save backup
    with open(f"archive_{tenant_name}.json", "w") as f:
        json.dump(data, f)
    
    # Then delete
    db = cinchdb.connect(database)
    db.tenants.delete_tenant(tenant_name)
```

## Next Steps

- [Multi-Tenancy Concepts](../concepts/multi-tenancy.md) - Deep dive
- [Tenant CLI](../cli/tenant.md) - CLI commands
- [Multi-Tenant Tutorial](../tutorials/multi-tenant-app.md) - Build an app
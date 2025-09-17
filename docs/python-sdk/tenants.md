# Tenant Operations

Tenants provide file-level data isolation in CinchDB. Each tenant gets its own SQLite database file.

## What Tenants Actually Are

- **Separate SQLite files**: Each tenant = one SQLite file
- **Same schema**: All tenants share the branch's schema
- **Lazy by default**: Created only when first used (no physical file until needed)
- **File-level isolation**: Complete separation, no cross-tenant queries

## Basic Usage

```python
import cinchdb

# Connect to default tenant (main)
db = cinchdb.connect("myapp")

# Connect to specific tenant
customer_db = cinchdb.connect("myapp", tenant="customer_123")

# Insert data (creates file if lazy)
customer_db.insert("users", {"name": "Alice", "email": "alice@customer123.com"})
```

## Tenant Management

```python
db = cinchdb.connect("myapp")

# List tenants
tenants = db.list_tenants()
for tenant in tenants:
    print(f"Tenant: {tenant.name}")  # Only has .name, .database, .branch

# Create tenant (lazy by default - no file created yet)
new_tenant = db.create_tenant("customer_456")

# Delete tenant (removes the SQLite file)
db.delete_tenant("old_customer")

# Copy tenant (copies the SQLite file)
db.copy_tenant("template_tenant", "new_customer")
```

## How Lazy Tenants Work

```python
# Create lazy tenant - no file created
db.create_tenant("lazy_customer")

# Connect to lazy tenant
lazy_db = cinchdb.connect("myapp", tenant="lazy_customer")

# First read uses __empty__ template (has schema, no data)
users = lazy_db.query("SELECT * FROM users")  # Returns empty results

# First write materializes the tenant (creates actual file)
lazy_db.insert("users", {"name": "Bob"})  # Now creates customer_123.db
```

## Multi-Tenant SaaS Pattern

```python
def create_customer_account(customer_id: str, admin_email: str):
    """Create isolated customer account."""
    # Create tenant for customer
    main_db = cinchdb.connect("saas_app")
    main_db.create_tenant(customer_id)

    # Connect to customer's isolated database
    customer_db = cinchdb.connect("saas_app", tenant=customer_id)

    # Add their data (triggers materialization)
    admin_user = customer_db.insert("users", {
        "email": admin_email,
        "role": "admin",
        "active": True
    })

    return customer_db

# Usage
acme_db = create_customer_account("acme_corp", "admin@acme.com")
startup_db = create_customer_account("startup_inc", "ceo@startup.com")

# Complete isolation - no cross-tenant access possible
acme_users = acme_db.query("SELECT * FROM users")      # Only ACME users
startup_users = startup_db.query("SELECT * FROM users") # Only Startup users
```

## Schema Changes

Schema changes are made at the branch level and affect the template:

```python
# Add column to branch (affects new tenants)
db = cinchdb.connect("myapp")  # main tenant
db.create_table("notifications", [
    Column(name="message", type="TEXT"),
    Column(name="user_id", type="TEXT")
])

# Existing tenants need schema migration
# New lazy tenants will get the updated schema automatically
```

## Storage and Performance

```python
# Check tenant storage
size_info = db.get_tenant_size("customer_123")
print(f"Size: {size_info['size_mb']:.1f} MB")
print(f"Materialized: {size_info['materialized']}")

# Get all tenant sizes
all_sizes = db.get_storage_info()
print(f"Total storage: {all_sizes['total_size_mb']:.1f} MB")
print(f"Lazy tenants: {all_sizes['lazy_count']}")

# Optimize tenant database
vacuum_result = db.vacuum_tenant("customer_123")
print(f"Reclaimed {vacuum_result['space_reclaimed_mb']:.1f} MB")
```

## Testing Pattern

```python
import tempfile
import shutil

def test_with_isolated_tenant():
    """Test with temporary tenant."""
    db = cinchdb.connect("test_app")

    # Create test tenant
    test_tenant = f"test_{int(time.time())}"
    db.create_tenant(test_tenant)

    try:
        # Test with isolated data
        test_db = cinchdb.connect("test_app", tenant=test_tenant)
        user = test_db.insert("users", {"name": "Test User"})
        assert user["id"] is not None

    finally:
        # Cleanup
        db.delete_tenant(test_tenant)
```

## Limitations

- **No cross-tenant queries**: Each tenant is a separate SQLite file
- **No tenant-level permissions**: Use application logic for access control
- **Schema migration complexity**: Changes don't auto-apply to existing tenants
- **File system limits**: Each tenant = one file, filesystem limits apply

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

def get_user_data(database, user_id, user_tenant, requested_tenant):
    """Get user data with proper tenant validation."""
    validate_tenant_access(user_tenant, requested_tenant)
    tenant_db = cinchdb.connect(database, tenant=requested_tenant)
    return tenant_db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

## When to Use Tenants

✅ **Good for:**
- B2B SaaS with customer data isolation
- Per-customer databases with shared schema
- Compliance requirements (separate files)
- Development/testing isolation

❌ **Not good for:**
- Cross-tenant reporting (use application aggregation)
- High tenant count (thousands of files)
- Complex tenant relationships
- Real-time multi-tenant queries

## Next Steps

- [Database Operations](database.md) - Managing databases and branches
- [Query Operations](queries.md) - Running SQL queries
- [CLI Reference](../cli/tenant.md) - Command line tenant management
# Tenant Operations

Work with multi-tenant data isolation using the Python SDK.

## Connecting to Tenants

### Direct Tenant Connection
```python
# Connect to specific tenant
tenant_db = cinchdb.connect("myapp", tenant="customer_a")

# Query tenant data
users = tenant_db.query("SELECT * FROM users")
```

### Switching Between Tenants
```python
# Start with default tenant
db = cinchdb.connect("myapp")

# Connect to specific tenant
customer_db = cinchdb.connect("myapp", tenant="customer_a")

# Work with tenant data
customer_db.insert("users", {"name": "Alice", "email": "alice@customer-a.com"})
```

## Tenant Management (Local Only)

### List Tenants
```python
db = cinchdb.connect("myapp")

if db.is_local:
    tenants = db.tenants.list_tenants()
    for tenant in tenants:
        print(f"Tenant: {tenant.name}")
        print(f"Database file: {tenant.db_path}")
```

### Create Tenant
```python
if db.is_local:
    # Create new tenant
    db.tenants.create_tenant("customer_b")
    
    # Verify creation
    customer_db = cinchdb.connect(db.database, tenant="customer_b")
    tables = customer_db.query("SELECT name FROM sqlite_master WHERE type='table'")
```

### Delete Tenant
```python
if db.is_local:
    # Warning: This deletes all tenant data!
    db.tenants.delete_tenant("old_customer")
```

### Copy Tenant
```python
if db.is_local:
    # Copy with data
    db.tenants.copy_tenant("template", "new_customer")
    
    # Copy structure only
    db.tenants.copy_tenant("template", "new_customer", copy_data=False)
```

## Multi-Tenant Patterns

### Tenant Isolation
```python
import cinchdb

# Each tenant has completely isolated data
tenant_a = cinchdb.connect(db.database, tenant="customer_a")
tenant_b = cinchdb.connect(db.database, tenant="customer_b")

# Insert into tenant A
tenant_a.insert("users", {"name": "Alice", "email": "alice@a.com"})

# Query tenant B - won't see tenant A's data
b_users = tenant_b.query("SELECT * FROM users")
assert len(b_users) == 0  # No data from tenant A
```

### Cross-Tenant Operations
```python
import cinchdb

def count_all_tenant_users(db, tenant_names):
    """Count users across all tenants."""
    total_users = 0
    
    for tenant_name in tenant_names:
        tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
        result = tenant_db.query("SELECT COUNT(*) as count FROM users")
        total_users += result[0]["count"]
    
    return total_users

# Usage
tenants = ["customer_a", "customer_b", "customer_c"]
total = count_all_tenant_users(db, tenants)
print(f"Total users across all tenants: {total}")
```

### Tenant Templates
```python
import cinchdb

def setup_tenant_template(db):
    """Create a template tenant with default data."""
    template_db = cinchdb.connect(db.database, tenant="_template")
    
    # Add default settings
    template_db.create_table("settings", [
        Column(name="key", type="TEXT"),
        Column(name="value", type="TEXT")
    ])
    
    # Insert defaults
    defaults = [
        {"key": "theme", "value": "light"},
        {"key": "timezone", "value": "UTC"},
        {"key": "language", "value": "en"}
    ]
    
    for setting in defaults:
        template_db.insert("settings", setting)
    
    return template_db

def create_tenant_from_template(db, tenant_name):
    """Create new tenant from template."""
    if db.is_local:
        # Copy template to new tenant
        db.tenants.copy_tenant("_template", tenant_name)
        
        # Customize for tenant
        tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
        tenant_db.update("settings", 
            {"key": "company_name"}, 
            {"value": tenant_name}
        )
        
        return tenant_db
```

## Common Use Cases

### SaaS Application
```python
class TenantManager:
    def __init__(self, db):
        self.db = db
    
    def onboard_customer(self, customer_name, admin_email):
        """Onboard a new customer with their own tenant."""
        # Create tenant
        if self.db.is_local:
            self.db.tenants.create_tenant(customer_name)
        
        # Connect to tenant
        tenant_db = cinchdb.connect(self.db.database, tenant=customer_name)
        
        # Create admin user
        admin = tenant_db.insert("users", {
            "email": admin_email,
            "role": "admin",
            "active": True
        })
        
        # Initialize settings
        tenant_db.insert("company_settings", {
            "name": customer_name,
            "admin_user_id": admin["id"],
            "plan": "trial",
            "trial_ends": "datetime('now', '+30 days')"
        })
        
        return tenant_db
    
    def get_tenant_stats(self, tenant_name):
        """Get usage statistics for a tenant."""
        tenant_db = cinchdb.connect(self.db.database, tenant=tenant_name)
        
        stats = {}
        
        # User count
        result = tenant_db.query("SELECT COUNT(*) as count FROM users")
        stats["user_count"] = result[0]["count"]
        
        # Storage usage (approximate)
        if self.db.is_local:
            import os
            tenant_path = f".cinchdb/databases/{self.db.database}/branches/{self.db.branch}/tenants/{tenant_name}.db"
            if os.path.exists(tenant_path):
                stats["storage_bytes"] = os.path.getsize(tenant_path)
        
        return stats
```

### Multi-Region Setup
```python
import cinchdb

REGIONS = {
    "us-east": ["customer_1", "customer_2"],
    "eu-west": ["customer_3", "customer_4"],
    "asia-pac": ["customer_5", "customer_6"]
}

def get_region_db(base_db, region):
    """Get connection for specific region."""
    # In practice, might connect to different servers
    return base_db

def query_by_region(base_db, region, query, params=None):
    """Execute query for all tenants in a region."""
    results = {}
    region_db = get_region_db(base_db, region)
    
    for tenant in REGIONS[region]:
        tenant_db = cinchdb.connect(region_db.database, tenant=tenant)
        results[tenant] = tenant_db.query(query, params)
    
    return results
```

### Development and Testing
```python
import cinchdb
import time

def create_test_tenant(db, test_name):
    """Create isolated tenant for testing."""
    tenant_name = f"test_{test_name}_{int(time.time())}"
    
    if db.is_local:
        db.tenants.create_tenant(tenant_name)
    
    return cinchdb.connect(db.database, tenant=tenant_name), tenant_name

def cleanup_test_tenant(db, tenant_name):
    """Remove test tenant after tests."""
    if db.is_local and tenant_name.startswith("test_"):
        db.tenants.delete_tenant(tenant_name)

# Usage in tests
def test_user_creation():
    db = cinchdb.connect("myapp")
    test_db, tenant_name = create_test_tenant(db, "user_creation")
    
    try:
        # Run tests in isolated tenant
        user = test_db.insert("users", {"name": "Test User"})
        assert user["id"] is not None
        
        users = test_db.query("SELECT * FROM users")
        assert len(users) == 1
    finally:
        cleanup_test_tenant(db, tenant_name)
```

## Schema Synchronization

Schema changes automatically apply to all tenants:

```python
import cinchdb
from cinchdb import Column

# Add column on main tenant
main_db = cinchdb.connect(db.database, tenant="main")
if main_db.is_local:
    main_db.columns.add_column("users", 
        Column(name="phone", type="TEXT", nullable=True)
    )

# Verify on other tenants
for tenant in ["customer_a", "customer_b"]:
    tenant_db = cinchdb.connect(db.database, tenant=tenant)
    columns = tenant_db.query("PRAGMA table_info(users)")
    column_names = [col["name"] for col in columns]
    assert "phone" in column_names
```

## Performance Considerations

### Tenant Isolation Benefits
```python
import cinchdb
from concurrent.futures import ThreadPoolExecutor

# Each tenant query is independent
# No cross-tenant performance impact

def parallel_tenant_queries(db, tenant_list):
    """Query multiple tenants in parallel."""
    def query_tenant(tenant_name):
        tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
        return tenant_db.query("SELECT COUNT(*) FROM users")[0]["count"]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(query_tenant, tenant_list)
    
    return dict(zip(tenant_list, results))
```

### Connection Pooling
```python
import cinchdb

# Connections are pooled per tenant
# Reuse connections for better performance

class TenantConnectionPool:
    def __init__(self, base_db):
        self.base_db = base_db
        self.connections = {}
    
    def get_connection(self, tenant_name):
        if tenant_name not in self.connections:
            self.connections[tenant_name] = cinchdb.connect(self.base_db.database, tenant=tenant_name)
        return self.connections[tenant_name]
    
    def close_all(self):
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()
```

## Best Practices

### 1. Tenant Naming
```python
# Use consistent naming
"customer_12345"     # Numeric IDs
"acme_corp"         # Company names
"tenant_us_west_1"  # Regional tenants

# Avoid special characters
# Use lowercase with underscores
```

### 2. Tenant Lifecycle
```python
import cinchdb
from datetime import datetime
import json

class TenantLifecycle:
    @staticmethod
    def create(db, tenant_name):
        """Standard tenant creation."""
        if db.is_local:
            db.tenants.create_tenant(tenant_name)
        
        tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
        # Add audit entry
        tenant_db.insert("audit_log", {
            "event": "tenant_created",
            "timestamp": datetime.now().isoformat()
        })
        
        return tenant_db
    
    @staticmethod
    def archive(db, tenant_name):
        """Archive tenant data before deletion."""
        # Export data first
        tenant_db = cinchdb.connect(db.database, tenant=tenant_name)
        users = tenant_db.query("SELECT * FROM users")
        
        # Save to archive
        with open(f"archive_{tenant_name}.json", "w") as f:
            json.dump(users, f)
        
        # Then delete
        if db.is_local:
            db.tenants.delete_tenant(tenant_name)
```

### 3. Security
```python
def validate_tenant_access(user_tenant, requested_tenant):
    """Ensure users can only access their tenant."""
    if user_tenant != requested_tenant:
        raise PermissionError(f"Access denied to tenant {requested_tenant}")

# In your application
def get_user_data(db, user_id, user_tenant):
    validate_tenant_access(user_tenant, user_tenant)
    tenant_db = cinchdb.connect(db.database, tenant=user_tenant)
    return tenant_db.query("SELECT * FROM users WHERE id = ?", [user_id])
```

## Next Steps

- [Multi-Tenancy Concepts](../concepts/multi-tenancy.md) - Deep dive
- [Tenant CLI](../cli/tenant.md) - CLI commands
- [Multi-Tenant Tutorial](../tutorials/multi-tenant-app.md) - Build an app
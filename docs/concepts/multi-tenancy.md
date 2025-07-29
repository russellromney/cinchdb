# Multi-Tenancy Concepts

Understanding CinchDB's approach to multi-tenant data isolation.

## What is Multi-Tenancy?

Multi-tenancy allows a single application instance to serve multiple customers (tenants) while keeping their data completely isolated. CinchDB implements this through separate SQLite databases per tenant.

## Architecture

### Tenant Isolation

Each tenant has:
- Separate SQLite database file
- Complete data isolation
- Shared schema across tenants
- Independent query execution

```
.cinchdb/databases/myapp/branches/main/tenants/
├── main.db           # Default tenant
├── acme_corp.db      # Customer tenant
├── wayne_ent.db      # Customer tenant
└── stark_ind.db      # Customer tenant
```

### Key Benefits

1. **Complete Isolation** - No data leakage between tenants
2. **Performance** - No cross-tenant query overhead  
3. **Scalability** - Add tenants without impacting others
4. **Security** - File-level access control possible
5. **Simplicity** - Standard SQLite operations

## How It Works

### Schema Synchronization

When you modify schema on a branch:
1. Change is recorded in `changes.json`
2. Change applies to ALL tenants automatically
3. Each tenant database is updated
4. Schema remains consistent

```bash
# Add column - affects all tenants
cinch column add users phone:TEXT

# Internally applies to:
# - main.db
# - acme_corp.db  
# - wayne_ent.db
# - stark_ind.db
```

### Tenant Operations

```python
# Connect to specific tenant
db = cinchdb.connect("myapp", tenant="acme_corp")

# All operations are tenant-scoped
users = db.query("SELECT * FROM users")  # Only acme_corp's users

# Switch tenants
wayne_db = db.switch_tenant("wayne_ent")
wayne_users = wayne_db.query("SELECT * FROM users")  # Only wayne_ent's users
```

## Use Cases

### 1. SaaS Applications

Perfect for B2B SaaS where each customer needs isolated data:

```python
class SaaSApp:
    def __init__(self):
        self.db = cinchdb.connect("saas_app")
    
    def get_customer_data(self, customer_id: str, user_id: str):
        # Each customer has their own tenant
        customer_db = self.db.switch_tenant(customer_id)
        
        # Query only sees customer's data
        return customer_db.query(
            "SELECT * FROM records WHERE user_id = ?",
            [user_id]
        )
```

### 2. Regional Isolation

Separate data by geography:

```python
REGIONS = {
    "us-east": ["customer_1", "customer_2"],
    "eu-west": ["customer_3", "customer_4"],
    "asia-pac": ["customer_5", "customer_6"]
}

def get_region_stats(region: str):
    stats = {}
    for tenant in REGIONS[region]:
        tenant_db = db.switch_tenant(tenant)
        count = tenant_db.query("SELECT COUNT(*) FROM users")[0]["count"]
        stats[tenant] = count
    return stats
```

### 3. Development/Testing

Isolated environments for testing:

```python
def create_test_environment(feature_name: str):
    test_tenant = f"test_{feature_name}_{int(time.time())}"
    
    # Create isolated test tenant
    db.tenants.create_tenant(test_tenant)
    
    # Run tests in isolation
    test_db = db.switch_tenant(test_tenant)
    run_tests(test_db)
    
    # Clean up
    db.tenants.delete_tenant(test_tenant)
```

## Tenant Lifecycle

### 1. Creation

```bash
# CLI
cinch tenant create customer_name

# Python
if db.is_local:
    db.tenants.create_tenant("customer_name")
```

Creates:
- New SQLite database file
- Applies current schema
- Ready for immediate use

### 2. Data Operations

All standard operations work per-tenant:

```python
# Insert data
tenant_db.insert("users", {"name": "Alice", "email": "alice@customer.com"})

# Query data
results = tenant_db.query("SELECT * FROM orders WHERE status = ?", ["pending"])

# Update data
tenant_db.update("users", user_id, {"last_login": datetime.now()})

# Delete data
tenant_db.delete("sessions", session_id)
```

### 3. Maintenance

```python
def maintain_tenant(tenant_name: str):
    tenant_db = db.switch_tenant(tenant_name)
    
    # Vacuum to reclaim space
    tenant_db.query("VACUUM")
    
    # Analyze for query optimization
    tenant_db.query("ANALYZE")
    
    # Check integrity
    result = tenant_db.query("PRAGMA integrity_check")
    return result[0]["integrity_check"] == "ok"
```

### 4. Deletion

```bash
# CLI - removes all tenant data
cinch tenant delete old_customer --force

# Python
if db.is_local:
    db.tenants.delete_tenant("old_customer")
```

## Performance Characteristics

### Advantages

1. **No Query Overhead** - Each tenant queries independently
2. **Parallel Access** - Multiple tenants can be queried simultaneously
3. **Cache Efficiency** - Each database has its own cache
4. **Simple Indexes** - No need for tenant_id in every index

### Considerations

1. **File Handle Limits** - Each tenant uses file handles
2. **Memory Usage** - Each connection has overhead
3. **Backup Size** - More files to backup
4. **Schema Changes** - Must update all tenant databases

### Optimization Strategies

```python
# Connection pooling per tenant
class TenantPool:
    def __init__(self, base_db, max_per_tenant=10):
        self.base_db = base_db
        self.pools = {}
        self.max_per_tenant = max_per_tenant
    
    def get_connection(self, tenant_name):
        if tenant_name not in self.pools:
            self.pools[tenant_name] = []
        
        pool = self.pools[tenant_name]
        
        # Reuse existing connection
        if pool:
            return pool.pop()
        
        # Create new connection
        return self.base_db.switch_tenant(tenant_name)
    
    def return_connection(self, tenant_name, conn):
        pool = self.pools[tenant_name]
        if len(pool) < self.max_per_tenant:
            pool.append(conn)
```

## Security Model

### 1. Complete Isolation

No SQL injection can access other tenant data:

```python
# Even with injection, only sees current tenant
tenant_db = db.switch_tenant("customer_a")
# This query CANNOT access customer_b's data
results = tenant_db.query(user_provided_sql)
```

### 2. Access Control

Implement at application level:

```python
def get_tenant_connection(user_id: str, requested_tenant: str):
    # Verify user has access to tenant
    user_tenant = get_user_tenant(user_id)
    if user_tenant != requested_tenant:
        raise PermissionError("Access denied")
    
    return db.switch_tenant(requested_tenant)
```

### 3. Encryption

Encrypt at rest per tenant:

```python
# Configure SQLite encryption per tenant
tenant_db.query("PRAGMA key = ?", [tenant_specific_key])
```

## Scaling Patterns

### 1. Sharding by Tenant

For many tenants (1000+):

```python
def get_shard_for_tenant(tenant_id: str) -> str:
    # Distribute tenants across shards
    shard_num = hash(tenant_id) % NUM_SHARDS
    return f"shard_{shard_num}"

# Route to appropriate server
server = SHARD_SERVERS[get_shard_for_tenant(tenant_id)]
```

### 2. Tenant Groups

Group related tenants:

```python
TENANT_GROUPS = {
    "enterprise": ["fortune500_a", "fortune500_b"],
    "standard": ["startup_1", "startup_2"],
    "trial": ["trial_user_1", "trial_user_2"]
}

def get_tenant_resources(tenant_name: str):
    for group, tenants in TENANT_GROUPS.items():
        if tenant_name in tenants:
            return RESOURCE_LIMITS[group]
```

### 3. Active/Archive Pattern

Move inactive tenants:

```python
def archive_inactive_tenant(tenant_name: str):
    # Check last activity
    tenant_db = db.switch_tenant(tenant_name)
    last_activity = tenant_db.query(
        "SELECT MAX(updated_at) as last FROM users"
    )[0]["last"]
    
    if days_since(last_activity) > 365:
        # Move to archive storage
        archive_path = f"/archive/{tenant_name}.db"
        shutil.move(get_tenant_path(tenant_name), archive_path)
        
        # Update registry
        mark_tenant_archived(tenant_name)
```

## Best Practices

### 1. Naming Conventions

```python
# Use consistent, valid names
"customer_12345"      # Good - alphanumeric with underscore
"acme-corp"          # Bad - avoid hyphens
"customer.com"       # Bad - avoid dots
"Acme Corp"          # Bad - avoid spaces
```

### 2. Template Pattern

```python
def create_tenant_from_template(tenant_name: str, template: str = "default"):
    # Copy template tenant
    if db.is_local:
        db.tenants.copy_tenant(f"_template_{template}", tenant_name)
    
    # Customize
    tenant_db = db.switch_tenant(tenant_name)
    tenant_db.insert("settings", {
        "tenant_name": tenant_name,
        "created_from": template,
        "created_at": datetime.now()
    })
```

### 3. Monitoring

```python
def get_tenant_metrics():
    metrics = []
    
    for tenant in db.tenants.list_tenants():
        tenant_db = db.switch_tenant(tenant.name)
        
        metrics.append({
            "tenant": tenant.name,
            "size_mb": get_db_size(tenant.name) / 1024 / 1024,
            "table_count": len(get_tables(tenant_db)),
            "total_rows": get_total_rows(tenant_db)
        })
    
    return metrics
```

## Common Pitfalls

### 1. Forgetting Tenant Context

```python
# Bad - uses default tenant
db = cinchdb.connect("myapp")
users = db.query("SELECT * FROM users")  # Wrong tenant!

# Good - explicit tenant
db = cinchdb.connect("myapp", tenant="customer_a")
users = db.query("SELECT * FROM users")  # Correct tenant
```

### 2. Cross-Tenant Queries

```python
# Cannot do cross-tenant joins
# Must query each tenant separately

def get_all_tenant_totals():
    totals = {}
    
    for tenant in tenants:
        tenant_db = db.switch_tenant(tenant)
        total = tenant_db.query("SELECT SUM(amount) FROM orders")[0]
        totals[tenant] = total
    
    return totals
```

### 3. Schema Drift

```python
# Always apply changes through CinchDB
# Never modify tenant databases directly

# Bad
sqlite3 tenant.db "ALTER TABLE users ADD COLUMN phone TEXT"

# Good
db.columns.add_column("users", Column(name="phone", type="TEXT"))
```

## Next Steps

- [Change Tracking](change-tracking.md)
- [Multi-Tenant Tutorial](../tutorials/multi-tenant-app.md)
- [Tenant CLI Commands](../cli/tenant.md)
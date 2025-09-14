# Multi-Tenancy

**Isolate customer data with separate SQLite files. Ultra-fast queries, better security.**

## What is Multi-Tenancy?

**Problem**: SaaS apps need to isolate customer data but share the same schema.

**Solution**: Each tenant gets their own SQLite database file. Shared schema, isolated data.

```bash
# Same schema, different data per tenant
cinch query "SELECT COUNT(*) FROM users" --tenant customer_a  # → 1,245 users
cinch query "SELECT COUNT(*) FROM users" --tenant customer_b  # → 892 users
```

## When to Use Multi-Tenancy

### ✅ **Perfect For:**

- **SaaS applications** - Separate customer data
- **B2B platforms** - Company-specific data isolation  
- **Compliance requirements** - Data must be isolated
- **Per-user databases** - Give each user their own database
- **Performance-critical apps** - Faster queries with smaller datasets

### ⚠️ **Consider Alternatives For:**

- **Simple apps** - Single tenant might be enough
- **Shared data needs** - Cross-tenant reporting/analytics  
- **Very small datasets** - Multi-tenancy overhead not worth it

## How It Works

### Key Concept: **Separate Databases, Shared Schema**

```
myapp/main/tenants/
├── main.db        ← Default tenant (your data)
├── acme_corp.db   ← Customer A's data  
├── globodyne.db   ← Customer B's data
└── initech.db     ← Customer C's data
```

Each file is a **complete SQLite database** with:
- Same tables and schema
- Different data  
- Independent queries

### Mental Model: **One App, Multiple Databases**

| Traditional Shared DB | CinchDB Multi-Tenant |
|----------------------|---------------------|
| `SELECT * FROM users WHERE tenant_id = 'acme'` | `SELECT * FROM users` (on acme_corp.db) |
| Query entire table, filter | Query only relevant data |
| Risk of data leakage | Impossible to see other tenant's data |
| Slow with many tenants | Fast regardless of tenant count |

## Tenant Operations

### Create Tenants
```bash
# Create new tenant
cinch tenant create acme_corp

# List all tenants
cinch tenant list

# Delete tenant (careful!)
cinch tenant delete old_customer
```

### Query Tenant Data
```bash
# Query default tenant (main)
cinch query "SELECT * FROM products"

# Query specific tenant
cinch query "SELECT * FROM products" --tenant acme_corp

# Insert tenant-specific data
cinch data insert users --data '{"name": "John", "email": "john@acme.com"}' --tenant acme_corp
```

### Python SDK
```python
# Connect to specific tenant
db = cinchdb.connect("myapp", tenant="acme_corp")

# All operations work on that tenant's data
users = db.query("SELECT * FROM users")  # Only acme_corp's users
user_id = db.insert("users", {"name": "Jane", "email": "jane@acme.com"})

# Switch tenants
globodyne_db = cinchdb.connect("myapp", tenant="globodyne")  
products = globodyne_db.query("SELECT * FROM products")  # Only globodyne's products
```

## Schema Management

### Automatic Schema Sync

**Key principle**: Schema changes apply to ALL tenants automatically.

```bash
# Add column - every tenant gets it
cinch column add users phone:TEXT

# main.db gets phone column
# acme_corp.db gets phone column  
# globodyne.db gets phone column
# (etc.)
```

### Branch + Tenant Workflow
```bash
# 1. Create feature branch (copies all tenant data)
cinch branch create add-orders --switch

# 2. Add new table (affects all tenants in this branch)
cinch table create orders user_id:TEXT total:REAL

# 3. Test with sample data
cinch data insert orders --data '{"user_id": "user-123", "total": 29.99}' --tenant acme_corp

# 4. Merge back (schema change applies to all tenants on main)  
cinch branch switch main
cinch branch merge-into-main add-orders
```

## Performance Benefits

### Ultra-Fast Queries

With multi-tenancy, query speed is `data_size ÷ tenant_count`:

```
Traditional: 1M users in shared table → Query scans 1M rows
Multi-tenant: 1M users across 100 tenants → Query scans 10K rows (100x faster!)
```

### Real-World Example
```bash
# Shared database approach
cinch query "SELECT * FROM orders WHERE tenant_id = 'acme' AND status = 'pending'"  
# → Scans entire orders table, filters by tenant

# Multi-tenant approach  
cinch query "SELECT * FROM orders WHERE status = 'pending'" --tenant acme
# → Only scans acme's orders table
```

## Common Patterns

### SaaS Application Setup
```bash
# Initialize app with default tenant
cinch init myapp && cd myapp

# Create customer tenants as they sign up
cinch tenant create customer_001
cinch tenant create customer_002  
cinch tenant create customer_003

# Each customer gets isolated data
cinch data insert users --data '{"name": "Admin", "email": "admin@customer001.com"}' --tenant customer_001
```

### Per-User Databases  
```bash
# Give each user their own database
cinch tenant create user_alice
cinch tenant create user_bob
cinch tenant create user_carol

# Users can only access their own data
cinch query "SELECT * FROM documents" --tenant user_alice  # Only Alice's documents
```

### Development vs Production
```python
# Development - use main tenant
dev_db = cinchdb.connect("myapp", tenant="main")

# Production - use customer-specific tenants  
prod_db = cinchdb.connect("myapp", tenant="customer_001")
```

## Security Benefits

### Complete Data Isolation
- **File-level security** - Each tenant is a separate file
- **No SQL injection across tenants** - Impossible to query other tenant's data  
- **Access control** - Can set file permissions per tenant
- **Backup granularity** - Backup individual tenants


### Compliance
- **GDPR** - Delete entire tenant file for data deletion
- **SOC 2** - Audit individual tenant access
- **Industry-specific** - Meet data isolation requirements

## Best Practices

### Tenant Naming
```bash
# Use consistent naming schemes
cinch tenant create customer_001    # Numbered
cinch tenant create acme_corp       # Company slug  
cinch tenant create user_alice      # User-based
```

### Application Code
```python
# Always specify tenant explicitly
def get_user_data(tenant_name, user_id):
    db = cinchdb.connect("myapp", tenant=tenant_name)
    return db.query("SELECT * FROM users WHERE id = ?", [user_id])

# Never hardcode tenant names
# BAD: db = cinchdb.connect("myapp", tenant="hardcoded_tenant")  
# GOOD: db = cinchdb.connect("myapp", tenant=request.headers["X-Tenant-ID"])
```

### Monitoring
```bash
# Check tenant sizes
cinch tenant list  # Shows tenant info including size

# Monitor query performance per tenant
# (queries naturally faster with smaller datasets)
```

## Troubleshooting

**"Tenant not found"** → Check tenant name: `cinch tenant list`

**"Slow queries"** → Might need indexes: `cinch create_index table_name ["column"]`

**"Running out of disk"** → Consider archiving unused tenants

**"Schema out of sync"** → Shouldn't happen, but check change history: `cinch branch changes`

## Next Steps

- [Schema Branching](branching.md) - How branches work with tenants
- [CLI Tenant Commands](../cli/tenant.md) - Complete command reference  
- [Python SDK Tenants](../python-sdk/tenants.md) - Code examples
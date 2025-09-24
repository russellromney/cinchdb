# Core Concepts

**Understanding Projects, Databases, Branches, and Tenants**

## Mental Model: **Git for Databases**

CinchDB works like Git, but for database schemas:

| Git Concept | CinchDB Equivalent | Purpose |
|-------------|-------------------|----------|
| Repository | Project | Contains all your databases |
| Branch | Schema Branch | Isolated schema changes |
| File | Table/Column | Database schema elements |
| Merge | Schema Merge | Apply changes safely |

## Projects

**A project = your application's data layer**

```bash
cinch init myapp  # Creates .cinchdb/ directory
```

```
myapp/
├── .cinchdb/
│   ├── config.toml
│   └── databases/
└── your-app-code/
```

### When to Use Projects
- **One per application** - Each app gets its own project
- **Separate environments** - Different projects for dev/staging/prod
- **Team boundaries** - Different projects for different teams

## Databases

**Multiple logical databases within a project**

```bash
cinch db create main        # Core app data
cinch db create analytics   # Reporting data  
cinch db create logs        # Application logs
```

### When to Create Multiple Databases

✅ **Good reasons:**

- **Different services** - User service vs Order service
- **Data lifecycle** - Transactional vs analytical data
- **Access patterns** - High-frequency vs archive data

⚠️ **Avoid if:**

- **Tables are related** - Orders belong with Users
- **Need joins** - Can't join across databases easily

## Schema Branches

**Git branches for database schema changes**

```bash
cinch branch create add-payments --switch
cinch table create payments user_id:TEXT amount:REAL
cinch branch switch main
cinch branch merge-into-main add-payments
```

### When to Create Branches
✅ **Always branch for:**

- **New features** - Adding tables/columns
- **Schema refactoring** - Changing existing structure  
- **Breaking changes** - Removing/renaming things
- **Experiments** - Testing schema ideas

⚠️ **Stay on main for:**

- **Data operations** - INSERT/UPDATE/DELETE queries
- **Simple additions** - Adding basic indexes

### Key Branch Concepts

**Complete Isolation**: Each branch copies all schema + data
```
main/           ← Production schema
├── users.db    ← 10K users
└── orders.db   ← 50K orders

add-payments/   ← Feature branch  
├── users.db    ← Copy of 10K users
├── orders.db   ← Copy of 50K orders  
└── payments.db ← New payments table
```

**Atomic Merges**: Either all changes apply or none do

- No partial states
- No rollback needed
- Changes apply to ALL tenants simultaneously

## Multi-Tenancy

**Separate customer data, shared schema**

```bash
cinch tenant create customer_a
cinch tenant create customer_b

# Same schema, different data
cinch query "SELECT COUNT(*) FROM users" --tenant customer_a  # 1,250 users
cinch query "SELECT COUNT(*) FROM users" --tenant customer_b  # 892 users
```

### When to Use Multi-Tenancy
✅ **Perfect for:**

- **SaaS applications** - Customer data isolation
- **B2B platforms** - Company-specific data
- **Compliance** - Data must be isolated by law
- **Performance** - Queries scan less data

⚠️ **Not ideal for:**

- **Simple apps** - Single tenant is simpler
- **Cross-tenant analytics** - Need shared reporting
- **Tiny datasets** - Overhead not worth it

### Tenant Performance Benefits

**Query speed = data_size ÷ tenant_count**

```
Traditional: SELECT * FROM users WHERE tenant_id = 'acme'
→ Scans 1M users, filters to 10K

Multi-tenant: SELECT * FROM users --tenant acme  
→ Scans 10K users directly (100x faster!)
```

## Key-Value Store

**Redis-like storage alongside your relational data**

Each database includes a built-in KV store for unstructured data:

```bash
# Sessions with auto-expiration
cinch kv set session:123 '{"user_id": 42}' --ttl 3600

# Application caching
cinch kv set cache:products '[...]' --ttl 300

# Atomic counters
cinch kv increment page:views
cinch kv increment api:calls --by 10
```

### When to Use KV Store vs Tables

**Use KV Store for:**
- **Sessions** - Temporary user state with TTL
- **Caching** - Query results, API responses
- **Feature flags** - Boolean toggles
- **Counters** - Page views, API calls
- **Rate limiting** - Request tracking
- **Temporary data** - OTP codes, tokens

**Use Tables for:**
- **Structured data** - User profiles, products
- **Relationships** - Foreign keys, joins
- **Complex queries** - WHERE, GROUP BY, JOIN
- **Reporting** - Analytics, aggregations
- **Audit trails** - Permanent history
- **Business logic** - Core application data

### KV Store Benefits

- **Sub-millisecond operations** - No query parsing
- **Atomic operations** - Thread-safe increment/decrement
- **Auto-expiration** - TTL for temporary data
- **Multi-tenant** - Each tenant has isolated KV space
- **No CDC overhead** - Not tracked by change capture
- **Pattern matching** - Redis-style key patterns

## How They Work Together

### Complete Hierarchy
```
Project: myapp
└── Database: main
    ├── Branch: main
    │   ├── Tenant: main (default)
    │   ├── Tenant: customer_a  
    │   └── Tenant: customer_b
    └── Branch: add-payments
        ├── Tenant: main (copy)
        ├── Tenant: customer_a (copy)
        └── Tenant: customer_b (copy)
```

### Development Workflow
```bash
# 1. Start with project
cinch init ecommerce && cd ecommerce

# 2. Create feature branch
cinch branch create add-inventory --switch

# 3. Make schema changes
cinch table create inventory product_id:TEXT quantity:INTEGER
cinch table create warehouse_locations name:TEXT address:TEXT

# 4. Test with different tenants
cinch data insert inventory --data '{"product_id": "prod-123", "quantity": 50}' --tenant customer_a
cinch data insert inventory --data '{"product_id": "prod-456", "quantity": 25}' --tenant customer_b

# 5. Verify schema works
cinch query "SELECT * FROM inventory" --tenant customer_a  # Only customer_a's data
cinch query "SELECT * FROM inventory" --tenant customer_b  # Only customer_b's data

# 6. Merge when ready (applies to ALL tenants on main)
cinch branch switch main
cinch branch merge-into-main add-inventory
```

## CLI vs Python SDK

### When to Use Each

**CLI** - Good for:

- **Schema changes** - Creating tables, branches
- **Data exploration** - Quick queries, debugging
- **DevOps tasks** - Migrations, deployment scripts  
- **Learning** - Interactive exploration

```bash
cinch table create products name:TEXT price:REAL
cinch query "SELECT COUNT(*) FROM products"
```

**Python SDK** - Good for:

- **Application code** - Your main app logic
- **Complex operations** - Bulk inserts, transactions
- **Integration** - With web frameworks, APIs
- **Type safety** - Full IDE support and validation

```python
db = cinchdb.connect("myapp", tenant="customer_a")
products = db.query("SELECT * FROM products WHERE price > ?", [100])
```

## Glossary

**Project** - Top-level container for all databases (like Git repo)  
**Database** - Logical collection of related tables (like schema)  
**Branch** - Isolated copy of schema for development (like Git branch)  
**Tenant** - Separate data space with shared schema (like customer)  
**Schema** - Table structure, columns, indexes (not data)  
**Materialized** - Physically created on disk with actual data  
**Merge** - Apply branch changes to target branch atomically

## Next Steps

- [Quick Start Guide](quickstart.md) - Build your first project
- [Constraints](../concepts/constraints.md) - How CinchDB uses SQLite
- [Schema Branching](../concepts/branching.md) - Deep dive into branches
- [Multi-Tenancy](../concepts/multi-tenancy.md) - Deep dive into tenants
- [CLI Reference](../cli/index.md) - All available commands
# Table Operations

Create and manage tables with the Python SDK.

## Creating Tables

### Basic Tables
```python
from cinchdb.models import Column

db = cinchdb.connect("myapp")

# Simple table (columns are nullable by default)
table = db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT", unique=True),
    Column(name="age", type="INTEGER")  # nullable=True by default
])
# Expected output: Table object with columns and metadata
# Performance: ~5ms to create table structure
# Note: Table created in ~5ms

print(f"Created table '{table.name}' with {len(table.columns)} columns")
# Console output: Created table 'users' with 6 columns (3 defined + 3 automatic)

# Empty table with only system columns
empty_table = db.create_table("placeholder", [])
# Expected: Table with only id, created_at, updated_at columns
print(f"Created table '{empty_table.name}' with {len(empty_table.columns)} columns")
# Console output: Created table 'placeholder' with 3 columns
# Use case: Placeholder tables, tables to be populated programmatically,
#           or when schema will be added incrementally via migrations
```

Every table automatically gets:
- `id` - UUID primary key (unique, not nullable)
- `created_at` - Creation timestamp (not nullable)
- `updated_at` - Last modified timestamp (nullable)

### Column Types
```python
# Common column types (case-insensitive with aliases)
Column(name="name", type="TEXT")           # String - stores up to 2^31 characters
Column(name="price", type="REAL")          # Decimal - 8-byte floating point
Column(name="quantity", type="INTEGER")    # Whole number - 64-bit signed integer
Column(name="active", type="BOOLEAN")      # True/false - returns Python bool values
Column(name="data", type="BLOB")           # Binary data - up to 2^31 bytes

# Types are case-insensitive and support common aliases
Column(name="field1", type="text")         # Same as TEXT
Column(name="field2", type="int")          # Alias for INTEGER
Column(name="field3", type="bool")         # Alias for BOOLEAN
Column(name="field4", type="float")        # Alias for REAL
Column(name="field5", type="str")          # Alias for TEXT
Column(name="field6", type="varchar")      # Alias for TEXT

# Column properties
Column(name="email", type="TEXT", nullable=False, unique=True)
# Creates unique index automatically, query performance: <1ms with index

Column(name="bio", type="TEXT")  # nullable=True by default
# Default nullable=True for flexibility

Column(name="required_field", type="TEXT", nullable=False)  # Must provide value

# Common errors:
# ValueError: Invalid column type 'STRING' - Use 'TEXT' or 'str' instead
# sqlite3.IntegrityError: NOT NULL constraint failed - Required field missing
```

### BOOLEAN Type
```python
# BOOLEAN columns return Python bool values
db.create_table("settings", [
    Column(name="enabled", type="BOOLEAN"),      # Can use BOOLEAN
    Column(name="visible", type="bool"),         # Or bool alias
    Column(name="active", type="Boolean")        # Case-insensitive
])

# Insert boolean values
db.insert("settings", {"enabled": True, "visible": False, "active": True})
# Internally stored as 1/0 for SQLite compatibility

# Query returns Python bool
result = db.query("SELECT * FROM settings WHERE enabled = ?", [True])
print(result[0]["enabled"])  # Outputs: True (not 1)
# Expected: True/False values, not integers
# Performance: No conversion overhead, handled at storage layer
```

### Tables with Indexes
```python
# Create table
table = db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="price", type="REAL"),
    Column(name="category", type="TEXT")
])
# Performance: ~5ms for table creation

# Add indexes after creation
idx1 = db.create_index("products", ["name"], name="idx_products_name")
# Expected: Index created in ~5ms
# Query performance improvement: 10-100x faster on WHERE name = ?

idx2 = db.create_index("products", ["email"], name="idx_products_email", unique=True)
# Expected: Unique index created, prevents duplicate emails
# Performance: <1ms lookups, automatic constraint enforcement

idx3 = db.create_index("products", ["category", "price"], name="idx_products_category_price")
# Expected: Compound index for multi-column queries
# Performance: Optimal for WHERE category = ? ORDER BY price queries
# Note: Column order matters - category queries fast, price-only queries won't use this index
```

## Common Table Patterns

### User Management
```python
# Users table with authentication
db.create_table("users", [
    Column(name="username", type="TEXT", unique=True),
    Column(name="email", type="TEXT", unique=True), 
    Column(name="password_hash", type="TEXT"),
    Column(name="active", type="BOOLEAN"),
    Column(name="last_login", type="TEXT", nullable=True)
])

# Index for fast lookups
db.create_index("users", ["email"], unique=True)
db.create_index("users", ["username"], unique=True)
```

### E-commerce Products
```python
# Products with categories and pricing
db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="description", type="TEXT", nullable=True),
    Column(name="price", type="REAL"),
    Column(name="category", type="TEXT"),
    Column(name="stock_quantity", type="INTEGER"),
    Column(name="active", type="BOOLEAN")
])

# Indexes for common queries
db.create_index("products", ["category"])           # Browse by category
db.create_index("products", ["price"])              # Sort by price
db.create_index("products", ["category", "price"])  # Category + price queries
```

### Orders and Relationships  
```python
# Orders table
db.create_table("orders", [
    Column(name="user_id", type="TEXT"),    # References users.id
    Column(name="total", type="REAL"),
    Column(name="status", type="TEXT"),
    Column(name="shipped_at", type="TEXT", nullable=True)
])

# Order items (many-to-many)
db.create_table("order_items", [
    Column(name="order_id", type="TEXT"),   # References orders.id
    Column(name="product_id", type="TEXT"), # References products.id  
    Column(name="quantity", type="INTEGER"),
    Column(name="unit_price", type="REAL")
])

# Indexes for relationships
db.create_index("orders", ["user_id"])
db.create_index("orders", ["status", "created_at"])
db.create_index("order_items", ["order_id"])
db.create_index("order_items", ["product_id"])
```

## Working with Existing Tables

### Insert Data
```python
# Single record
user = db.insert("users", {
    "username": "johndoe",
    "email": "john@company.com",
    "active": True
})
# Expected output: {"id": "uuid-123", "username": "johndoe", "email": "john@company.com",
#                   "active": True, "created_at": "2025-01-15T10:30:00Z", "updated_at": "2025-01-15T10:30:00Z"}
# Performance: ~1ms per single insert
print(f"Created user: {user['id']}")
# Console output: Created user: uuid-123

# Multiple records
users = db.insert("users",
    {"username": "alice", "email": "alice@company.com", "active": True},
    {"username": "bob", "email": "bob@company.com", "active": True},
    {"username": "carol", "email": "carol@company.com", "active": False}
)
# Expected output: List of 3 user dictionaries with generated IDs and timestamps
# Performance: ~0.3ms per record in batch (3x faster than individual inserts)
print(f"Created {len(users)} users")
# Console output: Created 3 users

# Common errors:
# sqlite3.IntegrityError: UNIQUE constraint failed: users.email - Duplicate email
# ValueError: Table 'users' does not exist - Create table first
```

### Query Data
```python
# Get all active users
active_users = db.query("SELECT * FROM users WHERE active = ?", [True])
# Expected output: [{"id": "uuid-1", "username": "alice", "active": True, ...}, ...]
# Performance: <5ms for indexed columns, 10-50ms for full table scan
# Tip: Add index on 'active' column if frequently queried

# Complex query with joins
order_summary = db.query("""
    SELECT u.username, COUNT(o.id) as order_count, SUM(o.total) as total_spent
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.active = ?
    GROUP BY u.id
    ORDER BY total_spent DESC
""", [True])
# Expected output: [{"username": "alice", "order_count": 5, "total_spent": 523.45}, ...]
# Performance: 10-30ms with proper indexes on join columns (u.id, o.user_id)
# Without indexes: 100-500ms for large datasets
# Optimization: Create index on orders.user_id for 10x speedup
```

### Update Records
```python
# Update single record
updated_user = db.update("users", {"id": user_id, "last_login": "2024-01-15T10:30:00Z"})
# Expected output: {"id": "uuid-123", ..., "last_login": "2024-01-15T10:30:00Z", "updated_at": "2025-01-15T11:00:00Z"}
# Performance: ~1ms per update
# Note: updated_at field automatically set to current timestamp

# Update via query
result = db.query("UPDATE products SET active = ? WHERE stock_quantity = 0", [False])
# Expected output: [] (UPDATE queries return empty list)
# Performance: ~5ms for indexed WHERE clause, 20-100ms for full table scan
# To get affected rows: Use db.query("SELECT changes()") immediately after
# Better approach: Query first, then update individually for audit trail
```

### Delete Records
```python
# Delete single record
deleted_count = db.delete("users", user_id)
# Expected output: 1 (number of deleted records)
# Performance: ~1ms per deletion
# Returns: 0 if record not found (no error thrown)

# Delete via query
db.query("DELETE FROM orders WHERE status = ? AND created_at < ?", ["cancelled", "2023-01-01"])
# Expected output: [] (DELETE queries return empty list)
# Performance: 5-20ms depending on index usage
# Warning: No automatic cascade delete - handle related records manually
# To get deleted count: db.query("SELECT changes()")[0]["changes()"]

# Common errors:
# sqlite3.IntegrityError: FOREIGN KEY constraint failed - Delete child records first
# Tip: Consider soft deletes for audit trails:
# db.update("orders", {"id": order_id, "deleted_at": "datetime('now')"})
```

## Multi-Tenant Tables

Tables work seamlessly with tenants:

```python
# Create table (affects all tenants)
table = db.create_table("companies", [
    Column(name="name", type="TEXT"),
    Column(name="industry", type="TEXT")
])
# Expected: Table schema replicated to all tenants
# Performance: ~5ms per tenant (lazy creation on first access)

# Connect to specific tenants
customer_a = cinchdb.connect("myapp", tenant="customer_a")
customer_b = cinchdb.connect("myapp", tenant="customer_b")
# Performance: <1ms connection time (lazy database creation)

# Each tenant has isolated data
company_a = customer_a.insert("companies", {"name": "Acme Corp", "industry": "Manufacturing"})
# Expected: {"id": "uuid-a1", "name": "Acme Corp", "industry": "Manufacturing", ...}

company_b = customer_b.insert("companies", {"name": "Globodyne", "industry": "Technology"})
# Expected: {"id": "uuid-b1", "name": "Globodyne", "industry": "Technology", ...}

# Queries only see tenant's data
acme_companies = customer_a.query("SELECT * FROM companies")
# Expected output: [{"id": "uuid-a1", "name": "Acme Corp", ...}]

globodyne_companies = customer_b.query("SELECT * FROM companies")
# Expected output: [{"id": "uuid-b1", "name": "Globodyne", ...}]

# Performance characteristics:
# - Complete data isolation between tenants
# - No performance impact from other tenants' data volume
# - Each tenant gets dedicated SQLite database file
```

## Best Practices

### Naming Conventions
```python
# Table names - plural nouns
"users", "products", "orders", "order_items"

# Column names - snake_case
"first_name", "email_address", "created_at", "is_active"

# Avoid reserved words
# BAD: "user", "order", "table"
# GOOD: "users", "orders", "data_tables"
```

### Indexing Strategy
```python
# Index frequently queried columns
db.create_index("users", ["email"])        # Login queries
db.create_index("products", ["category"])  # Browse queries
db.create_index("orders", ["user_id"])     # User's orders

# Compound indexes for complex queries
db.create_index("products", ["category", "price"])     # Category + price filtering
db.create_index("orders", ["status", "created_at"])    # Status + date queries
```

### Schema Design
```python
# Use appropriate types
Column(name="price", type="REAL")           # Not TEXT
Column(name="quantity", type="INTEGER")     # Not REAL
Column(name="active", type="BOOLEAN")       # Not INTEGER

# Make appropriate columns nullable
Column(name="name", type="TEXT", nullable=False)      # Required
Column(name="middle_name", type="TEXT", nullable=True) # Optional

# Add unique constraints where needed
Column(name="email", type="TEXT", unique=True)
Column(name="username", type="TEXT", unique=True)
```

## Flexible Data Storage Options

CinchDB emphasizes structured schemas with proper columns. This enables fast queries, indexes, type safety, and easier maintenance. However, different use cases call for different storage approaches:

### When to Use Structured Columns (Recommended)

Define explicit columns for data that needs to be queried, filtered, or indexed:

```python
# Good: Structured schema
db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT", unique=True),
    Column(name="theme", type="TEXT"),
    Column(name="language", type="TEXT"),
    Column(name="notifications_enabled", type="BOOLEAN")
])

# Benefits:
# - Fast queries: WHERE theme = 'dark'
# - Indexes work efficiently
# - Type safety and constraints
# - Easy to evolve schema (add columns as needed)
```

### When to Use Key-Value Store

For simple, unstructured data that doesn't need complex queries, use the KV store:

```python
# Good: Simple key-value pairs
db.kv.set("user:123:settings", {"theme": "dark", "lang": "en", "notifications": True})
settings = db.kv.get("user:123:settings")

# Good for:
# - Session data (with TTL)
# - Cache values
# - Simple configuration that's looked up by key only
# - Temporary data

# Not good for:
# - Data you need to query across multiple records
# - Data that needs indexes
# - Data with complex relationships
```

### Advanced: JSON in TEXT Columns

SQLite supports JSON functions for advanced users who need semi-structured data. Store JSON strings in TEXT columns:

```python
import json

# Store JSON in TEXT column
db.create_table("events", [
    Column(name="event_type", type="TEXT"),
    Column(name="metadata", type="TEXT")  # Will contain JSON
])

db.insert("events", {
    "event_type": "page_view",
    "metadata": json.dumps({"page": "/home", "duration": 3.5, "referrer": "google"})
})

# Query JSON fields using SQLite's json_extract()
results = db.query("""
    SELECT event_type, json_extract(metadata, '$.page') as page
    FROM events
    WHERE json_extract(metadata, '$.duration') > 3
""")
```

**When to use JSON columns:**
- Storing API responses or external data with varying structure
- Flexible metadata that changes per record
- Advanced users comfortable with JSON path syntax

**Important notes:**
- `db.query()` only allows SELECT statements - no json_set() or json_patch()
- To update JSON values, you must replace the entire field
- If you find yourself frequently querying JSON fields, normalize to proper columns instead
- JSON columns are harder to index and query efficiently

**Recommended approach:** Start with structured columns. Add specific columns as you identify common query patterns. Use KV store for simple lookups. Reserve JSON for truly flexible data that doesn't need complex queries.

## Troubleshooting

### Error: "Table already exists"
```python
db.create_table("users", [Column(name="email", type="TEXT")])
# Raises: ValueError: Table 'users' already exists
```
**Cause**: Table was created previously
**Solutions**:
1. Check existing tables: `tables = db.list_tables()`
2. Get table info: `table = db.get_table("users")`
3. Use different name: `db.create_table("user_profiles", ...)`
4. Delete and recreate: `db.drop_table("users")` then create

### Error: "No such table: users"
```python
result = db.query("SELECT * FROM users")
# Raises: sqlite3.OperationalError: no such table: users
```
**Cause**: Table doesn't exist on current branch/database
**Solutions**:
1. Check available tables: `db.list_tables()`
2. Verify current branch: `db.current_branch`
3. Create table first:
   ```python
   db.create_table("users", [
       Column(name="email", type="TEXT")
   ])
   ```

### Error: "UNIQUE constraint failed: users.email"
```python
db.insert("users", {"email": "john@example.com"})
db.insert("users", {"email": "john@example.com"})  # Fails
# Raises: sqlite3.IntegrityError: UNIQUE constraint failed: users.email
```
**Cause**: Inserting duplicate value in unique column
**Solutions**:
1. Check before insert:
   ```python
   existing = db.query("SELECT id FROM users WHERE email = ?", ["john@example.com"])
   if not existing:
       db.insert("users", {"email": "john@example.com"})
   ```
2. Use upsert pattern (update if exists)
3. Remove unique constraint if duplicates are allowed

**"Slow queries" (>100ms)**
- **Cause**: Missing indexes on WHERE/JOIN columns
- **Solution**: Add indexes: `db.create_index("table", ["column"], name="idx_name")`
- **Analyze**: `db.query("EXPLAIN QUERY PLAN SELECT ...")` to check index usage
- **Performance expectation**:
  - Indexed queries: <5ms
  - Non-indexed small tables (<1000 rows): 5-20ms
  - Non-indexed large tables: 100ms+

**"Database is locked"**
- **Cause**: Concurrent write operations or unclosed transactions
- **Solution**: CinchDB uses WAL mode to minimize locking
- **Debug**: Check for long-running operations
- **Prevention**: Keep write operations short

## Next Steps

- [Query Guide](queries.md) - Writing effective queries
- [Connection Guide](connection.md) - Managing database connections  
- [CLI Table Commands](../cli/table.md) - Command-line table management
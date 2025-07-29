# Table Operations

Create and manage database tables with the Python SDK.

## Creating Tables

### Basic Table Creation
```python
from cinchdb.models import Column

db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT"),
    Column(name="age", type="INTEGER")
])
```

### Column Types
```python
# All supported types
db.create_table("products", [
    Column(name="name", type="TEXT"),          # String
    Column(name="price", type="REAL"),         # Decimal
    Column(name="stock", type="INTEGER"),      # Whole number
    Column(name="active", type="BOOLEAN"),     # True/False
    Column(name="data", type="BLOB")           # Binary
])
```

### Nullable Columns
```python
# Required vs optional columns
db.create_table("posts", [
    Column(name="title", type="TEXT"),                    # Required
    Column(name="content", type="TEXT"),                  # Required
    Column(name="published_at", type="TEXT", nullable=True)  # Optional
])
```

### Automatic Columns
Every table includes:
- `id` - UUID primary key (auto-generated)
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## Listing Tables

### Get All Tables
```python
# Using convenience method
tables = db.query(
    "SELECT name FROM sqlite_master WHERE type='table'"
)

# Local connection with manager
if db.is_local:
    table_list = db.tables.list_tables()
    for table in table_list:
        print(f"Table: {table.name}")
        print(f"Columns: {len(table.columns)}")
```

### Check Table Exists
```python
def table_exists(db, table_name: str) -> bool:
    result = db.query(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        [table_name]
    )
    return len(result) > 0
```

## Table Information

### Get Table Schema
```python
# Query approach
columns = db.query(
    "PRAGMA table_info(users)"
)

for col in columns:
    print(f"{col['name']}: {col['type']}")
    
# Local manager approach
if db.is_local:
    info = db.tables.get_table_info("users")
    for column in info.columns:
        print(f"{column.name}: {column.type}")
```

### Count Rows
```python
result = db.query("SELECT COUNT(*) as count FROM users")
row_count = result[0]["count"]
```

## Modifying Tables

### Add Columns
```python
# Using local manager
if db.is_local:
    db.columns.add_column("users", 
        Column(name="phone", type="TEXT", nullable=True)
    )

# Or use raw SQL
db.query("ALTER TABLE users ADD COLUMN phone TEXT")
```

### Copy Table
```python
# Schema only
if db.is_local:
    db.tables.copy_table("users", "users_backup")

# With data
db.query("CREATE TABLE users_backup AS SELECT * FROM users")
```

## Deleting Tables

### Drop Table
```python
# With local manager
if db.is_local:
    db.tables.delete_table("old_table")

# With SQL
db.query("DROP TABLE IF EXISTS old_table")
```

**Warning**: This permanently deletes all data!

## Common Patterns

### User Management Table
```python
db.create_table("users", [
    Column(name="username", type="TEXT"),
    Column(name="email", type="TEXT"),
    Column(name="password_hash", type="TEXT"),
    Column(name="full_name", type="TEXT", nullable=True),
    Column(name="bio", type="TEXT", nullable=True),
    Column(name="avatar_url", type="TEXT", nullable=True),
    Column(name="is_active", type="BOOLEAN"),
    Column(name="is_admin", type="BOOLEAN"),
    Column(name="last_login", type="TEXT", nullable=True)
])
```

### E-commerce Tables
```python
# Products
db.create_table("products", [
    Column(name="sku", type="TEXT"),
    Column(name="name", type="TEXT"),
    Column(name="description", type="TEXT", nullable=True),
    Column(name="category", type="TEXT"),
    Column(name="price", type="REAL"),
    Column(name="cost", type="REAL"),
    Column(name="stock", type="INTEGER"),
    Column(name="min_stock", type="INTEGER"),
    Column(name="is_active", type="BOOLEAN")
])

# Orders
db.create_table("orders", [
    Column(name="user_id", type="TEXT"),
    Column(name="order_number", type="TEXT"),
    Column(name="status", type="TEXT"),
    Column(name="subtotal", type="REAL"),
    Column(name="tax", type="REAL"),
    Column(name="shipping", type="REAL"),
    Column(name="total", type="REAL"),
    Column(name="notes", type="TEXT", nullable=True)
])

# Order Items
db.create_table("order_items", [
    Column(name="order_id", type="TEXT"),
    Column(name="product_id", type="TEXT"),
    Column(name="quantity", type="INTEGER"),
    Column(name="unit_price", type="REAL"),
    Column(name="total_price", type="REAL")
])
```

### Audit Log Table
```python
db.create_table("audit_logs", [
    Column(name="user_id", type="TEXT"),
    Column(name="action", type="TEXT"),
    Column(name="resource_type", type="TEXT"),
    Column(name="resource_id", type="TEXT"),
    Column(name="old_values", type="TEXT", nullable=True),
    Column(name="new_values", type="TEXT", nullable=True),
    Column(name="ip_address", type="TEXT", nullable=True),
    Column(name="user_agent", type="TEXT", nullable=True)
])
```

## Best Practices

### 1. Naming Conventions
```python
# Good table names
db.create_table("users", ...)          # Plural, lowercase
db.create_table("order_items", ...)     # Snake_case for multi-word

# Avoid
db.create_table("User", ...)            # Singular, capitalized
db.create_table("OrderItems", ...)      # CamelCase
```

### 2. Column Design
```python
# Use appropriate types
Column(name="email", type="TEXT")       # Not INTEGER
Column(name="price", type="REAL")       # Not TEXT for money
Column(name="count", type="INTEGER")    # Not TEXT for numbers

# Be explicit about nullability
Column(name="required_field", type="TEXT", nullable=False)
Column(name="optional_field", type="TEXT", nullable=True)
```

### 3. Indexes for Performance
```python
# Create indexes on frequently queried columns
db.query("CREATE INDEX idx_users_email ON users(email)")
db.query("CREATE INDEX idx_orders_user_id ON orders(user_id)")
db.query("CREATE INDEX idx_orders_status ON orders(status)")
```

### 4. Constraints
```python
# Unique constraints
db.query("CREATE UNIQUE INDEX idx_users_username ON users(username)")

# Check constraints (SQLite 3.37+)
db.query("""
    ALTER TABLE products 
    ADD CONSTRAINT positive_price 
    CHECK (price >= 0)
""")
```

## Error Handling

```python
from cinchdb.exceptions import TableAlreadyExistsError, InvalidColumnTypeError

try:
    db.create_table("users", columns)
except TableAlreadyExistsError:
    print("Table already exists")
except InvalidColumnTypeError as e:
    print(f"Invalid column type: {e}")
```

## Migration Patterns

### Safe Column Addition
```python
def add_column_safely(db, table: str, column: Column):
    # Check if column exists
    existing = db.query(f"PRAGMA table_info({table})")
    column_names = [col["name"] for col in existing]
    
    if column.name not in column_names:
        if db.is_local:
            db.columns.add_column(table, column)
        else:
            db.query(f"ALTER TABLE {table} ADD COLUMN {column.name} {column.type}")
```

### Table Versioning
```python
# Keep track of schema versions
db.create_table("schema_versions", [
    Column(name="version", type="INTEGER"),
    Column(name="description", type="TEXT"),
    Column(name="applied_at", type="TEXT")
])

# Record migrations
db.insert("schema_versions", {
    "version": 1,
    "description": "Initial schema",
    "applied_at": datetime.now().isoformat()
})
```

## Next Steps

- [Query Guide](queries.md) - Query your tables
- [Column Reference](../cli/column.md) - Column management
- [Views](../cli/view.md) - Create virtual tables
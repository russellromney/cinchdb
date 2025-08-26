# Table Operations

Create and manage tables with the Python SDK.

## Creating Tables

### Basic Tables
```python
from cinchdb.models import Column

db = cinchdb.connect("myapp")

# Simple table
db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT", unique=True),
    Column(name="age", type="INTEGER", nullable=True)
])
```

Every table automatically gets:
- `id` - UUID primary key
- `created_at` - Creation timestamp  
- `updated_at` - Last modified timestamp

### Column Types
```python
# Common column types
Column(name="name", type="TEXT")           # String
Column(name="price", type="REAL")          # Decimal number
Column(name="quantity", type="INTEGER")    # Whole number  
Column(name="active", type="BOOLEAN")      # True/false
Column(name="data", type="BLOB")          # Binary data

# Column properties
Column(name="email", type="TEXT", nullable=False, unique=True)
Column(name="bio", type="TEXT", nullable=True)  # Can be NULL
```

### Tables with Indexes
```python
# Create table
db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="price", type="REAL"),
    Column(name="category", type="TEXT")
])

# Add indexes after creation
db.create_index("products", ["name"])              # Simple index
db.create_index("products", ["email"], unique=True) # Unique index  
db.create_index("products", ["category", "price"])  # Compound index
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
print(f"Created user: {user['id']}")

# Multiple records  
users = db.insert("users",
    {"username": "alice", "email": "alice@company.com", "active": True},
    {"username": "bob", "email": "bob@company.com", "active": True}, 
    {"username": "carol", "email": "carol@company.com", "active": False}
)
print(f"Created {len(users)} users")
```

### Query Data
```python
# Get all active users
active_users = db.query("SELECT * FROM users WHERE active = ?", [True])

# Complex query with joins
order_summary = db.query("""
    SELECT u.username, COUNT(o.id) as order_count, SUM(o.total) as total_spent
    FROM users u 
    LEFT JOIN orders o ON u.id = o.user_id 
    WHERE u.active = ?
    GROUP BY u.id
    ORDER BY total_spent DESC
""", [True])
```

### Update Records
```python
# Update single record
db.update("users", user_id, {"last_login": "2024-01-15T10:30:00Z"})

# Update via query
db.query("UPDATE products SET active = ? WHERE stock_quantity = 0", [False])
```

### Delete Records
```python
# Delete single record
db.delete("users", user_id)

# Delete via query  
db.query("DELETE FROM orders WHERE status = ? AND created_at < ?", ["cancelled", "2023-01-01"])
```

## Multi-Tenant Tables

Tables work seamlessly with tenants:

```python
# Create table (affects all tenants)
db.create_table("companies", [
    Column(name="name", type="TEXT"),
    Column(name="industry", type="TEXT")
])

# Connect to specific tenants
customer_a = cinchdb.connect("myapp", tenant="customer_a")
customer_b = cinchdb.connect("myapp", tenant="customer_b")

# Each tenant has isolated data
customer_a.insert("companies", {"name": "Acme Corp", "industry": "Manufacturing"})
customer_b.insert("companies", {"name": "Globodyne", "industry": "Technology"})

# Queries only see tenant's data
acme_companies = customer_a.query("SELECT * FROM companies")    # Only Acme Corp
globodyne_companies = customer_b.query("SELECT * FROM companies") # Only Globodyne
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

## Troubleshooting

**"Table already exists"** → Table was created previously. Use different name or delete existing table.

**"No such table"** → Make sure you're on the right branch: `cinch branch list`

**"UNIQUE constraint failed"** → Trying to insert duplicate value in unique column.

**"Slow queries"** → Add indexes on frequently queried columns.

## Next Steps

- [Query Guide](queries.md) - Writing effective queries
- [Connection Guide](connection.md) - Managing database connections  
- [CLI Table Commands](../cli/table.md) - Command-line table management
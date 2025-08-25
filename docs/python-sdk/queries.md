# Query Guide

Execute SQL queries and work with data using the Python SDK.

## Basic Queries

### SELECT Queries
```python
# Simple select
users = db.query("SELECT * FROM users")

# With conditions
active_users = db.query("SELECT * FROM users WHERE active = true")

# Specific columns
emails = db.query("SELECT email FROM users")
```

### Parameterized Queries
Always use parameters to prevent SQL injection:

```python
# Safe parameterized query
user = db.query(
    "SELECT * FROM users WHERE email = ?", 
    ["alice@example.com"]
)

# Multiple parameters
users = db.query(
    "SELECT * FROM users WHERE age > ? AND active = ?",
    [18, True]
)

# Named parameters (not supported - use positional)
# Use multiple ? placeholders instead
```

## Query Results

### Result Format
Query results are returned as list of dictionaries:

```python
users = db.query("SELECT id, name, email FROM users")
# Returns: [
#   {"id": "123", "name": "Alice", "email": "alice@example.com"},
#   {"id": "456", "name": "Bob", "email": "bob@example.com"}
# ]

# Access results
for user in users:
    print(f"{user['name']}: {user['email']}")

# Single result
first_user = users[0] if users else None
```

### Empty Results
```python
results = db.query("SELECT * FROM users WHERE age > ?", [200])
if not results:
    print("No users found")
```

## INSERT Operations

### Basic Insert
```python
# Insert returns the created record with generated fields
user = db.insert("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "active": True
})

print(f"Created user: {user['id']}")
print(f"Created at: {user['created_at']}")
```

### Batch Insert
```python
# Insert multiple records at once using star expansion
users = db.insert("users",
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
)
# Returns a list of created records

# Or with a list using star expansion
users_data = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
]
inserted_users = db.insert("users", *users_data)

# Each record includes generated fields (id, created_at, updated_at)
for user in inserted_users:
    print(f"Created user {user['name']} with ID: {user['id']}")
```

## UPDATE Operations

### Update by ID
```python
# Update specific record
updated = db.update("users", user_id, {
    "name": "Alice Smith",
    "active": False
})

print(f"Updated at: {updated['updated_at']}")
```

### Update with Conditions
```python
# For conditional updates, iterate through matching records
users_to_update = db.query(
    "SELECT id FROM users WHERE last_login < ?",
    ["2024-01-01"]
)
for user in users_to_update:
    db.update("users", user["id"], {"active": False})

# For bulk updates with calculations, fetch and update individually
products = db.query(
    "SELECT id, price FROM products WHERE category = ?",
    ["electronics"]
)
for product in products:
    db.update("products", product["id"], {"price": product["price"] * 1.1})
```

## DELETE Operations

### Delete by ID
```python
# Delete specific record
db.delete("users", user_id)
```

### Delete with Conditions
```python
# For conditional deletes, fetch matching records first
old_sessions = db.query(
    "SELECT id FROM sessions WHERE created_at < datetime('now', '-7 days')"
)
for session in old_sessions:
    db.delete("sessions", session["id"])

# Delete with multiple conditions
inactive_users = db.query(
    "SELECT id FROM users WHERE active = ? AND last_login < ?",
    [False, "2023-01-01"]
)
for user in inactive_users:
    db.delete("users", user["id"])
```

## Advanced Queries

### Joins
```python
# Inner join
user_orders = db.query("""
    SELECT u.name, o.order_number, o.total
    FROM users u
    INNER JOIN orders o ON u.id = o.user_id
    WHERE u.active = ?
""", [True])

# Left join
all_users_orders = db.query("""
    SELECT u.name, COUNT(o.id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id
""")
```

### Aggregations
```python
# Count
result = db.query("SELECT COUNT(*) as total FROM users")
total_users = result[0]["total"]

# Sum and average
stats = db.query("""
    SELECT 
        COUNT(*) as order_count,
        SUM(total) as revenue,
        AVG(total) as avg_order
    FROM orders
    WHERE status = ?
""", ["completed"])

# Group by
category_sales = db.query("""
    SELECT 
        p.category,
        COUNT(DISTINCT o.id) as orders,
        SUM(oi.quantity) as units_sold,
        SUM(oi.total_price) as revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.status = ?
    GROUP BY p.category
    ORDER BY revenue DESC
""", ["completed"])
```

### Subqueries
```python
# Subquery in WHERE
high_value_users = db.query("""
    SELECT * FROM users
    WHERE id IN (
        SELECT user_id FROM orders
        GROUP BY user_id
        HAVING SUM(total) > ?
    )
""", [1000])

# Subquery in SELECT
user_stats = db.query("""
    SELECT 
        u.*,
        (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as order_count,
        (SELECT SUM(total) FROM orders WHERE user_id = u.id) as lifetime_value
    FROM users u
""")
```

## Working with Dates

### Date Functions
```python
# Current timestamp
db.insert("events", {
    "name": "User Login",
    "timestamp": "datetime('now')"  # SQLite function
})

# Date filtering
recent = db.query("""
    SELECT * FROM users
    WHERE created_at > datetime('now', '-30 days')
""")

# Date formatting
formatted = db.query("""
    SELECT 
        name,
        strftime('%Y-%m-%d', created_at) as signup_date
    FROM users
""")
```

### Date Calculations
```python
# Days since signup
user_age = db.query("""
    SELECT 
        name,
        julianday('now') - julianday(created_at) as days_since_signup
    FROM users
""")

# Group by month
monthly = db.query("""
    SELECT 
        strftime('%Y-%m', created_at) as month,
        COUNT(*) as signups
    FROM users
    GROUP BY month
    ORDER BY month DESC
""")
```

## Transactions

### Automatic Transactions
Individual operations (insert, update, delete) are automatically wrapped in transactions.

### Complex Operations
```python
# For operations requiring multiple steps, use the API methods
try:
    # Create user and profile
    user = db.insert("users", {"name": "Alice"})
    profile = db.insert("profiles", {"user_id": user["id"], "bio": "..."})
    
    # Update stats
    stats = db.query("SELECT * FROM stats WHERE id = 1")[0]
    db.update("stats", stats["id"], {"user_count": stats["user_count"] + 1})
    
except Exception as e:
    print(f"Operation failed: {e}")
    raise
```

## Query Optimization

### Use Indexes
```python
# Create indexes through table management
# Indexes should be created when defining tables or through schema migrations
# For frequently queried columns, consider adding indexes at table creation time

# Check query plan (read-only operation)
plan = db.query("EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = ?", ["test@example.com"])
```

### Limit Results
```python
# Always limit when you don't need all results
recent_orders = db.query("""
    SELECT * FROM orders
    ORDER BY created_at DESC
    LIMIT 10
""")

# Pagination
page = 2
per_page = 20
offset = (page - 1) * per_page

results = db.query("""
    SELECT * FROM products
    ORDER BY name
    LIMIT ? OFFSET ?
""", [per_page, offset])
```

### Select Only Needed Columns
```python
# Bad - selects all columns
users = db.query("SELECT * FROM users")

# Good - selects only needed columns
users = db.query("SELECT id, name, email FROM users")
```

## Error Handling

```python
try:
    result = db.query("SELECT * FROM users WHERE id = ?", [user_id])
except Exception as e:
    print(f"Query failed: {e}")
    
# Check for no results
user = db.query("SELECT * FROM users WHERE id = ?", [user_id])
if not user:
    raise ValueError("User not found")
```

## Views and CTEs

### Query Views
```python
# Views work like tables
active_users = db.query("SELECT * FROM active_users_view")
```

### Common Table Expressions (CTEs)
```python
results = db.query("""
    WITH user_orders AS (
        SELECT user_id, COUNT(*) as order_count, SUM(total) as total_spent
        FROM orders
        GROUP BY user_id
    )
    SELECT u.name, uo.order_count, uo.total_spent
    FROM users u
    JOIN user_orders uo ON u.id = uo.user_id
    WHERE uo.order_count > ?
""", [5])
```

## Best Practices

1. **Always Use Parameters** - Never concatenate SQL strings
2. **Handle Empty Results** - Check if results exist before accessing
3. **Use Transactions** - For multi-step operations
4. **Limit Results** - Don't fetch more data than needed
5. **Create Indexes** - For frequently queried columns
6. **Close Connections** - Use context managers

## Next Steps

- [Branches](branches.md) - Query different branches
- [Tenants](tenants.md) - Multi-tenant queries
- [API Reference](api-reference.md) - Complete method reference
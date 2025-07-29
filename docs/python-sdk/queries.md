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

### Bulk Insert
```python
# Insert multiple records
users_data = [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
]

for user_data in users_data:
    db.insert("users", user_data)

# Or use raw SQL for efficiency
db.query("""
    INSERT INTO users (id, name, email, created_at, updated_at) 
    VALUES 
    (?, ?, ?, datetime('now'), datetime('now')),
    (?, ?, ?, datetime('now'), datetime('now'))
""", [
    str(uuid.uuid4()), "Alice", "alice@example.com",
    str(uuid.uuid4()), "Bob", "bob@example.com"
])
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
# Update multiple records
db.query(
    "UPDATE users SET active = ? WHERE last_login < ?",
    [False, "2024-01-01"]
)

# Update with calculations
db.query(
    "UPDATE products SET price = price * ? WHERE category = ?",
    [1.1, "electronics"]
)
```

## DELETE Operations

### Delete by ID
```python
# Delete specific record
db.delete("users", user_id)
```

### Delete with Conditions
```python
# Delete multiple records
db.query(
    "DELETE FROM sessions WHERE created_at < datetime('now', '-7 days')"
)

# Delete with parameters
db.query(
    "DELETE FROM users WHERE active = ? AND last_login < ?",
    [False, "2023-01-01"]
)
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

### Manual Transactions
```python
# For complex operations
try:
    db.query("BEGIN")
    
    # Multiple operations
    user = db.insert("users", {"name": "Alice"})
    db.insert("profiles", {"user_id": user["id"], "bio": "..."})
    db.query("UPDATE stats SET user_count = user_count + 1")
    
    db.query("COMMIT")
except Exception as e:
    db.query("ROLLBACK")
    raise
```

### Automatic Transactions
Individual operations are automatically wrapped in transactions.

## Query Optimization

### Use Indexes
```python
# Create indexes for frequently queried columns
db.query("CREATE INDEX idx_users_email ON users(email)")
db.query("CREATE INDEX idx_orders_user_status ON orders(user_id, status)")

# Check query plan
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
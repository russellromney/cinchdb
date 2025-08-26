# Query Guide

Execute SQL queries with the Python SDK.

## Problem → Solution

**Problem**: Need to safely execute SQL queries and work with results in Python  
**Solution**: CinchDB's `query()` method handles parameterization, results, and transactions

## Quick Reference

| Operation | Method | Example |
|-----------|--------|---------|
| SELECT | `db.query()` | `db.query("SELECT * FROM users")` |
| INSERT | `db.insert()` | `db.insert("users", {"name": "Alice"})` |
| UPDATE | `db.update()` | `db.update("users", user_id, {"name": "Bob"})` |
| DELETE | `db.delete()` | `db.delete("users", user_id)` |

## Safe Parameterized Queries

**Always use parameters** to prevent SQL injection:

```python
# ✅ Safe
user = db.query("SELECT * FROM users WHERE email = ?", ["alice@example.com"])
users = db.query("SELECT * FROM users WHERE age > ? AND active = ?", [18, True])

# ❌ Dangerous - never do this
user = db.query(f"SELECT * FROM users WHERE email = '{email}'")  # SQL injection risk
```

## Working with Results

```python
# Results are list of dictionaries
users = db.query("SELECT id, name, email FROM users")
# Returns: [{"id": "123", "name": "Alice", "email": "alice@example.com"}, ...]

# Iterate results
for user in users:
    print(f"{user['name']}: {user['email']}")

# Handle empty results
user = db.query("SELECT * FROM users WHERE id = ?", [user_id])
if not user:
    raise ValueError("User not found")

# Single result
first_user = user[0] if user else None
```

## INSERT Operations

```python
# Single insert - returns created record with generated fields
user = db.insert("users", {"name": "Alice", "email": "alice@example.com", "active": True})
print(f"Created user: {user['id']}")

# Batch insert using star expansion
users = db.insert("users",
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
)

# From a list
users_data = [{"name": "Alice", "email": "alice@example.com"}, {"name": "Bob", "email": "bob@example.com"}]
inserted_users = db.insert("users", *users_data)
```

## UPDATE Operations

```python
# Update by ID
updated = db.update("users", user_id, {"name": "Alice Smith", "active": False})
print(f"Updated at: {updated['updated_at']}")

# Conditional updates - query then update
users_to_deactivate = db.query("SELECT id FROM users WHERE last_login < ?", ["2024-01-01"])
for user in users_to_deactivate:
    db.update("users", user["id"], {"active": False})

# Bulk updates with calculations
products = db.query("SELECT id, price FROM products WHERE category = ?", ["electronics"])
for product in products:
    db.update("products", product["id"], {"price": product["price"] * 1.1})
```

## DELETE Operations

```python
# Delete by ID
db.delete("users", user_id)

# Conditional deletes - query then delete
old_sessions = db.query("SELECT id FROM sessions WHERE created_at < datetime('now', '-7 days')")
for session in old_sessions:
    db.delete("sessions", session["id"])

# Delete with multiple conditions
inactive_users = db.query("SELECT id FROM users WHERE active = ? AND last_login < ?", [False, "2023-01-01"])
for user in inactive_users:
    db.delete("users", user["id"])
```

## Advanced Queries

```python
# Joins
user_orders = db.query("""
    SELECT u.name, o.order_number, o.total FROM users u
    INNER JOIN orders o ON u.id = o.user_id WHERE u.active = ?
""", [True])

# Aggregations
total_users = db.query("SELECT COUNT(*) as total FROM users")[0]["total"]
order_stats = db.query("""
    SELECT COUNT(*) as orders, SUM(total) as revenue, AVG(total) as avg_order
    FROM orders WHERE status = ?
""", ["completed"])[0]

# Group by with joins
category_sales = db.query("""
    SELECT p.category, COUNT(DISTINCT o.id) as orders, SUM(oi.total_price) as revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    JOIN orders o ON oi.order_id = o.id
    WHERE o.status = ? GROUP BY p.category ORDER BY revenue DESC
""", ["completed"])

# Subqueries
high_value_users = db.query("""
    SELECT * FROM users WHERE id IN (
        SELECT user_id FROM orders GROUP BY user_id HAVING SUM(total) > ?
    )
""", [1000])
```

## Working with Dates

```python
# Current timestamp in SQLite
db.insert("events", {"name": "User Login", "timestamp": "datetime('now')"})

# Date filtering
recent_users = db.query("SELECT * FROM users WHERE created_at > datetime('now', '-30 days')")

# Date formatting  
formatted_dates = db.query("SELECT name, strftime('%Y-%m-%d', created_at) as signup_date FROM users")

# Date calculations
user_age = db.query("SELECT name, julianday('now') - julianday(created_at) as days_since_signup FROM users")
monthly_signups = db.query("SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as signups FROM users GROUP BY month")
```

## Transactions

**Individual operations** (insert, update, delete) are automatically wrapped in transactions.

```python
# Multi-step operations rely on individual operation atomicity
try:
    user = db.insert("users", {"name": "Alice"})
    profile = db.insert("profiles", {"user_id": user["id"], "bio": "Software Developer"})
    
    # Update counters
    stats = db.query("SELECT * FROM stats WHERE id = 1")[0]
    db.update("stats", stats["id"], {"user_count": stats["user_count"] + 1})
except Exception as e:
    print(f"Operation failed: {e}")
    raise

# Note: Full transaction rollback is not currently supported
```

## Performance Tips

| Technique | Example |
|-----------|----------|
| Use indexes | Create indexes on frequently queried columns |
| Limit results | `LIMIT 10` instead of fetching all rows |
| Select specific columns | `SELECT id, name` instead of `SELECT *` |
| Use parameters | Always use `?` placeholders |

```python
# Pagination
page, per_page = 2, 20
offset = (page - 1) * per_page
results = db.query("SELECT * FROM products ORDER BY name LIMIT ? OFFSET ?", [per_page, offset])

# Check query plan
plan = db.query("EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = ?", ["test@example.com"])

# ✅ Good - specific columns
users = db.query("SELECT id, name, email FROM users")

# ❌ Bad - all columns
users = db.query("SELECT * FROM users")
```

## Error Handling

```python
# Handle query errors
try:
    result = db.query("SELECT * FROM users WHERE id = ?", [user_id])
except Exception as e:
    print(f"Query failed: {e}")
    raise

# Handle empty results
user = db.query("SELECT * FROM users WHERE id = ?", [user_id])
if not user:
    raise ValueError("User not found")
```

## Advanced Features

```python
# Views work like tables
active_users = db.query("SELECT * FROM active_users_view")

# Common Table Expressions (CTEs)
high_value_customers = db.query("""
    WITH user_orders AS (
        SELECT user_id, COUNT(*) as order_count, SUM(total) as total_spent
        FROM orders GROUP BY user_id
    )
    SELECT u.name, uo.order_count, uo.total_spent
    FROM users u JOIN user_orders uo ON u.id = uo.user_id
    WHERE uo.order_count > ?
""", [5])
```

## Best Practices

- **Always use parameters** - Prevent SQL injection with `?` placeholders
- **Handle empty results** - Check `if not results:` before accessing
- **Limit results** - Use `LIMIT` to avoid fetching unnecessary data  
- **Select specific columns** - Avoid `SELECT *` in production
- **Create indexes** - Index frequently queried columns
- **Use proper error handling** - Catch and handle database exceptions

## Next Steps

- [Branches](branches.md) - Query different branches
- [Tenants](tenants.md) - Multi-tenant queries
- [API Reference](api-reference.md) - Complete method reference
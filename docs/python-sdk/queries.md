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
| UPDATE | `db.update()` | `db.update("users", {"id": user_id, "name": "Bob"})` |
| DELETE | `db.delete()` | `db.delete("users", user_id)` |
| Batch Insert | `db.insert()` | `db.insert("users", data1, data2, ...)` |
| Batch Update | `db.update()` | `db.update("users", {"id": id1, ...}, {"id": id2, ...})` |
| Batch Delete | `db.delete()` | `db.delete("users", id1, id2, ...)` |
| Update Where | `db.update_where()` | `db.update_where("users", {"active": False}, age__gt=65)` |
| Delete Where | `db.delete_where()` | `db.delete_where("users", status="inactive")` |

## Safe Parameterized Queries

**Always use parameters** to prevent SQL injection:

```python
# ✅ Safe
user = db.query("SELECT * FROM users WHERE email = ?", ["alice@example.com"])
# Expected output: [{"id": "123", "name": "Alice", "email": "alice@example.com"}]
# Performance: <1ms for indexed columns

users = db.query("SELECT * FROM users WHERE age > ? AND active = ?", [18, True])
# Expected output: [{"id": "124", "name": "Bob", "age": 25, "active": True}, ...]
# Performance: 1-5ms for typical queries with indexes

# ❌ Dangerous - never do this
user = db.query(f"SELECT * FROM users WHERE email = '{email}'")  # SQL injection risk
# Error: Vulnerable to SQL injection attacks!
```

## Working with Results

```python
# Results are list of dictionaries
users = db.query("SELECT id, name, email FROM users")
# Expected output: [{"id": "123", "name": "Alice", "email": "alice@example.com"}, ...]
# Performance: <1ms for small tables (<1000 rows), 5-20ms for larger tables

# Iterate results
for user in users:
    print(f"{user['name']}: {user['email']}")
# Console output:
# Alice: alice@example.com
# Bob: bob@example.com

# Handle empty results
user = db.query("SELECT * FROM users WHERE id = ?", [user_id])
if not user:
    raise ValueError("User not found")
# Expected output when user exists: [{"id": "123", ...}]
# Expected output when user doesn't exist: []
# Common error: ValueError: User not found

# Single result
first_user = user[0] if user else None
# Expected: {"id": "123", "name": "Alice", ...} or None
```

## INSERT Operations

```python
# Single insert - returns created record with generated fields
user = db.insert("users", {"name": "Alice", "email": "alice@example.com", "active": True})
# Expected output: {"id": "generated-uuid", "name": "Alice", "email": "alice@example.com", "active": True, "created_at": "2025-01-15T10:30:00Z"}
# Performance: ~1ms per single insert
print(f"Created user: {user['id']}")
# Console output: Created user: generated-uuid

# Batch insert using star expansion
users = db.insert("users",
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
)
# Expected output: [{"id": "uuid1", "name": "Alice", ...}, {"id": "uuid2", "name": "Bob", ...}, {"id": "uuid3", "name": "Charlie", ...}]
# Performance: ~0.1ms per record in batch (10x faster than individual inserts)

# From a list
users_data = [{"name": "Alice", "email": "alice@example.com"}, {"name": "Bob", "email": "bob@example.com"}]
inserted_users = db.insert("users", *users_data)
# Expected output: [{"id": "uuid4", "name": "Alice", ...}, {"id": "uuid5", "name": "Bob", ...}]

# Common errors:
# ValueError: Table 'users' does not exist - Create table first
# sqlite3.IntegrityError: UNIQUE constraint failed - Duplicate unique values
# TypeError: insert() requires at least one data dictionary
```

## UPDATE Operations

```python
# Update by ID
updated = db.update("users", {"id": user_id, "name": "Alice Smith", "active": False})
# Expected output: {"id": "123", "name": "Alice Smith", "active": False, "updated_at": "2025-01-15T11:00:00Z"}
# Performance: ~1ms per update
print(f"Updated at: {updated['updated_at']}")
# Console output: Updated at: 2025-01-15T11:00:00Z

# Conditional updates - query then update
users_to_deactivate = db.query("SELECT id FROM users WHERE last_login < ?", ["2024-01-01"])
# Expected: [{"id": "123"}, {"id": "124"}, ...]
for user in users_to_deactivate:
    db.update("users", {"id": user["id"], "active": False})
    # Each update: ~1ms
# Total performance: ~1ms per user (consider batch operations for large datasets)

# Bulk updates with calculations
products = db.query("SELECT id, price FROM products WHERE category = ?", ["electronics"])
for product in products:
    new_price = product["price"] * 1.1  # 10% increase
    db.update("products", {"id": product["id"], "price": new_price})
    # Performance tip: For >100 items, consider raw SQL UPDATE for better performance

# Common errors:
# ValueError: Record with ID '999' not found - Check if record exists
# TypeError: update() requires a dictionary of changes
```

## DELETE Operations

```python
# Delete by ID
deleted_count = db.delete("users", user_id)
# Expected output: 1 (number of deleted records)
# Performance: ~1ms per delete
# Note: Returns 0 if record doesn't exist (no error)

# Conditional deletes - query then delete
old_sessions = db.query("SELECT id FROM sessions WHERE created_at < datetime('now', '-7 days')")
# Expected: [{"id": "sess1"}, {"id": "sess2"}, ...]
print(f"Found {len(old_sessions)} sessions to delete")
for session in old_sessions:
    db.delete("sessions", session["id"])
# Performance: ~1ms per delete (consider batch deletes for large datasets)

# Delete with multiple conditions
inactive_users = db.query("SELECT id FROM users WHERE active = ? AND last_login < ?", [False, "2023-01-01"])
for user in inactive_users:
    db.delete("users", user["id"])
    print(f"Deleted inactive user: {user['id']}")

# Common patterns:
# Soft delete (recommended for audit trails):
db.update("users", {"id": user_id, "deleted_at": "datetime('now')", "active": False})

# Common errors:
# sqlite3.IntegrityError: FOREIGN KEY constraint failed - Delete related records first
```

## Batch Operations

CinchDB supports efficient batch operations for inserting, updating, and deleting multiple records:

```python
# Batch insert - more efficient than individual inserts
users = db.insert("users",
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Carol", "email": "carol@example.com"}
)
# Expected output: [{"id": "123", "name": "Alice", ...}, {"id": "124", "name": "Bob", ...}, ...]
# Performance: ~0.3ms per record (3x faster than individual inserts)

# Or with a list using star expansion
user_data = [
    {"name": "Dave", "email": "dave@example.com"},
    {"name": "Eve", "email": "eve@example.com"}
]
users = db.insert("users", *user_data)

# Batch update - each dict must contain 'id' field
updates = db.update("users",
    {"id": "123", "status": "active"},
    {"id": "124", "status": "inactive"},
    {"id": "125", "name": "Updated Name"}
)
# Expected output: [{"id": "123", "status": "active", ...}, {"id": "124", "status": "inactive", ...}, ...]
# Performance: ~0.5ms per update

# Batch delete - accepts multiple IDs
deleted_count = db.delete("users", "123", "124", "125")
# Expected output: 3 (number of records deleted)
# Performance: ~0.5ms per delete

# With a list of IDs
user_ids = ["abc", "def", "ghi"]
deleted_count = db.delete("users", *user_ids)
```

### Conditional Batch Operations

For bulk updates/deletes based on criteria, use `update_where()` and `delete_where()`:

```python
# Update all records matching criteria
count = db.update_where("users", {"status": "inactive"}, last_login__lt="2024-01-01")
# Expected output: 15 (number of records updated)
# Updates all users with last_login before 2024-01-01

# Delete all records matching criteria
count = db.delete_where("users", status="deleted", created_at__lt="2023-01-01")
# Expected output: 8 (number of records deleted)

# Supported operators: __gt, __lt, __gte, __lte, __in, __like, __not
# Combine with operator="OR" for OR conditions
count = db.update_where("products", {"active": False}, operator="OR", stock__lt=1, discontinued=True)
```

## Advanced Queries

```python
# Joins
user_orders = db.query("""
    SELECT u.name, o.order_number, o.total FROM users u
    INNER JOIN orders o ON u.id = o.user_id WHERE u.active = ?
""", [True])
# Expected output: [{"name": "Alice", "order_number": "ORD-001", "total": 99.99}, ...]
# Performance: 5-20ms for typical joins with indexes on join columns
# Tip: Always index foreign key columns for better join performance

# Aggregations
total_users = db.query("SELECT COUNT(*) as total FROM users")[0]["total"]
# Expected output: 42 (integer count)
# Performance: <1ms for COUNT(*) on indexed tables

order_stats = db.query("""
    SELECT COUNT(*) as orders, SUM(total) as revenue, AVG(total) as avg_order
    FROM orders WHERE status = ?
""", ["completed"])[0]
# Expected output: {"orders": 156, "revenue": 15234.50, "avg_order": 97.66}
# Performance: 1-5ms for aggregations on indexed columns

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

## Column Masking (Security)

Protect sensitive data by masking specific columns in query results:

```python
# Mask sensitive columns (PII, credentials, etc.)
users = db.query(
    "SELECT * FROM users",
    mask_columns=["email", "phone", "ssn"]
)
# Expected output: [{"id": "123", "name": "Alice", "email": "***MASKED***", "phone": "***MASKED***", ...}]
# Use case: Logging, debugging, or displaying data without exposing PII

# Mask password hashes in audit logs
admins = db.query(
    "SELECT id, username, password_hash, role FROM admin_users",
    mask_columns=["password_hash"]
)
# Expected: [{"id": "1", "username": "admin", "password_hash": "***MASKED***", "role": "superuser"}]

# Multiple masked columns
payment_info = db.query(
    "SELECT user_id, card_number, cvv, billing_address FROM payments",
    mask_columns=["card_number", "cvv"]
)
# Use for: Compliance with data protection regulations (GDPR, PCI-DSS)

# Note: Masking is applied to results after query execution
# The actual database data remains unchanged
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
    db.update("stats", {"id": stats["id"], "user_count": stats["user_count"] + 1})
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
# Expected output: 20 products starting from position 21
# Performance: <5ms with proper indexes on ORDER BY columns
# Warning: Large OFFSET values (>10000) can be slow - consider cursor-based pagination

# Check query plan
plan = db.query("EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = ?", ["test@example.com"])
# Expected output: [{"detail": "SEARCH users USING INDEX idx_users_email (email=?)"}]
# Use this to verify indexes are being used

# ✅ Good - specific columns
users = db.query("SELECT id, name, email FROM users")
# Performance: 30-50% faster than SELECT * for tables with many columns
# Network bandwidth: Reduced by only fetching needed data

# ❌ Bad - all columns
users = db.query("SELECT * FROM users")
# Performance impact: Fetches unnecessary data, slower serialization
# Maintenance issue: Breaking changes when columns are added/removed
```

## Error Handling

```python
# Handle query errors
try:
    result = db.query("SELECT * FROM users WHERE id = ?", [user_id])
except sqlite3.OperationalError as e:
    # Common: Table doesn't exist, syntax error
    print(f"Query failed: {e}")
    # Error examples:
    # - "no such table: users" - Table not created
    # - "no such column: username" - Column doesn't exist
    # - "near 'SELCT': syntax error" - SQL syntax error
    raise
except Exception as e:
    # Other errors: connection issues, locks, etc.
    print(f"Unexpected error: {e}")
    raise

# Handle empty results
user = db.query("SELECT * FROM users WHERE id = ?", [user_id])
if not user:
    # No exception raised for empty results - handle gracefully
    raise ValueError(f"User not found with ID: {user_id}")
    # Alternative: Return default
    # return {"id": user_id, "name": "Unknown", "active": False}

# Troubleshooting tips:
# 1. Check table exists: db.list_tables()
# 2. Verify column names: db.get_table("users").columns
# 3. Test with simpler query: db.query("SELECT 1")
# 4. Check database connection: db.query("SELECT name FROM sqlite_master WHERE type='table'")
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
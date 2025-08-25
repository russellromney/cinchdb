# Query Command

Execute SQL queries against your database.

## Usage

```bash
cinch query "SQL_STATEMENT" [OPTIONS]
```

### Arguments
- `SQL_STATEMENT` - SQL query to execute

### Options
- `--tenant TENANT` - Target tenant (default: main)
- `--format FORMAT` - Output format: `table` (default), `json`, `csv`
- `--limit N` - Limit result rows
- `--local` - Force local connection
- `--remote ALIAS` - Use specific remote

## SELECT Queries

### Basic Queries
```bash
# Select all records
cinch query "SELECT * FROM users"

# With conditions
cinch query "SELECT * FROM users WHERE active = true"

# With joins
cinch query "
  SELECT u.name, COUNT(o.id) as order_count
  FROM users u
  LEFT JOIN orders o ON u.id = o.user_id
  GROUP BY u.id
"
```

### Output Formats

#### Table Format (default)
```bash
cinch query "SELECT name, email FROM users"
```
Output:
```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ name    ┃ email              ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Alice   │ alice@example.com  │
│ Bob     │ bob@example.com    │
└─────────┴────────────────────┘
```

#### JSON Format
```bash
cinch query "SELECT name, email FROM users" --format json
```
Output:
```json
[
  {"name": "Alice", "email": "alice@example.com"},
  {"name": "Bob", "email": "bob@example.com"}
]
```

#### CSV Format
```bash
cinch query "SELECT name, email FROM users" --format csv
```
Output:
```csv
name,email
Alice,alice@example.com
Bob,bob@example.com
```

### Limiting Results
```bash
# Limit to 10 rows
cinch query "SELECT * FROM orders" --limit 10

# Or use SQL LIMIT
cinch query "SELECT * FROM orders LIMIT 10"
```

## INSERT Queries

```bash
# Single insert
cinch query "INSERT INTO users (name, email) VALUES ('Charlie', 'charlie@example.com')"

# Multiple inserts
cinch query "
  INSERT INTO users (name, email) VALUES 
  ('Dave', 'dave@example.com'),
  ('Eve', 'eve@example.com')
"
```

## UPDATE Queries

```bash
# Update single record
cinch query "UPDATE users SET active = true WHERE email = 'alice@example.com'"

# Update multiple records
cinch query "UPDATE products SET price = price * 1.1 WHERE category = 'electronics'"

# Update with conditions
cinch query "
  UPDATE orders 
  SET status = 'shipped', shipped_at = datetime('now')
  WHERE status = 'pending' AND created_at < datetime('now', '-2 days')
"
```

## DELETE Queries

```bash
# Delete specific records
cinch query "DELETE FROM users WHERE active = false"

# Delete with conditions
cinch query "DELETE FROM sessions WHERE created_at < datetime('now', '-7 days')"
```

## Working with Parameters

For safety, use parameter binding in your application code:

```python
# In Python SDK
db.query("SELECT * FROM users WHERE email = ?", ["alice@example.com"])
```

From CLI, escape quotes properly:
```bash
cinch query "SELECT * FROM users WHERE name = 'O''Brien'"
```

## Multi-Tenant Queries

```bash
# Query specific tenant
cinch query "SELECT COUNT(*) FROM users" --tenant customer_a

# Insert into specific tenant
cinch query "INSERT INTO products (name, price) VALUES ('Widget', 9.99)" --tenant customer_b
```

## Common Query Patterns

### Aggregations
```bash
# Count records
cinch query "SELECT COUNT(*) as total FROM users"

# Group and count
cinch query "
  SELECT category, COUNT(*) as count, AVG(price) as avg_price
  FROM products
  GROUP BY category
"

# Sum values
cinch query "SELECT SUM(total) as revenue FROM orders WHERE status = 'completed'"
```

### Date Queries
```bash
# Recent records
cinch query "SELECT * FROM users WHERE created_at > datetime('now', '-7 days')"

# Date grouping
cinch query "
  SELECT DATE(created_at) as date, COUNT(*) as signups
  FROM users
  GROUP BY DATE(created_at)
  ORDER BY date DESC
"
```

### Searching
```bash
# Text search
cinch query "SELECT * FROM products WHERE name LIKE '%phone%'"

# Case-insensitive search
cinch query "SELECT * FROM users WHERE LOWER(email) = LOWER('Alice@Example.com')"
```

### Pagination
```bash
# Page 1 (first 20)
cinch query "SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 0"

# Page 2 (next 20)
cinch query "SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 20"
```

## Working with Views

```bash
# Query views like tables
cinch query "SELECT * FROM active_users"

# Join views with tables
cinch query "
  SELECT v.*, u.last_login
  FROM active_users v
  JOIN users u ON v.id = u.id
"
```

## Performance Tips

1. **Limit Results** - Always use LIMIT for large tables
2. **Select Specific Columns** - Avoid `SELECT *` in production
3. **Use Views** - Pre-define complex queries as views

## Remote Queries

```bash
# Query remote database
cinch query "SELECT * FROM users" --remote production

# Force local query
cinch query "SELECT * FROM users" --local
```

## Error Handling

Common errors:
- `no such table` - Table doesn't exist in current branch
- `no such column` - Column name is wrong or doesn't exist
- `UNIQUE constraint failed` - Trying to insert duplicate ID
- `syntax error` - Check SQL syntax

## SQLite Functions

CinchDB supports all SQLite functions:

```bash
# String functions
cinch query "SELECT UPPER(name), LENGTH(email) FROM users"

# Date functions  
cinch query "SELECT datetime('now'), date('now', '-1 day')"

# Math functions
cinch query "SELECT AVG(price), MAX(price), MIN(price) FROM products"
```

## Next Steps

- [Table Commands](table.md) - Create tables to query
- [View Commands](view.md) - Save complex queries
- [Python SDK Queries](../python-sdk/queries.md) - Query from code
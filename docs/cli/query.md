# Query Command

Run SQL queries against your database.

```bash
cinch query "SELECT * FROM users"
```

## Options

- `--tenant TENANT` - Target specific tenant (default: main)
- `--format FORMAT` - Output as `table`, `json`, or `csv` 
- `--limit N` - Limit result rows

## Examples

### Basic Queries
```bash
# Select data
cinch query "SELECT * FROM users WHERE active = true"

# Note: query command is for SELECT statements only
# For INSERT, UPDATE, DELETE operations, use dedicated commands:
# cinch data bulk-insert users --data '[{"name": "John", "email": "john@company.com"}]'
# cinch data update users --set "active=false" --where "id=user-123"
# cinch data delete users --where "id=user-123"
```

### With Parameters
Always use parameterized queries in your application code:

```python
# In Python SDK (secure)
db.query("SELECT * FROM users WHERE email = ?", ["john@company.com"])
```

From CLI, escape quotes:
```bash
cinch query "SELECT * FROM users WHERE name = 'O''Brien'"
```

### Output Formats
```bash
# Table (default) - pretty formatted
cinch query "SELECT name, email FROM users"

# JSON - for scripts
cinch query "SELECT * FROM users" --format json

# CSV - for exports  
cinch query "SELECT * FROM users" --format csv
```

### Multi-Tenant
```bash
# Query specific tenant
cinch query "SELECT * FROM users" --tenant customer_a

# Insert for specific tenant
cinch data bulk-insert products --tenant customer_b --data '[{"name": "Widget"}]'
```

### Advanced Queries
```bash
# Aggregations
cinch query "SELECT category, COUNT(*), AVG(price) FROM products GROUP BY category"

# Joins
cinch query "SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id"

# Pagination
cinch query "SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 40"
```

## Tips

- Use `--limit` for large tables to avoid overwhelming output
- Use JSON format when piping to other tools: `cinch query "..." --format json | jq`
- For safety, test queries on development branches first
- SQLite supports [all standard functions](https://sqlite.org/lang_corefunc.html)

## Common Errors

- `no such table` - Table doesn't exist in current branch
- `no such column` - Wrong column name
- `UNIQUE constraint failed` - Trying to insert duplicate values
- `syntax error` - Check your SQL syntax

## Next Steps

- [Table Commands](table.md) - Create tables to query
- [Python SDK Queries](../python-sdk/queries.md) - Query from code
# Index Commands

Manage database indexes for improved query performance.

**Important:** Indexes are created at the branch level and automatically apply to all tenants within that branch. This ensures consistent query performance across all tenants.

## Commands

### Create Index

Create an index on one or more columns of a table.

```bash
# Simple index on single column
cinch index create users email

# Compound index on multiple columns
cinch index create orders user_id created_at

# Named index
cinch index create products sku --name idx_product_sku

# Unique index
cinch index create users username --unique

# Compound unique index
cinch index create subscriptions user_id plan_id --unique --name uniq_user_plan
```

**Options:**
- `--name, -n`: Custom index name (auto-generated if not provided)
- `--unique, -u`: Create a unique index
- `--database, -d`: Target database (uses active if not specified)
- `--branch, -b`: Target branch (uses active if not specified)

### Drop Index

Remove an index from the database.

```bash
# Drop an index
cinch index drop idx_users_email

# Drop with specific database/branch
cinch index drop idx_products_sku --database mydb --branch main
```

**Options:**
- `--database, -d`: Target database (uses active if not specified)
- `--branch, -b`: Target branch (uses active if not specified)

### List Indexes

List all indexes or indexes for a specific table.

```bash
# List all indexes
cinch index list

# List indexes for a specific table
cinch index list users

# List with specific database/branch
cinch index list --database mydb --branch feature
```

**Options:**
- `--database, -d`: Target database (uses active if not specified)
- `--branch, -b`: Target branch (uses active if not specified)

### Index Info

Get detailed information about a specific index.

```bash
# Get index details
cinch index info idx_users_email

# With specific database/branch
cinch index info idx_orders_status --database mydb
```

**Options:**
- `--database, -d`: Target database (uses active if not specified)
- `--branch, -b`: Target branch (uses active if not specified)

## Index Naming Convention

When index names are auto-generated, they follow these patterns:

- **Regular index**: `idx_{table}_{column1}_{column2}...`
  - Example: `idx_users_email`
  - Example: `idx_orders_user_id_status`

- **Unique index**: `uniq_{table}_{column1}_{column2}...`
  - Example: `uniq_users_username`
  - Example: `uniq_subscriptions_user_id_plan_id`

## Best Practices

### When to Create Indexes

1. **Frequently queried columns** - Columns that appear often in WHERE clauses
2. **Join columns** - Columns used in JOIN operations
3. **Sorting columns** - Columns used in ORDER BY clauses
4. **Unique constraints** - Columns that must have unique values

### Index Strategy

```bash
# Index for frequent lookups
cinch index create users email
cinch query "SELECT * FROM users WHERE email = 'user@example.com'"

# Compound index for multi-column queries
cinch index create orders user_id status
cinch query "SELECT * FROM orders WHERE user_id = '123' AND status = 'pending'"

# Unique constraint
cinch index create products sku --unique
```

### Performance Considerations

1. **Index Overhead** - Indexes speed up reads but slow down writes
2. **Storage Space** - Each index requires additional disk space
3. **Selectivity** - Indexes on highly selective columns are most effective
4. **Compound Index Order** - Most selective column should come first

## Examples

### E-commerce Application

```bash
# Products table indexes
cinch index create products sku --unique
cinch index create products category price --name idx_category_price
cinch index create products brand

# Orders table indexes
cinch index create orders user_id
cinch index create orders status created_at --name idx_status_date
cinch index create orders order_number --unique

# Order items table indexes
cinch index create order_items order_id
cinch index create order_items product_id
```

### User Management System

```bash
# Users table indexes
cinch index create users email --unique
cinch index create users username --unique
cinch index create users created_at

# Sessions table indexes
cinch index create sessions user_id
cinch index create sessions token --unique
cinch index create sessions expires_at

# Roles and permissions
cinch index create user_roles user_id role_id --unique
```

## Index Analysis

Check which indexes are being used by your queries:

```bash
# Check query plan
cinch query "EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'test@example.com'"

# List all indexes for analysis
cinch index list

# Get detailed index information
cinch index info idx_users_email
```

## Python SDK Integration

The Python SDK provides an enhanced API for creating tables with indexes:

```python
from cinchdb.models import Column, Index

# Create table with indexes in one operation
db.tables.create_table("users",
    columns=[
        Column(name="name", type="TEXT", nullable=False),
        Column(name="email", type="TEXT", nullable=False)
    ],
    indexes=[
        Index(columns=["email"], unique=True),    # Auto-named: uniq_users_email
        Index(columns=["name"]),                  # Auto-named: idx_users_name
        Index(columns=["name", "email"])          # Auto-named: idx_users_name_email
    ]
)

# Backward compatibility - old approach still works
db.create_index("users", ["created_at"])
db.create_index("products", ["category", "price"], unique=True)
```

**Benefits:**
- **Atomic Operations**: Table and indexes created together
- **Type Safety**: Index model validates parameters
- **Consistency**: Same naming conventions as CLI
- **Performance**: No separate transactions needed

## Integration with Branches

Indexes are branch-specific and included in branch merges:

```bash
# Create indexes on feature branch
cinch branch create add-indexes
cinch branch switch add-indexes

cinch index create users last_login
cinch index create orders shipped_date

# Test queries with new indexes
cinch query "SELECT * FROM users WHERE last_login > date('now', '-7 days')"

# Merge indexes to main
cinch branch merge-into-main add-indexes
```

## Troubleshooting

### Index Not Used

If queries aren't using your indexes:
1. Check the query plan with `EXPLAIN QUERY PLAN`
2. Ensure the indexed columns match the query conditions
3. Verify index exists with `cinch index list`

### Duplicate Index Error

```bash
# Check existing indexes
cinch index list users

# Drop old index if needed
cinch index drop old_index_name

# Create new index
cinch index create users column_name
```

### Performance Issues

```bash
# Analyze table statistics
cinch query "ANALYZE users"

# Check index usage
cinch query "EXPLAIN QUERY PLAN SELECT ..."

# Consider compound indexes for multi-column queries
cinch index create table col1 col2 col3
```
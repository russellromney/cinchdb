# View Commands

Manage database views (saved queries).

## list

List all views in the current branch.

```bash
cinch view list
```

### Example Output
```
Views in main/main:
• active_users
• recent_orders
• product_inventory
• customer_summary
```

## create

Create a new view with a SQL query.

```bash
cinch view create VIEW_NAME "SQL_QUERY"
```

### Arguments
- `VIEW_NAME` - Name for the view
- `SQL_QUERY` - SQL SELECT statement

### Examples
```bash
# Simple view
cinch view create active_users "SELECT * FROM users WHERE active = true"

# View with joins
cinch view create user_orders "
  SELECT u.name, COUNT(o.id) as order_count, SUM(o.total) as total_spent
  FROM users u
  LEFT JOIN orders o ON u.id = o.user_id
  GROUP BY u.id
"

# View with conditions
cinch view create recent_products "
  SELECT * FROM products 
  WHERE created_at > datetime('now', '-30 days')
  ORDER BY created_at DESC
"
```

### Notes
- Views are read-only
- Can reference tables and other views
- Updated automatically when underlying data changes

## delete

Delete a view.

```bash
cinch view delete VIEW_NAME
```

### Arguments
- `VIEW_NAME` - View to delete

### Options
- `--force` - Skip confirmation

### Example
```bash
# With confirmation
cinch view delete old_view

# Without confirmation
cinch view delete old_view --force
```

## info

Show view definition and details.

```bash
cinch view info VIEW_NAME
```

### Arguments
- `VIEW_NAME` - View to inspect

### Example Output
```
View: active_users
Created: 2024-01-15 10:30:00

SQL Definition:
SELECT * FROM users WHERE active = true

Columns:
• id (TEXT)
• name (TEXT)
• email (TEXT)
• active (BOOLEAN)
• created_at (TEXT)
• updated_at (TEXT)
```

## rename

Rename a view.

```bash
cinch view rename OLD_NAME NEW_NAME
```

### Arguments
- `OLD_NAME` - Current view name
- `NEW_NAME` - New view name

### Example
```bash
cinch view rename active_users current_users
```

## Common View Patterns

### User Analytics
```bash
# Active users in last 30 days
cinch view create monthly_active_users "
  SELECT COUNT(DISTINCT id) as mau
  FROM users
  WHERE last_login > datetime('now', '-30 days')
"

# User engagement
cinch view create user_engagement "
  SELECT 
    u.id,
    u.name,
    COUNT(DISTINCT DATE(o.created_at)) as active_days,
    COUNT(o.id) as total_orders
  FROM users u
  LEFT JOIN orders o ON u.id = o.user_id
  WHERE o.created_at > datetime('now', '-90 days')
  GROUP BY u.id
"
```

### E-commerce Views
```bash
# Low stock products
cinch view create low_stock "
  SELECT * FROM products
  WHERE stock < 10 AND active = true
  ORDER BY stock ASC
"

# Best sellers
cinch view create best_sellers "
  SELECT 
    p.name,
    p.price,
    COUNT(oi.id) as times_ordered,
    SUM(oi.quantity) as total_quantity
  FROM products p
  JOIN order_items oi ON p.id = oi.product_id
  GROUP BY p.id
  ORDER BY times_ordered DESC
  LIMIT 20
"

# Revenue by category
cinch view create category_revenue "
  SELECT 
    p.category,
    COUNT(DISTINCT o.id) as order_count,
    SUM(o.total) as revenue
  FROM orders o
  JOIN order_items oi ON o.id = oi.order_id
  JOIN products p ON oi.product_id = p.id
  WHERE o.status = 'completed'
  GROUP BY p.category
"
```

### Reporting Views
```bash
# Daily summary
cinch view create daily_summary "
  SELECT 
    DATE(created_at) as date,
    COUNT(*) as new_users,
    (SELECT COUNT(*) FROM orders WHERE DATE(created_at) = DATE(u.created_at)) as orders,
    (SELECT SUM(total) FROM orders WHERE DATE(created_at) = DATE(u.created_at)) as revenue
  FROM users u
  GROUP BY DATE(created_at)
  ORDER BY date DESC
"

# Customer lifetime value
cinch view create customer_ltv "
  SELECT 
    u.id,
    u.name,
    u.email,
    MIN(o.created_at) as first_order,
    MAX(o.created_at) as last_order,
    COUNT(o.id) as total_orders,
    SUM(o.total) as lifetime_value
  FROM users u
  JOIN orders o ON u.id = o.user_id
  GROUP BY u.id
  HAVING COUNT(o.id) > 0
"
```

## Using Views

Query views like regular tables:

```bash
# Select from view
cinch query "SELECT * FROM active_users"

# Join with views
cinch query "
  SELECT u.*, ltv.lifetime_value
  FROM users u
  JOIN customer_ltv ltv ON u.id = ltv.id
  WHERE ltv.lifetime_value > 1000
"
```

## Best Practices

1. **Naming Conventions**
   - Use descriptive names
   - Include time ranges: `daily_`, `monthly_`
   - Indicate aggregations: `_summary`, `_totals`

2. **Performance**
   - Views don't store data (computed on query)
   - Consider indexes on underlying tables
   - Avoid complex nested views

3. **Maintenance**
   - Document complex view logic
   - Update views when schema changes
   - Test views after table modifications

## View Limitations

- Views are read-only (no INSERT/UPDATE/DELETE)
- Cannot create indexes on views
- Cannot use parameters in view definitions
- Views are recomputed on each query

## Remote Operations

```bash
# Create view on remote
cinch view create active_users "SELECT * FROM users WHERE active = true" --remote production

# List remote views
cinch view list --remote production
```

## Next Steps

- [Query Command](query.md) - Query views and tables
- [Table Commands](table.md) - Manage underlying tables
- [Branching Concepts](../concepts/branching.md) - Views in branches
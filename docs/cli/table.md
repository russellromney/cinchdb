# Table Commands

Manage database tables and their structure.

## list

List all tables in the current branch.

```bash
cinch table list
```

### Options
- `--format FORMAT` - Output format: `table` (default), `json`

### Example Output
```
Tables in main/main:
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Name      ┃ Columns ┃ Created            ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ users     │ 3       │ 2024-01-15 10:30:00│
│ products  │ 5       │ 2024-01-15 11:00:00│
│ orders    │ 4       │ 2024-01-15 11:30:00│
└───────────┴─────────┴────────────────────┘
```

## create

Create a new table with columns and optional foreign key constraints.

```bash
cinch table create TABLE_NAME COLUMN:TYPE[:nullable][:fk=table[.column][:action]]...
```

### Arguments
- `TABLE_NAME` - Name of the table
- `COLUMN:TYPE` - Column definitions with optional modifiers

### Column Format
```
name:type[:nullable][:fk=table[.column][:action]]
```

### Column Types
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `REAL` - Decimal numbers
- `BLOB` - Binary data
- `NUMERIC` - Numeric values

### Foreign Key Actions
- `CASCADE` - Delete/update child rows when parent is deleted/updated
- `SET NULL` - Set foreign key to NULL when parent is deleted/updated
- `RESTRICT` - Prevent deletion/update of parent (default)
- `NO ACTION` - Similar to RESTRICT

### Examples
```bash
# Simple table
cinch table create users name:TEXT email:TEXT
```
```
✓ Created table 'users' with 5 columns (id, name, email, created_at, updated_at)
```

```bash
# With nullable columns
cinch table create posts title:TEXT content:TEXT:nullable author:TEXT:nullable
```
```
✓ Created table 'posts' with 6 columns (id, title, content, author, created_at, updated_at)
```

```bash
# With foreign key (references id column by default)
cinch table create posts title:TEXT content:TEXT author_id:TEXT:fk=users
```
```
✓ Created table 'posts' with foreign key constraint: author_id → users(id)
```

```bash
# With foreign key to specific column
cinch table create posts title:TEXT author_email:TEXT:fk=users.email

# With CASCADE delete
cinch table create comments content:TEXT post_id:TEXT:fk=posts:cascade

# Full syntax with column and action
cinch table create order_items \
  product_id:TEXT:fk=products.id:cascade \
  order_id:TEXT:fk=orders.id:cascade \
  quantity:INTEGER

# Multiple foreign keys
cinch table create reviews \
  content:TEXT \
  rating:INTEGER \
  user_id:TEXT:fk=users \
  product_id:TEXT:fk=products
```

### Automatic Columns
Every table includes:
- `id` - UUID primary key
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## delete

Delete a table and all its data.

```bash
cinch table delete TABLE_NAME
```

### Arguments
- `TABLE_NAME` - Table to delete

### Options
- `--force` - Skip confirmation

### Example
```bash
# With confirmation
cinch table delete old_table

# Without confirmation
cinch table delete old_table --force
```

## info

Show detailed information about a table.

```bash
cinch table info TABLE_NAME
```

### Arguments
- `TABLE_NAME` - Table to inspect

### Example Output
```
Table: users
Created: 2024-01-15 10:30:00

Columns:
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ Name        ┃ Type    ┃ Nullable ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ id          │ TEXT    │ No       │
│ name        │ TEXT    │ Yes      │
│ email       │ TEXT    │ Yes      │
│ created_at  │ TEXT    │ No       │
│ updated_at  │ TEXT    │ No       │
└─────────────┴─────────┴──────────┘

Row count: 42
```

## copy

Create a copy of an existing table.

```bash
cinch table copy SOURCE_TABLE NEW_TABLE
```

### Arguments
- `SOURCE_TABLE` - Table to copy from
- `NEW_TABLE` - Name for the new table

### Options
- `--data` - Also copy data (schema only by default)

### Examples
```bash
# Copy schema only
cinch table copy users users_backup

# Copy with data
cinch table copy users users_backup --data
```

## Column Management

For column operations, see [Column Commands](column.md):
- Add columns: `cinch column add`
- Remove columns: `cinch column delete`
- Rename columns: `cinch column rename`

## Common Patterns

### User Management
```bash
cinch table create users \
  username:TEXT \
  email:TEXT \
  password_hash:TEXT \
  active:BOOLEAN \
  role:TEXT
```

### E-commerce
```bash
# Categories table
cinch table create categories \
  name:TEXT \
  description:TEXT:nullable

# Products table with category reference
cinch table create products \
  name:TEXT \
  description:TEXT:nullable \
  price:REAL \
  stock:INTEGER \
  category_id:TEXT:fk=categories

# Orders table with user reference
cinch table create orders \
  user_id:TEXT:fk=users \
  total:REAL \
  status:TEXT \
  notes:TEXT:nullable

# Order items with cascading deletes
cinch table create order_items \
  order_id:TEXT:fk=orders:cascade \
  product_id:TEXT:fk=products \
  quantity:INTEGER \
  price:REAL
```

### Content Management
```bash
# Posts table with author reference
cinch table create posts \
  title:TEXT \
  slug:TEXT \
  content:TEXT \
  published:INTEGER \
  author_id:TEXT:fk=users

# Comments table with post reference (cascade delete)
cinch table create comments \
  post_id:TEXT:fk=posts:cascade \
  user_id:TEXT:fk=users \
  content:TEXT \
  approved:INTEGER

# Tags table
cinch table create tags \
  name:TEXT \
  slug:TEXT

# Post-tag relationship (many-to-many)
cinch table create post_tags \
  post_id:TEXT:fk=posts:cascade \
  tag_id:TEXT:fk=tags:cascade
```

## Best Practices

1. **Naming Conventions**
   - Use lowercase with underscores: `user_profiles`
   - Use plural names: `users` not `user`
   - Be descriptive: `order_items` not `items`

2. **Column Types**
   - Use TEXT for IDs (stores UUIDs)
   - Use REAL for money/prices
   - Use INTEGER for boolean flags (0/1)

3. **Nullable Columns**
   - Make columns nullable with `:nullable` modifier
   - Required data should not be nullable
   - Foreign keys can be nullable for optional relationships

4. **Foreign Keys**
   - Always create parent tables before child tables
   - Use CASCADE for dependent data that should be deleted with parent
   - Use SET NULL for optional relationships
   - Default to RESTRICT to prevent accidental data loss
   - Name foreign key columns clearly: `user_id`, `product_id`

## Troubleshooting

### "Table already exists"
**Problem**: `cinch table create users` fails with "Table already exists"
**Solution**: Use `cinch table list` to check, or `cinch table info users` for details

### "Foreign key constraint failed"
**Problem**: Creating table with foreign key to non-existent table
**Solution**: Create parent table first: `cinch table create users name:TEXT`, then child table

### "Cannot create table: Invalid column syntax"
**Problem**: Wrong column format in table creation
**Solution**: Use format `name:TYPE[:nullable][:fk=table]`, e.g. `user_id:TEXT:fk=users`

## Protected Names

These column names are reserved:
- `id` - Automatic UUID primary key
- `created_at` - Automatic timestamp
- `updated_at` - Automatic timestamp

## Remote Operations

```bash
```

## Next Steps

- [Column Commands](column.md) - Manage table columns
- [Query Command](query.md) - Work with table data  
- [View Commands](view.md) - Create virtual tables
- [Schema Branching](../concepts/branching.md) - Safe table changes with branches
- [Multi-Tenancy](../concepts/multi-tenancy.md) - How tables work with tenants
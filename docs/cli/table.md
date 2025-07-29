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

Create a new table with columns.

```bash
cinch table create TABLE_NAME COLUMN:TYPE...
```

### Arguments
- `TABLE_NAME` - Name of the table
- `COLUMN:TYPE` - Column definitions (name:type pairs)

### Column Types
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `REAL` - Decimal numbers
- `BOOLEAN` - True/false values
- `BLOB` - Binary data

### Examples
```bash
# Simple table
cinch table create users name:TEXT email:TEXT

# With multiple types
cinch table create products name:TEXT price:REAL stock:INTEGER active:BOOLEAN

# With optional columns (nullable)
cinch table create posts title:TEXT content:TEXT published:BOOLEAN?
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
# Products table
cinch table create products \
  name:TEXT \
  description:TEXT? \
  price:REAL \
  stock:INTEGER \
  category:TEXT

# Orders table  
cinch table create orders \
  user_id:TEXT \
  total:REAL \
  status:TEXT \
  notes:TEXT?
```

### Content Management
```bash
# Posts table
cinch table create posts \
  title:TEXT \
  slug:TEXT \
  content:TEXT \
  published:BOOLEAN \
  author_id:TEXT

# Comments table
cinch table create comments \
  post_id:TEXT \
  author:TEXT \
  content:TEXT \
  approved:BOOLEAN
```

## Best Practices

1. **Naming Conventions**
   - Use lowercase with underscores: `user_profiles`
   - Use plural names: `users` not `user`
   - Be descriptive: `order_items` not `items`

2. **Column Types**
   - Use TEXT for IDs (stores UUIDs)
   - Use REAL for money/prices
   - Use BOOLEAN for flags

3. **Nullable Columns**
   - Make columns nullable with `?` suffix
   - Required data should not be nullable
   - Consider defaults for optional data

## Protected Names

These column names are reserved:
- `id` - Automatic UUID primary key
- `created_at` - Automatic timestamp
- `updated_at` - Automatic timestamp

## Remote Operations

```bash
# Create table on remote
cinch table create products name:TEXT price:REAL --remote production

# List remote tables
cinch table list --remote production
```

## Next Steps

- [Column Commands](column.md) - Manage table columns
- [Query Command](query.md) - Work with table data
- [View Commands](view.md) - Create virtual tables
# Column Commands

Manage columns within existing tables.

## list

List all columns in a table.

```bash
cinch column list TABLE_NAME
```

### Arguments
- `TABLE_NAME` - Table to list columns for

### Example Output
```
Columns in table 'users':
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┓
┃ Name        ┃ Type    ┃ Nullable ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━┩
│ id          │ TEXT    │ No       │
│ username    │ TEXT    │ Yes      │
│ email       │ TEXT    │ Yes      │
│ active      │ BOOLEAN │ Yes      │
│ created_at  │ TEXT    │ No       │
│ updated_at  │ TEXT    │ No       │
└─────────────┴─────────┴──────────┘
```

## add

Add a new column to an existing table.

```bash
cinch column add TABLE_NAME COLUMN:TYPE
```

### Arguments
- `TABLE_NAME` - Table to add column to
- `COLUMN:TYPE` - Column definition (name:type)

### Column Types
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `REAL` - Decimal numbers
- `BOOLEAN` - True/false values
- `BLOB` - Binary data

### Options
- Add `?` suffix for nullable columns

### Examples
```bash
# Add required column
cinch column add users phone:TEXT

# Add nullable column
cinch column add users avatar_url:TEXT?

# Add various types
cinch column add products weight:REAL
cinch column add products in_stock:BOOLEAN
cinch column add users age:INTEGER
```

### Notes
- New columns are added with NULL values for existing rows
- Make columns nullable if table has existing data
- Column names must be unique within the table

## delete

Remove a column from a table.

```bash
cinch column delete TABLE_NAME COLUMN_NAME
```

### Arguments
- `TABLE_NAME` - Table containing the column
- `COLUMN_NAME` - Column to delete

### Options
- `--force` - Skip confirmation

### Examples
```bash
# With confirmation
cinch column delete users old_field

# Without confirmation
cinch column delete users old_field --force
```

### Notes
- Cannot delete protected columns (id, created_at, updated_at)
- **Permanently deletes all data in the column**
- Cannot be undone

## rename

Rename a column.

```bash
cinch column rename TABLE_NAME OLD_NAME NEW_NAME
```

### Arguments
- `TABLE_NAME` - Table containing the column
- `OLD_NAME` - Current column name
- `NEW_NAME` - New column name

### Example
```bash
cinch column rename users username user_name
```

### Notes
- Preserves all data
- Updates any views that reference the column
- Cannot rename protected columns

## info

Show detailed information about a column.

```bash
cinch column info TABLE_NAME COLUMN_NAME
```

### Arguments
- `TABLE_NAME` - Table containing the column
- `COLUMN_NAME` - Column to inspect

### Example Output
```
Column: email
Table: users
Type: TEXT
Nullable: Yes
Default: NULL
Values: 1,234 non-null, 56 null
```

## Common Workflows

### Adding User Features
```bash
# Add profile fields
cinch column add users bio:TEXT?
cinch column add users website:TEXT?
cinch column add users location:TEXT?

# Add authentication fields
cinch column add users password_reset_token:TEXT?
cinch column add users last_login:TEXT?
cinch column add users failed_attempts:INTEGER
```

### E-commerce Enhancements
```bash
# Add product attributes
cinch column add products sku:TEXT
cinch column add products weight:REAL?
cinch column add products dimensions:TEXT?

# Add order tracking
cinch column add orders tracking_number:TEXT?
cinch column add orders shipped_at:TEXT?
cinch column add orders delivered_at:TEXT?
```

### Migration Examples
```bash
# Rename for clarity
cinch column rename users name full_name
cinch column rename products desc description

# Remove deprecated columns
cinch column delete users old_password_field
cinch column delete orders legacy_status
```

## Best Practices

1. **Nullable for Existing Tables**
   - Always use nullable (`?`) when adding to tables with data
   - Required columns need default values or migration

2. **Naming Conventions**
   - Use lowercase with underscores
   - Be descriptive: `email_verified` not `verified`
   - Include units: `weight_kg`, `price_usd`

3. **Type Selection**
   - Use TEXT for emails, URLs, names
   - Use INTEGER for counts, IDs
   - Use REAL for money, measurements
   - Use BOOLEAN for flags/states

4. **Safe Migrations**
   - Test column changes on feature branches
   - Backup before bulk column operations
   - Consider data migration needs

## Constraints

- Cannot modify column types after creation
- Cannot add NOT NULL columns to tables with data
- Cannot use reserved names (id, created_at, updated_at)

## Remote Operations

```bash
# Add column on remote
cinch column add users phone:TEXT --remote production

# List remote columns
cinch column list users --remote production
```

## Next Steps

- [Table Commands](table.md) - Create and manage tables
- [Query Command](query.md) - Work with column data
- [Migration Patterns](../tutorials/schema-branching.md) - Safe schema changes
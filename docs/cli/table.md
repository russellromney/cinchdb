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
│ users     │ 6       │ 2024-01-15 10:30:00│
│ products  │ 8       │ 2024-01-15 11:00:00│
│ orders    │ 7       │ 2024-01-15 11:30:00│
└───────────┴─────────┴────────────────────┘
```

**Note:** Column count includes all columns (user-defined + system columns: id, created_at, updated_at)

## create

Create a new table with columns and optional foreign key constraints.

```bash
cinch table create TABLE_NAME [COLUMN:TYPE[:not_null][:fk=table[.column][:action]]...]
```

### Arguments
- `TABLE_NAME` - Name of the table
- `COLUMN:TYPE` - Column definitions with optional modifiers (optional - can create empty table)

### Column Format
```
name:type[:not_null][:fk=table[.column][:action]]
```

**Note:** Columns are nullable by default. Use `:not_null` to make them required.

### Column Types
Primary types (case-insensitive):
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `REAL` - Decimal numbers
- `BLOB` - Binary data
- `NUMERIC` - Numeric values
- `BOOLEAN` - True/false values

Type aliases (all case-insensitive):
- `int` → `INTEGER`
- `bool` → `BOOLEAN`
- `str`, `string`, `varchar` → `TEXT`
- `float`, `double` → `REAL`

### Foreign Key Actions
- `CASCADE` - Delete/update child rows when parent is deleted/updated
- `SET NULL` - Set foreign key to NULL when parent is deleted/updated
- `RESTRICT` - Prevent deletion/update of parent (default)
- `NO ACTION` - Similar to RESTRICT

### Examples

#### Basic Table Creation
```bash
# Simple table (columns are nullable by default)
cinch table create users name:TEXT email:TEXT
```
**Expected output:**
```
[yellow]Creating table with system columns (id, created_at, updated_at)[/yellow]
[green]✅ Created table 'users' with 5 columns[/green]
```
**Performance:** ~5ms for table creation

#### Table with Required Fields
```bash
# With required columns (not_null)
cinch table create posts title:TEXT:not_null content:TEXT author:TEXT
```
**Expected output:**
```
[green]✅ Created table 'posts' with 6 columns[/green]
```
**Note:** title is required, content and author are nullable

#### Empty Table (System Columns Only)
```bash
# Empty table (only system columns)
cinch table create placeholder
```
**Expected output:**
```
[yellow]Creating table with only system columns (id, created_at, updated_at)[/yellow]
[green]✅ Created table 'placeholder' with 3 columns[/green]
```
**Use case:** Useful for placeholder tables or tables that will be populated programmatically

#### Using Case-Insensitive Types and Aliases
```bash
# All these are equivalent - types are case-insensitive
cinch table create users1 name:text email:TEXT age:integer
cinch table create users2 name:Text email:text age:Integer

# Using type aliases
cinch table create settings \
  enabled:bool \
  timeout:int \
  description:str \
  percentage:float

# Mix and match styles
cinch table create products \
  name:varchar \
  price:double \
  active:BOOLEAN \
  stock:INT
```
**Expected output:**
```
[green]✅ Created table with normalized types[/green]
```
**Note:** All variations produce identical table schemas

```bash
# With foreign key (references id column by default)
cinch table create posts title:TEXT content:TEXT author_id:TEXT:fk=users
```
**Expected output:**
```
[green]✅ Created table 'posts' with 6 columns[/green]
```
**Foreign key:** author_id → users(id) with RESTRICT on delete/update
**Performance:** ~7ms (includes foreign key validation)

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
- `id` - UUID primary key (unique, not nullable)
- `created_at` - Creation timestamp (not nullable)
- `updated_at` - Last update timestamp (nullable)

## delete

Delete a table and all its data.

```bash
cinch table delete TABLE_NAME
```

### Arguments
- `TABLE_NAME` - Table to delete

### Options
- `--force` - Skip confirmation

### Examples
```bash
# With confirmation
cinch table delete old_table
```
**Expected output:**
```
Are you sure you want to delete table 'old_table'? [y/N]: y
[green]✅ Deleted table 'old_table'[/green]
```

```bash
# Without confirmation
cinch table delete old_table --force
```
**Expected output:**
```
[green]✅ Deleted table 'old_table'[/green]
```
**Performance:** ~3ms for table deletion
**Warning:** This permanently deletes all data in the table

## info

Show detailed information about a table.

```bash
cinch table info TABLE_NAME
```

### Arguments
- `TABLE_NAME` - Table to inspect

### Example
```bash
cinch table info users
```
**Expected output:**
```
[bold]Table: users[/bold]
Database: main
Branch: main
Tenant: main

[bold]Columns:[/bold]
┏━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ Type    ┃ Nullable ┃ Unique ┃ Default ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━┩
│ id          │ TEXT    │ No       │ Yes    │ -       │
│ name        │ TEXT    │ Yes      │ No     │ -       │
│ email       │ TEXT    │ Yes      │ No     │ -       │
│ created_at  │ TEXT    │ No       │ No     │ -       │
│ updated_at  │ TEXT    │ Yes      │ No     │ -       │
└─────────────┴─────────┴──────────┴────────┴─────────┘
```
**Note:** id column shows as Unique=Yes because it's the PRIMARY KEY
**Performance:** ~2ms for metadata retrieval

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
```
**Expected output:**
```
[green]✅ Copied table 'users' to 'users_backup'[/green]
```
**Performance:** ~5ms (schema only)

```bash
# Copy with data
cinch table copy users users_backup --data
```
**Expected output:**
```
[green]✅ Copied table 'users' to 'users_backup'[/green]
```
**Performance:** Depends on data size (~10ms per 1000 rows)

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
   - Use BOOLEAN for true/false flags (returns Python bool values)

3. **Nullable Columns**
   - Columns are nullable by default - use `:nullable` to be explicit
   - Use `:not_null` modifier for required fields
   - Foreign keys can be nullable for optional relationships

4. **Foreign Keys**
   - Always create parent tables before child tables
   - Use CASCADE for dependent data that should be deleted with parent
   - Use SET NULL for optional relationships
   - Default to RESTRICT to prevent accidental data loss
   - Name foreign key columns clearly: `user_id`, `product_id`

## Troubleshooting

### Error: "Table already exists"
**Command**: `cinch table create users name:TEXT`
**Error message**:
```
[red]❌ Table 'users' already exists[/red]
```
**Cause**: A table with this name already exists in the current database/branch
**Solutions**:
1. Check existing tables: `cinch table list`
2. View table structure: `cinch table info users`
3. Use a different name: `cinch table create user_profiles name:TEXT`
4. Delete existing table first: `cinch table delete users --force`

### Error: "Foreign key reference to non-existent table"
**Command**: `cinch table create posts author_id:TEXT:fk=users`
**Error message**:
```
[red]❌ Foreign key reference to non-existent table: 'users'[/red]
```
**Cause**: Referenced table doesn't exist
**Solutions**:
1. Create parent table first:
   ```bash
   cinch table create users name:TEXT email:TEXT
   cinch table create posts title:TEXT author_id:TEXT:fk=users
   ```
2. Check table name spelling: `cinch table list`
3. Verify you're in the correct branch: `cinch branch current`

### Error: "Invalid column definition"
**Command**: `cinch table create users name:STRING`
**Error message**:
```
[red]❌ Invalid type: 'STRING'[/red]
[yellow]Valid types: TEXT, INTEGER, REAL, BLOB, NUMERIC[/yellow]
```
**Cause**: Incorrect column type or syntax
**Solutions**:
1. Use valid SQLite types: TEXT, INTEGER, REAL, BLOB, NUMERIC
2. Check column format: `name:TYPE[:not_null][:fk=table[.column][:action]]`
3. Examples of correct syntax:
   - `name:TEXT` - nullable text column
   - `age:INTEGER:not_null` - required integer
   - `user_id:TEXT:fk=users` - foreign key

### Error: "Column name is protected"
**Command**: `cinch table create posts id:TEXT title:TEXT`
**Error message**:
```
[red]❌ Column name 'id' is protected and cannot be used[/red]
```
**Cause**: Using reserved column names (id, created_at, updated_at)
**Solutions**:
1. Use different column name: `post_id:TEXT` instead of `id:TEXT`
2. System columns are added automatically - no need to define them
3. For custom IDs, use names like `external_id`, `legacy_id`, etc.

### Error: "Table does not exist"
**Command**: `cinch table info nonexistent`
**Error message**:
```
[red]❌ Table 'nonexistent' does not exist[/red]
```
**Cause**: Trying to access a table that doesn't exist
**Solutions**:
1. Check available tables: `cinch table list`
2. Verify spelling and case sensitivity
3. Ensure you're in the correct database: `cinch db current`
4. Check if table exists in another branch: `cinch branch list`

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
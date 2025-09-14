# Data Operations

Manipulate data using bulk operations with filtering and validation.

## Commands Overview

| Command | Description |
|---------|-------------|
| [`insert`](#insert) | Insert a single record with JSON data |
| [`bulk-insert`](#bulk-insert) | Insert multiple records with JSON data |
| [`delete`](#delete) | Delete records with filtering criteria |
| [`update`](#update) | Update records with filtering criteria | 
| [`bulk-update`](#bulk-update) | Update multiple records with JSON data |
| [`bulk-delete`](#bulk-delete) | Delete multiple records by ID |

## insert

Insert a single record into a table using JSON data.

```bash
cinch data insert <table> --data <json> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to insert into

**Options:**
- `--data, -d` - JSON object to insert (required)
- `--tenant, -t` - Tenant name (default: main)

**Examples:**
```bash
# Insert single record
cinch data insert users --data '{"name": "Alice", "email": "alice@example.com", "age": 30}'

# Insert with specific tenant
cinch data insert products --tenant customer_a --data '{"name": "Widget", "price": 99.99}'

# Insert from file
cinch data insert users --data "$(cat user.json)"
```

**Notes:**
- Automatically generates UUID for `id` field
- Sets `created_at` and `updated_at` timestamps
- Returns the ID of the inserted record
- Validates data types against table schema
- For multiple records, use `bulk-insert` command

## bulk-insert

Insert multiple records into a table using JSON data.

```bash
cinch data bulk-insert <table> --data <json> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to insert into

**Options:**
- `--data, -d` - JSON array of objects to insert (required)
- `--tenant, -t` - Tenant name (default: main)

**Examples:**
```bash
# Insert single record (use insert command instead)
cinch data insert users --data '{"name": "Alice", "email": "alice@example.com", "age": 30}'

# Insert multiple records
cinch data bulk-insert users --data '[
  {"name": "Bob", "email": "bob@example.com", "age": 25},
  {"name": "Charlie", "email": "charlie@example.com", "age": 35}
]'

# Insert with specific tenant
cinch data bulk-insert products --tenant customer_a --data '[
  {"name": "Widget", "price": 99.99},
  {"name": "Gadget", "price": 149.99}
]'

# Insert from file
cinch data bulk-insert users --data "$(cat users.json)"
```

**Notes:**
- Automatically generates UUID for `id` field
- Sets `created_at` and `updated_at` timestamps
- Returns the ID(s) of inserted records
- Validates data types against table schema
- All inserts are performed in a single transaction

## delete

Delete records from a table based on filter criteria.

```bash
cinch data delete <table> --where <conditions> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to delete from

**Options:**
- `--where, -w` - Filter conditions (required)
- `--tenant, -t` - Tenant name (default: main)
- `--confirm, -y` - Skip confirmation prompt

**Filter Examples:**
```bash
# Simple equality
cinch data delete users --where "status=inactive"

# Numeric comparison
cinch data delete logs --where "created_at__lt=2024-01-01"

# List membership
cinch data delete items --where "category__in=deprecated,old,unused"

# Multiple conditions
cinch data delete users --where "status=inactive,last_login__lt=2023-01-01"
```

## update

Update records in a table based on filter criteria.

```bash
cinch data update <table> --set <data> --where <conditions> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to update

**Options:**
- `--set, -s` - Data to update (required)
- `--where, -w` - Filter conditions (required)
- `--tenant, -t` - Tenant name (default: main)
- `--confirm, -y` - Skip confirmation prompt

**Examples:**
```bash
# Single field update
cinch data update users --set "status=active" --where "status=pending"

# Multiple fields
cinch data update items --set "price=99.99,category=sale" --where "price__gt=100"

# With tenant
cinch data update users --set "plan=premium" --where "status=active" --tenant customer_a
```

## bulk-update

Update multiple records using JSON data.

```bash
cinch data bulk-update <table> --data <json> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to update

**Options:**
- `--data, -d` - JSON array of update objects with 'id' field (required)
- `--tenant, -t` - Tenant name (default: main)
- `--confirm, -y` - Skip confirmation prompt

**Examples:**
```bash
# Update multiple users
cinch data bulk-update users --data '[
  {"id":"user-1","name":"Alice Updated","status":"premium"},
  {"id":"user-2","email":"bob.new@example.com"},
  {"id":"user-3","status":"inactive"}
]'

# From file
cinch data bulk-update products --data "$(cat updates.json)"
```

## bulk-delete

Delete multiple records by their IDs.

```bash
cinch data bulk-delete <table> --ids <ids> [OPTIONS]
```

**Arguments:**
- `<table>` - Name of table to delete from

**Options:**
- `--ids, -i` - Comma-separated IDs or JSON array (required)
- `--tenant, -t` - Tenant name (default: main)
- `--confirm, -y` - Skip confirmation prompt

**Examples:**
```bash
# Comma-separated IDs
cinch data bulk-delete users --ids "user-1,user-2,user-3"

# JSON array format
cinch data bulk-delete items --ids '["item-abc","item-def","item-ghi"]'
```

## Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `status=active` |
| `__gt` | Greater than | `age__gt=18` |
| `__lt` | Less than | `created_at__lt=2024-01-01` |
| `__gte` | Greater than or equal | `score__gte=80` |
| `__lte` | Less than or equal | `price__lte=100` |
| `__in` | In list | `category__in=A,B,C` |
| `__like` | SQL LIKE pattern | `name__like=%john%` |
| `__not` | Not equals | `status__not=deleted` |

## Data Types

Values are automatically converted to appropriate types:

- **Integers**: `42`, `0`, `-10`
- **Floats**: `3.14`, `99.99`, `-1.5`
- **Booleans**: `true`, `false`
- **Strings**: Everything else

## Safety Features

- **Confirmation prompts** for destructive operations
- **Filter validation** prevents accidental bulk operations
- **Transaction safety** ensures data consistency
- **Type conversion** handles data types automatically
# Change Tracking

How CinchDB tracks and manages schema changes across branches and tenants.

## Overview

CinchDB maintains a complete history of all schema modifications. This enables:
- Reproducible schema evolution
- Safe merging between branches  
- Consistent multi-tenant updates
- Audit trail of changes

## Change Types

### Tracked Operations

CinchDB tracks these schema modifications:

1. **Table Operations**
   - `CREATE_TABLE` - New table creation
   - `DROP_TABLE` - Table deletion
   - `RENAME_TABLE` - Table renaming

2. **Column Operations**
   - `ADD_COLUMN` - New column addition
   - `DROP_COLUMN` - Column removal
   - `RENAME_COLUMN` - Column renaming

3. **View Operations**
   - `CREATE_VIEW` - View creation
   - `DROP_VIEW` - View deletion
   - `UPDATE_VIEW` - View modification

4. **Index Operations**
   - `CREATE_INDEX` - Index creation
   - `DROP_INDEX` - Index removal

## Change Storage

### File Structure

Changes are stored in `changes.json` within each branch:

```
.cinchdb/databases/myapp/branches/feature/
├── metadata.json
├── changes.json    # All changes for this branch
└── tenants/
```

### Change Format

Each change is recorded with:

```json
{
  "id": "chg_1234567890",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "type": "CREATE_TABLE",
  "details": {
    "table": "users",
    "columns": [
      {
        "name": "id",
        "type": "TEXT",
        "nullable": false
      },
      {
        "name": "email",
        "type": "TEXT",
        "nullable": false
      },
      {
        "name": "created_at",
        "type": "TEXT",
        "nullable": false
      }
    ]
  },
  "applied_to": ["main", "customer_a", "customer_b"]
}
```

## Change Recording

### Automatic Tracking

All schema operations through CinchDB are automatically tracked:

```python
# This operation
db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="price", type="REAL")
])

# Generates this change record
{
  "id": "chg_1705316400123",
  "timestamp": "2024-01-15T10:40:00.123Z",
  "type": "CREATE_TABLE",
  "details": {
    "table": "products",
    "columns": [
      {"name": "id", "type": "TEXT", "nullable": false},
      {"name": "name", "type": "TEXT", "nullable": true},
      {"name": "price", "type": "REAL", "nullable": true},
      {"name": "created_at", "type": "TEXT", "nullable": false},
      {"name": "updated_at", "type": "TEXT", "nullable": false}
    ]
  }
}
```

### Change IDs

Each change has a unique identifier:
- Format: `chg_<timestamp><random>`
- Globally unique across branches
- Immutable once created
- Used for ordering and deduplication

## Change Application

### Order Matters

Changes must be applied in chronological order:

```python
# These changes must apply in sequence
changes = [
    {
        "type": "CREATE_TABLE",
        "details": {"table": "users", ...}
    },
    {
        "type": "ADD_COLUMN", 
        "details": {"table": "users", "column": "phone"}
    }
]

# Cannot add column before table exists!
```

## Viewing Changes

### CLI Commands

```bash
# View changes in current branch
cinch branch changes

# Output:
# Changes in branch 'feature.new-schema':
# 1. CREATE TABLE products (name TEXT, price REAL)
# 2. ADD COLUMN description TEXT TO products  
# 3. CREATE VIEW expensive_products AS SELECT * FROM products WHERE price > 100
```

### Programmatic Access

```python
def get_branch_changes(db, branch_name):
    """Get all changes for a branch."""
    if not db.is_local:
        return []
    
    changes_path = (
        db.project_dir / ".cinchdb" / "databases" / 
        db.database / "branches" / branch_name / "changes.json"
    )
    
    with open(changes_path) as f:
        return json.load(f)

# Analyze changes
changes = get_branch_changes(db, "feature.updates")
table_changes = [c for c in changes if "TABLE" in c["type"]]
column_changes = [c for c in changes if "COLUMN" in c["type"]]
```

## Merge Behavior

### Change Comparison

During merge, CinchDB compares change histories:

```python
def can_merge(source_branch, target_branch):
    source_changes = get_changes(source_branch)
    target_changes = get_changes(target_branch)
    
    # Target must have all source's parent changes
    source_parent_ids = get_parent_change_ids(source_branch)
    target_ids = {c["id"] for c in target_changes}
    
    return source_parent_ids.issubset(target_ids)
```

### Change Application

Merging applies new changes to target:

```python
def merge_changes(source_branch, target_branch):
    source_changes = get_changes(source_branch)
    target_changes = get_changes(target_branch)
    
    # Find new changes
    target_ids = {c["id"] for c in target_changes}
    new_changes = [c for c in source_changes if c["id"] not in target_ids]
    
    # Apply in order
    for change in sorted(new_changes, key=lambda c: c["timestamp"]):
        apply_change_to_branch(change, target_branch)
```

## Change Types in Detail

### CREATE_TABLE

Records full table definition:

```json
{
  "type": "CREATE_TABLE",
  "details": {
    "table": "orders",
    "columns": [
      {"name": "id", "type": "TEXT", "nullable": false},
      {"name": "user_id", "type": "TEXT", "nullable": true},
      {"name": "total", "type": "REAL", "nullable": true},
      {"name": "status", "type": "TEXT", "nullable": true}
    ],
    "indexes": [],
    "constraints": []
  }
}
```

### ADD_COLUMN

Tracks column additions:

```json
{
  "type": "ADD_COLUMN",
  "details": {
    "table": "users",
    "column": {
      "name": "phone",
      "type": "TEXT",
      "nullable": true,
      "default": null
    }
  }
}
```

### CREATE_VIEW

Stores view definition:

```json
{
  "type": "CREATE_VIEW",
  "details": {
    "view": "active_users",
    "sql": "SELECT * FROM users WHERE active = true",
    "columns": ["id", "name", "email", "active"]
  }
}
```

## Best Practices

### 1. Atomic Changes

Make one logical change at a time:

```python
# Good - single purpose
db.create_table("users", columns)

# Bad - multiple unrelated changes
db.create_table("users", columns)
db.create_table("products", columns)  # Separate change
db.add_column("orders", "notes")      # Separate change
```

### 2. Descriptive Changes

Changes should be self-documenting:

```json
{
  "type": "ADD_COLUMN",
  "details": {
    "table": "users",
    "column": {
      "name": "email_verified",
      "type": "BOOLEAN",
      "nullable": false,
      "default": false
    }
  },
  "description": "Add email verification tracking"
}
```


## Troubleshooting

### Common Issues

1. **Change Order Violations**
   ```
   Error: Cannot add column to non-existent table
   Solution: Ensure changes are applied in correct order
   ```

2. **Duplicate Changes**
   ```
   Error: Table already exists
   Solution: Check if change was already applied
   ```

3. **Incompatible Changes**
   ```
   Error: Cannot merge - branches have diverged
   Solution: Rebase or recreate branch from latest main
   ```

### Debugging Changes

```python
def debug_changes(branch_name):
    """Debug change tracking issues."""
    changes = get_branch_changes(db, branch_name)
    
    print(f"Total changes: {len(changes)}")
    print(f"Change types: {Counter(c['type'] for c in changes)}")
    
    # Check for issues
    tables_created = set()
    for change in changes:
        if change["type"] == "CREATE_TABLE":
            table = change["details"]["table"]
            if table in tables_created:
                print(f"WARNING: Duplicate CREATE_TABLE for {table}")
            tables_created.add(table)
        
        elif change["type"] == "ADD_COLUMN":
            table = change["details"]["table"]
            if table not in tables_created:
                print(f"WARNING: ADD_COLUMN to non-existent table {table}")
```

## Next Steps

- [Branching Concepts](branching.md)
- [CLI Branch Commands](../cli/branch.md)
# Branching Concepts

Understanding CinchDB's branching system for schema management.

## What is Schema Branching?

Schema branching brings version control concepts to database schema management. Like Git branches for code, CinchDB branches allow you to:

- Isolate schema changes
- Test modifications safely
- Collaborate without conflicts
- Merge changes when ready

## How Branching Works

### Branch Structure

Each branch maintains:
- Complete schema definition
- Change history
- All tenant databases
- Independent data

A key benefit: schema merges happen atomically with **zero rollback risk**. Either all changes apply successfully to all tenants, or none do.

```
.cinchdb/databases/myapp/branches/
├── main/
│   ├── metadata.json     # Branch metadata
│   ├── changes.json      # Change history
│   └── tenants/          # Tenant databases
│       ├── main.db
│       └── customer_a.db
└── feature-branch/
    ├── metadata.json
    ├── changes.json
    └── tenants/
        ├── main.db       # Copy of main's data
        └── customer_a.db # Copy of customer_a's data
```

### Creating Branches

When you create a branch:
1. Directory structure is copied
2. All tenant databases are duplicated
3. Change tracking starts fresh
4. Schema matches source exactly

```bash
cinch branch create feature.new-schema
```

This creates an exact copy, allowing independent development.

## Change Tracking

### What's Tracked

CinchDB tracks all schema modifications:
- Table creation/deletion
- Column additions/removals/renames
- View creation/updates/deletion
- Index creation/deletion

### Change Format

Changes are stored in `changes.json`:
```json
[
  {
    "id": "change_123",
    "timestamp": "2024-01-15T10:30:00Z",
    "type": "CREATE_TABLE",
    "details": {
      "table": "users",
      "columns": [
        {"name": "id", "type": "TEXT"},
        {"name": "email", "type": "TEXT"}
      ]
    }
  },
  {
    "id": "change_124",
    "timestamp": "2024-01-15T10:31:00Z",
    "type": "ADD_COLUMN",
    "details": {
      "table": "users",
      "column": {"name": "phone", "type": "TEXT", "nullable": true}
    }
  }
]
```

### Change Order

Changes are applied in chronological order. This ensures:
- Reproducible schema evolution
- Consistent merge behavior
- Predictable results

## Merging

### Merge Rules

CinchDB enforces these merge rules:

1. **Main Branch Protection** - Cannot modify main directly
2. **Linear History** - Target must have all source changes
3. **No Conflicts** - Changes must be compatible
4. **All Tenants** - Changes apply to every tenant

### Merge Process

When merging `feature` into `main`:

1. **Validation**
   - Check main has all feature's parent changes
   - Verify no conflicting modifications
   - Ensure changes are applicable

2. **Application**
   - Apply each change to main
   - Update all tenant databases
   - Record in change history

3. **Completion**
   - Update branch metadata
   - Log merge operation
   - Branch can be deleted

### Example Merge

```bash
# On feature branch
cinch table create products name:TEXT price:REAL

# Switch to main
cinch branch switch main

# Merge feature
cinch branch merge feature.products main
```

## Conflict Prevention

CinchDB prevents conflicts through:

### 1. Linear History Requirement

Branches must share a common ancestor:
```
main: A → B → C
feature: A → B → D → E

✓ Can merge feature→main (main has A,B)
✗ Cannot merge if main adds F (diverged)
```

### 2. Operation Ordering

Changes are atomic and ordered:
- Each change has unique ID
- Timestamp ensures order
- No parallel modifications

### 3. Schema Validation

Before merge, CinchDB validates:
- Tables don't already exist
- Columns don't conflict
- Types are compatible

## Working with Branches

### Development Workflow

1. **Create Feature Branch**
   ```bash
   cinch branch create feature.user-profiles
   ```

2. **Make Changes**
   ```bash
   cinch table create profiles user_id:TEXT bio:TEXT
   ```

3. **Test Thoroughly**
   ```bash
   cinch query "INSERT INTO profiles ..." 
   cinch query "SELECT * FROM profiles"
   ```

4. **Merge When Ready**
   ```bash
   cinch branch merge feature.user-profiles main
   ```

### Parallel Development

Multiple developers can work simultaneously:

```
Developer A: main → feature.auth → implements auth tables
Developer B: main → feature.billing → implements billing tables

Both can merge to main independently (no conflicts)
```

### Long-Running Branches

For major features:

```bash
# Create long-running branch
cinch branch create release.v2

# Periodically sync with main
cinch branch merge main release.v2

# Continue development
cinch table create v2_features ...

# Eventually merge back
cinch branch merge release.v2 main
```

## Best Practices

### 1. Branch Naming

Use descriptive, consistent names:
- `feature.` - New functionality
- `bugfix.` - Fixing issues
- `refactor.` - Schema improvements
- `experiment.` - Trying ideas
- `release.` - Version preparation

### 2. Small, Focused Changes

Keep branches focused:
```bash
# Good - single purpose
feature.add-user-avatars
feature.optimize-indexes

# Bad - too broad
feature.big-update
feature.everything
```

### 3. Regular Merging

Merge completed work promptly:
- Reduces divergence
- Avoids conflicts
- Shares improvements

### 4. Testing Before Merge

Always test on branch:
```python
# Automated tests
def test_branch_schema(branch_name):
    db = cinchdb.connect("myapp", branch=branch_name)
    
    # Verify schema
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    assert "expected_table" in [t["name"] for t in tables]
    
    # Test operations
    db.insert("expected_table", test_data)
    results = db.query("SELECT * FROM expected_table")
    assert len(results) > 0
```

## Advanced Concepts

### Branch Metadata

Each branch tracks:
```json
{
  "name": "feature.new-schema",
  "created_at": "2024-01-15T10:00:00Z",
  "created_from": "main",
  "last_change": "2024-01-15T11:00:00Z",
  "change_count": 5
}
```

### Change Application

Changes are applied using SQL:
```python
def apply_change(db, change):
    if change["type"] == "CREATE_TABLE":
        columns = []
        for col in change["details"]["columns"]:
            columns.append(f"{col['name']} {col['type']}")
        
        sql = f"CREATE TABLE {change['details']['table']} ({', '.join(columns)})"
        db.execute(sql)
    
    elif change["type"] == "ADD_COLUMN":
        sql = f"ALTER TABLE {change['details']['table']} ADD COLUMN {change['details']['column']['name']} {change['details']['column']['type']}"
        db.execute(sql)
```

## Limitations

### 1. No Concurrent Merges
Only one merge at a time to ensure consistency.

### 2. No Cherry-Picking
Must merge all changes - cannot select specific ones.

### 3. Limited Rollback
After merge, changes are permanent. Plan carefully.

### 4. Schema Only
Branches track schema, not data modifications.

## Next Steps

- [Multi-Tenancy Concepts](multi-tenancy.md)
- [Change Tracking](change-tracking.md)
- [Schema Branching Tutorial](../tutorials/schema-branching.md)
# Schema Branching

**Branch database schemas like Git branches. Test changes safely, merge atomically.**

## What is Schema Branching?

**Problem**: Database schema changes are risky. One mistake breaks production.

**Solution**: Branch schemas like code. Test changes in isolation, merge when ready.

```bash
cinch branch create add-payments --switch
cinch table create payments user_id:TEXT amount:REAL status:TEXT
# Test thoroughly...
cinch branch switch main  
cinch branch merge-into-main add-payments  # Atomic merge
```

## When to Use Branches

### ✅ **Always Use Branches For:**

- **New features** - Adding tables, columns, indexes
- **Schema refactoring** - Renaming, restructuring  
- **Breaking changes** - Removing columns, changing types
- **Experiments** - Testing schema ideas before committing

### ⚠️ **Usually Stay on Main For:**

- **Data-only changes** - INSERT, UPDATE, DELETE queries
- **Minor tweaks** - Adding simple indexes, views
- **Emergency fixes** - Quick data corrections

## How Branching Works

### Key Concept: **Complete Isolation**

Each branch is a **complete copy** of your database:
- Full schema definition
- All tenant data
- Independent change history

```
myapp/
├── main/           ← Production branch
│   ├── main.db     ← Default tenant
│   └── customer_a.db  
└── add-payments/   ← Feature branch  
    ├── main.db     ← Copy of main's data
    └── customer_a.db ← Copy of customer_a's data
```

### Mental Model: **Git for Databases**

| Git Concept | CinchDB Equivalent |
|-------------|-------------------|
| `git branch feature` | `cinch branch create feature` |
| `git checkout feature` | `cinch branch switch feature` |
| `git merge feature` | `cinch branch merge-into-main feature` |
| Files + history | Schema + data + change history |

## Branch Operations

### Create & Switch
```bash
# Create new branch from main
cinch branch create user-profiles

# Create and switch immediately  
cinch branch create user-profiles --switch

# Create from specific branch
cinch branch create hotfix --from production
```

### Make Changes
```bash
# All operations work on current branch
cinch table create profiles user_id:TEXT bio:TEXT avatar_url:TEXT
cinch column add users profile_completed:BOOLEAN
cinch data insert profiles --data '{"user_id": "user-123", "bio": "Software developer"}'
```

### Merge Back
```bash
cinch branch switch main
cinch branch merge-into-main user-profiles

# Branch is automatically deleted after successful merge
```

## Safe Merging

### Zero Rollback Risk

CinchDB merges are **atomic across all tenants**:
- Either ALL tenants get the changes
- Or NO tenants get the changes  
- No partial state, no rollback needed

### Merge Process
1. **Analyze changes** - Compare schemas between branches
2. **Validate safety** - Check for conflicts, breaking changes  
3. **Apply atomically** - Execute all changes as single transaction
4. **Update all tenants** - Changes apply to every tenant database
5. **Clean up** - Delete source branch, update change history

## Best Practices

### Branch Naming
```bash
# Feature branches (use dots for namespacing)
cinch branch create feature.add-payments
cinch branch create feature.user-authentication

# Bug fixes
cinch branch create fix.login-validation
cinch branch create hotfix.critical-bug-123

# Experiments
cinch branch create experiment.new-schema
```

### Development Workflow
```bash
# 1. Start feature
cinch branch create feature.orders --switch

# 2. Develop iteratively
cinch table create orders user_id:TEXT total:REAL
cinch data insert orders --data '{"user_id": "test-user", "total": 29.99}'
cinch query "SELECT * FROM orders" # Test it works

# 3. More changes
cinch table create order_items order_id:TEXT product_id:TEXT quantity:INTEGER
cinch create_index orders ["user_id", "created_at"]

# 4. Final testing
cinch query "SELECT o.*, COUNT(oi.id) FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id GROUP BY o.id"

# 5. Merge when confident
cinch branch switch main
cinch branch merge-into-main feature.orders
```

### Multi-Developer Teams
- **One branch per feature** - Avoid conflicts
- **Short-lived branches** - Merge frequently  
- **Test before merging** - Use sample data to verify
- **Coordinate breaking changes** - Discuss schema changes as a team

## Troubleshooting

**"Branch merge failed"** → Schema conflict. Check what changed on main since you branched.

**"Too much disk space"** → Branches duplicate all data. Delete unused branches.

**"Changes not showing"** → Make sure you're on the right branch: `cinch branch list`

## Comparison: Traditional vs CinchDB

| Traditional Migrations | CinchDB Branches |
|----------------------|------------------|
| Write migration scripts | Make changes directly |
| Risk of rollback needed | Zero rollback risk |
| Hard to test safely | Complete isolation |
| One-way only | Can merge, branch, re-branch |
| Manual conflict resolution | Automatic conflict detection |

## Next Steps

- [Multi-Tenancy](multi-tenancy.md) - How branches work with tenants
- [Change Tracking](change-tracking.md) - Understanding change history
- [CLI Branch Commands](../cli/branch.md) - Complete command reference
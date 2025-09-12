# Schema Branching Tutorial

Safe schema evolution using CinchDB's branching system.

## Problem → Solution

**Problem**: Schema changes risk breaking production apps and corrupting data  
**Solution**: CinchDB branches isolate changes, enable testing, and provide rollback

## When to Use

| Change Type | Use Branch? | Reason |
|-------------|-------------|--------|
| Add table/column | Yes | Test integration first |
| Drop table/column | Yes | Avoid accidental data loss |
| Rename column | Yes | Coordinate app updates |
| Add index | Optional | Low risk, but good practice |

## Quick Workflow

```bash
# 1. Create feature branch
cinch branch create feature.add-user-profiles
cinch branch switch feature.add-user-profiles

# 2. Make schema changes
cinch table create user_profiles user_id:TEXT bio:TEXT? website:TEXT? location:TEXT? avatar_url:TEXT?
cinch column add users profile_complete:BOOLEAN

# 3. Test changes
cinch data insert user_profiles --data '{"user_id": "123", "bio": "Software developer"}'
cinch table info user_profiles

# 4. Deploy to production
cinch branch changes  # Review
cinch branch merge-into-main
```

## Migration Patterns

### Safe Changes (No App Coordination Needed)
```bash
# Add new tables
cinch table create audit_logs event:TEXT user_id:TEXT data:TEXT?

# Add nullable columns  
cinch column add users last_seen:TEXT?

# Add indexes
cinch index create users email --unique
```

### Risky Changes (Coordinate with App)
```bash
# Renaming strategy - two-phase deployment
cinch branch create refactor.rename-columns

# Phase 1: Add new column, populate it
cinch column add users display_name:TEXT?
# Update data via your application code, not CLI

# Update app to use display_name, deploy app
# Phase 2: Drop old column (separate branch)
cinch branch create cleanup.remove-old-name-column
cinch column drop users name  # Use column command, not raw SQL
```

## Branch Testing

**Pattern**: Test schema changes before merging to catch issues early

```python
import pytest
import cinchdb

def test_new_user_profiles_table():
    # Test against feature branch
    db = cinchdb.connect("myapp", branch="feature.add-user-profiles")
    
    # Verify table exists
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'")
    assert len(tables) == 1
    
    # Test CRUD operations
    profile = db.insert("user_profiles", {"user_id": "test-123", "bio": "Test bio"})
    assert profile["id"] is not None
    
    # Test constraints
    with pytest.raises(Exception):
        db.insert("user_profiles", {"bio": "No user"})  # Missing required user_id

def validate_branch(branch_name: str):
    """Run full validation suite."""
    db = cinchdb.connect("myapp", branch=branch_name)
    
    # Schema validation
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    assert len(tables) > 0
    
    # Performance check  
    import time
    start = time.time()
    db.query("SELECT COUNT(*) FROM users")
    assert (time.time() - start) < 1.0
    
    # Data integrity
    orphans = db.query("SELECT COUNT(*) as count FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE u.id IS NULL")
    assert orphans[0]["count"] == 0
    
    return True
```

### Testing Checklist

| Check | Command/Test |
|-------|-------------|
| Schema valid | `cinch table list` |
| Core queries work | `cinch query "SELECT * FROM users LIMIT 1"` |
| Performance OK | Time critical queries |
| No orphaned data | Check foreign key integrity |
| App compatibility | Run app test suite against branch |

## Merge Strategies

### Fast-Forward (Simple)
```bash
# No conflicts - direct merge
cinch branch merge feature.simple-addition main
```

### Review Changes First
```bash
# Review what will be merged
cinch branch changes feature.risky-change

# Look for dangerous operations
grep -E "DROP|DELETE" changes.sql

# Merge if safe
cinch branch merge feature.risky-change main
```

### Staged Rollout
```python
def staged_rollout(branch_name: str):
    """Roll out schema changes gradually."""
    db = cinchdb.connect("myapp")
    
    # Stage 1: Test tenants
    test_tenants = ["test_tenant_1", "test_tenant_2"]
    for tenant in test_tenants:
        test_db = cinchdb.connect(db.database, branch=branch_name, tenant=tenant)
        # Run validation tests...
        print(f"✓ Tested on {tenant}")
    
    # Stage 2: Beta customers (after manual approval)
    if input("Proceed to beta customers? (y/n): ") == 'y':
        # Apply to beta tenants...
        pass
    
    # Stage 3: Full production rollout
    if input("Deploy to all customers? (y/n): ") == 'y':
        db.branches.merge_branches(branch_name, "main")
```
```


## Rollback Procedures

| Situation | Action |
|-----------|--------|
| Pre-merge | `cinch branch delete feature.bad-idea --force` |
| Post-merge | Create rollback branch with reverse changes |
| Emergency | Switch all apps back to previous main branch |

### Emergency Rollback
```bash
# Create rollback branch
cinch branch create rollback/emergency-$(date +%s)

# Reverse changes using appropriate commands
cinch table drop problematic_table

# Deploy rollback  
cinch branch merge-into-main
```

## Best Practices

### Branch Naming Convention
- `feature.description` - New features
- `bugfix.issue-123` - Bug fixes  
- `hotfix.urgent-fix` - Urgent production fixes
- `refactor.cleanup` - Code improvements
- `experiment.idea` - Experimental changes

### Keep Changes Small
```bash
# ✅ Good: Single purpose
cinch branch create feature.add-user-avatars

# ❌ Bad: Too many changes
cinch branch create feature.everything-update
```

### Clean Up After Merge
```bash
# Remove completed branches
cinch branch delete feature.completed-feature

# List old branches
cinch branch list | grep feature.
```

## Next Steps

- Apply branching to [Multi-Tenant Apps](multi-tenant-app.md)
- Review [Branching Concepts](../concepts/branching.md) for advanced patterns
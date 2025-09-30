# Branch Commands

Manage schema branches for isolated development.

## list

List all branches in the active database.

```bash
cinch branch list
```

### Example Output
```
Branches in database 'main':
• main (active)
• feature.add-users
• feature.update-schema
• hotfix.fix-indexes
```

## create

Create a new branch from the current branch.

```bash
cinch branch create BRANCH_NAME
```

### Arguments
- `BRANCH_NAME` - Name of the new branch

### Options
- `--from BRANCH` - Source branch (defaults to current branch)

### Examples
```bash
# Create from current branch
cinch branch create feature.add-comments
```
```
✓ Created branch 'feature.add-comments' from 'main'
✓ Copied 3 tables and 5 tenants to new branch
```

```bash
# Create from specific branch
cinch branch create hotfix.fix-bug --from main
```
```
✓ Created branch 'hotfix.fix-bug' from 'main'
```

### Notes
- Copies all schema and tenants from source branch
- Branch names can include periods and dashes for organization
- Cannot create duplicate branch names

## switch

Switch to a different branch.

```bash
cinch branch switch BRANCH_NAME
```

### Arguments
- `BRANCH_NAME` - Branch to switch to

### Example
```bash
cinch branch switch feature.add-users
```

### Notes
- Updates `active_branch` in config
- All subsequent commands use the new branch
- Does not affect any uncommitted data

## delete

Delete a branch.

```bash
cinch branch delete BRANCH_NAME
```

### Arguments
- `BRANCH_NAME` - Branch to delete

### Options
- `--force` - Skip confirmation

### Example
```bash
# With confirmation
cinch branch delete feature.old-feature

# Without confirmation  
cinch branch delete feature.old-feature --force
```

### Notes
- Cannot delete the `main` branch
- Cannot delete the active branch
- Permanently removes all branch data

## merge

Merge changes from one branch into another.

```bash
cinch branch merge SOURCE_BRANCH [TARGET_BRANCH]
```

### Arguments
- `SOURCE_BRANCH` - Branch with changes to merge
- `TARGET_BRANCH` - Branch to merge into (defaults to current branch)

### Options
- `--force` - Force merge even with conflicts
- `--preview` - Preview merge without executing
- `--dry-run` - Show SQL statements without applying

### Examples
```bash
# Merge feature into main
cinch branch merge feature.add-users main

# Preview merge before executing
cinch branch merge feature.add-users main --preview

# Merge with explicit target
cinch branch merge feature.add-users --target main
```

### Notes
- When merging to main, source branch must be up-to-date with main
- Changes are automatically applied to all tenants
- Cannot merge if there are conflicts (unless using --force)

## changes

View changes made in a branch.

```bash
cinch branch changes [BRANCH_NAME]
```

### Arguments
- `BRANCH_NAME` - Branch to inspect (defaults to current)

### Example Output
```
Changes in branch 'feature.add-users':
1. CREATE TABLE users (name TEXT, email TEXT)
2. CREATE VIEW active_users AS SELECT * FROM users WHERE active = true
3. ADD COLUMN avatar_url TEXT TO users
```

## Common Workflows

### Feature Development
```bash
# Create feature branch
cinch branch create feature.shopping-cart

# Make changes
cinch table create cart_items product_id:TEXT quantity:INTEGER
cinch table create orders user_id:TEXT total:REAL

# Review changes
cinch branch changes

# Merge to main
cinch branch merge feature.shopping-cart main
```

### Hotfix Workflow
```bash
# Create hotfix from main
cinch branch create hotfix.fix-index --from main

# Make fix
cinch column add users last_login:TEXT

# Merge back quickly
cinch branch merge hotfix.fix-index main
```

### Parallel Development
```bash
# Multiple features in parallel
cinch branch create feature.users
cinch branch create feature.products
cinch branch create feature.orders

# Work independently
cinch branch switch feature.users
cinch table create users name:TEXT

cinch branch switch feature.products  
cinch table create products name:TEXT price:REAL

# Merge when ready
cinch branch merge feature.users main
cinch branch merge feature.products main
```

## Best Practices

1. **Branch Naming** - Use descriptive names like `feature.`, `bugfix.`, `hotfix.`
2. **Small Changes** - Keep branches focused on single features
3. **Regular Merges** - Merge completed features promptly
4. **Review Changes** - Always review before merging to main
5. **Clean Up** - Delete merged branches to keep list manageable

## Troubleshooting

### "Branch already exists"
**Problem**: `cinch branch create feature.users` fails with "Branch already exists"
**Solution**: Use `cinch branch list` to check existing branches, choose a different name

### "Cannot merge: conflicts detected"
**Problem**: Merge fails with schema conflicts
**Solution**: 
1. Review changes: `cinch branch changes feature.branch`
2. Check target: `cinch branch changes main`
3. Resolve manually or recreate branch from updated main

### "Cannot delete active branch"
**Problem**: Trying to delete the currently active branch
**Solution**: Switch first: `cinch branch switch main`, then delete

## Protection Rules

- The `main` branch cannot be deleted
- When merging to main, source branch must be up-to-date with main
- All schema changes must go through branches

## Remote Operations

Branch commands work with remote connections:

```bash
```

## Next Steps

- [Table Commands](table.md) - Create tables in branches
- [Column Commands](column.md) - Modify schemas in branches
- [Schema Branching Concepts](../concepts/branching.md) - Deep dive into branching theory
- [Change Tracking](../concepts/change-tracking.md) - How changes are tracked
- [Schema Branching Tutorial](../tutorials/schema-branching.md) - End-to-end workflow example
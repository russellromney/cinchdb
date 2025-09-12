# CLI Reference

Manage databases, branches, and schema from the command line.

## Getting Started

```bash
# Initialize project
cinch init myproject && cd myproject

# Check status
cinch status
```

## Commands

### Project & Database
- [`cinch init`](project.md#init) - Initialize new project
- [`cinch db`](database.md) - Database operations (list, create, use, delete)

### Schema Management  
- [`cinch table`](table.md) - Create and manage tables
- [`cinch column`](column.md) - Add/drop/modify columns
- [`cinch view`](view.md) - Create database views
- [`cinch query`](query.md) - Execute SQL queries

### Data Operations
- [`cinch data`](data.md) - Bulk data operations (insert, update, delete)

### Branching & Tenancy
- [`cinch branch`](branch.md) - Branch operations (create, switch, merge, delete)
- [`cinch tenant`](tenant.md) - Multi-tenant operations

### Code Generation
- [`cinch codegen`](codegen.md) - Generate type-safe SDKs

## Quick Reference

| Task | Command |
|------|---------|
| Initialize project | `cinch init myapp` |
| Create table | `cinch table create users name:TEXT email:TEXT` |
| Query data | `cinch query "SELECT * FROM users"` |
| Delete records | `cinch data delete users --where "status=inactive"` |
| Update records | `cinch data update users --set "status=active" --where "plan=free"` |
| Create branch | `cinch branch create feature-auth --switch` |
| Merge to main | `cinch branch merge-into-main feature-auth` |
| Multi-tenant query | `cinch query "SELECT * FROM users" --tenant customer_a` |
| Generate SDK | `cinch codegen generate python models/` |

## Common Workflows

### Feature Development
```bash
# Create feature branch
cinch branch create add-products --switch

# Make changes
cinch table create products name:TEXT price:REAL category:TEXT
cinch data insert products --data '{"name": "Laptop", "price": 999.99, "category": "electronics"}'

# Test changes
cinch query "SELECT * FROM products"

# Merge when ready
cinch branch switch main
cinch branch merge-into-main add-products
```

### Multi-Tenant Setup
```bash
# Create tenants
cinch tenant create customer_a
cinch tenant create customer_b

# Add tenant-specific data
cinch data insert users --tenant customer_a --data '{"name": "John", "email": "john@customer-a.com"}'
cinch data insert users --tenant customer_b --data '{"name": "Jane", "email": "jane@customer-b.com"}'

# Query per tenant
cinch query "SELECT * FROM users" --tenant customer_a
```

## Global Options

- `--help` - Show command help
- `--tenant TENANT` - Target specific tenant (for data operations)
- `--format FORMAT` - Output format: table, json, csv (for queries)

## Need Help?

```bash
cinch --help              # General help
cinch <command> --help    # Command-specific help
```

## Next Steps

- [Core Concepts](../getting-started/concepts.md)
- [Python SDK](../python-sdk/index.md)
- [Quick Start Guide](../getting-started/quickstart.md)
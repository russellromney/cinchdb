# Core Concepts

Understanding CinchDB's key concepts will help you use it effectively.

## Projects

A CinchDB project is a directory containing your databases. It's created with `cinch init` and contains:

```
.cinchdb/
├── config.toml          # Project configuration
└── databases/           # Your databases
    └── main/           # Default database
        └── branches/   # Database branches
            └── main/   # Default branch
```

## Databases

Each project can have multiple databases. Think of a database as a completely separate application or service.

```bash
# Create a new database
cinch db create analytics

# Switch active database
cinch db use analytics

# List all databases
cinch db list
```

## Branches

Branches allow you to make isolated schema changes, similar to Git branches for code.

Key principles:
- Each branch has its own schema
- Changes are tracked per branch
- You can merge branches
- The `main` branch is protected (merge-only)

```bash
# Create and switch to a new branch
cinch branch create feature/add-users
cinch branch switch feature/add-users

# Make changes
cinch table create users name:TEXT

# Merge back to main
cinch branch switch main
cinch branch merge feature/add-users
```

## Tables and Columns

Tables are created with automatic fields:

```bash
cinch table create posts title:TEXT content:TEXT
```

This creates:
- `id` - UUID primary key
- `title` - TEXT column
- `content` - TEXT column  
- `created_at` - Timestamp
- `updated_at` - Timestamp

Column types:
- `TEXT` - String data
- `INTEGER` - Whole numbers
- `REAL` - Decimal numbers
- `BOOLEAN` - True/false
- `BLOB` - Binary data

## Views

Views are saved SQL queries that act like virtual tables:

```bash
# Create a view
cinch view create active_users "SELECT * FROM users WHERE active = true"

# Query the view
cinch query "SELECT * FROM active_users"
```

## Multi-Tenancy

CinchDB supports complete data isolation between tenants while sharing the same schema:

```bash
# Create tenants
cinch tenant create customer_a
cinch tenant create customer_b

# Work with tenant data
cinch query "INSERT INTO users ..." --tenant customer_a
cinch query "SELECT * FROM users" --tenant customer_a
```

Key points:
- Each tenant has separate SQLite database files
- Schema changes apply to all tenants
- Default tenant is "main"

## Change Tracking

Every schema modification is tracked:
- Table creation/deletion
- Column additions/removals
- View changes

Changes are stored in JSON files and used for:
- Merging branches
- Applying changes to all tenants
- Schema history

## Remote Access

CinchDB can work locally or connect to a remote API:

```bash
# Add a remote server
cinch remote add prod --url https://api.example.com --key YOUR_KEY

# Use remote connection
cinch remote use prod

# All commands now execute remotely
cinch query "SELECT * FROM users"
```

## Connection Modes

CinchDB operates in two modes:

### Local Mode
- Direct SQLite file access
- Full control over database files
- No network required

### Remote Mode  
- API-based access
- Authentication via API keys
- Suitable for production deployments

## Best Practices

1. **Branch for Features** - Create a branch for each feature or schema change
2. **Test on Branches** - Verify changes before merging to main
3. **Use Tenants for Isolation** - Keep customer data separate
4. **Track Changes** - Review changes before merging
5. **Backup Before Major Operations** - Especially before merges

## Next Steps

- [CLI Reference](../cli/index.md) - Detailed command documentation
- [Branching Guide](../concepts/branching.md) - Deep dive into branching
- [Multi-Tenancy Guide](../concepts/multi-tenancy.md) - Advanced tenant management
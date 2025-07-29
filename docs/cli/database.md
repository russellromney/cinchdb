# Database Commands

Manage databases within your CinchDB project.

## list

List all databases in the project.

```bash
cinch db list
```

### Example Output
```
Databases:
• main (active)
• analytics
• staging
```

## create

Create a new database.

```bash
cinch db create DATABASE_NAME
```

### Arguments
- `DATABASE_NAME` - Name of the database to create

### Example
```bash
cinch db create analytics
```

### Notes
- Creates a new database with a default `main` branch
- Database names must be unique within the project
- Automatically creates initial tenant structure

## delete

Delete a database and all its data.

```bash
cinch db delete DATABASE_NAME
```

### Arguments
- `DATABASE_NAME` - Name of the database to delete

### Options
- `--force` - Skip confirmation prompt

### Example
```bash
# With confirmation
cinch db delete staging

# Without confirmation
cinch db delete staging --force
```

### Warning
- **This permanently deletes all branches, tenants, and data**
- Cannot delete the active database
- Cannot be undone

## use

Switch the active database.

```bash
cinch db use DATABASE_NAME
```

### Arguments
- `DATABASE_NAME` - Name of the database to make active

### Example
```bash
cinch db use analytics
```

### Notes
- Updates `active_database` in config.toml
- All subsequent commands will use this database
- Also switches to the main branch of the new database

## info

Show information about a database.

```bash
cinch db info [DATABASE_NAME]
```

### Arguments
- `DATABASE_NAME` - Database to inspect (optional, defaults to active database)

### Example
```bash
# Info about active database
cinch db info

# Info about specific database
cinch db info analytics
```

### Output includes:
- Database name
- Number of branches
- Active branch
- Number of tenants
- Total size on disk

## Common Workflows

### Multiple Environments
```bash
# Create databases for different environments
cinch db create development
cinch db create staging
cinch db create production

# Switch between them
cinch db use development
```

### Project Organization
```bash
# Create databases for different services
cinch db create users_service
cinch db create orders_service
cinch db create analytics_service
```

### Remote Operations

All database commands work with remote connections:

```bash
# List remote databases
cinch db list --remote production

# Create database on remote
cinch db create analytics --remote production
```

## Best Practices

1. **Use descriptive names** - Choose names that reflect the database purpose
2. **Separate concerns** - Use different databases for different services/domains
3. **Environment isolation** - Consider separate databases for dev/staging/prod
4. **Regular backups** - Backup databases before major operations

## Next Steps

- [Branch Commands](branch.md) - Manage branches within databases
- [Table Commands](table.md) - Create and manage tables
- [Tenant Commands](tenant.md) - Set up multi-tenancy
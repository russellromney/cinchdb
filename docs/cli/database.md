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

## Common Patterns

### Environment Separation
```bash
# Mirror production structure in dev/staging
cinch db create development
cinch db create staging
cinch db create production

# Copy schema from prod to staging
cinch db use production
cinch branch create v2_schema
# ... make changes ...
cinch db use staging
cinch branch create v2_schema
cinch branch merge-into-main v2_schema
```

### Service-Oriented Architecture
```bash
# Separate databases by domain
cinch db create user_management
cinch db create order_processing  
cinch db create analytics_warehouse
cinch db create notification_service

# Switch context as needed
cinch db use user_management
cinch table create users email:TEXT username:TEXT
cinch db use order_processing
cinch table create orders user_id:INTEGER total:REAL
```

### Feature Development Workflow
```bash
# Develop features in isolation
cinch db create feature_experiments
cinch db use feature_experiments

# Create feature branch
cinch branch create new_user_onboarding
cinch table create onboarding_steps step:TEXT completed:BOOLEAN

# Test, then merge to main service
cinch db use user_management
cinch branch create new_user_onboarding
# ... replicate changes ...
cinch branch merge-into-main new_user_onboarding
```

### Data Migration Pattern
```bash
# Safe migration approach
cinch db create migration_staging
cinch db use migration_staging

# Test migration steps
cinch query "INSERT INTO users (email) SELECT old_email FROM legacy_users"
cinch query "UPDATE users SET username = SUBSTR(email, 1, INSTR(email, '@')-1)"

# Apply to production when validated
cinch db use production
# ... run validated migration steps ...
```

### Analytics & Reporting
```bash
# Separate analytics from transactional data
cinch db create analytics
cinch db use analytics

# Create aggregation tables
cinch table create daily_stats date:TEXT revenue:REAL orders:INTEGER
cinch table create user_metrics user_id:INTEGER last_active:TEXT orders_count:INTEGER

# Populate from operational databases
cinch query "INSERT INTO daily_stats SELECT DATE(created_at), SUM(total), COUNT(*) FROM production.orders GROUP BY DATE(created_at)"
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
- [Multi-Tenancy Concepts](../concepts/multi-tenancy.md) - Understanding tenant isolation
- [Multi-Tenant Tutorial](../tutorials/multi-tenant-app.md) - Build a complete multi-tenant app
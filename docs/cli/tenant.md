# Tenant Commands

Manage multi-tenant data isolation.

## Overview

Tenants provide complete data isolation while sharing the same schema. Each tenant has separate SQLite database files.

## list

List all tenants in the current branch.

```bash
cinch tenant list
```

### Example Output
```
Tenants in main/main:
• main (default)
• acme_corp
• wayne_enterprises  
• stark_industries
```

## create

Create a new tenant.

```bash
cinch tenant create TENANT_NAME [OPTIONS]
```

### Arguments
- `TENANT_NAME` - Name for the new tenant

### Options
- `--encrypt` - Create an encrypted tenant database
- `--key` - Encryption key (required with --encrypt)
- `--description` / `-d` - Tenant description

### Examples
```bash
# Create single tenant
cinch tenant create customer_a

# Create encrypted tenant
cinch tenant create secure_customer --encrypt --key="my-secret-key-123"

# Create multiple tenants
cinch tenant create acme_corp
cinch tenant create wayne_enterprises
```

### Notes
- Tenant names must be unique within a branch
- Creates new SQLite database file for the tenant
- Inherits current branch schema automatically

## delete

Delete a tenant and all its data.

```bash
cinch tenant delete TENANT_NAME
```

### Arguments
- `TENANT_NAME` - Tenant to delete

### Options
- `--force` - Skip confirmation

### Example
```bash
# With confirmation
cinch tenant delete old_customer

# Without confirmation
cinch tenant delete old_customer --force
```

### Warning

- **Permanently deletes all tenant data**
- Cannot delete the `main` tenant
- Cannot be undone

## rename

Rename a tenant.

```bash
cinch tenant rename OLD_NAME NEW_NAME
```

### Arguments
- `OLD_NAME` - Current tenant name
- `NEW_NAME` - New tenant name

### Example
```bash
cinch tenant rename customer_123 acme_corp
```

## copy

Create a new tenant by copying an existing one.

```bash
cinch tenant copy SOURCE_TENANT NEW_TENANT
```

### Arguments
- `SOURCE_TENANT` - Tenant to copy from
- `NEW_TENANT` - Name for the new tenant

### Options
- `--no-data` - Copy schema only (default: copies data too)

### Examples
```bash
# Copy with data
cinch tenant copy template_tenant customer_b

# Copy schema only
cinch tenant copy main new_customer --no-data
```


## Working with Tenants

### Query Specific Tenant
```bash
# Query tenant data
cinch query "SELECT * FROM users" --tenant acme_corp

# Insert into tenant
cinch data insert users --tenant acme_corp --data '{"name": "Alice", "email": "alice@acme.com"}'
```

### Tenant-Specific Operations
All commands support `--tenant` flag:
```bash
# Table info for tenant
cinch table info users --tenant customer_a

# Create view for tenant
cinch view create active_users "SELECT * FROM users WHERE active = true" --tenant customer_a
```

## Common Use Cases

### SaaS Applications
```bash
# Create tenant per customer
cinch tenant create customer_001
cinch tenant create customer_002

# Customer-specific data
cinch data insert settings --tenant customer_001 --data '{"key": "theme", "value": "dark"}'
```

### Development/Testing
```bash
# Create test tenants
cinch tenant create test_env
cinch tenant create staging_env

# Copy production data for testing
cinch tenant copy main test_env
```

### Multi-Region Setup
```bash
# Regional tenants
cinch tenant create us_east
cinch tenant create us_west  
cinch tenant create eu_central
cinch tenant create asia_pacific
```

## Schema Synchronization

Schema changes automatically apply to all tenants:

```bash
# Add column - affects all tenants
cinch column add users phone:TEXT

# Verify across tenants
cinch table info users --tenant main
cinch table info users --tenant customer_a
```

## Tenant Isolation

Each tenant has:
- Separate SQLite database file
- Complete data isolation
- Shared schema definition
- Independent query execution

Example file structure:
```
.cinchdb/databases/main/branches/main/tenants/
├── main.db
├── customer_a.db
├── customer_b.db
└── customer_c.db
```

## Best Practices

1. **Naming Conventions**
   - Use lowercase with underscores
   - Include customer/region identifiers
   - Avoid special characters

2. **Template Tenant**
   - Create a template tenant with default data
   - Copy from template for new customers
   ```bash
   cinch tenant create _template
   # Add default data...
   cinch tenant copy _template new_customer
   ```

3. **Regular Cleanup**
   - Remove inactive tenants
   - Archive old tenant data
   - Monitor tenant disk usage

4. **Access Control**
   - Map API keys to specific tenants
   - Implement tenant filtering in application
   - Log tenant access for auditing

## Performance Considerations

- Each tenant has separate SQLite file
- No cross-tenant query overhead
- Linear scaling with tenant count
- Consider sharding for many tenants (1000+)

## Migration Patterns

### Onboarding New Customer
```bash
# Create tenant
cinch tenant create bigcorp

# Import initial data
# Use Python SDK for complex data migration
# Python: db = cinchdb.connect("myapp", tenant="bigcorp")
# Python: db.query("INSERT INTO users SELECT * FROM import_table")

# Verify setup
cinch query "SELECT COUNT(*) FROM users" --tenant bigcorp
```

### Tenant Data Export
```bash
# Export tenant data
cinch query "SELECT * FROM users" --tenant customer_a --format csv > customer_a_users.csv
```

## Remote Operations

```bash
```

## Next Steps

- [Query Command](query.md) - Query tenant data
- [Multi-Tenancy Concepts](../concepts/multi-tenancy.md) - Deep dive
- [Multi-Tenant Tutorial](../tutorials/multi-tenant-app.md) - Build an app
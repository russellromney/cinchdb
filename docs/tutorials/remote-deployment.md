# Remote Connection Guide

Connect to a remote CinchDB server for production use.

## Overview

CinchDB supports connecting to remote instances, allowing you to:
- Use the CLI against remote databases
- Access production data securely
- Collaborate with team members
- Deploy applications without local database files

## Configuring Remote Access

### 1. Add a Remote Connection
```bash
# Add a remote with an alias
cinch remote add production --url https://your-cinchdb-server.com --key YOUR_API_KEY

# List configured remotes
cinch remote list
```

### 2. Use the Remote
```bash
# Set as active remote
cinch remote use production

# All commands now execute remotely
cinch table list
cinch query "SELECT COUNT(*) FROM users"
```

### 3. Switch Between Local and Remote
```bash
# Switch back to local
cinch remote clear

# Use a specific remote for one command
cinch query "SELECT * FROM users" --remote production

# Force local execution when a remote is active
cinch query "SELECT * FROM users" --local
```

## Python SDK Remote Connection

```python
import cinchdb

# Connect to remote instance
db = cinchdb.connect(
    "myapp",
    url="https://your-cinchdb-server.com",
    api_key="YOUR_API_KEY"
)

# All operations work the same
tables = db.list_tables()
results = db.query("SELECT * FROM users")
```

## Security Best Practices

1. **Store API Keys Securely**
   - Use environment variables
   - Never commit keys to version control
   - Rotate keys regularly

2. **Use HTTPS**
   - Always use HTTPS URLs for production
   - Verify SSL certificates

3. **Limit Key Permissions**
   - Use read-only keys where possible
   - Restrict keys to specific branches

## Next Steps

- Learn about [Multi-tenancy](../concepts/multi-tenancy.md)
- Explore [Remote Access Concepts](../concepts/remote-access.md)
- Review [CLI Remote Commands](../cli/remote.md)
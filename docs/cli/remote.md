# Remote Commands

Configure and manage remote CinchDB connections.

## Overview

Remote commands allow you to connect your local CLI to remote CinchDB API servers.

## add

Add a remote configuration.

```bash
cinch remote add ALIAS --url URL --key API_KEY
```

### Arguments
- `ALIAS` - Name for this remote connection

### Options
- `--url URL` - Base URL of the remote API
- `--key API_KEY` - API key for authentication

### Example
```bash
cinch remote add production \
  --url https://api.example.com \
  --key ck_live_a1b2c3d4e5f6
```

### Notes
- URLs are stored without trailing slashes
- API keys are stored in local config
- Keep your config.toml secure

## list

List all configured remotes.

```bash
cinch remote list
```

### Example Output
```
Configured Remotes
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Alias      ┃ URL                     ┃ Active ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ production │ https://api.example.com │ ✓      │
│ staging    │ https://staging.api.com │        │
│ dev        │ http://localhost:8000   │        │
└────────────┴─────────────────────────┴────────┘
```

## use

Set the active remote connection.

```bash
cinch remote use ALIAS
```

### Arguments
- `ALIAS` - Remote to make active

### Example
```bash
cinch remote use production
```

### Notes
- All subsequent commands will use this remote
- Override with `--local` or `--remote <alias>`

## clear

Clear the active remote (switch to local mode).

```bash
cinch remote clear
```

### Example
```bash
cinch remote clear
# Now using local mode
```

## show

Display the currently active remote.

```bash
cinch remote show
```

### Example Output
```
Active remote: production
URL: https://api.example.com
```

## remove

Remove a remote configuration.

```bash
cinch remote remove ALIAS
```

### Arguments
- `ALIAS` - Remote to remove

### Example
```bash
cinch remote remove old_server
```

## Using Remotes

### Automatic Remote Usage
When a remote is active, all commands use it automatically:
```bash
# Set active remote
cinch remote use production

# These commands now execute remotely
cinch table list
cinch query "SELECT * FROM users"
cinch branch create feature.new
```

### Temporary Remote Usage
Use a specific remote for one command:
```bash
# Use staging for this command only
cinch table list --remote staging

# Active remote unchanged
cinch remote show  # Still shows production
```

### Force Local Mode
Override active remote:
```bash
# Force local execution
cinch query "SELECT * FROM users" --local
```

## Configuration Storage

Remotes are stored in `.cinchdb/config.toml`:
```toml
active_remote = "production"

[remotes.production]
url = "https://api.example.com"
key = "ck_live_a1b2c3d4e5f6"

[remotes.staging]
url = "https://staging.example.com"
key = "ck_test_x9y8z7w6v5u4"
```

## Security Best Practices

1. **Protect Your Config**
   ```bash
   # Add to .gitignore
   echo ".cinchdb/config.toml" >> .gitignore
   ```

2. **Use Environment Variables**
   ```bash
   # Store sensitive keys in environment
   export CINCHDB_API_KEY="ck_live_secret"
   cinch remote add prod --url https://api.com --key $CINCHDB_API_KEY
   ```

3. **Separate Keys per Environment**
   - Use different API keys for dev/staging/prod
   - Rotate keys regularly
   - Revoke unused keys

## Common Workflows

### Development Setup
```bash
# Local development
cinch remote clear

# Connect to dev server
cinch remote add dev --url http://localhost:8000 --key dev_key
cinch remote use dev
```

### Production Deployment
```bash
# Add production remote
cinch remote add prod \
  --url https://api.myapp.com \
  --key $PROD_API_KEY

# Switch to production
cinch remote use prod

# Verify connection
cinch db list
```

### Multi-Environment Testing
```bash
# Add all environments
cinch remote add dev --url http://localhost:8000 --key dev_key
cinch remote add staging --url https://staging.api.com --key stage_key  
cinch remote add prod --url https://api.com --key prod_key

# Test across environments
cinch query "SELECT COUNT(*) FROM users" --remote dev
cinch query "SELECT COUNT(*) FROM users" --remote staging
cinch query "SELECT COUNT(*) FROM users" --remote prod
```

## Troubleshooting

### Connection Issues
```bash
# Test remote connection
cinch db list --remote production

# Common errors:
# - "Connection refused" - Check URL and server status
# - "401 Unauthorized" - Check API key
# - "Network error" - Check internet connection
```

### URL Format
- Include protocol: `https://` or `http://`
- No trailing slashes
- Include port if needed: `http://localhost:8000`

### API Key Issues
- Ensure key has required permissions
- Check key hasn't expired
- Verify key matches environment

## Remote vs Local

| Feature | Local | Remote |
|---------|-------|--------|
| Performance | Fast | Network dependent |
| File access | Direct | API only |
| Authentication | None | API key required |
| Multi-user | No | Yes |
| Deployment | Manual | Automatic |

## Next Steps

- [Remote Deployment Tutorial](../tutorials/remote-deployment.md) - Set up remote server
- [Authentication](../api/authentication.md) - API key management
- [Query Command](query.md) - Execute remote queries
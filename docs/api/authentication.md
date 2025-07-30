# Authentication

Secure your CinchDB API with proper authentication.

## API Key Authentication

CinchDB uses API key authentication for all requests.

### Key Format

```
ck_[environment]_[uuid]

Examples:
ck_live_a1b2c3d4-e5f6-7890-abcd-ef1234567890
ck_test_x9y8z7w6-v5u4-3210-fedc-ba0987654321
```

### Authentication Header

Include the API key in request headers:

```bash
curl -H "X-API-Key: ck_live_your_key_here" \
     https://api.example.com/api/v1/tables
```

## Creating API Keys

### CLI Method

```bash
# Create a new API key
cinch-server create-key \
  --name "Production App" \
  --permissions read,write \
  --databases myapp,analytics \
  --expires-in 365

# Output:
# Created API key: ck_live_a1b2c3d4-e5f6-7890-abcd-ef1234567890
# Expires: 2025-01-15T10:30:00Z
```

### Programmatic Creation

```python
from cinchdb.api import auth

# Create a master key
master_key = auth.create_api_key(
    name="Master Key",
    environment="live",
    permissions=["read", "write", "admin"],
    databases=["*"],  # All databases
    branches=["*"],   # All branches
    tenants=["*"]     # All tenants
)

# Create a restricted key
app_key = auth.create_api_key(
    name="Mobile App",
    environment="live",
    permissions=["read"],
    databases=["myapp"],
    branches=["main"],
    tenants=["*"],
    expires_in_days=90
)

# Create tenant-specific key
tenant_key = auth.create_api_key(
    name="Customer API",
    environment="live",
    permissions=["read", "write"],
    databases=["saas_app"],
    branches=["main"],
    tenants=["customer_123"],
    rate_limit=1000  # Requests per hour
)
```

## Key Types and Permissions

### Master Keys

Full access to all operations:

```python
{
    "name": "Master Key",
    "permissions": ["read", "write", "admin"],
    "databases": ["*"],
    "branches": ["*"],
    "tenants": ["*"]
}
```

### Application Keys

Limited to specific operations:

```python
{
    "name": "Web App",
    "permissions": ["read", "write"],
    "databases": ["production"],
    "branches": ["main"],
    "tenants": ["*"]
}
```

### Read-Only Keys

For analytics and reporting:

```python
{
    "name": "Analytics Service",
    "permissions": ["read"],
    "databases": ["analytics"],
    "branches": ["main"],
    "tenants": ["*"]
}
```

### Tenant-Specific Keys

Isolated to single tenant:

```python
{
    "name": "Customer Portal",
    "permissions": ["read", "write"],
    "databases": ["saas_app"],
    "branches": ["main"],
    "tenants": ["customer_abc"]
}
```

## Permission Model

### Permission Types

- `read` - SELECT queries, list operations
- `write` - INSERT, UPDATE, DELETE operations
- `schema` - CREATE/ALTER/DROP tables
- `admin` - Key management, server operations

### Database Restrictions

```python
# Specific databases
"databases": ["myapp", "analytics"]

# All databases
"databases": ["*"]

# Pattern matching
"databases": ["prod_*"]  # All starting with prod_
```

### Branch Restrictions

```python
# Main branch only
"branches": ["main"]

# Specific branches
"branches": ["main", "staging"]

# All branches
"branches": ["*"]
```

### Tenant Restrictions

```python
# Specific tenants
"tenants": ["customer_a", "customer_b"]

# Pattern matching
"tenants": ["test_*"]  # All test tenants

# All tenants
"tenants": ["*"]
```

## Key Management

### Listing Keys

```python
# List all keys
keys = auth.list_api_keys()

for key in keys:
    print(f"{key.name}: {key.key_prefix}... (expires: {key.expires_at})")

# Filter by status
active_keys = auth.list_api_keys(status="active")
expired_keys = auth.list_api_keys(status="expired")
```

### Key Rotation

```python
def rotate_api_key(old_key_id: str, overlap_days: int = 7):
    """Rotate an API key with overlap period."""
    
    # Get old key details
    old_key = auth.get_api_key(old_key_id)
    
    # Create new key with same permissions
    new_key = auth.create_api_key(
        name=f"{old_key.name} (rotated)",
        environment=old_key.environment,
        permissions=old_key.permissions,
        databases=old_key.databases,
        branches=old_key.branches,
        tenants=old_key.tenants
    )
    
    # Schedule old key deletion
    auth.schedule_key_deletion(
        old_key_id,
        delete_after_days=overlap_days
    )
    
    return new_key

# Rotate keys
new_key = rotate_api_key("key_123", overlap_days=7)
print(f"New key: {new_key.key}")
print(f"Old key expires in 7 days")
```

### Revoking Keys

```python
# Immediate revocation
auth.revoke_api_key("key_123")

# Schedule revocation
auth.schedule_key_revocation(
    "key_456",
    revoke_at="2024-12-31T23:59:59Z"
)
```

## Security Best Practices

### 1. Environment Variables

Never hardcode API keys:

```python
# Bad
api_key = "ck_live_secret123"

# Good
import os
api_key = os.environ["CINCHDB_API_KEY"]

# Better - with fallback
api_key = os.environ.get("CINCHDB_API_KEY")
if not api_key:
    raise ValueError("CINCHDB_API_KEY not set")
```

### 2. Secure Storage

Use secret management services:

```python
# AWS Secrets Manager
import boto3

def get_api_key():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='cinchdb/api-key')
    return response['SecretString']

# HashiCorp Vault
import hvac

def get_api_key():
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.environ['VAULT_TOKEN']
    secret = client.read('secret/data/cinchdb')
    return secret['data']['data']['api_key']
```

### 3. Key Rotation Policy

Implement regular rotation:

```python
# Automated rotation script
def rotate_all_keys():
    keys = auth.list_api_keys(status="active")
    
    for key in keys:
        # Skip recently created keys
        if key.age_days < 30:
            continue
            
        # Rotate keys older than 90 days
        if key.age_days > 90:
            print(f"Rotating key: {key.name}")
            rotate_api_key(key.id, overlap_days=7)
```

### 4. Least Privilege

Grant minimal required permissions:

```python
# Don't use master keys for applications
# Bad
app_key = create_key(permissions=["*"])

# Good - specific permissions
app_key = create_key(
    permissions=["read", "write"],
    databases=["production"],
    branches=["main"]
)
```

### 5. Audit Logging

Track key usage:

```python
def log_api_request(request, api_key):
    audit_log = {
        "timestamp": datetime.now().isoformat(),
        "api_key_id": api_key.id,
        "api_key_name": api_key.name,
        "method": request.method,
        "path": request.path,
        "database": request.args.get("database"),
        "tenant": request.args.get("tenant"),
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent")
    }
    
    # Log to monitoring system
    logger.info(json.dumps(audit_log))
```

## Rate Limiting

### Per-Key Limits

Set rate limits during creation:

```python
# 1000 requests per hour
limited_key = auth.create_api_key(
    name="Rate Limited App",
    rate_limit=1000,
    rate_limit_window="hour"
)

# 10000 requests per day
daily_limit_key = auth.create_api_key(
    name="Daily Limited App",
    rate_limit=10000,
    rate_limit_window="day"
)
```

### Dynamic Rate Limiting

Adjust limits based on usage:

```python
def adjust_rate_limit(key_id: str):
    usage = auth.get_key_usage(key_id, period="day")
    
    if usage.error_rate > 0.1:  # 10% errors
        # Reduce limit
        auth.update_key_rate_limit(key_id, 
            rate_limit=usage.current_limit * 0.5
        )
    elif usage.utilization < 0.5:  # Under 50% usage
        # Increase limit
        auth.update_key_rate_limit(key_id,
            rate_limit=usage.current_limit * 1.5
        )
```

## Multi-Factor Authentication

For admin operations, implement MFA:

```python
def verify_admin_request(api_key: str, mfa_token: str):
    # Verify API key
    key = auth.verify_api_key(api_key)
    
    if "admin" not in key.permissions:
        raise PermissionError("Admin permission required")
    
    # Verify MFA token
    if not auth.verify_mfa_token(key.user_id, mfa_token):
        raise AuthenticationError("Invalid MFA token")
    
    return key
```

## IP Whitelisting

Restrict keys to specific IPs:

```python
# Create key with IP restrictions
secure_key = auth.create_api_key(
    name="Office App",
    allowed_ips=[
        "203.0.113.0/24",  # Office network
        "198.51.100.42"    # VPN endpoint
    ]
)

# Verify IP during request
def verify_ip_whitelist(request, api_key):
    if api_key.allowed_ips:
        client_ip = request.remote_addr
        
        if not any(ip_in_network(client_ip, allowed) 
                   for allowed in api_key.allowed_ips):
            raise AuthenticationError(f"IP {client_ip} not allowed")
```

## Token Expiration

### Temporary Tokens

For short-lived access:

```python
# 1-hour token for file upload
temp_token = auth.create_temporary_token(
    parent_key=api_key,
    expires_in_minutes=60,
    permissions=["write"],
    scope={"table": "uploads"}
)

# Use in client
headers = {
    "X-API-Key": temp_token,
    "X-Token-Type": "temporary"
}
```

### Refresh Tokens

For long-lived sessions:

```python
def create_session(api_key: str):
    # Verify API key
    key = auth.verify_api_key(api_key)
    
    # Create refresh token
    refresh_token = auth.create_refresh_token(
        key_id=key.id,
        expires_in_days=30
    )
    
    # Create access token
    access_token = auth.create_access_token(
        key_id=key.id,
        expires_in_minutes=15
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900  # 15 minutes
    }
```

## Troubleshooting

### Common Issues

1. **Invalid API Key**
   ```
   Error: Invalid API key
   Solution: Check key is active and not expired
   ```

2. **Permission Denied**
   ```
   Error: Permission denied for operation
   Solution: Verify key has required permissions
   ```

3. **Rate Limit Exceeded**
   ```
   Error: Rate limit exceeded
   Solution: Implement backoff or request limit increase
   ```

4. **IP Not Allowed**
   ```
   Error: Request from unauthorized IP
   Solution: Add IP to whitelist or use VPN
   ```

### Debug Mode

Enable detailed auth logging:

```python
# Set environment variable
export CINCHDB_AUTH_DEBUG=true

# Or in code
auth.set_debug_mode(True)

# Logs will include:
# - Key validation steps
# - Permission checks
# - IP verification
# - Rate limit status
```

## Next Steps

- [API Endpoints](endpoints.md)
- [API Endpoints](endpoints.md)
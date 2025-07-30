# Remote Access

Understanding how CinchDB works with remote API servers.

## Overview

CinchDB supports two connection modes:
- **Local** - Direct file access to SQLite databases
- **Remote** - API-based access through HTTP/HTTPS

Remote access enables:
- Multi-user collaboration
- Cloud deployment
- Centralized management
- Scalable architecture

## Architecture

### Components

```
┌─────────────┐     HTTPS      ┌──────────────┐     Files      ┌─────────────┐
│   Client    │ ─────────────> │  API Server  │ ─────────────> │  Databases  │
│  (CLI/SDK)  │ <───────────── │  (FastAPI)   │ <───────────── │  (SQLite)   │
└─────────────┘     JSON       └──────────────┘     SQLite     └─────────────┘
```

### Connection Flow

1. **Client** sends authenticated request
2. **API Server** validates credentials
3. **Server** executes operation locally
4. **Results** returned as JSON
5. **Client** processes response

## API Authentication

### API Keys

CinchDB uses UUID-based API keys:

```
Format: ck_[env]_[random_uuid]
Example: ck_live_a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Key Types

1. **Master Keys** - Full access to all operations
2. **Database Keys** - Restricted to specific databases
3. **Branch Keys** - Limited to certain branches
4. **Tenant Keys** - Access to specific tenants only

### Authentication Flow

```python
# Client includes key in header
headers = {
    "X-API-Key": "ck_live_your_key_here",
    "Content-Type": "application/json"
}

# Server validates
def validate_api_key(key: str) -> dict:
    key_data = lookup_key(key)
    
    if not key_data or key_data["revoked"]:
        raise AuthenticationError("Invalid API key")
    
    return {
        "permissions": key_data["permissions"],
        "databases": key_data["databases"],
        "tenants": key_data["tenants"]
    }
```

## Client Configuration

### CLI Setup

```bash
# Add remote
cinch remote add production \
  --url https://api.example.com \
  --key ck_live_your_key

# Use remote
cinch remote use production

# All commands now use API
cinch table list
cinch query "SELECT * FROM users"
```

### SDK Setup

```python
# Python SDK
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key="ck_live_your_key",
    database="myapp"
)

# Operations work identically
users = db.query("SELECT * FROM users")
db.create_table("products", columns)
```

## API Endpoints

### Core Endpoints

```
# Database Management
GET    /api/v1/databases
POST   /api/v1/databases
DELETE /api/v1/databases/{name}

# Branch Operations  
GET    /api/v1/branches
POST   /api/v1/branches
POST   /api/v1/branches/merge

# Table Management
GET    /api/v1/tables
POST   /api/v1/tables
DELETE /api/v1/tables/{name}

# Query Execution
POST   /api/v1/query

# Data Operations
POST   /api/v1/tables/{table}/data
PUT    /api/v1/tables/{table}/data/{id}
DELETE /api/v1/tables/{table}/data/{id}
```

### Request Format

All requests include standard parameters:

```json
{
  "database": "myapp",
  "branch": "main",
  "tenant": "customer_a",
  "data": {
    // Operation-specific data
  }
}
```

### Response Format

Successful responses:

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123"
  }
}
```

Error responses:

```json
{
  "success": false,
  "error": {
    "code": "TABLE_NOT_FOUND",
    "message": "Table 'users' does not exist",
    "details": {}
  }
}
```

## Connection Management

### Connection Pooling

The SDK manages connections efficiently:

```python
class RemoteConnection:
    def __init__(self, api_url, api_key):
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
        
        # Connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=50,
            max_retries=3
        )
        self.session.mount("https://", adapter)
```

### Retry Logic

Automatic retry for transient failures:

```python
def make_request_with_retry(method, url, **kwargs):
    max_attempts = 3
    backoff_factor = 1.0
    
    for attempt in range(max_attempts):
        try:
            response = method(url, **kwargs)
            
            if response.status_code == 429:  # Rate limited
                wait_time = int(response.headers.get("Retry-After", 60))
                time.sleep(wait_time)
                continue
                
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            if attempt == max_attempts - 1:
                raise
            
            wait_time = backoff_factor * (2 ** attempt)
            time.sleep(wait_time)
```

### Timeout Handling

Configure appropriate timeouts:

```python
# Short timeout for metadata operations
response = session.get(
    f"{api_url}/api/v1/tables",
    timeout=(3.0, 10.0)  # (connect, read)
)

# Longer timeout for queries
response = session.post(
    f"{api_url}/api/v1/query",
    json={"sql": complex_query},
    timeout=(3.0, 300.0)  # 5 minute read timeout
)
```

## Performance Optimization

### Request Batching

Combine multiple operations:

```python
# Instead of multiple requests
for user in users:
    db.insert("users", user)  # N requests

# Batch insert
db.query(
    "INSERT INTO users (name, email) VALUES " +
    ",".join(["(?, ?)"] * len(users)),
    [val for user in users for val in (user["name"], user["email"])]
)  # 1 request
```

### Response Caching

Cache frequently accessed data:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedRemoteDB:
    def __init__(self, db):
        self.db = db
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def query_cached(self, sql: str, params=None):
        cache_key = f"{sql}:{params}"
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() - entry["time"] < self.cache_ttl:
                return entry["data"]
        
        # Fetch from remote
        data = self.db.query(sql, params)
        
        # Cache result
        self.cache[cache_key] = {
            "data": data,
            "time": datetime.now()
        }
        
        return data
```

### Pagination

Handle large result sets:

```python
def query_paginated(db, sql, page_size=1000):
    """Query with pagination for large results."""
    offset = 0
    
    while True:
        page_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"
        results = db.query(page_sql)
        
        if not results:
            break
            
        yield from results
        offset += page_size
        
        if len(results) < page_size:
            break

# Usage
for row in query_paginated(db, "SELECT * FROM large_table"):
    process_row(row)
```

## Security Considerations

### TLS/HTTPS

Always use encrypted connections:

```python
# Verify SSL certificates
db = cinchdb.connect_api(
    api_url="https://api.example.com",  # HTTPS required
    api_key=api_key,
    verify_ssl=True  # Default
)

# For self-signed certificates (development only)
db = cinchdb.connect_api(
    api_url="https://dev.local",
    api_key=api_key,
    verify_ssl="/path/to/ca-bundle.crt"
)
```

### API Key Management

Best practices:

```python
# Don't hardcode keys
# BAD
api_key = "ck_live_secret123"

# GOOD - Environment variables
api_key = os.environ["CINCHDB_API_KEY"]

# BETTER - Secret management
from secretsmanager import get_secret
api_key = get_secret("cinchdb/prod/api_key")
```

### Request Validation

Server-side validation:

```python
def validate_request(request_data, user_permissions):
    # Validate database access
    if request_data["database"] not in user_permissions["databases"]:
        raise PermissionError("Access denied to database")
    
    # Validate tenant access
    if request_data.get("tenant") not in user_permissions["tenants"]:
        raise PermissionError("Access denied to tenant")
    
    # Validate operations
    if request_data["operation"] not in user_permissions["operations"]:
        raise PermissionError("Operation not permitted")
```

## Monitoring

### Request Logging

Track API usage:

```python
def log_api_request(request, response, duration):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "path": request.path,
        "database": request.args.get("database"),
        "tenant": request.args.get("tenant"),
        "user": get_user_from_api_key(request.headers.get("X-API-Key")),
        "status": response.status_code,
        "duration_ms": duration * 1000,
        "size_bytes": len(response.content)
    }
    
    # Log to monitoring system
    logger.info(json.dumps(log_entry))
```

### Metrics Collection

Key metrics to track:

```python
# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter(
    'cinchdb_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'cinchdb_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'cinchdb_active_connections',
    'Active database connections'
)
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check server is running
   - Verify URL is correct
   - Check firewall rules

2. **Authentication Failed**
   - Verify API key is valid
   - Check key permissions
   - Ensure key isn't revoked

3. **Timeout Errors**
   - Increase timeout values
   - Check server performance
   - Optimize slow queries

4. **Rate Limiting**
   - Implement backoff logic
   - Batch operations
   - Request higher limits

### Debug Mode

Enable detailed logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Log all requests
import requests
import http.client
http.client.HTTPConnection.debuglevel = 1
```

## Best Practices

1. **Use Connection Pooling** - Reuse connections for efficiency
2. **Implement Retry Logic** - Handle transient failures gracefully
3. **Cache When Possible** - Reduce unnecessary API calls
4. **Batch Operations** - Combine multiple operations
5. **Monitor Usage** - Track performance and errors
6. **Secure Keys** - Never expose API keys
7. **Use HTTPS** - Always encrypt connections
8. **Handle Errors** - Graceful degradation

## Next Steps

- [Remote Deployment Tutorial](../tutorials/remote-deployment.md)
- [Authentication](../api/authentication.md)
- [API Endpoints](../api/endpoints.md)
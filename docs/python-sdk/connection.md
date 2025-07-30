# Connection Guide

Detailed guide for connecting to CinchDB databases.

## Local Connections

### Basic Connection
```python
import cinchdb

# Connect to database in current project
db = cinchdb.connect("myapp")

# Explicit project directory
db = cinchdb.connect("myapp", project_dir="/path/to/project")
```

### Connection Parameters
```python
db = cinchdb.connect(
    database="myapp",           # Database name (required)
    branch="feature",           # Branch name (default: "main")
    tenant="customer_a",        # Tenant name (default: "main")
    project_dir="/path/to/dir"  # Project path (optional)
)
```

### Auto-discovery
If `project_dir` is not provided, CinchDB searches for `.cinchdb` directory:
1. Current directory
2. Parent directories (up to root)

## Remote Connections

### API Connection
```python
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key="ck_live_a1b2c3d4",
    database="myapp"
)
```

### Full Parameters
```python
db = cinchdb.connect_api(
    api_url="https://api.example.com",  # API base URL (required)
    api_key="your-api-key",             # Authentication key (required)
    database="myapp",                   # Database name (required)
    branch="production",                # Branch (default: "main")
    tenant="customer_b"                 # Tenant (default: "main")
)
```

### Environment Variables
```python
import os

db = cinchdb.connect_api(
    api_url=os.environ["CINCHDB_API_URL"],
    api_key=os.environ["CINCHDB_API_KEY"],
    database="myapp"
)
```

## Connection Management

### Context Manager (Recommended)
```python
with cinchdb.connect("myapp") as db:
    # Database operations
    users = db.query("SELECT * FROM users")
# Connection automatically closed
```

### Manual Management
```python
db = cinchdb.connect("myapp")
try:
    # Database operations
    users = db.query("SELECT * FROM users")
finally:
    db.close()
```

### Connection Pooling
Local connections use SQLite connection pooling:
```python
# Connections are pooled per tenant
db1 = cinchdb.connect("myapp", tenant="a")
db2 = cinchdb.connect("myapp", tenant="a")  # Reuses connection
```

## Switching Context

### Working with Different Branches
```python
# Connect to main branch
main_db = cinchdb.connect("myapp", branch="main")

# Connect to development branch
dev_db = cinchdb.connect("myapp", branch="development")

# Each connection is independent
main_data = main_db.query("SELECT * FROM users")
dev_data = dev_db.query("SELECT * FROM users")
```

### Working with Different Tenants
```python
# Connect to default tenant
default_db = cinchdb.connect("myapp")

# Connect to specific tenant
tenant_db = cinchdb.connect("myapp", tenant="customer_a")

# Query tenant-specific data
users = tenant_db.query("SELECT * FROM users")
```

### Specific Branch and Tenant
```python
# Connect to specific branch and tenant
specific_db = cinchdb.connect("myapp", branch="feature", tenant="customer_b")
```

## Connection Properties

### Check Connection Type
```python
db = cinchdb.connect("myapp")
print(f"Local: {db.is_local}")         # True
print(f"Database: {db.database}")      # "myapp"
print(f"Branch: {db.branch}")          # "main"
print(f"Tenant: {db.tenant}")          # "main"

# Remote connection
api_db = cinchdb.connect_api(...)
print(f"Local: {api_db.is_local}")     # False
print(f"API URL: {api_db.api_url}")    # "https://api.example.com"
```

### Manager Access (Local Only)
```python
db = cinchdb.connect("myapp")

if db.is_local:
    # Access underlying managers
    tables = db.tables.list_tables()
    branches = db.branches.list_branches()
    tenants = db.tenants.list_tenants()
else:
    # Remote connections use methods
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
```

## Error Handling

### Connection Errors
```python
try:
    db = cinchdb.connect("myapp")
except FileNotFoundError:
    print("Project not found - run 'cinch init' first")

try:
    db = cinchdb.connect_api(...)
except ConnectionError:
    print("Cannot reach API server")
except AuthenticationError:
    print("Invalid API key")
```

### Retry Logic
```python
import time
from typing import Optional

def connect_with_retry(
    max_attempts: int = 3,
    delay: float = 1.0
) -> Optional[cinchdb.CinchDB]:
    for attempt in range(max_attempts):
        try:
            return cinchdb.connect_api(...)
        except ConnectionError:
            if attempt < max_attempts - 1:
                time.sleep(delay * (attempt + 1))
            else:
                raise
    return None
```

## Configuration

### From Config File
```python
import toml
from pathlib import Path

# Load config
config_path = Path(".cinchdb/config.toml")
config = toml.load(config_path)

# Connect using config
db = cinchdb.connect(
    database=config["active_database"],
    branch=config["active_branch"]
)
```

### Multiple Environments
```python
import os

ENV = os.environ.get("APP_ENV", "development")

CONFIGS = {
    "development": {
        "project_dir": "/path/to/dev"
    },
    "staging": {
        "api_url": "https://staging.api.com",
        "api_key": os.environ.get("STAGING_KEY")
    },
    "production": {
        "api_url": "https://api.com",
        "api_key": os.environ.get("PROD_KEY")
    }
}

config = CONFIGS[ENV]
if "api_url" in config:
    db = cinchdb.connect_api(database="myapp", **config)
else:
    db = cinchdb.connect(database="myapp", **config)
```

## Performance Tips

1. **Reuse Connections** - Don't create new connections for each query
2. **Use Context Managers** - Ensures proper cleanup
3. **Connection Pooling** - Automatic for local connections
4. **Batch Operations** - Group related queries together

## Security

### API Key Management
```python
# Don't hardcode keys
# BAD
db = cinchdb.connect_api(api_key="ck_live_secret123", ...)

# GOOD - Use environment variables
db = cinchdb.connect_api(
    api_key=os.environ["CINCHDB_API_KEY"],
    ...
)

# BETTER - Use secret manager
from my_secrets import get_secret
db = cinchdb.connect_api(
    api_key=get_secret("cinchdb_api_key"),
    ...
)
```

### Secure Storage
- Store API keys in environment variables
- Use `.env` files for local development
- Never commit keys to version control
- Rotate keys regularly

## Next Steps

- [Table Operations](tables.md) - Create and manage tables
- [Query Guide](queries.md) - Execute queries
- [Branch Operations](branches.md) - Work with branches
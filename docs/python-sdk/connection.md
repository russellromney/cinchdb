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

### Check Connection Properties
```python
db = cinchdb.connect("myapp")
print(f"Local: {db.is_local}")         # True
print(f"Database: {db.database}")      # "myapp"
print(f"Branch: {db.branch}")          # "main"
print(f"Tenant: {db.tenant}")          # "main"
```

### Database Operations
```python
db = cinchdb.connect("myapp")

# Use direct methods on CinchDB instance
results = db.query("SELECT * FROM users")
user_id = db.insert("users", {"name": "John", "email": "john@example.com"})
db.update("users", user_id, {"name": "John Smith"})
```

## Error Handling

### Connection Errors
```python
try:
    db = cinchdb.connect("myapp")
except FileNotFoundError:
    print("Project not found - run 'cinch init' first")
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
from pathlib import Path

ENV = os.environ.get("APP_ENV", "development")

CONFIGS = {
    "development": {
        "project_dir": Path("/path/to/dev")
    },
    "staging": {
        "project_dir": Path("/path/to/staging")
    },
    "production": {
        "project_dir": Path("/path/to/prod")
    }
}

config = CONFIGS[ENV]
db = cinchdb.connect(database="myapp", **config)
```

## Performance Tips

1. **Reuse Connections** - Don't create new connections for each query
2. **Use Context Managers** - Ensures proper cleanup
3. **Connection Pooling** - Automatic for local connections
4. **Batch Operations** - Group related queries together

## Security

### Secure Storage
- Use `.env` files for local development configuration
- Never commit sensitive data to version control
- Keep database files secure in production

## Next Steps

- [Table Operations](tables.md) - Create and manage tables
- [Query Guide](queries.md) - Execute queries
- [Branch Operations](branches.md) - Work with branches
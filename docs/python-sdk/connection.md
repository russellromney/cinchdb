# Connection Guide

Detailed guide for connecting to CinchDB databases.

## Local Connections

### Basic Connection
```python
import cinchdb

# Connect to database in current project
db = cinchdb.connect("myapp")
# Expected: CinchDB instance connected to main database/branch/tenant
# Performance: <1ms connection time (SQLite local file)

# Explicit project directory
db = cinchdb.connect("myapp", project_dir="/path/to/project")
# Expected: CinchDB instance with specified project path
# Common error: FileNotFoundError - Project directory '.cinchdb' not found
```

### Connection Parameters
```python
db = cinchdb.connect(
    database="myapp",           # Database name (required)
    branch="feature",           # Branch name (default: "main")
    tenant="customer_a",        # Tenant name (default: "main")
    project_dir="/path/to/dir", # Project path (optional)
    encryption_key="secret-key" # Encryption key for encrypted tenants
)
# Expected output: CinchDB instance with specified configuration
# Performance: <1ms for existing tenant, ~10ms for new tenant (lazy creation)
# Memory: Each connection ~1MB overhead

# Common errors:
# ValueError: Database 'myapp' does not exist - Create database first
# ValueError: Branch 'feature' does not exist - Create branch first
# ValueError: Invalid encryption key - Check key format
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
    # Expected: List of user dictionaries
    print(f"Found {len(users)} users")
# Connection automatically closed
# Performance benefit: Ensures connection cleanup, prevents "database locked" errors
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
# Performance: Second connection <0.1ms (reused from pool)
# Memory: Shared connection reduces memory usage by ~50%
# Pool size: Up to 5 connections per tenant by default
```

## Switching Context

### Working with Different Branches
```python
# Connect to main branch
main_db = cinchdb.connect("myapp", branch="main")
# Expected: Connection to main branch schema

# Connect to development branch
dev_db = cinchdb.connect("myapp", branch="development")
# Expected: Connection to development branch (may have different schema)

# Each connection is independent
main_data = main_db.query("SELECT * FROM users")
# Expected output: Users from main branch data
dev_data = dev_db.query("SELECT * FROM users")
# Expected output: Users from dev branch (same tenant, different schema possible)

# Performance: Each branch connection is separate (~1ms each)
# Note: Schema changes in branches don't affect data
```

### Working with Different Tenants
```python
# Connect to default tenant
default_db = cinchdb.connect("myapp")
# Expected: Connection to 'main' tenant (default)

# Connect to specific tenant
tenant_db = cinchdb.connect("myapp", tenant="customer_a")
# Expected: Connection to isolated 'customer_a' data
# Performance: <1ms if tenant exists, ~10ms for first access (lazy creation)

# Query tenant-specific data
users = tenant_db.query("SELECT * FROM users")
# Expected output: Only customer_a's users (complete isolation)
# Performance: No impact from other tenants' data volume

# Common pattern: Multi-tenant SaaS
for tenant_id in ["customer_a", "customer_b", "customer_c"]:
    tenant_db = cinchdb.connect("myapp", tenant=tenant_id)
    count = tenant_db.query("SELECT COUNT(*) as c FROM users")[0]["c"]
    print(f"Tenant {tenant_id}: {count} users")
```

### Specific Branch and Tenant
```python
# Connect to specific branch and tenant
specific_db = cinchdb.connect("myapp", branch="feature", tenant="customer_b")
```

## Encrypted Tenants

```python
# Connect with encryption key
db = cinchdb.connect("myapp", tenant="secure", encryption_key="your-32-char-key")
# Expected: Encrypted SQLite database with ChaCha20 cipher
# Performance: ~5% overhead for encryption/decryption
# Security: Data at rest encryption, key required for all access

# Use environment variables for keys (recommended)
import os
key = os.environ.get("TENANT_KEY")
if not key:
    raise ValueError("TENANT_KEY environment variable not set")
db = cinchdb.connect("myapp", tenant="secure", encryption_key=key)
# Expected: Secure connection with environment-based key

# Common errors:
# ValueError: Incorrect encryption key - Wrong key for encrypted database
# sqlite3.DatabaseError: file is not a database - Trying to open encrypted DB without key
```

## Connection Properties

### Check Connection Properties
```python
db = cinchdb.connect("myapp")
print(f"Local: {db.is_local}")         # Expected: True (local SQLite)
print(f"Database: {db.database_name}") # Expected: "myapp"
print(f"Branch: {db.branch_name}")     # Expected: "main" (default)
print(f"Tenant: {db.tenant_id}")       # Expected: "main" (default)

# Additional useful properties
print(f"Project: {db.project_dir}")    # Expected: Path to .cinchdb directory
print(f"Tables: {len(db.list_tables())}") # Expected: Number of tables

# Check connection health
try:
    db.query("SELECT 1")
    print("Connection healthy")
except Exception as e:
    print(f"Connection error: {e}")
```

### Database Operations
```python
db = cinchdb.connect("myapp")

# Use direct methods on CinchDB instance
results = db.query("SELECT * FROM users")
user = db.insert("users", {"name": "John", "email": "john@example.com"})
db.update("users", {"id": user["id"], "name": "John Smith"})
```

## Error Handling

### Connection Errors
```python
try:
    db = cinchdb.connect("myapp")
except FileNotFoundError as e:
    print(f"Project not found: {e}")
    print("Solution: Run 'cinch init' to create project")
except ValueError as e:
    if "does not exist" in str(e):
        print(f"Database/branch not found: {e}")
        print("Solution: Create with 'cinch database create' or 'cinch branch create'")
    else:
        print(f"Configuration error: {e}")
except sqlite3.DatabaseError as e:
    print(f"Database error: {e}")
    print("Possible causes:")
    print("- Corrupted database file")
    print("- Wrong encryption key")
    print("- Insufficient permissions")
except Exception as e:
    print(f"Unexpected error: {e}")
    print("Check logs for details")
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
   - Performance: New connection ~1ms, reused <0.1ms
   - Memory: Each connection ~1MB overhead

2. **Use Context Managers** - Ensures proper cleanup
   - Prevents "database locked" errors
   - Automatic rollback on exceptions

3. **Connection Pooling** - Automatic for local connections
   - Pool size: 5 connections per tenant
   - Idle timeout: 30 seconds

4. **Batch Operations** - Group related queries together
   - Example: Insert 100 records in batch = 10ms vs 100ms individually
   - Use transactions for consistency

5. **Performance Benchmarks**:
   - Connection creation: <1ms
   - Simple query: <1ms
   - Complex join: 5-20ms
   - Batch insert (100 records): ~10ms
   - Encrypted operations: +5% overhead

## Security

### Secure Storage
- Use `.env` files for local development configuration
- Never commit sensitive data to version control
- Keep database files secure in production

## Next Steps

- [Table Operations](tables.md) - Create and manage tables
- [Query Guide](queries.md) - Execute queries
- [Branch Operations](branches.md) - Work with branches
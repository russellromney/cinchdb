# Python SDK Overview

The CinchDB Python SDK provides a simple, type-safe interface for database operations.

## Installation

```bash
pip install cinchdb
```

## Quick Start

```python
import cinchdb
from cinchdb.models import Column

# Local connection
db = cinchdb.connect("myapp")

# Create a table
db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT"),
    Column(name="active", type="BOOLEAN", nullable=True)
])

# Insert data
user_id = db.insert("users", {
    "name": "Alice",
    "email": "alice@example.com",
    "active": True
})

# Query data
users = db.query("SELECT * FROM users WHERE active = ?", [True])
```

## Connection Types

### Local Connection
```python
# Auto-detect project
db = cinchdb.connect("myapp")

# Explicit project path
db = cinchdb.connect("myapp", project_dir="/path/to/project")

# With branch and tenant
db = cinchdb.connect("myapp", branch="feature", tenant="customer_a")
```

### Remote Connection
```python
# Connect to API
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key="your-api-key",
    database="myapp"
)

# With specific branch/tenant
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key="your-api-key", 
    database="myapp",
    branch="production",
    tenant="customer_b"
)
```

## Core Features

- **Type-safe operations** - Full type hints and IDE support
- **Automatic fields** - ID and timestamps handled automatically
- **Context switching** - Easy branch and tenant switching
- **Query builder** - Safe parameterized queries
- **Connection pooling** - Efficient resource usage

## Key Classes

### CinchDB
Main connection class for all operations:
- Schema management (tables, columns, views)
- Data operations (insert, update, delete, query)
- Branch and tenant switching

### Column
Defines table columns with:
- Name and type
- Nullable flag
- Validation rules

### Models
Generated model classes provide:
- Type-safe data access
- Automatic serialization
- IDE autocomplete

## Usage Patterns

### Context Manager
```python
with cinchdb.connect("myapp") as db:
    users = db.query("SELECT * FROM users")
    # Connection closed automatically
```

### Direct Connection
```python
db = cinchdb.connect("myapp")
try:
    users = db.query("SELECT * FROM users")
finally:
    db.close()
```

### Manager Access
For advanced operations:
```python
db = cinchdb.connect("myapp")

# Direct manager access (local only)
db.tables.create_table(...)
db.branches.create_branch(...)
db.merge.merge_branches(...)
```

## Error Handling

```python
try:
    db.create_table("users", columns)
except TableAlreadyExistsError:
    print("Table already exists")
except BranchNotFoundError:
    print("Branch doesn't exist")
except RemoteConnectionError:
    print("API connection failed")
```

## Best Practices

1. **Use context managers** - Ensures proper cleanup
2. **Parameterize queries** - Prevent SQL injection
3. **Handle errors** - Catch specific exceptions
4. **Type your data** - Use generated models
5. **Close connections** - Especially in long-running apps

## Next Steps

- [Connection Guide](connection.md) - Detailed connection options
- [Table Operations](tables.md) - Creating and managing tables
- [Query Guide](queries.md) - Writing effective queries
- [API Reference](api-reference.md) - Complete API documentation
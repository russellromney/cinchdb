# CinchDB

**Git-like SQLite database management with branching and multi-tenancy**

[![PyPI version](https://badge.fury.io/py/cinchdb.svg)](https://badge.fury.io/py/cinchdb)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)


NOTE: CinchDB is in early alpha. This is project to test out an idea. Do not use this in production.

CinchDB is for projects that need fast queries, isolated data per-tenant [or even per-user](https://turso.tech/blog/give-each-of-your-users-their-own-sqlite-database-b74445f4), and a branchable database that makes it easy to merge changes between branches.

Because it's so lightweight and its only dependencies are pydantic, requests, and Typer, it makes for a perfect local development database that can be controlled programmatically.

On a meta level: I made this because I wanted a database structure that I felt comfortable letting AI agents take full control over.

```bash
# Recommended: Install with uv (faster, better dependency resolution)
uv add cinchdb

# Or with pip
pip install cinchdb

# Initialize project
cinch init 

# Create and query tables
cinch table create users name:TEXT email:TEXT
cinch query "SELECT * FROM users"

# Git-like branching
cinch branch create feature
cinch branch switch feature
cinch table create products name:TEXT price:REAL
cinch branch merge-into-main feature

# Multi-tenant support
cinch tenant create customer_a
cinch query "SELECT * FROM users" --tenant customer_a

# Tenant encryption (bring your own keys)
cinch tenant create secure_customer --encrypt --key="your-secret-key"
cinch query "SELECT * FROM users" --tenant secure_customer --key="your-secret-key"

# Future: Remote connectivity planned for production deployment

# Autogenerate Python SDK from database
cinch codegen generate python cinchdb_models/
```

## What is CinchDB?

CinchDB combines SQLite with Git-like workflows for database schema management:

- **Branch schemas** like code - create feature branches, make changes, merge back
- **Multi-tenant isolation** - shared schema, isolated data per tenant
- **Automatic change tracking** - all schema changes tracked and mergeable
- **Safe structure changes** - change merges happen atomically with zero rollback risk (seriously)
- **Type-safe Python SDK** - Python SDK with full type safety
- **SDK generation from database schema** - Generate a typesafe SDK from your database models for CRUD operations
- **Built-in Key-Value Store** - Redis-like KV store with TTL, patterns, and atomic operations

## Installation

Requires Python 3.10+:

```bash
pip install cinchdb
```

## Quick Start

### CLI Usage

```bash
# Initialize project
cinch init my_app
cd my_app

# Create schema on feature branch
cinch branch create user-system
cinch table create users username:TEXT email:TEXT
cinch view create active_users "SELECT * FROM users WHERE created_at > datetime('now', '-30 days')"

# Merge to main
cinch branch merge-into-main user-system

# Multi-tenant operations
cinch tenant create customer_a
cinch tenant create customer_b
cinch query "SELECT COUNT(*) FROM users" --tenant customer_a
```

### Python SDK

```python
import cinchdb
from cinchdb.models import Column

# Local connection
db = cinchdb.connect("myapp")

# Create schema
db.create_table("posts", [
    Column(name="title", type="TEXT",nullable=False),
    Column(name="content", type="TEXT")
])

# Query data
results = db.query("SELECT * FROM posts WHERE title LIKE ?", ["%python%"])

# CRUD operations - single insert
post_id = db.insert("posts", {"title": "Hello World", "content": "First post"})

# Batch insert - multiple records at once
posts = db.insert("posts",
    {"title": "First", "content": "Content 1"},
    {"title": "Second", "content": "Content 2"},
    {"title": "Third", "content": "Content 3"}
)

# Or with a list using star expansion
post_list = [
    {"title": "Post A", "content": "Content A"},
    {"title": "Post B", "content": "Content B"}
]
results = db.insert("posts", *post_list)

db.update("posts", post_id, {"content": "Updated content"})

# Key-Value Store Operations (NEW)
# High-performance unstructured data storage with TTL support
db.kv.set("user:123", {"name": "Alice", "role": "admin"})
user = db.kv.get("user:123")  # Returns: {"name": "Alice", "role": "admin"}

# Set with TTL (expires in 1 hour)
db.kv.set("session:abc", {"user_id": 123}, ttl=3600)

# Atomic increment for counters
count = db.kv.increment("page:views", 1)  # Returns new value

# Batch operations
db.kv.mset({
    "config:debug": True,
    "config:timeout": 30,
    "config:api_url": "https://api.example.com"
})

configs = db.kv.mget(["config:debug", "config:timeout"])
# Returns: {"config:debug": True, "config:timeout": 30}

# Pattern matching (Redis-style)
user_keys = db.kv.keys("user:*")  # Returns all keys starting with "user:"
```


## Architecture

### Storage Architecture

CinchDB uses a **tenant-first storage model** where database and branch are organizational metadata concepts, while tenants represent the actual isolated data stores.

**Key-Value Store:** Each tenant has its own isolated KV store in the `__kv` system table, providing high-performance unstructured storage alongside relational data. KV data is excluded from CDC tracking and branch merging operations.

```
.cinchdb/
├── metadata.db                    # Organizational metadata
└── {database}-{branch}/           # Context root (e.g., main-main, prod-feature)
    ├── {shard}/                   # SHA256-based sharding (first 2 chars)
    │   ├── {tenant}.db            # Actual SQLite database
    │   └── {tenant}.db-wal        # WAL file
    └── ...
```

**Key Design Decisions:**
- **Tenant-first**: Each tenant gets its own SQLite database file
- **Flat hierarchy**: Database/branch form a single context root, avoiding deep nesting
- **Hash sharding**: Tenants are distributed across 256 shards using SHA256 for scalability
- **Lazy initialization**: Tenant databases are created on first access, not on tenant creation
- **WAL mode**: All databases use Write-Ahead Logging for better concurrency

This architecture enables:
- True multi-tenant isolation at the file system level
- Efficient branching without duplicating tenant data
- Simple backup/restore per tenant
- Horizontal scaling through sharding

### Components

- **Python SDK**: Core functionality for local development
- **CLI**: Full-featured command-line interface

## CinchDB API Reference

### Core Methods

#### Database Connection

```python
db = cinchdb.CinchDB(database="myapp", branch="main")
```

#### Query Execution

##### `query(sql: str, params: List = None) -> List[Dict]`
Execute a SQL query and return results.

```python
# Simple query
users = db.query("SELECT * FROM users WHERE age > ?", [18])
# Expected output: [{"id": 1, "name": "Alice", "age": 25}, ...]

# Query with no results
empty = db.query("SELECT * FROM users WHERE id = ?", [999])
# Expected output: []
```

**Common Errors:**
- `ValueError: Table 'users' does not exist` - Create the table first
- `sqlite3.OperationalError` - Check SQL syntax

#### Table Management

##### `create_table(name: str, columns: List[Column], indexes: List[Index] = None) -> Table`
Create a new table with specified columns.

```python
from cinchdb.models import Column

table = db.create_table(
    "products",
    columns=[
        Column(name="name", type="TEXT", nullable=False),
        Column(name="price", type="REAL", default=0.0)
    ]
)
# Expected: Table 'products' created in ~5ms
```

##### `get_table(name: str) -> Table`
Get table information and schema.

```python
table = db.get_table("users")
# Returns: Table object with columns, indexes, row count
```

##### `list_tables() -> List[Table]`
List all tables in the database.

```python
tables = db.list_tables()
# Expected output: [Table(name="users"), Table(name="products")]
```

#### Data Operations

##### `insert(table: str, *data: Dict) -> Dict | List[Dict]`
Insert one or more records into a table.

```python
# Single insert
user = db.insert("users", {"name": "Bob", "email": "bob@example.com"})
# Expected output: {"id": 1, "name": "Bob", "email": "bob@example.com"}

# Bulk insert
users = db.insert("users",
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Charlie", "email": "charlie@example.com"}
)
# Expected output: [{"id": 2, ...}, {"id": 3, ...}]
# Performance: ~1ms per record for small datasets
```

##### `update(table: str, record_id: str, data: Dict) -> Dict`
Update a record by ID.

```python
updated = db.update("users", "1", {"email": "newemail@example.com"})
# Expected output: {"id": 1, "name": "Bob", "email": "newemail@example.com"}
```

#### Key-Value Store Operations

CinchDB includes a high-performance key-value store with Redis-like API, perfect for caching, sessions, unstructured data, and potential TTL needs.

##### `kv.set(key: str, value: Any, ttl: Optional[int] = None) -> None`
Store a key-value pair with optional TTL (time-to-live in seconds).

```python
# Store various data types
db.kv.set("user:123", {"name": "Alice", "role": "admin"})
db.kv.set("count", 42)
db.kv.set("enabled", True)  # Booleans stored with proper type
db.kv.set("data", b"binary_data")  # Binary data supported

# Set with TTL (expires in 1 hour)
db.kv.set("session:abc", {"user_id": 123, "ip": "192.168.1.1"}, ttl=3600)
# Expected: Key stored, will auto-expire after 3600 seconds
```

**Common Error:**
```python
db.kv.set("", "value")  # ValueError: Key must be a non-empty string
db.kv.set("key@#$", "value")  # ValueError: Invalid characters in key
db.kv.set("k" * 256, "value")  # ValueError: Key exceeds 255 characters
```

##### `kv.get(key: str) -> Any`
Retrieve value by key. Returns None if key doesn't exist or is expired.

```python
user = db.kv.get("user:123")
# Expected output: {"name": "Alice", "role": "admin"}

bool_val = db.kv.get("enabled")
# Expected output: True (proper boolean, not 1)

expired = db.kv.get("expired_key")
# Expected output: None
```

##### `kv.mset(items: Dict[str, Any], ttl: Optional[int] = None) -> None`
Set multiple key-value pairs atomically.

```python
db.kv.mset({
    "config:debug": True,
    "config:timeout": 30,
    "config:api_url": "https://api.example.com",
    "config:features": ["auth", "api", "webhooks"]
})
# Expected: All keys set atomically in ~2ms
```

##### `kv.mget(keys: List[str]) -> Dict[str, Any]`
Get multiple values at once. Raises error if any key is missing.

```python
configs = db.kv.mget(["config:debug", "config:timeout", "config:api_url"])
# Expected output: {
#   "config:debug": True,
#   "config:timeout": 30,
#   "config:api_url": "https://api.example.com"
# }

# Missing key raises error
try:
    db.kv.mget(["exists", "missing"])
except ValueError as e:
    print(e)  # "Keys not found: ['missing']"
```

##### `kv.increment(key: str, amount: int = 1) -> int | float`
Atomically increment a numeric value. Creates key with initial value if it doesn't exist.

```python
views = db.kv.increment("page:views")  # Returns: 1 (created)
views = db.kv.increment("page:views", 5)  # Returns: 6

# Type safety - can't increment non-numeric values
db.kv.set("text_key", "hello")
try:
    db.kv.increment("text_key")
except ValueError:
    print("Cannot increment non-numeric value")
```

##### `kv.keys(pattern: str = '*') -> List[str]`
List keys matching a Redis-style glob pattern.

```python
# Store some keys
db.kv.set("user:1", {"name": "Alice"})
db.kv.set("user:2", {"name": "Bob"})
db.kv.set("session:abc", {"user": 1})

# Pattern matching
user_keys = db.kv.keys("user:*")
# Expected output: ["user:1", "user:2"]

all_keys = db.kv.keys()  # Returns all keys
# Expected output: ["session:abc", "user:1", "user:2"]
```

##### `kv.delete(*keys) -> int`
Delete one or more keys. Returns count of deleted keys.

```python
deleted = db.kv.delete("user:1")
# Expected output: 1 (number of keys deleted)

deleted = db.kv.delete("user:2", "user:3", "session:abc")
# Expected output: 2 (user:3 didn't exist)
```

##### `kv.expire(key: str, ttl: int) -> bool`
Set or update TTL for an existing key.

```python
db.kv.set("important", "data")
db.kv.expire("important", 86400)  # Expire in 24 hours
# Expected output: True (TTL set)

db.kv.expire("nonexistent", 60)
# Expected output: False (key doesn't exist)
```

##### `kv.ttl(key: str) -> Optional[int]`
Get remaining TTL in seconds. Returns None if no expiry, -1 if expired/missing.

```python
db.kv.set("temp", "data", ttl=300)
remaining = db.kv.ttl("temp")
# Expected output: 299 (or close to 300)

permanent = db.kv.ttl("no_expiry_key")
# Expected output: None
```

##### `kv.setnx(key: str, value: Any, ttl: Optional[int] = None) -> bool`
Set key only if it doesn't exist (SET if Not eXists).

```python
success = db.kv.setnx("lock:resource", "locked", ttl=30)
# Expected output: True (key was set)

success = db.kv.setnx("lock:resource", "locked_again")
# Expected output: False (key already exists)
```

**Performance Characteristics:**
- Single operations: < 1ms
- Batch operations: ~1ms per 100 items
- Pattern matching: O(n) where n = total keys
- Storage overhead: ~100 bytes per key

**Note on CDC:** KV operations are NOT tracked by Change Data Capture since the `__kv` table is a system table.

**Common Errors:**
- `ValueError: Record with ID '999' not found` - Check if record exists

##### `delete(table: str, *ids: str) -> int`
Delete records by ID.

```python
deleted_count = db.delete("users", "1", "2", "3")
# Expected output: 3 (number of deleted records)
```

##### `delete_where(table: str, **filters) -> int`
Delete records matching filters.

```python
deleted = db.delete_where("users", age__lt=18)
# Expected output: 5 (number of deleted records)
```

#### Branch Operations

##### `create_branch(name: str, source_branch: str = "main") -> Branch`
Create a new schema branch.

```python
branch = db.create_branch("feature/new-tables")
# Expected: Branch created in ~10ms
# Note: Does not copy tenant data, only schema
```

##### `list_branches() -> List[Branch]`
List all branches.

```python
branches = db.list_branches()
# Expected output: [Branch(name="main"), Branch(name="feature/new-tables")]
```

##### `merge_branches(source: str, target: str = "main") -> Dict`
Merge schema changes between branches.

```python
result = db.merge_branches("feature/new-tables", "main")
# Expected output: {
#   "status": "success",
#   "changes_applied": 3,
#   "conflicts": []
# }
```

**Common Errors:**
- `ConflictError: Table 'users' has conflicting changes` - Resolve conflicts manually

#### Tenant Management

##### `create_tenant(name: str, lazy: bool = True) -> Tenant`
Create a new tenant (isolated data store).

```python
tenant = db.create_tenant("customer_123")
# Expected: Tenant created (lazy mode - database created on first access)
# Performance: <1ms in lazy mode, ~10ms if immediate
```

##### `list_tenants() -> List[Tenant]`
List all tenants.

```python
tenants = db.list_tenants()
# Expected output: [Tenant(name="main"), Tenant(name="customer_123")]
```

##### `delete_tenant(name: str) -> None`
Delete a tenant and all its data.

```python
db.delete_tenant("customer_123")
# Warning: This permanently deletes all tenant data!
```

#### Index Management

##### `create_index(name: str, table: str, columns: List[str], unique: bool = False) -> Index`
Create an index for better query performance.

```python
index = db.create_index(
    "idx_users_email",
    table="users",
    columns=["email"],
    unique=True
)
# Expected: Index created in ~5ms
# Performance impact: 10-100x faster lookups on indexed columns
```

##### `list_indexes(table: str = None) -> List[Dict]`
List indexes, optionally filtered by table.

```python
indexes = db.list_indexes("users")
# Expected output: [
#   {"name": "idx_users_email", "unique": True, "columns": ["email"]}
# ]
```

#### Column Operations

##### `add_column(table: str, column: Column) -> None`
Add a new column to an existing table.

```python
from cinchdb.models import Column

db.add_column("users", Column(name="age", type="INTEGER", default=0))
# Expected: Column added to all tenants in ~10ms
```

##### `drop_column(table: str, column: str) -> None`
Remove a column from a table.

```python
db.drop_column("users", "age")
# Warning: This removes the column from all tenants!
```

##### `rename_column(table: str, old_name: str, new_name: str) -> None`
Rename a column.

```python
db.rename_column("users", "email", "email_address")
# Expected: Column renamed across all tenants
```

#### View Management

##### `create_view(name: str, sql: str) -> View`
Create a SQL view.

```python
view = db.create_view(
    "active_users",
    "SELECT * FROM users WHERE last_login > datetime('now', '-30 days')"
)
# Expected: View created in ~5ms
```

##### `list_views() -> List[View]`
List all views in the database.

```python
views = db.list_views()
# Expected output: [View(name="active_users")]
```

### Performance Guidelines

- **Query Performance**: Simple queries < 1ms, complex joins < 10ms
- **Insert Performance**: ~1ms per record for single inserts, ~0.1ms per record for bulk
- **Branch Operations**: Schema operations < 20ms
- **Tenant Creation**: Lazy mode < 1ms, immediate mode ~10ms
- **Analytics Overhead**: < 5% performance impact when enabled

### Troubleshooting Common Issues

#### "Table does not exist"
- Check current database/branch: `db.current_branch`
- List tables: `db.list_tables()`
- Ensure tenant is active: `db.current_tenant`

#### "Database is locked"
- CinchDB uses WAL mode to minimize locking
- Check for long-running transactions
- Ensure connections are properly closed

#### Performance Issues
- Create indexes on frequently queried columns
- Use `db.get_analytics_stats()` to identify slow queries
- Consider tenant sharding for large datasets

## Security

CinchDB uses standard SQLite security features:

- **WAL mode**: Better concurrency and crash recovery
- **Foreign key constraints**: Enforced data integrity  
- **File permissions**: Standard OS-level access control
- **Multi-tenant isolation**: Separate database files per tenant

For production deployments, consider additional security measures at the infrastructure level.

## Development

```bash
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb
make install-all
make test
```

## Future

CinchDB focuses on being a simple, reliable SQLite management layer. Future development will prioritize:

- Remote API server improvements
- Better CLI user experience  
- Performance optimizations
- Additional language SDKs (TypeScript, Go, etc.)
- Enhanced codegen features


## License

Apache 2.0 - see [LICENSE](LICENSE)

---

**CinchDB** - Database management as easy as version control

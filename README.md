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
```


## Architecture

### Storage Architecture

CinchDB uses a **tenant-first storage model** where database and branch are organizational metadata concepts, while tenants represent the actual isolated data stores:

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

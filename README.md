# CinchDB

**Git-like SQLite database management with branching and multi-tenancy**

```bash
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

# API server
cinch-server serve
```

## What is CinchDB?

CinchDB combines SQLite with Git-like workflows for database schema management:

- **Branch schemas** like code - create feature branches, make changes, merge back
- **Multi-tenant isolation** - shared schema, isolated data per tenant
- **Automatic change tracking** - all schema changes tracked and mergeable
- **Remote deployment** - FastAPI server with UUID authentication
- **Type-safe SDK** - Python and TypeScript SDKs with full type safety

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
    Column(name="title", type="TEXT"),
    Column(name="content", type="TEXT", nullable=True)
])

# Query data
results = db.query("SELECT * FROM posts WHERE title LIKE ?", ["%python%"])

# CRUD operations
post_id = db.insert("posts", {"title": "Hello World", "content": "First post"})
db.update("posts", post_id, {"content": "Updated content"})

# Switch contexts
dev_db = db.switch_branch("development")
tenant_db = db.switch_tenant("customer_a")
```

### Remote API

```python
# Connect to remote API
db = cinchdb.connect_api("https://api.example.com", "your-api-key", "myapp")

# Same interface as local
results = db.query("SELECT * FROM users")
user_id = db.insert("users", {"username": "alice", "email": "alice@example.com"})
```

## API Server

Start the server:

```bash
cinch-server serve --create-key
# Creates API key and starts server on http://localhost:8000
```

Interactive docs at `/docs`, health check at `/health`.

## Architecture

- **Python SDK**: Core functionality (local + remote)
- **CLI**: Full-featured command-line interface  
- **FastAPI Server**: REST API with authentication
- **TypeScript SDK**: Browser and Node.js client

## Development

```bash
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb
make install-all
make test
```

## License

Apache 2.0 - see [LICENSE](LICENSE)

---

**CinchDB** - Database management as easy as version control
# CinchDB

**Git-like SQLite database management with branching and multi-tenancy**

NOTE: CinchDB is in early alpha. This is project to test out an idea. Do not use this in production.

CinchDB is for projects that need fast queries, data isolated data per-tenant [or even per-user](https://turso.tech/blog/give-each-of-your-users-their-own-sqlite-database-b74445f4), and a branchable database that makes it easy to merge changes between branches.

On a meta level, I made this because I wanted a database structure that I felt comfortable letting AI agents take full control over, safely, and I didn't want to run my own Postgres instance somewhere or pay for it on e.g. Neon - I don't need hyperscaling, I just need super fast queries.

Because it's so lightweight and its only dependencies are pydantic, requests, and Typer, it makes for a perfect local development database that can be controlled programmatically.


```bash
uv pip install cinchdb

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

# Connect to remote CinchDB instance
cinch remote add production https://your-cinchdb-server.com your-api-key
cinch remote use production

# Autogenerate Python SDK from database
cinch codegen generate python cinchdb_models/
```

## What is CinchDB?

CinchDB combines SQLite with Git-like workflows for database schema management:

- **Branch schemas** like code - create feature branches, make changes, merge back
- **Multi-tenant isolation** - shared schema, isolated data per tenant
- **Automatic change tracking** - all schema changes tracked and mergeable
- **Safe structure changes** - change merges happen atomically with zero rollback risk (seriously)
- **Remote connectivity** - Connect to hosted CinchDB instances
- **Type-safe SDK** - Python and TypeScript SDKs with full type safety
- **Remote-capable** - CLI and SDK can connect to remote instances
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

# CRUD operations
post_id = db.insert("posts", {"title": "Hello World", "content": "First post"})
db.update("posts", post_id, {"content": "Updated content"})
```

### Remote Connection

```python
# Connect to remote instance
db = cinchdb.connect("myapp", url="https://your-cinchdb-server.com", api_key="your-api-key")

# Same interface as local
results = db.query("SELECT * FROM users")
user_id = db.insert("users", {"username": "alice", "email": "alice@example.com"})
```

## Remote Access

Connect to a remote CinchDB instance:

```bash
cinch remote add production https://your-cinchdb-server.com your-api-key
cinch remote use production
# Now all commands will use the remote instance
```

Interactive docs at `/docs`, health check at `/health`.

## Architecture

- **Python SDK**: Core functionality (local + remote)
- **CLI**: Full-featured command-line interface  
- **Remote Access**: Connect to hosted CinchDB instances
- **TypeScript SDK**: Browser and Node.js client

## Development

```bash
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb
make install-all
make test
```

## Future

Though probably not, perhaps I'll evolve it into something bigger and more full-featured, with things like
- data backups
- replication to S3
- audit access
- SaaS-like dynamics
- multi-project hosting
- auth proxying
- leader-follower abilities for edge deployment


## License

Apache 2.0 - see [LICENSE](LICENSE)

---

**CinchDB** - Database management as easy as version control

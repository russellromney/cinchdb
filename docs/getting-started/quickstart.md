# Quick Start

Get up and running with CinchDB in 5 minutes.

> ⚠️ **NOTE**: CinchDB is in early alpha. This is a project to test out an idea. Do not use this in production.

## Initialize Your First Project

```bash
# Create a new CinchDB project
cinch init myapp
cd myapp

# List databases (shows 'main' by default)
cinch db list
```

## Create Your First Table

```bash
# Create a users table
cinch table create users name:TEXT email:TEXT age:INTEGER

# View the table structure
cinch table info users
```

Every table automatically includes:
- `id` - UUID primary key
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

## Insert and Query Data

```bash
# Insert data
cinch data insert users --data '{"name": "Alice", "email": "alice@example.com", "age": 30}'

# Query data
cinch query "SELECT * FROM users"
```

## Use the Key-Value Store

CinchDB includes a built-in Redis-like KV store for high-performance caching and session management:

```bash
# Set a session with auto-expiration
cinch kv set session:123 '{"user_id": 1, "ip": "192.168.1.1"}' --ttl 3600

# Get the session
cinch kv get session:123

# Use atomic counters
cinch kv increment page:views
cinch kv increment api:calls --by 5

# List all sessions
cinch kv keys "session:*"
```

## Work with Branches

```bash
# Create a feature branch
cinch branch create add-products

# Switch to the new branch
cinch branch switch add-products

# Add a products table
cinch table create products name:TEXT price:REAL category:TEXT

# Switch back to main
cinch branch switch main

# Merge changes
cinch branch merge add-products main
```

## Multi-Tenant Operations

```bash
# Create a new tenant
cinch tenant create customer_a

# Query tenant-specific data
cinch query "SELECT * FROM users" --tenant customer_a

# Insert data for a specific tenant
cinch data insert users --tenant customer_a --data '{"name": "Bob", "email": "bob@customer-a.com"}'
```

## Python SDK Usage

```python
import cinchdb
from cinchdb.models import Column

# Connect to your database
db = cinchdb.connect("myapp")

# Create a table
db.create_table("posts", [
    Column(name="title", type="TEXT"),
    Column(name="content", type="TEXT"),
    Column(name="published", type="BOOLEAN", nullable=True)
])

# Insert data
post = db.insert("posts", {
    "title": "Hello CinchDB",
    "content": "This is my first post",
    "published": True
})

# Query data
posts = db.query("SELECT * FROM posts WHERE published = ?", [True])
for post in posts:
    print(f"{post['title']}: {post['content']}")

# Use the built-in KV store for caching and sessions
db.kv.set("session:user123", {"user_id": 123, "role": "admin"}, ttl=3600)
db.kv.set("cache:posts", posts, ttl=300)  # Cache query results
session = db.kv.get("session:user123")
db.kv.increment("post:views:1")  # Atomic counter

# Work with branches
dev_db = cinchdb.connect("myblog", branch="development")
dev_db.create_table("comments", [
    Column(name="post_id", type="TEXT"),
    Column(name="content", type="TEXT")
])
```

## Generate SDK from Your Schema

```bash
# After creating tables, generate a type-safe SDK
cinch codegen generate python models/

# Use the generated SDK
```

```python
from models import cinch_models

# Connect and use your models
db = cinchdb.connect("myapp")
models = cinch_models(db)

# Type-safe CRUD operations
user = models.User.create(name="Alice", email="alice@example.com", age=30)
all_users = models.User.get_all()
models.User.update(user["id"], age=31)
```


## Next Steps

- [Core Concepts](concepts.md) - Understand CinchDB's architecture
- [CLI Reference](../cli/index.md) - Complete command documentation
- [Python SDK](../python-sdk/index.md) - Full SDK documentation
- [Code Generation](../cli/codegen.md) - Generate SDKs from your schema
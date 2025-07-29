# Quick Start

Get up and running with CinchDB in 5 minutes.

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
cinch query "INSERT INTO users (name, email, age) VALUES ('Alice', 'alice@example.com', 30)"

# Query data
cinch query "SELECT * FROM users"
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
cinch branch merge add-products
```

## Multi-Tenant Operations

```bash
# Create a new tenant
cinch tenant create customer_a

# Query tenant-specific data
cinch query "SELECT * FROM users" --tenant customer_a

# Insert data for a specific tenant
cinch query "INSERT INTO users (name, email) VALUES ('Bob', 'bob@customer-a.com')" --tenant customer_a
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

# Work with branches
dev_db = db.switch_branch("development")
dev_db.create_table("comments", [
    Column(name="post_id", type="TEXT"),
    Column(name="content", type="TEXT")
])
```

## Remote API Access

```bash
# Start the API server
cinch-server serve --create-key
# Note the API key that's generated

# Configure remote access
cinch remote add production --url http://localhost:8000 --key YOUR_API_KEY
cinch remote use production

# Now all commands work remotely
cinch query "SELECT * FROM users"
```

## Next Steps

- [Core Concepts](concepts.md) - Understand CinchDB's architecture
- [CLI Reference](../cli/index.md) - Complete command documentation
- [Python SDK](../python-sdk/index.md) - Full SDK documentation
# CinchDB

A Git-like SQLite database management system with branching and multi-tenancy.

## Features

- **Git-like Branching**: Create, merge, and switch between database branches
- **Multi-tenancy**: Isolated data environments within the same database
- **Change Tracking**: Track schema and data changes across branches
- **Python API & CLI**: Full-featured command-line interface and Python API
- **Remote Access**: Connect to remote CinchDB instances via API

## Installation

```bash
pip install cinchdb
```

## Quick Start

### CLI Usage

Initialize a new CinchDB project:

```bash
cinch init
```

Create and switch to a new branch:

```bash
cinch branch create feature-branch
cinch branch switch feature-branch
```

Create a table:

```bash
cinch table create users "name:TEXT:NOT NULL" "email:TEXT:UNIQUE"
```

Query data:

```bash
cinch query "SELECT * FROM users"
```

### Python API

```python
from cinchdb import connect

# Connect to a local database
db = connect(database="myapp", branch="main")

# Execute queries with validation (only SELECT, INSERT, UPDATE, DELETE allowed)
users = db.query("SELECT * FROM users WHERE active = ?", [True])

# Create tables
db.create_table("products", [
    {"name": "name", "type": "TEXT", "nullable": False},
    {"name": "price", "type": "REAL", "nullable": False}
])

# Switch branches
db.switch_branch("feature-branch")
```

### Remote Connection

```python
from cinchdb import connect_api

# Connect to a remote CinchDB instance
db = connect_api(
    api_url="https://api.example.com",
    api_key="your-api-key",
    database="myapp",
    branch="main"
)

# Use the same interface as local connections
results = db.query("SELECT * FROM users")
```

## CLI Commands

- `cinch init` - Initialize a new project
- `cinch branch` - Manage branches (create, list, switch, merge)
- `cinch table` - Manage tables (create, list, drop)
- `cinch query` - Execute SQL queries
- `cinch tenant` - Manage tenants
- `cinch remote` - Manage remote connections

## Documentation

For more detailed documentation, visit: https://github.com/yourusername/cinchdb

## License

MIT License
# CLI Reference

The CinchDB CLI provides complete control over your databases from the command line.

## Installation

The CLI is installed automatically with CinchDB:

```bash
pip install cinchdb
```

## Basic Usage

```bash
cinch [OPTIONS] COMMAND [ARGS]...
```

## Global Options

Options available for all commands:

- `--help` - Show help message
- `--version` - Show CinchDB version

## Command Groups

### Project Management
- [`cinch init`](project.md#init) - Initialize a new project

### Database Operations
- [`cinch db`](database.md) - Manage databases

### Branch Management
- [`cinch branch`](branch.md) - Work with branches

### Schema Management
- [`cinch table`](table.md) - Manage tables
- [`cinch column`](column.md) - Manage columns
- [`cinch view`](view.md) - Manage views

### Data Operations
- [`cinch query`](query.md) - Execute SQL queries

### Multi-Tenancy
- [`cinch tenant`](tenant.md) - Manage tenants

### Remote Access
- [`cinch remote`](remote.md) - Configure remote connections

### Code Generation
- [`cinch codegen`](codegen.md) - Generate model code

## Common Workflows

### Local Development
```bash
# Initialize project
cinch init myapp
cd myapp

# Create schema
cinch table create users name:TEXT email:TEXT
cinch table create posts user_id:TEXT title:TEXT content:TEXT

# Work with data
cinch query "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')"
cinch query "SELECT * FROM users"
```

### Feature Development
```bash
# Create feature branch
cinch branch create feature/comments

# Make changes
cinch table create comments post_id:TEXT content:TEXT

# Test changes
cinch query "INSERT INTO comments (post_id, content) VALUES ('123', 'Great post!')"

# Merge to main
cinch branch switch main
cinch branch merge feature/comments
```

### Multi-Tenant Setup
```bash
# Create tenants
cinch tenant create acme_corp
cinch tenant create wayne_enterprises

# Work with tenant data
cinch query "SELECT COUNT(*) FROM users" --tenant acme_corp
```

### Remote Management
```bash
# Configure remote
cinch remote add production --url https://api.example.com --key YOUR_KEY
cinch remote use production

# All commands now work remotely
cinch table list
cinch query "SELECT * FROM users"
```

## Connection Modes

Commands work in two modes:

### Local Mode (default)
- Direct file access
- No network required
- Full control

### Remote Mode
- API-based access
- Requires authentication
- Use `--local` to force local mode
- Use `--remote <alias>` to use specific remote

## Output Formats

Many commands support different output formats:

```bash
# Table format (default)
cinch table list

# JSON format
cinch table list --format json

# CSV format (query command)
cinch query "SELECT * FROM users" --format csv
```

## Next Steps

- [Database Commands](database.md)
- [Branch Commands](branch.md)
- [Table Commands](table.md)
- [Query Command](query.md)
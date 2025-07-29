# CinchDB

**Git-like SQLite database management with branching and multi-tenancy**

CinchDB brings version control workflows to database schema management. Create feature branches, make changes, and merge them back - just like code.

## Key Features

- **Schema Branching** - Create isolated branches for schema changes
- **Multi-Tenant Architecture** - Shared schema with isolated tenant data
- **Automatic Change Tracking** - Every schema modification is tracked
- **Remote API Access** - Deploy with FastAPI server and UUID authentication
- **Type-Safe SDKs** - Python and TypeScript clients with full type safety

## Quick Example

```bash
# Initialize a new project
cinch init myapp

# Create a feature branch
cinch branch create add-users
cinch branch switch add-users

# Make schema changes
cinch table create users name:TEXT email:TEXT
cinch column add users avatar_url:TEXT

# Merge back to main
cinch branch switch main
cinch branch merge add-users
```

## Use Cases

CinchDB is ideal for:

- **SaaS Applications** - Manage multi-tenant data with ease
- **Development Workflows** - Test schema changes in isolation
- **Feature Development** - Branch schemas alongside code
- **Data Migrations** - Track and apply changes systematically

## Getting Started

Install CinchDB with pip:

```bash
pip install cinchdb
```

Then check out our [Quick Start Guide](getting-started/quickstart.md) to build your first project.

## Architecture Overview

CinchDB consists of:

- **Python SDK** - Core functionality for local and remote operations
- **CLI** - Command-line interface for all operations
- **API Server** - FastAPI server for remote access
- **TypeScript SDK** - Client library for JavaScript applications

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Core Concepts](getting-started/concepts.md)
- [CLI Reference](cli/index.md)
- [Python SDK Documentation](python-sdk/index.md)
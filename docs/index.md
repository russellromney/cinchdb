# CinchDB

**Git-like SQLite database management with branching and multi-tenancy**

> ⚠️ **NOTE**: CinchDB is in early alpha. This is a project to test out an idea. Do not use this in production.

CinchDB brings version control workflows to database schema management. Create feature branches, make changes, and merge them back - just like code.

## Key Features

- **Schema Branching** - Create isolated branches for schema changes
- **Multi-Tenant Architecture** - Shared schema with isolated tenant data
- **Automatic Change Tracking** - Every schema modification is tracked
- **Safe Structure Changes** - Schema merges happen atomically with zero rollback risk
- **Remote API Access** - Deploy with FastAPI server and UUID authentication
- **Type-Safe SDKs** - Python and TypeScript clients with full type safety
- **SDK Generation** - Auto-generate type-safe Python or Typescript SDK from your database schema

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

# Generate SDK from schema
cinch codegen generate python models/
```

## Use Cases

CinchDB is ideal for:

- **Per-User/Per-Tenant Databases** - Isolate data completely between tenants or even [give each user their own database](https://turso.tech/blog/give-each-of-your-users-their-own-sqlite-database-b74445f4)
- **AI Agent Database Control** - Let AI agents safely manage database structure without risk
- **SaaS Applications** - Ultra-fast queries with data size divided by number of tenants
- **Development Workflows** - Test schema changes in isolation
- **Feature Development** - Branch schemas alongside code with zero rollback risk
- **Lightweight Deployments** - Minimal dependencies make it perfect for small VMs

## Getting Started

Install CinchDB with pip:

```bash
pip install cinchdb
```

Then check out our [Quick Start Guide](getting-started/quickstart.md) to build your first project.

## Why CinchDB?

I built CinchDB for a specific need: a database structure that AI agents could safely control without risk. It's designed to be:

- **Lightweight** - Only depends on FastAPI, Pydantic, Requests, and Typer
- **Cheap to Deploy** - Runs great on small VMs like [Fly.io](https://fly.io)
- **Remote-First** - No SSH needed, just store an API key in your projects
- **Fast** - Queries are super fast due to per-tenant data isolation

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
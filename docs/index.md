# CinchDB

**Git-like SQLite with schema branching and multi-tenancy**

> ⚠️ **Early Alpha**: Test project. Don't use in production.

Branch database schemas like code. Make changes, test them, merge safely.

Generate type-safe SDKs in Python/Typescript from your database schema and use in your codebase
instead of using an ORM schema as a source of truth and running migrations. 

## Core Features

- **Multi-Tenancy** - Shared schema, isolated data
- **Schema Branching** - Branch schemas like Git repos
- **Change Tracking** - Every modification tracked
- **Safe Merges** - Atomic operations, no rollback risk (seriously)
- **Type-Safe Python SDK** - Full type safety with code generation
- **Key-Value Store** - Redis-like API built-in

## Quick Start

```bash
# Initialize project
cinch init myapp && cd myapp

# Create feature branch  
cinch branch create add-users --switch

# Make schema changes
cinch table create users name:TEXT email:TEXT
cinch column add users avatar_url:TEXT

# Merge to main
cinch branch switch main
cinch branch merge add-users main

# Generate type-safe SDK
cinch codegen generate python models/

# Use Key-Value store (Redis-like)
cinch kv set "session:123" '{"user_id": 42}'
cinch kv get "session:123"
```

## Why CinchDB?

**Problem**: Database schema changes are risky and hard to test in isolation.

**Solution**: Branch schemas like code. Test changes safely, merge atomically.

### Perfect For
- **SaaS apps** - Per-tenant data isolation  
- **AI agents** - Safe schema control without rollback risk
- **Development** - Test schema changes in branches
- **Small deployments** - Minimal dependencies, runs anywhere

### Performance Benefits  
- **Ultra-fast queries** - Data size ÷ tenant count
- **Small footprint** - Only depends on Pydantic, Requests, Typer
- **Self hosting** - Runs great on small VMs

## Installation

```bash
# Recommended: Install with uv (faster)
uv add cinchdb

# Or with pip
pip install cinchdb
```

## What's Next

- **New to CinchDB?** → [Quick Start Guide](getting-started/quickstart.md)
- **How it works?** → [Core Concepts](getting-started/concepts.md)
- **Why not just SQLite?** → [Constraints](concepts/constraints.md)
- **Need commands?** → [CLI Reference](cli/index.md)
- **Want to code?** → [Python SDK](python-sdk/index.md)
- **Key-Value Store?** → [KV CLI](cli/kv.md) | [KV Python](python-sdk/kv-store.md)
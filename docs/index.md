# CinchDB

**Git-like SQLite with schema branching and multi-tenancy**

> ⚠️ **Early Alpha**: Test project. Don't use in production.

Branch database schemas like code. Make changes, test them, merge safely.

## Core Features

- **Schema Branching** - Branch schemas like Git repos
- **Multi-Tenancy** - Shared schema, isolated data  
- **Change Tracking** - Every modification tracked
- **Safe Merges** - Atomic operations, no rollback risk
- **Type-Safe Python SDK** - Full type safety with code generation

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
cinch branch merge-into-main add-users

# Generate type-safe SDK
cinch codegen generate python models/
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
- **Cheap hosting** - Runs great on small VMs

## Installation

```bash
# Recommended: Install with uv (faster)
uv add cinchdb

# Or with pip
pip install cinchdb
```

## What's Next

- **New to CinchDB?** → [Quick Start Guide](getting-started/quickstart.md)
- **Need commands?** → [CLI Reference](cli/index.md) 
- **Want to code?** → [Python SDK](python-sdk/index.md)
- **How it works?** → [Core Concepts](getting-started/concepts.md)
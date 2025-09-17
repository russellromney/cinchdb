# Constraints and Design Choices

CinchDB is a **very opinionated interface** to managing many SQLite databases (tenants) across many databases and branches.
It is intended to be very safe for any developer (even AI) to use and make broad changes.

As such it makes certain design decisions that constrain what the user can do.

## Core Philosophy: Database as Source of Truth, Git-like Flow for Changes

Unlike traditional development where code defines the database structure through ORMs and migrations, CinchDB inverts this relationship:

**Traditional**: Code → Migrations → Database
**CinchDB**: Database → Codegen → Type-Safe Code

This inversion is important because it means the database schema is always the source of truth. Your code is generated from what actually exists in the database, not the other way around. This eliminates an entire category of bugs where your code thinks the database looks one way but it actually looks different.

CinchDB modifies SQLite's default behavior to create a safer, more predictable development experience. 

## Schema Constraints

### UUID Primary Keys (Not AUTOINCREMENT)

**What**: Every table gets a UUID4 TEXT primary key named `id`
```sql
id TEXT PRIMARY KEY,  -- UUID4, not AUTOINCREMENT
```

AUTOINCREMENT exposes information about your data (like row counts and creation order) and makes it easy to enumerate through your records. UUIDs prevent ID collisions across different databases and tenants, and they work better in distributed systems.

### Mandatory Timestamps

**What**: Every table automatically gets:
```sql
created_at TEXT NOT NULL,  -- ISO timestamp on INSERT
updated_at TEXT             -- ISO timestamp on UPDATE
```

**Why**: Complete audit trail, debugging support, consistent data model

### Protected Column Names

**What**: Cannot create columns named `id`, `created_at`, `updated_at`

**Why**: Ensures system columns are always present and consistent

## SQL Restrictions

### Limited SQL Operations

CinchDB purposefully exposes a limited set of SQLite data operations:

**Allowed**: `SELECT, INSERT, UPDATE, DELETE`

**Blocked**: All schema changes and admin operations
- `CREATE, ALTER, DROP, TRUNCATE`
- `PRAGMA, VACUUM, REINDEX, ATTACH`
- Multiple statements (prevents injection)

**Why**: Schema changes go through CinchDB's [branch system](branching.md); admin operations are managed by CinchDB

### Query Method Separation

**What**: Strict API routing
- `db.query()` - Only SELECT statements
- `db.insert()`, `db.update()`, `db.delete()` - Structured data operations

**Why**: Prevents accidental data modification, enables better analytics

### System Table Protection

**What**: Cannot access tables starting with `__` or `sqlite_`

**Why**: Protects CinchDB metadata and SQLite system integrity (see [Security](security.md) for details)

## Connection and Configuration

### SQLite Settings

**What**: CinchDB chooses very specific settings and doesn't provide an interface to change them.
```sql
PRAGMA journal_mode = WAL
PRAGMA foreign_keys = ON
PRAGMA synchronous = NORMAL
```

**Why**: Ensures consistency and data integrity in CinchDB's [multi-tenant architecture](multi-tenancy.md)

### No Direct Database Access

**What**: Users never get raw SQLite connections or file access

**Why**: Enables CinchDB's [branching system](branching.md), [multi-tenancy](multi-tenancy.md), and [security](security.md) controls

## Naming Rules

### Strict Naming Conventions

**Requirements**:
- Lowercase only (`a-z`, `0-9`, `_`)
- Table names must start with letter
- 63 character limit (PostgreSQL compatibility)
- No path traversal characters (`..`, `/`, `\`)

**Why**: Security (SQL injection prevention), cross-platform compatibility, future migration readiness

## Multi-Tenant Architecture

### Tenant Isolation

**What**: Each tenant gets its own SQLite file stored in efficient shard directories.
```
.cinchdb/
└── mydb-main/
    ├── ab/tenant1.db
    ├── cd/tenant2.db
    └── ef/tenant3.db
```

**Why**: True data isolation means each tenant's queries only touch their own data, improving performance and security. The hash-based sharding prevents filesystem issues when you have thousands of tenants.

### No Cross-Tenant Queries

**What**: Cannot query across tenants in regular operations

**Why**: Maintains tenant isolation, prevents data leaks

## Development Model Constraints

### Database-First Development (Not ORM-First)

**Traditional Flow (What CinchDB doesn't do):**
```
ORM Models → Migrations → Database Schema
```

**CinchDB Flow (Database as Source of Truth):**
```
Database Branch → Schema Changes → Codegen → Type-Safe SDK
```

CinchDB reverses the traditional development flow. Instead of defining models in code and then migrating the database, you make changes directly to the database schema and generate type-safe code from it. This means there are no ORM model definitions that can drift from the actual schema and no migration files to manage.

### Codegen-Driven SDK

The SDK is always generated from your database schema, never hand-written. After making schema changes, you run `cinch codegen generate python models/` to create type-safe Python models that exactly match your database structure. This ensures your code always knows the exact types and constraints of your data.

### Git-Like Workflow Required

Database changes follow the same patterns as version control. You create a feature branch in the database, make schema changes there, generate a new SDK from that branch's schema, test everything in isolation, then merge the database branch which atomically updates the schema. Finally you commit the regenerated SDK to Git. This keeps both database and code changes synchronized through parallel branch and merge workflows.

## Branch-Based Schema Management

### No Direct Schema Changes

**What**: No interface is provided to use `ALTER TABLE, CREATE TABLE` directly

**Why**: Schema changes go through branch/merge workflow for safety:
1. Create branch
2. Make changes
3. Test in isolation
4. Merge to main (atomic)

### Atomic Merge Operations

Schema merges are atomic operations that either completely succeed or completely fail. There's no possibility of ending up with a partially-merged schema or having to manually resolve conflicts in the database itself.

## Comparison to Traditional Approaches

### vs Raw SQLite

| Feature | SQLite | CinchDB |
|---------|--------|---------|
| Primary Keys | Any type | UUID4 TEXT only |
| Schema Changes | Direct DDL | Branch/merge only |
| SQL Access | Full API | Limited DML |
| Connections | Direct | Managed pool |
| File Access | Direct .db files | API only |
| Multi-tenancy | None | Built-in |

### vs ORM-Based Systems

| Aspect | Traditional ORM | CinchDB |
|--------|----------------|----------|
| Source of Truth | ORM Models | Database Schema |
| Schema Changes | Migration Files | Branch & Merge |
| Type Safety | Runtime Validation | Compile-Time (via Codegen) |
| Multi-tenancy | Application Logic | File-Level Isolation |
| Rollback | Migration Reversal | Branch Switch |
| Testing Changes | Staging Database | Feature Branches |

## Why These Constraints?

**Safety**: Prevents common SQLite footguns and dangerous operations

**Security**: SQL injection protection, no information disclosure through IDs

**Multi-tenancy**: True data isolation without application complexity

**Consistency**: Standardized schema patterns across all CinchDB projects

**Team Collaboration**: [Git-like workflows](branching.md) for database changes

**AI-Ready**: Safe enough for automated tools to manage database structure

**Zero Drift**: Generated code always matches database reality through [codegen](../cli/codegen.md)

**Future-proofing**: PostgreSQL-compatible naming for potential migration

## Next Steps

- [Naming Conventions](naming-conventions.md) - Detailed naming rules
- [Schema Branching](branching.md) - How branch workflows work
- [Multi-Tenancy](multi-tenancy.md) - Deep dive into tenant isolation
- [Codegen](../cli/codegen.md) - Generate type-safe SDKs from your schema
- [Change Tracking](change-tracking.md) - Automatic audit trails
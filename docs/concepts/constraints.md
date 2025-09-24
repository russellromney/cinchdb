# Constraints and Design Choices

CinchDB is a **very opinionated interface** to managing many SQLite databases (tenants) across many databases and branches.
It is intended to be very safe for any developer (even AI) to use and make broad changes.

As such it makes certain design decisions that constrain what the user can do.

## Core Philosophy: Database as Source of Truth, Git-like Flow for Changes

Unlike traditional development where code defines the database structure through ORMs and migrations, CinchDB inverts this relationship:

**Traditional**: Code → Migrations → Database
**CinchDB**: Database → Codegen → Type-Safe Code

This fundamental inversion drives most of CinchDB's constraints. The database isn't just storage - it's the authoritative source from which all code is generated. 

**Why CinchDB modifies SQLite's default behavior**

CinchDB constrains in some key ways SQLite to create a safer, more consistent database experience. 
It incorporates some best practices and makes some very opinionated design choices. 

## Schema Constraints

### UUID Primary Keys (Not AUTOINCREMENT)

**What**: Every table gets a UUID4 TEXT primary key named `id`
```sql
id TEXT PRIMARY KEY,  -- UUID4, not AUTOINCREMENT
```

**Why not AUTOINCREMENT?**
- **Security**: AUTOINCREMENT reveals creation order and row counts
- **No enumeration attacks**: Can't guess valid IDs by incrementing
- **Multi-tenant safe**: No ID collisions between tenants
- **Distributed-friendly**: UUIDs work across multiple databases

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
- `db.insert()`, `db.update()`, `db.delete()` - Structured data operations with parameters

**Why**: Prevents accidental data modification 

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

**Why**: True data isolation, performance (queries only scan relevant data), horizontal scaling without hitting system file limits

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

**What**: CinchDB reverses the traditional development flow
- Database schema is the single source of truth
- Code is generated FROM the database, not vice versa
- No ORM model definitions that drift from actual schema
- No migration files to manage or coordinate

**Why**:
- **Zero drift**: Generated code always matches actual database schema
- **Branch safety**: Test schema changes in isolation before merging
- **AI-friendly**: Safe for automated tools to modify database directly
- **Team coordination**: Changes merge atomically in both database and code

### Codegen-Driven SDK

**What**: SDK is always generated, never hand-written
```bash
# After schema changes:
cinch codegen generate python models/
# This creates type-safe Python models matching your exact schema
```

**Why**: Eliminates the entire class of type mismatches between code and database

### Git-Like Workflow Required

**What**: Database changes follow version control patterns
1. Create feature branch in database
2. Make schema changes on branch
3. Generate new SDK from branch schema
4. Test changes in isolation
5. Merge database branch (atomically updates schema)
6. Commit generated SDK to Git

**Why**: Database and code changes are coordinated through parallel workflows

## Branch-Based Schema Management

### No Direct Schema Changes

**What**: No interface is provided to use `ALTER TABLE, CREATE TABLE` directly

**Why**: Schema changes go through branch/merge workflow for safety:
1. Create branch
2. Make changes
3. Test in isolation
4. Merge to main (atomic)

### Atomic Merge Operations

**What**: Schema merges are atomic - either fully succeed or fully fail

**Why**: No partial states, no corrupted schemas, no manual conflict resolution in database

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
# Active Context - CinchDB Development

## Current Session State
- **Date**: 2025-07-24
- **Phase**: Phase 2 - Branch and Tenant Management (In Progress)
- **Current Focus**: BranchManager and TenantManager complete, moving to change tracking

## Completed Tasks
1. ✅ Initialized Python project with uv
2. ✅ Created Makefile for common development tasks
3. ✅ Read and analyzed DESIGN.md
4. ✅ Created comprehensive IMPLEMENTATION_PLAN.md
5. ✅ Restructured as monorepo with Python, TypeScript, Frontend, and Docs
6. ✅ Updated Makefile with monorepo commands
7. ✅ Added repository structure to implementation plan
8. ✅ Implemented Config class for .cinchdb/config.toml
   - Simple TOML-based configuration
   - Project initialization with default structure
   - Full test coverage
9. ✅ Defined core Pydantic models
   - CinchDBTableModel for entities stored as tables (only Change model)
   - CinchDBBaseModel for metadata/config entities
   - Project, Database, Branch, Tenant models with deletion protection
   - Table/Column models with automatic default fields
   - Change tracking model with generic entity support
   - View model for SQL views
   - All models tested and working
10. ✅ Created directory structure management utilities
   - Path utilities for project/database/branch/tenant paths
   - Functions to list databases, branches, tenants
   - Project root finder
   - All utilities tested
11. ✅ Implemented SQLite connection with WAL mode
   - DatabaseConnection class with WAL mode configuration
   - Transaction support with automatic rollback
   - Row factory for dict-like access
   - Connection pooling for multi-tenant scenarios
   - All connection features tested
12. ✅ Changed CLI command from "cinchdb" to "cinch"
   - Updated pyproject.toml scripts
   - Added `make install-dev` command
   - Basic CLI with init and version commands
13. ✅ Implemented BranchManager class (Phase 2.1)
   - Create branches by copying from source
   - Delete branches (with main branch protection)
   - List branches with metadata
   - Switch active branch in config
   - Branch metadata management
   - Full test coverage (12 tests)
14. ✅ Implemented TenantManager class (Phase 2.2)
   - Create tenants with schema copying
   - Delete tenants (with main tenant protection)
   - Copy tenants with data
   - Rename tenants
   - List tenants
   - Get tenant database connections
   - Full test coverage (13 tests)

## Monorepo Structure
```
cinchdb/
├── src/cinchdb/         # Python package (SDK + CLI + API)
│   ├── models/          # Pydantic models
│   ├── core/            # Core functionality
│   ├── managers/        # Business logic
│   ├── cli/             # CLI implementation
│   │   └── commands/    # CLI commands
│   ├── api/             # FastAPI server
│   │   └── routers/     # API routes
│   └── codegen/         # Code generation
├── sdk/typescript/      # TypeScript SDK
├── frontend/            # NextJS app
├── docs/                # Documentation site
├── tests/               # Test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── examples/
├── scripts/
├── pyproject.toml
├── Makefile
└── README.md
```

## Phase 1 Implementation Approach
Following "Start Simple" principle:
1. **Config Class** - Simple TOML reader/writer for .cinchdb/config.toml
2. **Basic Models** - Minimal Pydantic models with essential fields only
3. **Path Utils** - Simple functions for directory management
4. **SQLite Setup** - Basic connection with WAL mode enabled

## Key Design Decisions
- Using SQLite in WAL mode with specific configurations
- Hierarchical structure: Project → Database → Branch → Tenant
- Git-like branching for database schemas
- Automatic id, created_at, updated_at fields
- JSON-based change tracking
- **Monorepo approach**: Python SDK/CLI/API bundled together

## Dependencies
- Core: pydantic, toml, typer, rich
- API: fastapi, uvicorn
- Dev: pytest, pytest-cov, ruff, mypy

## Key Commands
- `make install-all` - Install all dependencies
- `make dev` - Run API + Frontend
- `make test` - Run all tests
- `make lint` - Check code quality
- `make build-all` - Build everything
- `cinch` - Main CLI command (after install)
- `cinch-server` - Start API server

## Phase 2 Progress
Phase 2 (Branch and Tenant Management) progress:
- ✅ BranchManager class implemented and tested
- ✅ TenantManager class implemented and tested
- ⏳ Change tracking (next)
- ⏳ Metadata management

## Current Test Status
- **57 unit tests** all passing
- BranchManager: 12 tests
- TenantManager: 13 tests
- Config: 5 tests
- Connection: 8 tests
- Models: 10 tests
- Path utils: 9 tests

## Next Steps
1. Design and implement change tracking (Phase 2.3)
2. Complete metadata management
3. Move to Phase 3: Schema Management

## Key Technical Decisions
- WAL mode with autocheckpoint disabled for better concurrency
- Row factory for dict-like access to query results
- Connection pooling for efficient multi-tenant access
- Strict separation between table models and metadata models
- Branch creation copies all tenants (as per design)
- Tenant creation copies schema but not data from main tenant
# CinchDB Implementation Plan

## Overview
This document outlines the phased implementation approach for CinchDB, a SQLite-based database management system with Git-like branching capabilities for schema management.

## Repository Structure

CinchDB is organized as a monorepo with the following structure:

```
cinchdb/
├── src/cinchdb/         # Python package (SDK + CLI + API)
│   ├── models/          # Pydantic data models
│   ├── core/            # Core SDK functionality
│   ├── managers/        # Business logic managers
│   ├── cli/             # CLI implementation
│   │   └── commands/    # CLI command modules
│   ├── api/             # FastAPI server
│   │   └── routers/     # API route handlers
│   └── codegen/         # Code generation utilities
├── sdk/                 # Language-specific SDKs
│   └── typescript/      # TypeScript SDK
│       ├── src/         # Source code
│       └── tests/       # SDK tests
├── frontend/            # NextJS web application
│   ├── app/            # App router pages
│   └── components/     # React components
├── docs/               # Documentation site (Nextra)
│   └── content/        # Documentation content
├── tests/              # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   ├── e2e/            # End-to-end tests
│   └── fixtures/       # Test fixtures
├── examples/           # Usage examples
├── scripts/            # Development scripts
├── pyproject.toml      # Python package configuration
├── Makefile            # Development commands
└── README.md           # Project documentation
```

### Key Design Decisions:

1. **Unified Python Package**: The Python SDK, CLI, and API are bundled together in a single package for easier installation and version management. Users install with `pip install cinchdb` and get everything.

2. **SDK Organization**: Language-specific SDKs are placed under `sdk/` to allow for future additions (e.g., `sdk/go/`, `sdk/rust/`).

3. **Monorepo Benefits**: 
   - Simplified dependency management
   - Atomic commits across components
   - Easier integration testing
   - Consistent versioning

4. **Development Workflow**: The Makefile provides commands for common tasks:
   - `make install-all` - Install all dependencies
   - `make dev` - Run API and frontend in development mode
   - `make test` - Run all tests
   - `make build-all` - Build all components

## Phase 1: Core Foundation (Week 1-2)

### 1.1 Project Structure and Configuration
- [x] Create monorepo structure with Python, TypeScript, and frontend components
- [ ] Create core package structure under `src/cinchdb/`
- [ ] Implement `Config` class for managing `.cinchdb/config.toml`
- [ ] Define core data models using Pydantic:
  - `Project`, `Database`, `Branch`, `Tenant`
  - `Table`, `Column`, `View`
  - `Change`, `ChangeSet`
- [ ] Implement directory structure management:
  ```
  .cinchdb/
    config.toml
    databases/
      {db_name}/
        branches/
          {branch_name}/
            metadata.json
            changes.json
            tenants/
              {tenant_name}.db
              {tenant_name}.db-wal
              {tenant_name}.db-shm
  ```

### 1.2 SQLite Connection Management
- [ ] Create `DatabaseConnection` class with WAL mode configuration
- [ ] Implement connection pooling for multi-tenant access
- [ ] Configure SQLite settings:
  - WAL mode with autocheckpoint disabled
  - NORMAL synchronous mode
  - Proper timeout handling
- [ ] Add transaction management utilities

### 1.3 Base Repository Pattern
- [ ] Create abstract `BaseRepository` class
- [ ] Implement common CRUD operations
- [ ] Add automatic field management (id, created_at, updated_at)
- [ ] Create query builder helpers

## Phase 2: Branch and Tenant Management (Week 2-3)

### 2.1 Branch Operations
- [ ] Implement `BranchManager` class:
  - `create_branch(source_branch, new_branch_name)`
  - `delete_branch(branch_name)`
  - `list_branches()`
  - `switch_branch(branch_name)`
- [ ] Add branch metadata tracking
- [ ] Implement directory copying for branch creation

### 2.2 Tenant Operations
- [ ] Implement `TenantManager` class:
  - `create_tenant(tenant_name)`
  - `delete_tenant(tenant_name)`
  - `copy_tenant(source, target)`
  - `list_tenants()`
- [ ] Add tenant isolation in queries
- [ ] Implement tenant-aware connection routing

### 2.3 Change Tracking
- [ ] Design JSON schema for tracking changes
- [ ] Implement `ChangeTracker` class
- [ ] Add change serialization/deserialization
- [ ] Create change history viewing

## Phase 3: Schema Management (Week 3-4)

### 3.1 Table Management
- [ ] Implement `TableManager` class:
  - `create_table(table_name, columns)`
  - `delete_table(table_name)`
  - `copy_table(source, target)`
  - `get_table_info(table_name)`
- [ ] Add automatic UUID4 id field
- [ ] Add automatic timestamps (created_at, updated_at)
- [ ] Implement table existence validation

### 3.2 Column Management
- [ ] Implement `ColumnManager` class:
  - `add_column(table, column_def)`
  - `drop_column(table, column_name)`
  - `rename_column(table, old_name, new_name)`
- [ ] Add column type validation
- [ ] Implement safe ALTER TABLE operations
- [ ] Track column changes in metadata

### 3.3 View/Model Management
- [ ] Implement `ViewModel` class:
  - `create_view(name, sql_statement)`
  - `update_view(name, sql_statement)`
  - `delete_view(name)`
- [ ] Add SQL validation for views
- [ ] Track views in change history
- [ ] Implement view dependencies checking

## Phase 4: Merging and Synchronization (Week 4-5)

### 4.1 Change Comparison
- [ ] Implement `ChangeComparator` class
- [ ] Add branch divergence detection
- [ ] Create change conflict identification
- [ ] Implement change ordering logic

### 4.2 Merge Operations
- [ ] Implement `MergeManager` class:
  - `can_merge(source, target)`
  - `merge_branches(source, target)`
  - `apply_changes(changes, branch)`
- [ ] Add main branch protection
- [ ] Implement atomic merge transactions
- [ ] Create merge conflict resolution

### 4.3 Schema Synchronization
- [ ] Implement schema diff generation
- [ ] Add batch schema updates
- [ ] Create rollback capabilities
- [ ] Implement tenant synchronization

## Phase 5: CLI Implementation (Week 5-6)

### 5.1 CLI Structure
- [ ] Set up Typer application structure
- [ ] Implement command groups:
  - `cinchdb project`
  - `cinchdb db`
  - `cinchdb branch`
  - `cinchdb table`
  - `cinchdb column`
  - `cinchdb view`
  - `cinchdb query`
- [ ] Add global options (--project-dir, --db, --branch, --tenant)
- [ ] Implement output formatting (table, json, yaml)

### 5.2 Command Implementation
- [ ] Implement all project commands
- [ ] Implement all database commands
- [ ] Implement all branch commands
- [ ] Implement all table/column commands
- [ ] Implement query command with result display
- [ ] Add interactive mode for complex operations

### 5.3 CLI Testing
- [ ] Create CLI test fixtures
- [ ] Add integration tests for all commands
- [ ] Implement CLI documentation generation
- [ ] Add command examples

## Phase 6: API Development (Week 6-7)

### 6.1 FastAPI Setup
- [ ] Create FastAPI application structure
- [ ] Implement authentication middleware
- [ ] Add API key management (UUID4 based)
- [ ] Create permission system (read/write, branch-specific)
- [ ] Set up CORS and security headers

### 6.2 API Endpoints
- [ ] Implement project endpoints
- [ ] Implement database management endpoints
- [ ] Implement branch operations endpoints
- [ ] Implement table/column endpoints
- [ ] Implement query execution endpoint
- [ ] Add batch operation support

### 6.3 API Features
- [ ] Add request validation
- [ ] Implement response pagination
- [ ] Create WebSocket support for live queries
- [ ] Add API documentation (OpenAPI)
- [ ] Implement rate limiting

## Phase 7: TypeScript SDK (Week 7-8)

### 7.1 SDK Structure
- [ ] Set up TypeScript project
- [ ] Define type definitions for all models
- [ ] Create API client base class
- [ ] Implement authentication handling
- [ ] Add request/response interceptors

### 7.2 SDK Implementation
- [ ] Implement all API operations
- [ ] Add TypeScript-specific features
- [ ] Create promise-based interface
- [ ] Add retry logic and error handling
- [ ] Implement caching layer

### 7.3 SDK Testing and Documentation
- [ ] Create comprehensive test suite
- [ ] Add usage examples
- [ ] Generate TypeDoc documentation
- [ ] Create npm package configuration

## Phase 8: Frontend and Documentation (Week 8-9)

### 8.1 NextJS Frontend
- [ ] Set up NextJS application
- [ ] Implement authentication flow
- [ ] Create project dashboard
- [ ] Add database/branch visualization
- [ ] Implement table browser
- [ ] Add query interface
- [ ] Create change history viewer

### 8.2 Documentation Site
- [ ] Set up documentation framework
- [ ] Write getting started guide
- [ ] Document all CLI commands
- [ ] Document Python SDK
- [ ] Document TypeScript SDK
- [ ] Document API endpoints
- [ ] Add tutorials and examples

## Phase 9: Advanced Features (Week 9-10)

### 9.1 Code Generation
- [ ] Implement model generation for Python
- [ ] Implement model generation for TypeScript
- [ ] Add ORM-style query builders
- [ ] Create migration helpers

### 9.2 Performance Optimization
- [ ] Add query optimization
- [ ] Implement caching strategies
- [ ] Add bulk operation support
- [ ] Optimize branch operations

### 9.3 Monitoring and Debugging
- [ ] Add logging framework
- [ ] Implement performance metrics
- [ ] Create debugging utilities
- [ ] Add health check endpoints

## Testing Strategy

### Unit Tests
- Test all core classes and functions
- Achieve >80% code coverage
- Use pytest and pytest-cov

### Integration Tests
- Test full workflows
- Test multi-tenant scenarios
- Test concurrent operations

### End-to-End Tests
- Test CLI commands
- Test API endpoints
- Test SDK operations

## Development Guidelines

1. **Start Simple**: Implement minimal working versions first
2. **Test Early**: Write tests alongside implementation
3. **Document as You Go**: Keep documentation updated
4. **Security First**: Consider security implications in all features
5. **Performance Aware**: Profile and optimize critical paths

## Success Metrics

- All core functionality working locally
- Comprehensive test coverage
- Clear documentation
- Working examples for all major features
- Performance benchmarks established

## Next Steps

1. Begin with Phase 1.1 - Create project structure and configuration
2. Set up continuous integration
3. Create development environment setup guide
4. Start implementing core data models

---

*This plan is subject to refinement as development progresses and new insights are gained.*
# CLAUDE-decisions.md - Architecture Decisions and Rationale

## Core Architecture Decisions

### 1. Monorepo Structure
**Decision**: Bundle Python SDK, CLI, and API in single package
**Rationale**: 
- Simplifies installation (`pip install cinchdb` gets everything)
- Ensures version consistency across components
- Easier to maintain and test together
- Reduces deployment complexity for users

### 2. File-Based Metadata
**Decision**: Use directory structure and JSON files for metadata
**Rationale**:
- "Branches and tenants are implied from the directory structure" (DESIGN.md)
- No disconnect between metadata and actual state
- Easy to inspect and debug
- Simple backup/restore via file copy

### 3. Model Base Class Separation
**Decision**: Two base classes - CinchDBTableModel and CinchDBBaseModel
**Rationale**:
- Only Change records need database table fields (id, timestamps)
- Metadata entities (Branch, Tenant, etc.) are not stored in tables
- Prevents confusion about what gets persisted where
- Cleaner separation of concerns

### 4. WAL Mode Configuration
**Decision**: WAL mode with autocheckpoint disabled
**Rationale**:
- Better concurrency for multi-tenant access
- Prevents blocking during checkpoints
- NORMAL synchronous mode balances safety and performance
- Matches design requirement for WAL mode

### 5. Main Entity Protection
**Decision**: Prevent deletion of "main" database, branch, and tenant
**Rationale**:
- These are foundational entities required by the system
- Prevents accidental data loss
- Enforces consistent project structure
- Simplifies assumptions in other code

### 6. Branch Copy Strategy
**Decision**: Copy entire branch directory including all tenants
**Rationale**:
- Design specifies "all tenants are automatically copied, always"
- Ensures branch isolation
- Simplifies rollback scenarios
- Maintains consistency across tenants

### 7. Tenant Schema Copy
**Decision**: Copy schema but not data when creating tenants
**Rationale**:
- Each tenant starts with same structure
- Prevents data leakage between tenants
- Allows immediate use of new tenant
- Maintains multi-tenant isolation

### 8. Change Tracking Design
**Decision**: Store changes as JSON array in branch directory
**Rationale**:
- Simple and human-readable
- Easy to merge/compare
- No external dependencies
- Can be versioned with git

### 9. Connection Pooling
**Decision**: Implement connection pool for database connections
**Rationale**:
- Efficient multi-tenant access
- Reduces connection overhead
- Better resource management
- Prepared for concurrent operations

### 10. Test-First Development
**Decision**: Write tests before implementation
**Rationale**:
- Ensures all functionality is tested
- Catches issues early
- Documents expected behavior
- Maintains high code quality

## Technology Choices

### Python Stack
- **Pydantic**: Type safety and validation
- **Typer**: Modern CLI with good UX
- **FastAPI**: High-performance async API
- **pytest**: Comprehensive testing

### Database
- **SQLite**: Embedded, zero-configuration
- **WAL mode**: Better concurrency
- **Row factory**: Dict-like access to results

## Future Considerations

### Scalability
- Current design optimized for single-machine use
- Connection pooling prepares for concurrent access
- File-based approach may need revision for distributed systems

### API Design
- FastAPI chosen for async support
- Prepared for WebSocket live queries
- Authentication via UUID4 API keys

### Extensibility
- Manager pattern allows easy addition of new operations
- Model base classes can be extended
- Plugin system could be added via entry points

## CLI Design Decisions

### 11. No Global Tenant Flag
**Decision**: Only `query` and `tenant` commands have `--tenant` flag
**Rationale**:
- Schema changes always apply to all tenants
- Reduces confusion about which operations are tenant-specific
- Query and tenant management are the only tenant-aware operations
- Enforces design principle of consistent schema across tenants

### 12. Help on No Arguments
**Decision**: All CLI commands show help when called with no arguments
**Rationale**:
- Better user experience for discovery
- Prevents accidental operations
- Consistent behavior across all command levels
- Standard pattern in modern CLI tools

### 13. No fastentrypoints
**Decision**: Don't use fastentrypoints for CLI optimization
**Rationale**:
- Modern Python/setuptools don't have pkg_resources overhead
- CinchDB already uses lazy imports via Typer
- Additional complexity not justified
- Performance is already good with current structure

## API Design Decisions

### 14. UUID4 API Keys
**Decision**: Use UUID4 for API authentication
**Rationale**:
- Simple and secure
- No external auth dependencies
- Easy to generate and revoke
- Matches design specification

### 15. Branch-Specific Permissions
**Decision**: API keys can be restricted to specific branches
**Rationale**:
- Enables fine-grained access control
- Useful for CI/CD scenarios
- Protects production branches
- Flexible permission model

### 16. Separate Read/Write Permissions
**Decision**: API keys have either read or write permission
**Rationale**:
- Simple permission model
- Clear security boundaries
- Easy to understand and implement
- Covers most use cases

### 17. All SDK Operations via REST
**Decision**: Every SDK operation available through API
**Rationale**:
- Complete feature parity
- Enables remote management
- Consistent interface
- Simplifies client implementations
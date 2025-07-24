# API Update Plan - Remote Data Operations

## Current State Analysis

The CinchDB **local development experience is excellent** with comprehensive functionality:

- **DataManager** - Sophisticated CRUD with filtering (`age__gte`, `name__like`), bulk operations, Pydantic integration
- **Generated Models** - Full-featured with `select()`, `create()`, `save()`, `delete()`, `bulk_create()` methods  
- **Unified CinchDB Interface** - Local/remote abstraction with `query()`, `insert()`, `update()`, `delete()`
- **Maintenance Mode** - Already integrated across all write operations 
- **Change Tracking** - Comprehensive with snapshot-based rollback

## The Real Gap: Remote API Endpoint Coverage

The API provides excellent **schema management** but is missing **data operation endpoints** that would enable full remote functionality.

### 1. Missing Data CRUD Endpoints (HIGH PRIORITY)
DataManager operations exist locally but need REST API exposure:

```
POST   /api/v1/tables/{table}/data           # Create records
GET    /api/v1/tables/{table}/data           # List with filtering (age__gte, name__like, etc.)
GET    /api/v1/tables/{table}/data/{id}      # Get specific record
PUT    /api/v1/tables/{table}/data/{id}      # Update record
DELETE /api/v1/tables/{table}/data/{id}      # Delete record
POST   /api/v1/tables/{table}/data/bulk      # Bulk operations
DELETE /api/v1/tables/{table}/data          # Delete with filters
GET    /api/v1/tables/{table}/data/count     # Count with filters
```

### 2. Code Generation API (MEDIUM PRIORITY)
Remote model generation workflow:

```
GET    /api/v1/codegen/languages             # List supported languages  
POST   /api/v1/codegen/generate              # Generate models (returns ZIP or files)
```

### 3. Branch Operations API (LOW PRIORITY)
Advanced workflow support:

```
GET    /api/v1/branches/{branch}/compare     # Compare branches  
POST   /api/v1/branches/{branch}/merge       # Merge branches
POST   /api/v1/branches/{branch}/dry-run     # Preview operations
```

## Implementation Strategy

### Phase 1: Data CRUD API Endpoints
**Target**: Enable generated models to work with remote connections

**Current Generated Model Pattern**:
```python
# Local usage (works perfectly)
User.set_connection(local_data_manager)
user = User.create(name="Alice", email="alice@example.com")
user.name = "Alice Smith"  
user.save()
user.delete()

# Remote usage (needs API endpoints)
User.set_connection(remote_data_manager)  # Should work the same way
user = User.create(name="Alice", email="alice@example.com")  # -> POST /tables/users/data
```

**Implementation Approach**:
- **Delegate to DataManager**: API endpoints simply call existing DataManager methods
- **Pydantic Request/Response**: Use existing model validation patterns
- **Filter Parameter Parsing**: Support existing `age__gte`, `name__like` operators  
- **Automatic Maintenance Mode**: DataManager already handles this
- **Permission Integration**: Use existing API key read/write permissions

### Phase 2: Remote Code Generation
**Target**: Enable model generation via API calls

**Key Design Questions**:
1. **File Delivery Method**:
   - ZIP file download with all models?
   - Streaming individual files?
   - Base64 encoded file contents in JSON?

2. **Connection Configuration**: 
   - Generated models auto-detect remote vs local?
   - Explicit connection type in `set_connection()`?
   - Environment variable override?

3. **Generated Model Updates**:
   - Include remote-specific DataManager configuration?
   - Modify `set_connection()` to handle API connections?
   - Keep identical interface regardless of connection type?

**Proposed Approach**:
```python
# API generates models that work identically  
POST /codegen/generate {
  "language": "python",
  "tables": ["users", "posts"],
  "output_format": "zip"  # or "files"
}

# Generated models work the same locally or remotely
User.set_connection(cinchdb.connect_api(url, key, "mydb"))
user = User.create(name="Alice")  # Uses API endpoints transparently
```

### Phase 3: Branch Operations API (Optional)
**Target**: Advanced distributed development workflow support

**Implementation Notes**:
- These operations already exist in managers (BranchManager, ChangeComparator)
- Would enable remote branch management and collaboration
- Lower priority since most development likely happens locally

## Key Design Principles

### Leverage Existing Implementation
- **No Reinvention**: API endpoints delegate to existing managers
- **Maintain Patterns**: Use established Pydantic validation and error handling
- **Preserve Security**: Existing maintenance mode and permission checking work automatically

### Remote/Local Transparency  
- **Identical Interface**: Generated models work the same way regardless of connection
- **Connection Abstraction**: DataManager handles local vs remote transparently
- **No New Configuration**: Use existing CinchDB connection pattern

### Realistic Implementation Scope
- **Focus on Data Operations**: Schema management already works well via API
- **Codegen Questions**: Need clarification on file delivery and caching strategy
- **Branch Operations**: Nice-to-have for advanced workflows

## Questions for Clarification

### Remote Codegen Implementation
1. **File Delivery**: Should generated models be returned as:
   - ZIP file download?
   - JSON with base64-encoded file contents?
   - Individual file endpoints?

2. **Connection Handling**: Should generated models:
   - Auto-detect connection type (local vs remote)?  
   - Require explicit connection configuration?
   - Use environment variables for remote endpoints?

3. **Caching Strategy**: Should the API:
   - Cache generated models per project/schema?
   - Regenerate on every request?
   - Provide cache invalidation?

### DataManager Remote Integration
1. **How should remote DataManager work?**
   - Modify existing DataManager to make HTTP calls?
   - Create separate RemoteDataManager class?
   - Make it transparent in CinchDB?

2. **Error handling for remote operations?**
   - Network timeouts and retries?
   - API key expiration handling?
   - Maintenance mode response handling?

## Success Criteria

### Core Requirements
- [ ] Generated models work identically with local and remote connections
- [ ] All DataManager CRUD operations available via API endpoints
- [ ] Existing security and maintenance mode features preserved
- [ ] No breaking changes to current API or local functionality

### Implementation Priorities
1. **Phase 1**: Data CRUD endpoints (`/tables/{table}/data/*`)
2. **Phase 2**: Remote codegen (pending design decisions above)
3. **Phase 3**: Branch operations (if needed for distributed workflows)

## Next Steps

1. **Clarify codegen design questions** above
2. **Implement data CRUD API endpoints** - highest priority gap
3. **Update CinchDB remote connection** to use new endpoints
4. **Test generated model compatibility** with remote connections

This revised plan focuses on the actual gaps while leveraging the excellent existing implementation.
# API Active Database/Branch Design Analysis

## Current State

The API currently has the concept of "active database" and "active branch" which:
1. Are stored in the project's config.toml file
2. Can be changed via the `/project/config` endpoint
3. Are returned in the `/project/info` response
4. Are used to show which database/branch is "active" in UI contexts

However, looking at the API endpoints, **all data operations already require explicit database and branch parameters**:
- All data endpoints: `GET /tables/{table}/data?database=X&branch=Y&tenant=Z`
- All schema endpoints: `POST /tables?database=X&branch=Y`
- All view endpoints: `GET /views?database=X&branch=Y`
- All tenant endpoints: `GET /tenants?database=X&branch=Y`

## Analysis

### Why Active Database/Branch Exists

1. **CLI Heritage**: The concept comes from the CLI/local usage where having an "active" context makes sense:
   - Users work in a specific database/branch context
   - Commands like `cinch query` use the active database/branch
   - Similar to git's current branch concept

2. **Project Info**: The API exposes project-level information including what's currently "active"
   - Useful for UI to show current context
   - Helps with CLI remote operations

3. **Config Management**: The API can modify the project's config.toml
   - Allows remote clients to change the active context
   - Maintains consistency with local CLI usage

### Arguments For Keeping It

1. **CLI/API Consistency**: When using the API as a backend for the CLI in remote mode, having the same config concepts helps
2. **UI Context**: For web UIs or IDEs, showing which database/branch is "active" provides useful context
3. **Future Features**: Could be used for default values if we ever make parameters optional
4. **Project State**: It's legitimate project state that might be useful to query/modify remotely

### Arguments For Removing It

1. **API Doesn't Use It**: All API operations already require explicit parameters
2. **Stateless is Better**: APIs should generally be stateless - having "active" state is unusual
3. **Confusion**: Developers might think they need to set active database/branch before operations
4. **Redundant**: Since every operation requires explicit parameters anyway

## Recommendation

**Keep it, but clarify its purpose**. Here's why:

1. **It's not hurting anything** - The API doesn't rely on it for operations
2. **CLI Remote Mode** - When the CLI uses the API backend, it's useful to maintain the same project state
3. **Project Management** - The API legitimately manages project configuration, and active database/branch are part of that
4. **Future Flexibility** - We might want to add convenience endpoints that use defaults

However, we should:
1. **Document clearly** that all API operations require explicit parameters
2. **Consider renaming** in API responses to `current_database`/`current_branch` to avoid implying they affect API behavior
3. **Add to API docs** that these are project configuration values, not request context

## Implementation Notes

No code changes needed, but documentation should clarify:
- All API operations are stateless and require explicit database/branch/tenant parameters
- The active database/branch in project config is for CLI context only
- Remote clients should always specify all parameters explicitly

This is a sensible design that maintains compatibility with the CLI while keeping the API properly stateless.
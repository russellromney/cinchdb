# CLAUDE-troubleshooting.md - Common Issues and Solutions

## CLI Issues

### Error when running command without arguments
**Problem**: Running `cinch` subcommands without arguments shows an error after displaying help.

**Solution**: Use `invoke_without_command=True` in Typer constructor and add a callback:
```python
app = typer.Typer(help="Command description", invoke_without_command=True)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Command description."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(0)
```

**Note**: Don't use `no_args_is_help=True` with callbacks as they conflict.

## API Issues

### Internal server error on API requests
**Problem**: API endpoints return 500 errors due to import issues.

**Solution**: Check all imports are correct and models are properly defined. Common issues:
- Missing imports in router files
- Circular imports between modules
- Using wrong import paths

## Query Issues

### INSERT/UPDATE/DELETE queries don't persist
**Problem**: Write queries execute but changes aren't saved.

**Solution**: Add commit after non-SELECT queries:
```python
if not query.strip().upper().startswith("SELECT"):
    conn.commit()
```

### SELECT query results not displayed
**Problem**: SELECT query executes but results aren't shown.

**Solution**: Check indentation of result processing code. Must be at correct level after query execution.

## Config Issues

### Config attribute errors in CLI commands
**Problem**: `'Config' object has no attribute 'get_active_database'` errors.

**Solution**: Use the `get_config_with_data()` utility function:
```python
config, config_data = get_config_with_data()
db_name = config_data.active_database
branch_name = config_data.active_branch
```

## Test Issues

### TypeScript tests failing with "No tests found"
**Problem**: Jest exits with code 1 when no test files are found in TypeScript SDK.

**Solution**: Add `--passWithNoTests` flag to jest configuration:
```json
{
  "scripts": {
    "test": "jest --passWithNoTests"
  }
}
```

### Python linting failures blocking CI
**Problem**: ruff check finds unused variables, imports, bare excepts, boolean comparisons.

**Solution**: Use ruff auto-fix capabilities:
```bash
# Fix safe issues automatically
uv run ruff check --fix src/ tests/

# Fix remaining issues with unsafe fixes
uv run ruff check --fix --unsafe-fixes src/ tests/

# Fix specific patterns
uv run ruff check --fix src/ tests/ --select E712  # Boolean comparisons
```

**Common Patterns to Fix**:
- `except:` → `except Exception:`
- `== True` → use `if condition:`
- `== False` → use `if not condition:`
- Remove unused variables: `applied = func()` → `func()`
- Remove unused imports
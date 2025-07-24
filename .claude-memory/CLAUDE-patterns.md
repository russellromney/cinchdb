# CLAUDE-patterns.md - Established Code Patterns

## Testing Patterns

### Test-First Development
- Write tests before implementation
- Each test class uses fixtures for setup/teardown
- Use pytest fixtures for temporary directories and test data
- Run all tests after implementing each component

### Test Structure
```python
class TestComponentName:
    @pytest.fixture
    def temp_project(self):
        """Create temporary test environment."""
        temp = tempfile.mkdtemp()
        # Setup
        yield Path(temp)
        shutil.rmtree(temp)  # Cleanup
```

## Manager Pattern

### Base Structure
```python
class ComponentManager:
    def __init__(self, project_root: Path, ...):
        self.project_root = Path(project_root)
        # Initialize paths
    
    def list_items(self) -> List[Model]:
        """List all items."""
        
    def create_item(self, ...) -> Model:
        """Create new item with validation."""
        # Validate doesn't exist
        # Create
        # Return model
        
    def delete_item(self, name: str) -> None:
        """Delete item with protection checks."""
        # Check if can delete
        # Validate exists
        # Delete
```

### Protection Pattern
- Always check `can_delete()` for main entities
- Raise ValueError with descriptive messages
- Validate existence before operations

## Model Patterns

### Base Class Usage
- `CinchDBTableModel` - Only for entities stored as tables (Change model)
- `CinchDBBaseModel` - For all metadata/configuration entities

### Model Structure
```python
class EntityModel(CinchDBBaseModel):
    name: str = Field(description="...")
    parent: str = Field(description="...")
    
    def can_delete(self) -> bool:
        """Check if entity can be deleted."""
        return self.name != "main"
```

## Path Management

### Consistent Path Building
- Use path utility functions from `core.path_utils`
- Always resolve paths when comparing
- Create parent directories with `parents=True, exist_ok=True`

## Database Patterns

### Connection Management
```python
with DatabaseConnection(db_path) as conn:
    conn.execute(sql)
    conn.commit()
```

### WAL Mode Configuration
- Always use WAL mode for SQLite
- Disable autocheckpoint
- Use NORMAL synchronous mode
- Enable foreign keys

## Error Handling

### Validation Pattern
```python
if not condition:
    raise ValueError(f"Descriptive error message with '{variable}'")
```

### File Operations
- Check existence before operations
- Clean up related files (WAL, SHM) when deleting databases
- Use shutil for copying directories/files

## JSON File Management

### Reading Pattern
```python
if path.exists():
    with open(path, "r") as f:
        return json.load(f)
return default_value
```

### Writing Pattern
```python
with open(path, "w") as f:
    json.dump(data, f, indent=2)
```

## Naming Conventions

### Files
- Python modules: lowercase with underscores (e.g., `branch_manager.py`)
- Test files: `test_` prefix (e.g., `test_branch_manager.py`)
- JSON files: lowercase (e.g., `metadata.json`, `changes.json`)

### Classes
- Managers: `ComponentManager` (e.g., `BranchManager`)
- Models: Singular nouns (e.g., `Branch`, `Tenant`)
- Tests: `TestComponentName` (e.g., `TestBranchManager`)

### Methods
- List operations: `list_items()` returns List[Model]
- Create operations: `create_item()` returns Model
- Delete operations: `delete_item()` returns None
- Get operations: `get_item()` returns Model or data

## Directory Structure Pattern

```
.cinchdb/
  databases/
    {database}/
      branches/
        {branch}/
          metadata.json    # Branch metadata
          changes.json     # Change history
          tenants/
            {tenant}.db    # SQLite database
            {tenant}.db-wal
            {tenant}.db-shm
```

## Copy Patterns

### Branch Creation
- Copy entire branch directory including all tenants
- Reset changes.json
- Update metadata with parent info

### Tenant Creation
- Copy schema from main tenant
- Clear all data from tables
- Preserve structure only

## CLI Patterns

### Command Structure
- Use Typer with callbacks for help display (not `no_args_is_help=True`)
- Lazy import commands to improve startup performance
- Group related commands under subcommands (db, branch, table, etc.)
- Always show help when no arguments provided:
```python
app = typer.Typer(help="Description", invoke_without_command=True)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit(0)
```

### Option Patterns
```python
# Required arguments
name: str = typer.Argument(..., help="Description")

# Optional with defaults
force: bool = typer.Option(False, "--force", "-f", help="Description")

# Options with choices
format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, csv)")
```

### Output Patterns
- Use Rich Console for colored output
- Success: `[green]✅ Message[/green]`
- Error: `[red]❌ Message[/red]`
- Warning: `[yellow]Message[/yellow]`
- Tables: Use RichTable for structured data

### Tenant Flag Usage
- Only `query` and `tenant` commands have `--tenant` flag
- All other commands operate on main tenant and apply to all

## API Patterns

### Authentication
- UUID4 API keys stored in config.toml
- Read/write permissions
- Optional branch-specific restrictions
- Header: `X-API-Key`

### Router Structure
```python
router = APIRouter()

@router.get("/", response_model=List[Model])
async def list_items(
    auth: AuthContext = Depends(require_read_permission)
):
    """List all items."""
    
@router.post("/")
async def create_item(
    request: CreateRequest,
    auth: AuthContext = Depends(require_write_permission)
):
    """Create new item."""
```

### Error Handling
```python
if not condition:
    raise HTTPException(status_code=400, detail="Message")
```

### Query Parameters
```python
database: Optional[str] = Query(None, description="Database name (defaults to active)")
branch: Optional[str] = Query(None, description="Branch name (defaults to active)")
```

## Performance Patterns

### Lazy Imports
- Import heavy modules inside functions, not at module level
- Use Typer's built-in lazy loading for subcommands
- Don't import pkg_resources (not needed with modern setuptools)

### CLI Optimization
- Modern Python/setuptools don't need fastentrypoints
- Use `python -O` for production (removes assertions)
- Pre-compile with `python -m compileall`
- Profile with `python -X importtime`
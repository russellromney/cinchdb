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

## Code Quality Patterns

### Linting and Formatting
```bash
# Run ruff for linting and auto-fixing
uv run ruff check --fix src/ tests/

# Use unsafe fixes for remaining issues
uv run ruff check --fix --unsafe-fixes src/ tests/

# Format code
uv run ruff format src/ tests/
```

### Exception Handling Best Practices
```python
# Good: Specific exception types
try:
    risky_operation()
except ValueError as e:
    handle_value_error(e)
except Exception as e:
    handle_general_error(e)

# Avoid: Bare except statements
try:
    risky_operation()
except:  # ❌ Don't do this
    pass
```

### Boolean Comparisons
```python
# Good: Direct boolean usage
if result["can_merge"]:
    proceed_with_merge()

if not result["has_conflicts"]:
    apply_changes()

# Avoid: Explicit boolean comparisons  
if result["can_merge"] == True:  # ❌ Don't do this
    proceed_with_merge()
```

### Variable Usage
```python
# Good: Use return values when needed
changes_applied = applier.apply_all_unapplied()
if changes_applied > 0:
    log_success()

# Good: Call without assignment when result not needed
applier.apply_all_unapplied()  # Result not used

# Avoid: Unused variable assignments
applied = applier.apply_all_unapplied()  # ❌ Variable never used
```

## Codegen Patterns

### Model Generation
```python
class CodegenManager:
    def generate_models(self, language, output_dir, include_tables=True, include_views=True):
        """Generate models with proper type mapping."""
        
    def _sqlite_to_python_type(self, sqlite_type: str, column_name: str = ""):
        """Handle special cases for timestamp fields."""
        if column_name in ["created_at", "updated_at"]:
            return "datetime"
```

### Type Mapping Rules
- TEXT → str (except created_at/updated_at → datetime)
- INTEGER → int
- REAL/FLOAT/DOUBLE → float
- BLOB → bytes
- NUMERIC → float

### Generated Model Structure
```python
class ModelName(BaseModel):
    """Generated model for table_name table."""
    
    # Fields with proper types and defaults
    id: str = Field(description="id field")
    created_at: datetime = Field(description="created_at field", default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(description="updated_at field", default=None)
    
    class Config:
        from_attributes = True
        json_schema_extra = {"table_name": "table_name"}
```

### Directory Structure
```
generated_models/
├── __init__.py          # Exports all models
├── table_name.py        # Individual table models
└── view_name_view.py    # View models (read-only)
```

### CLI Command Structure
- `codegen languages` - List supported languages
- `codegen generate <language> <output_dir>` - Generate models
- Support --tables/--views flags for selective generation
- --force flag for overwriting existing files

### Test Maintenance Patterns

```bash
# Run full test suite
make test

# Run only Python tests
make test-python

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_codegen_manager.py -v
```

### Project Health Checks
```bash
# Complete health check workflow
make test-python          # All tests must pass
make lint-python          # All linting issues must be clean
make typecheck-python     # Type check (warnings acceptable)
make format-python        # Format code consistently
```

### CI/CD Patterns
- Always fix failing tests before proceeding with new features
- Use ruff for consistent code formatting and linting
- Maintain comprehensive test coverage for all new features
- TypeScript SDK can have placeholder status with `--passWithNoTests`

## Unified Database Interface Patterns

### Connection Factory Pattern
```python
# Local connection
db = cinchdb.connect(
    database="mydb",
    branch="main",
    tenant="main",
    project_dir=Path("/path/to/project")  # Optional
)

# Remote connection
db = cinchdb.connect_api(
    api_url="https://api.example.com",
    api_key="your-api-key",
    database="mydb",
    branch="main",
    tenant="main"
)
```

### Single Class Design
```python
class CinchDatabase:
    def __init__(self, database, branch="main", tenant="main", 
                 project_dir=None, api_url=None, api_key=None):
        """Single class handles both local and remote connections."""
        if project_dir is not None:
            self.is_local = True
            # Local connection setup
        elif api_url is not None and api_key is not None:
            self.is_local = False
            # Remote connection setup
        else:
            raise ValueError("Must provide connection parameters")
```

### Lazy Loading Pattern
```python
@property
def tables(self) -> TableManager:
    """Lazy load managers only when accessed."""
    if not self.is_local:
        raise RuntimeError("Direct manager access not available for remote")
    if self._table_manager is None:
        from cinchdb.managers.table import TableManager
        self._table_manager = TableManager(...)
    return self._table_manager
```

### Unified Method Pattern
```python
def query(self, sql: str, params: Optional[List[Any]] = None):
    """Same interface for local and remote."""
    if self.is_local:
        # Use local QueryManager
        return self._query_manager.execute(sql, params)
    else:
        # Make API request
        return self._make_request("POST", "/query", json={"sql": sql, "params": params})
```

### Context Manager Support
```python
# Automatic cleanup for remote connections
with cinchdb.connect_api(url, key, "mydb") as db:
    results = db.query("SELECT * FROM users")
    # Session automatically closed on exit
```

### Testing Remote Connections
```python
# Mock the session property instead of requests module
with patch.object(CinchDatabase, 'session', new_callable=PropertyMock) as mock_session_prop:
    mock_session = Mock()
    mock_session_prop.return_value = mock_session
    
    # Test remote operations
    db = CinchDatabase(database="test", api_url="...", api_key="...")
    db.query("SELECT * FROM users")
```

### Usage Patterns
```python
# Simple operations
db = cinchdb.connect("mydb")
db.create_table("users", columns)
results = db.query("SELECT * FROM users")
user = db.insert("users", {"name": "Alice"})
db.update("users", user["id"], {"name": "Alice Smith"})
db.delete("users", user["id"])

# Advanced operations (local only)
if db.is_local:
    db.tables.copy_table("users", "users_backup")
    db.columns.rename_column("users", "email", "email_address")
    db.branches.merge("feature", "main")

# Switching contexts
dev_db = db.switch_branch("dev")
customer_db = db.switch_tenant("customer1")
```

## CLI Argument Validation Pattern

### Required Arguments with Help Display
```python
def validate_required_arg(value: Optional[str], arg_name: str, ctx: typer.Context) -> str:
    """Validate required argument and show help if missing."""
    if value is None:
        console.print(ctx.get_help())
        console.print(f"\n[red]❌ Error: Missing argument '{arg_name.upper()}'.[/red]")
        raise typer.Exit(1)
    return value

# Usage in commands
@app.command()
def merge(
    ctx: typer.Context,
    source: Optional[str] = typer.Argument(None, help="Source branch to merge from")
):
    source = validate_required_arg(source, "source", ctx)
```

## Dry-run Pattern

### Manager Implementation
```python
def merge_branches(self, source: str, target: str, force: bool = False, dry_run: bool = False):
    """Support dry-run mode to preview operations."""
    if dry_run:
        sql_statements = self._collect_sql_statements(changes, target)
        return {
            "success": True,
            "dry_run": True,
            "sql_statements": sql_statements
        }
    # Normal execution
```

### SQL Statement Collection
```python
def _collect_sql_statements(self, changes: List[Change], target_branch: str) -> List[Dict[str, Any]]:
    """Collect SQL statements without tenant information."""
    sql_statements = []
    for change in changes:
        # Handle different change types
        if change.type == ChangeType.UPDATE_VIEW:
            # Multi-step operations
            sql_statements.append({
                "change_id": change.id,
                "change_type": change.type.value if hasattr(change.type, 'value') else change.type,
                "entity_name": change.entity_name,
                "step": "drop_existing",
                "sql": f"DROP VIEW IF EXISTS {change.entity_name}"
            })
            # Add CREATE step...
```

### CLI Display Pattern
```python
if result.get("sql_statements"):
    console.print("\n[bold]SQL statements that would be executed:[/bold]")
    for stmt in result["sql_statements"]:
        console.print(f"\n[cyan]Change {stmt['change_id']} ({stmt['change_type']}): {stmt['entity_name']}[/cyan]")
        if "step" in stmt:
            console.print(f"  Step: {stmt['step']}")
        console.print(f"  SQL: [yellow]{stmt['sql']}[/yellow]")
```
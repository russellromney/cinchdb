# Python SDK API Reference

This document provides a comprehensive reference for all classes, methods, and functions available in the CinchDB Python SDK.

## Table of Contents

- [Connection Functions](#connection-functions)
  - [connect()](#connect)
  - [connect_api()](#connect_api)
- [CinchDB Class](#cinchdb-class)
  - [Constructor](#constructor)
  - [Properties](#properties)
  - [Query Methods](#query-methods)
  - [Table Methods](#table-methods)
  - [Data Methods](#data-methods)
  - [Context Manager](#context-manager)
- [Column Model](#column-model)
- [Manager Classes (Local Only)](#manager-classes-local-only)
  - [TableManager](#tablemanager)
  - [ColumnManager](#columnmanager)
  - [QueryManager](#querymanager)
  - [DataManager](#datamanager)
  - [ViewModel](#viewmodel)
  - [BranchManager](#branchmanager)
  - [TenantManager](#tenantmanager)
  - [CodegenManager](#codegenmanager)
  - [MergeManager](#mergemanager)
- [Exceptions](#exceptions)

## Connection Functions

### connect()

Connect to a local CinchDB database.

```python
connect(
    database: str,
    branch: str = "main",
    tenant: str = "main",
    project_dir: Optional[Path] = None
) -> CinchDB
```

**Parameters:**
- `database` (str): Database name
- `branch` (str, optional): Branch name. Default: "main"
- `tenant` (str, optional): Tenant name. Default: "main"
- `project_dir` (Path, optional): Path to project directory. If not provided, searches for .cinchdb directory

**Returns:**
- `CinchDB`: Connection instance for local database

**Raises:**
- `ValueError`: If no .cinchdb directory is found when project_dir is not specified

**Example:**
```python
from cinchdb import connect

# Connect using current directory
db = connect("mydb")

# Connect to specific branch
db = connect("mydb", "feature-branch")

# Connect with explicit project directory
from pathlib import Path
db = connect("mydb", project_dir=Path("/path/to/project"))
```

### connect_api()

Connect to a remote CinchDB API.

```python
connect_api(
    api_url: str,
    api_key: str,
    database: str,
    branch: str = "main",
    tenant: str = "main"
) -> CinchDB
```

**Parameters:**
- `api_url` (str): Base URL of the CinchDB API
- `api_key` (str): API authentication key
- `database` (str): Database name
- `branch` (str, optional): Branch name. Default: "main"
- `tenant` (str, optional): Tenant name. Default: "main"

**Returns:**
- `CinchDB`: Connection instance for remote API

**Example:**
```python
from cinchdb import connect_api

# Connect to remote API
db = connect_api("https://api.example.com", "your-api-key", "mydb")

# Connect to specific branch
db = connect_api("https://api.example.com", "your-api-key", "mydb", "dev")

# Use with context manager
with connect_api("https://api.example.com", "key", "mydb") as db:
    results = db.query("SELECT * FROM users")
```

## CinchDB Class

Unified interface for CinchDB operations, supporting both local and remote connections.

### Constructor

```python
CinchDB(
    database: str,
    branch: str = "main",
    tenant: str = "main",
    project_dir: Optional[Path] = None,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None
)
```

**Parameters:**
- `database` (str): Database name
- `branch` (str, optional): Branch name. Default: "main"
- `tenant` (str, optional): Tenant name. Default: "main"
- `project_dir` (Path, optional): Path to project directory for local connection
- `api_url` (str, optional): Base URL for remote API connection
- `api_key` (str, optional): API key for remote connection

**Raises:**
- `ValueError`: If neither local nor remote connection parameters are provided

**Example:**
```python
from cinchdb import CinchDB
from pathlib import Path

# Local connection
db = CinchDB(project_dir="/path/to/project", database="mydb", branch="dev")

# Remote connection
db = CinchDB(
    api_url="https://api.example.com",
    api_key="your-api-key",
    database="mydb",
    branch="dev"
)
```

### Properties

#### is_local

```python
is_local: bool
```

Returns `True` if this is a local connection, `False` for remote connections.

#### database

```python
database: str
```

The name of the connected database.

#### branch

```python
branch: str
```

The current branch name.

#### tenant

```python
tenant: str
```

The current tenant name.

### Query Methods

#### query()

Execute a SQL query.

```python
query(sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]
```

**Parameters:**
- `sql` (str): SQL query to execute
- `params` (List[Any], optional): Query parameters for parameterized queries

**Returns:**
- `List[Dict[str, Any]]`: List of result rows as dictionaries

**Example:**
```python
# Simple query
results = db.query("SELECT * FROM users")

# Parameterized query
results = db.query("SELECT * FROM users WHERE active = ?", [True])

# Query with multiple parameters
results = db.query(
    "SELECT * FROM orders WHERE status = ? AND created_at > ?",
    ["pending", "2024-01-01"]
)
```

### Table Methods

#### create_table()

Create a new table.

```python
create_table(name: str, columns: List[Column]) -> None
```

**Parameters:**
- `name` (str): Table name
- `columns` (List[Column]): List of column definitions

**Example:**
```python
from cinchdb.models import Column

db.create_table("products", [
    Column(name="name", type="TEXT", nullable=False),
    Column(name="price", type="REAL", nullable=False),
    Column(name="description", type="TEXT")
])
```

### Data Methods

#### insert()

Insert a record into a table.

```python
insert(table: str, data: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `table` (str): Table name
- `data` (Dict[str, Any]): Record data as dictionary

**Returns:**
- `Dict[str, Any]`: Inserted record with generated fields (id, created_at, updated_at)

**Example:**
```python
record = db.insert("users", {
    "name": "John Doe",
    "email": "john@example.com",
    "active": True
})
print(record["id"])  # Generated UUID
```

#### update()

Update a record in a table.

```python
update(table: str, id: str, data: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `table` (str): Table name
- `id` (str): Record ID
- `data` (Dict[str, Any]): Updated data as dictionary

**Returns:**
- `Dict[str, Any]`: Updated record

**Example:**
```python
updated = db.update("users", "user-id-123", {
    "name": "Jane Doe",
    "active": False
})
```

#### delete()

Delete a record from a table.

```python
delete(table: str, id: str) -> None
```

**Parameters:**
- `table` (str): Table name
- `id` (str): Record ID

**Example:**
```python
db.delete("users", "user-id-123")
```

### Context Manager

#### close()

Close any open connections.

```python
close() -> None
```

The CinchDB class supports context manager protocol:

```python
with connect("mydb") as db:
    results = db.query("SELECT * FROM users")
    # Connection automatically closed when exiting context
```

## Column Model

Represents a column in a table.

```python
from cinchdb.models import Column, ColumnType

Column(
    name: str,
    type: ColumnType,
    nullable: bool = True,
    default: Optional[str] = None,
    primary_key: bool = False,
    unique: bool = False
)
```

**Parameters:**
- `name` (str): Column name
- `type` (ColumnType): SQLite column type. One of: "TEXT", "INTEGER", "REAL", "BLOB", "NUMERIC"
- `nullable` (bool, optional): Whether column allows NULL values. Default: True
- `default` (str, optional): Default value SQL expression
- `primary_key` (bool, optional): Whether this is a primary key. Default: False
- `unique` (bool, optional): Whether values must be unique. Default: False

**Example:**
```python
from cinchdb.models import Column

# Simple column
name_col = Column(name="username", type="TEXT", nullable=False)

# Column with default value
status_col = Column(name="status", type="TEXT", default="'active'")

# Unique column
email_col = Column(name="email", type="TEXT", unique=True)
```

## Manager Classes (Local Only)

Manager classes provide advanced operations for local connections. They are accessed through the CinchDB instance properties and are not available for remote connections.

### TableManager

Manages table operations.

Accessed via: `db.tables`

#### list_tables()

List all tables in the tenant.

```python
list_tables() -> List[Table]
```

**Returns:**
- `List[Table]`: List of Table objects

#### create_table()

Create a new table.

```python
create_table(table_name: str, columns: List[Column]) -> Table
```

**Parameters:**
- `table_name` (str): Name of the table
- `columns` (List[Column]): List of column definitions

**Returns:**
- `Table`: Created Table object

**Raises:**
- `ValueError`: If table already exists or uses protected column names
- `MaintenanceError`: If branch is in maintenance mode

#### get_table()

Get table information.

```python
get_table(table_name: str) -> Table
```

**Parameters:**
- `table_name` (str): Name of the table

**Returns:**
- `Table`: Table object with schema information

**Raises:**
- `ValueError`: If table doesn't exist

#### delete_table()

Delete a table.

```python
delete_table(table_name: str) -> None
```

**Parameters:**
- `table_name` (str): Name of the table to delete

**Raises:**
- `ValueError`: If table doesn't exist
- `MaintenanceError`: If branch is in maintenance mode

#### copy_table()

Copy a table to a new table.

```python
copy_table(
    source_table: str,
    dest_table: str,
    include_data: bool = True
) -> Table
```

**Parameters:**
- `source_table` (str): Name of source table
- `dest_table` (str): Name of destination table
- `include_data` (bool, optional): Whether to copy data. Default: True

**Returns:**
- `Table`: Created table object

### ColumnManager

Manages column operations within tables.

Accessed via: `db.columns`

#### list_columns()

List all columns in a table.

```python
list_columns(table_name: str) -> List[Column]
```

**Parameters:**
- `table_name` (str): Table name

**Returns:**
- `List[Column]`: List of Column objects

#### add_column()

Add a new column to a table.

```python
add_column(table_name: str, column: Column) -> None
```

**Parameters:**
- `table_name` (str): Table name
- `column` (Column): Column definition

**Raises:**
- `ValueError`: If table doesn't exist or column already exists
- `MaintenanceError`: If branch is in maintenance mode

#### drop_column()

Drop a column from a table.

```python
drop_column(table_name: str, column_name: str) -> None
```

**Parameters:**
- `table_name` (str): Table name
- `column_name` (str): Name of column to drop

**Raises:**
- `ValueError`: If table or column doesn't exist, or if column is protected
- `MaintenanceError`: If branch is in maintenance mode

#### rename_column()

Rename a column.

```python
rename_column(table_name: str, old_name: str, new_name: str) -> None
```

**Parameters:**
- `table_name` (str): Table name
- `old_name` (str): Current column name
- `new_name` (str): New column name

**Raises:**
- `ValueError`: If table or column doesn't exist, or if names are protected
- `MaintenanceError`: If branch is in maintenance mode

#### get_column_info()

Get information about a specific column.

```python
get_column_info(table_name: str, column_name: str) -> Column
```

**Parameters:**
- `table_name` (str): Table name
- `column_name` (str): Column name

**Returns:**
- `Column`: Column information

**Raises:**
- `ValueError`: If table or column doesn't exist

### QueryManager

Manages query execution.

Accessed via: `db.query()` method or directly for advanced use cases.

#### execute()

Execute a query and return results as dictionaries.

```python
execute(sql: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict[str, Any]]
```

**Parameters:**
- `sql` (str): SQL query
- `params` (Union[tuple, dict], optional): Query parameters

**Returns:**
- `List[Dict[str, Any]]`: Query results

#### execute_typed()

Execute a query and return results as model instances.

```python
execute_typed(
    sql: str,
    model_class: Type[T],
    params: Optional[Union[tuple, dict]] = None
) -> List[T]
```

**Parameters:**
- `sql` (str): SQL query
- `model_class` (Type[T]): Pydantic model class for results
- `params` (Union[tuple, dict], optional): Query parameters

**Returns:**
- `List[T]`: List of model instances

#### execute_one()

Execute a query and return a single result.

```python
execute_one(sql: str, params: Optional[Union[tuple, dict]] = None) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `sql` (str): SQL query
- `params` (Union[tuple, dict], optional): Query parameters

**Returns:**
- `Optional[Dict[str, Any]]`: Single result or None

#### execute_non_query()

Execute a non-SELECT query (INSERT, UPDATE, DELETE).

```python
execute_non_query(sql: str, params: Optional[Union[tuple, dict]] = None) -> int
```

**Parameters:**
- `sql` (str): SQL statement
- `params` (Union[tuple, dict], optional): Query parameters

**Returns:**
- `int`: Number of affected rows

#### execute_many()

Execute a query multiple times with different parameters.

```python
execute_many(sql: str, params_list: List[Union[tuple, dict]]) -> int
```

**Parameters:**
- `sql` (str): SQL statement
- `params_list` (List[Union[tuple, dict]]): List of parameter sets

**Returns:**
- `int`: Total number of affected rows

### DataManager

Manages data operations with model-based interface.

Accessed via: `db.data`

#### select()

Select records from a table with optional filtering.

```python
select(
    model_class: Type[T],
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    **filters
) -> List[T]
```

**Parameters:**
- `model_class` (Type[T]): Pydantic model class representing the table
- `limit` (int, optional): Maximum number of records
- `offset` (int, optional): Number of records to skip
- `**filters`: Column filters (supports operators like `column__gte`, `column__like`)

**Returns:**
- `List[T]`: List of model instances

**Example:**
```python
# Define a model
from pydantic import BaseModel

class User(BaseModel):
    id: str
    name: str
    email: str
    
    class Config:
        json_schema_extra = {"table_name": "users"}

# Select users
users = db.data.select(User, limit=10)

# With filters
active_users = db.data.select(User, active=True)

# With operators
recent_users = db.data.select(User, created_at__gte="2024-01-01")
```

#### find_by_id()

Find a single record by ID.

```python
find_by_id(model_class: Type[T], record_id: str) -> Optional[T]
```

**Parameters:**
- `model_class` (Type[T]): Model class
- `record_id` (str): Record ID

**Returns:**
- `Optional[T]`: Model instance or None

#### create()

Create a new record.

```python
create(instance: T) -> T
```

**Parameters:**
- `instance` (T): Model instance to create

**Returns:**
- `T`: Created instance with populated ID and timestamps

#### update()

Update an existing record.

```python
update(instance: T) -> T
```

**Parameters:**
- `instance` (T): Model instance with updated data (must have ID)

**Returns:**
- `T`: Updated instance

#### delete()

Delete records matching filters.

```python
delete(model_class: Type[T], **filters) -> int
```

**Parameters:**
- `model_class` (Type[T]): Model class
- `**filters`: Column filters

**Returns:**
- `int`: Number of deleted records

#### delete_by_id()

Delete a specific record by ID.

```python
delete_by_id(model_class: Type[T], record_id: str) -> bool
```

**Parameters:**
- `model_class` (Type[T]): Model class
- `record_id` (str): Record ID

**Returns:**
- `bool`: True if record was deleted

#### bulk_create()

Create multiple records in a single transaction.

```python
bulk_create(instances: List[T]) -> List[T]
```

**Parameters:**
- `instances` (List[T]): List of model instances

**Returns:**
- `List[T]`: Created instances with populated IDs and timestamps

#### count()

Count records matching filters.

```python
count(model_class: Type[T], **filters) -> int
```

**Parameters:**
- `model_class` (Type[T]): Model class
- `**filters`: Column filters

**Returns:**
- `int`: Number of matching records

### ViewModel

Manages database views.

Accessed via: `db.views`

#### list_views()

List all views.

```python
list_views() -> List[View]
```

**Returns:**
- `List[View]`: List of View objects

#### create_view()

Create a new view.

```python
create_view(name: str, query: str) -> View
```

**Parameters:**
- `name` (str): View name
- `query` (str): SQL query defining the view

**Returns:**
- `View`: Created view object

#### get_view()

Get view information.

```python
get_view(name: str) -> View
```

**Parameters:**
- `name` (str): View name

**Returns:**
- `View`: View object

#### delete_view()

Delete a view.

```python
delete_view(name: str) -> None
```

**Parameters:**
- `name` (str): View name

### BranchManager

Manages branch operations.

Accessed via: `db.branches`

#### list_branches()

List all branches.

```python
list_branches() -> List[Branch]
```

**Returns:**
- `List[Branch]`: List of Branch objects

#### create_branch()

Create a new branch.

```python
create_branch(name: str, from_branch: str = "main") -> Branch
```

**Parameters:**
- `name` (str): New branch name
- `from_branch` (str, optional): Source branch. Default: "main"

**Returns:**
- `Branch`: Created branch object

#### delete_branch()

Delete a branch.

```python
delete_branch(name: str) -> None
```

**Parameters:**
- `name` (str): Branch name to delete

#### get_current_branch()

Get the current branch name.

```python
get_current_branch() -> str
```

**Returns:**
- `str`: Current branch name

### TenantManager

Manages tenant operations.

Accessed via: `db.tenants`

#### list_tenants()

List all tenants in the branch.

```python
list_tenants() -> List[Tenant]
```

**Returns:**
- `List[Tenant]`: List of Tenant objects

#### create_tenant()

Create a new tenant.

```python
create_tenant(name: str) -> Tenant
```

**Parameters:**
- `name` (str): Tenant name

**Returns:**
- `Tenant`: Created tenant object

#### delete_tenant()

Delete a tenant.

```python
delete_tenant(name: str) -> None
```

**Parameters:**
- `name` (str): Tenant name to delete

#### get_current_tenant()

Get the current tenant name.

```python
get_current_tenant() -> str
```

**Returns:**
- `str`: Current tenant name

### CodegenManager

Manages code generation for database models.

Accessed via: `db.codegen`

#### generate_models()

Generate Pydantic models for database tables.

```python
generate_models(
    output_file: Optional[str] = None,
    include_tables: Optional[List[str]] = None,
    exclude_tables: Optional[List[str]] = None
) -> str
```

**Parameters:**
- `output_file` (str, optional): Output file path. If not provided, returns code as string
- `include_tables` (List[str], optional): Tables to include
- `exclude_tables` (List[str], optional): Tables to exclude

**Returns:**
- `str`: Generated Python code

### MergeManager

Manages branch merging operations.

Accessed via: `db.merge`

#### merge()

Merge changes from one branch into another.

```python
merge(
    from_branch: str,
    to_branch: str,
    strategy: str = "auto"
) -> MergeResult
```

**Parameters:**
- `from_branch` (str): Source branch
- `to_branch` (str): Target branch
- `strategy` (str, optional): Merge strategy. Default: "auto"

**Returns:**
- `MergeResult`: Result of merge operation

## Exceptions

### MergeError

Raised when a merge operation fails.

```python
from cinchdb.managers import MergeError

try:
    db.merge.merge("feature", "main")
except MergeError as e:
    print(f"Merge failed: {e}")
```

### MaintenanceError

Raised when attempting to modify a branch in maintenance mode.

```python
from cinchdb.core.maintenance import MaintenanceError

try:
    db.create_table("new_table", columns)
except MaintenanceError as e:
    print(f"Branch is in maintenance mode: {e}")
```

### ChangeError

Raised when a change operation fails.

```python
from cinchdb.managers.change_applier import ChangeError

try:
    # Change operations
    pass
except ChangeError as e:
    print(f"Change failed: {e}")
```
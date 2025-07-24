# CinchDB

**A Git-like SQLite database management system with branching and multi-tenancy**

CinchDB provides a simple Python SDK and CLI for managing SQLite databases with Git-like branching workflows and built-in multi-tenant architecture. Whether you need to manage database schema changes across environments or isolate tenant data, CinchDB makes it straightforward.

Here's a quick CLI example (the `cinchdb` Python package has all the same functionality):

```bash
pip install cinchdb

# simple initialization
cinch init 

# create, modify, and query tables
cinch table create users name:TEXT
cinch query 'select * from users'

# git-like branching
cinch branch create test
cinch branch switch test
cinch table create products name:TEXT
cinch branch switch main
cinch branch merge test # safe merges with atomic txns and rollback
cinch table list 
>> users, products

## tenant support
cinch tenant create lebron
cinch tenant list
>> main, lebron
cinch branch create new
cinch branch switch new
cinch tenant list # new branches have the same tenants and data
>> main, lebron

## built in API server
cinch-server serve # launch API
```

## What is CinchDB?

CinchDB is a database management system that combines the simplicity of SQLite with the power of version control workflows. It enables you to:

- **Branch database schemas** like you branch code - create feature branches, make changes, and merge them back
- **Manage multiple tenants** with isolated data but shared schema structure  
- **Track schema changes** automatically with built-in change management
- **Deploy remotely** using the included FastAPI server and API keys
- **Generate code** from your schemas with built-in Python/TypeScript model generation

### Key Features

- **Git-like branching**: Create feature branches for database changes, merge them when ready
- **Multi-tenant architecture**: Each branch supports multiple isolated tenants sharing the same schema
- **Automatic change tracking**: All schema modifications are tracked and can be merged between branches
- **Remote deployment**: Built-in FastAPI server with UUID-based API key authentication
- **Code generation**: Generate Python Pydantic models and TypeScript interfaces from your schemas
- **Rich CLI interface**: Comprehensive command-line interface with colored output and help
- **Python SDK**: Full-featured Python library for programmatic access
- **WAL mode SQLite**: Uses SQLite in WAL mode for better concurrency and performance

### Core Concepts

- **Project**: A local workspace containing your databases (stored in `.cinchdb/`)
- **Database**: A named collection of branches (default: "main") 
- **Branch**: An isolated development environment with its own schema (default: "main")
- **Tenant**: A data namespace within a branch - multiple tenants share schema but have isolated data (default: "main")
- **Changes**: Schema modifications are automatically tracked and can be merged between branches

### Architecture

CinchDB consists of six integrated components:

1. **Python SDK**: Core functionality that can operate locally or via remote API
2. **FastAPI API**: Remote server that exposes SDK functionality via REST endpoints  
3. **TypeScript SDK**: API client for Node.js backends and JavaScript webapps
4. **Python CLI**: Command-line interface built on the Python SDK
5. **NextJS Frontend**: Web interface for database exploration and management (soon)
6. **Documentation Site**: Unified documentation with tutorials and API references (soon)

## Installation

CinchDB requires Python 3.10+ and uses [uv](https://docs.astral.sh/uv/) for fast dependency management.

### Install uv (if not already installed)

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Via pip
pip install uv
```

### Install CinchDB

#### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/yourusername/cinchdb.git
cd cinchdb

# Install dependencies
uv sync

# Install CLI in editable mode
uv pip install -e .

# Verify installation
cinch --version
```

#### Production Install (coming soon)

```bash
# Via pip (when published to PyPI)
pip install cinchdb

# Via uv (when published to PyPI)  
uv add cinchdb
```

### Quick Start

```bash
# Initialize a new project
cinch init

# Create a table
cinch table create users name:TEXT email:TEXT

# Query the table
cinch query "SELECT * FROM users"

# Start the API server
cinch-server serve
```

## Basic Usage

### CLI Examples

#### Project Management
```bash
# Initialize a new project
cinch init

# Initialize in specific directory
cinch init /path/to/project

# Get project info
cinch info
```

#### Database Operations
```bash
# List databases
cinch db list

# Create new database
cinch db create myapp

# Switch active database
cinch db switch myapp

# Get database info
cinch db info
```

#### Branch Workflow
```bash
# List branches
cinch branch list

# Create feature branch
cinch branch create add-users --source main

# Switch to feature branch
cinch branch switch add-users

# Preview merge changes (dry run)
cinch branch merge add-users --target main --preview

# Merge into main branch
cinch branch merge-into-main add-users
```

#### Schema Management
```bash
# Create table with columns (format: name:type[:nullable])
# Columns are NOT NULL by default, add :nullable for optional columns
cinch table create users username:TEXT email:TEXT age:INTEGER

# List tables
cinch table list

# Add column to existing table
cinch column add users "phone" "TEXT"

# Create a view
cinch view create active_users \
  "SELECT * FROM users WHERE created_at > datetime('now', '-30 days')"

# List all schema objects
cinch table list
cinch view list
```

#### Multi-Tenant Operations
```bash
# List tenants
cinch tenant list

# Create new tenant
cinch tenant create customer_a

# Copy tenant with data
cinch tenant copy customer_a customer_b

# Query specific tenant
cinch query "SELECT * FROM users" --tenant customer_a

# Query with different output formats
cinch query "SELECT * FROM users" --format json --limit 10
cinch query "SELECT * FROM users" --format csv > users.csv
```

### Python SDK Examples

#### Local Database Connection
```python
import cinchdb
from cinchdb.models import Column

# Connect to local database
db = cinchdb.connect(
    database="myapp",
    branch="main", 
    tenant="customer_a"
)

# Execute queries
results = db.query("SELECT * FROM users WHERE age > ?", [21])
print(f"Found {len(results)} adult users")

# Create schema (for local connections)
if db.is_local:
    columns = [
        Column(name="title", type="TEXT"),
        Column(name="content", type="TEXT", nullable=True),
        Column(name="published", type="INTEGER", default="0")
    ]
    db.create_table("posts", columns)

# Data operations
user_id = db.insert("users", {
    "username": "alice",
    "email": "alice@example.com",
    "age": 25
})

# Update data
updated_user = db.update("users", user_id, {"age": 26})

# Switch contexts
dev_db = db.switch_branch("development")
customer_b_db = db.switch_tenant("customer_b")
```

#### Remote API Usage
```python
# Connect to remote CinchDB API
remote_db = cinchdb.connect_api(
    api_url="https://api.mycompany.com",
    api_key="your-api-key-here",
    database="production",
    branch="main",
    tenant="customer_a"
)

# Same interface as local
results = remote_db.query("SELECT COUNT(*) as user_count FROM users")
print(f"Production has {results[0]['user_count']} users")

# Context manager for automatic cleanup
with cinchdb.connect_api(url, key, "mydb") as db:
    results = db.query("SELECT * FROM users")
    # Connection automatically closed
```

### Complete Workflow Example

Here's a complete example showing a typical development workflow:

```bash
# 1. Initialize project
cinch init my_saas_app
cd my_saas_app

# 2. Create feature branch for user management
cinch branch create user-system --source main
cinch branch switch user-system

# 3. Create user-related tables
cinch table create users username:TEXT email:TEXT password_hash:TEXT is_active:INTEGER

cinch table create user_profiles user_id:TEXT first_name:TEXT:nullable last_name:TEXT:nullable avatar_url:TEXT:nullable

# 4. Create useful views
cinch view create active_users \
  "SELECT u.*, p.first_name, p.last_name 
   FROM users u 
   LEFT JOIN user_profiles p ON u.id = p.user_id 
   WHERE u.is_active = 1"

# 5. Create tenant for testing
cinch tenant create test_org

# 6. Test with some queries
cinch query "SELECT * FROM active_users LIMIT 5" --tenant test_org

# 7. Preview and merge changes
cinch branch merge user-system --target main --preview
cinch branch merge-into-main user-system

# 8. Switch back to main and verify
cinch branch switch main
cinch table list
cinch view list

# 9. Generate Python models for your application
cinch codegen generate python ./models/

# 10. Start API server for remote access
cinch-server serve
```

## Development

### Development Setup

CinchDB uses a monorepo structure with Python, TypeScript, and documentation components.

#### Prerequisites
- Python 3.10+
- Node.js 18+ (for TypeScript SDK and frontend)
- [uv](https://docs.astral.sh/uv/) for Python dependency management

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/russellromney/cinchdb.git
cd cinchdb

# Install all dependencies (Python + TypeScript + Frontend + Docs)
make install-all

# Or install components individually:
make install          # Python dependencies only
make install-dev      # CinchDB CLI in editable mode  
cd sdk/typescript && npm install    # TypeScript SDK
cd frontend && npm install          # Frontend dependencies
cd docs && npm install              # Documentation dependencies
```

#### Development Commands

```bash
# Start development environment
make dev              # Runs API server + frontend
make dev-api          # API server only
make dev-frontend     # Frontend only  
make dev-docs         # Documentation site only

# Run linting and formatting
make lint             # Lint all code (Python + TypeScript)
make format           # Format Python code with ruff
make typecheck        # Run mypy type checking

# Build everything
make build-all        # Build all components
make build-python     # Python package only
make build-ts         # TypeScript SDK only
make build-frontend   # Frontend only
make build-docs       # Documentation only
```

### Repository Structure

```
cinchdb/
├── src/cinchdb/         # Python package (SDK + CLI + API)
│   ├── models/          # Pydantic models  
│   ├── core/            # Core functionality (config, connection, paths)
│   ├── managers/        # Business logic (tables, branches, tenants, etc.)
│   ├── cli/             # CLI implementation
│   │   └── commands/    # CLI command modules
│   ├── api/             # FastAPI server
│   │   └── routers/     # API route modules
│   └── utils/           # Utility functions
├── sdk/typescript/      # TypeScript SDK for API access
├── frontend/            # NextJS web application  
├── docs/                # Documentation site
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── e2e/             # End-to-end tests  
│   └── fixtures/        # Test data and utilities
├── examples/            # Usage examples
├── scripts/             # Development and deployment scripts
├── pyproject.toml       # Python project configuration
├── Makefile            # Development commands
└── README.md           # This file
```

### Testing

CinchDB has a comprehensive test suite covering unit tests, integration tests, and end-to-end scenarios.

#### Run Tests

```bash
# Run all tests (Python + TypeScript)
make test

# Run Python tests only
make test-python

# Run unit tests only
make test-unit

# Run integration tests only  
make test-integration

# Run TypeScript SDK tests
make test-ts

# Run tests with coverage
make coverage
```

#### Test Organization

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions and CLI workflows  
- **End-to-End Tests** (`tests/e2e/`): Test complete user scenarios
- **Fixtures** (`tests/fixtures/`): Shared test data and utilities

#### Running Specific Tests

```bash
# Run specific test file
uv run pytest tests/unit/test_table_manager.py -v

# Run tests matching pattern
uv run pytest tests/ -k "test_create_table" -v

# Run tests with coverage for specific module
uv run pytest tests/unit/test_branch_manager.py --cov=cinchdb.managers.branch --cov-report=html

# Run integration tests with detailed output
uv run pytest tests/integration/ -v --tb=short
```

### Code Quality

The project maintains high code quality standards with automated linting and formatting.

#### Code Quality Commands

```bash
# Check code style and linting
make lint-python        # Python linting with ruff
make lint-ts           # TypeScript linting  
make lint-frontend     # Frontend linting

# Format code
make format-python     # Format Python code with ruff

# Type checking
make typecheck-python  # Type check with mypy
```

#### Pre-commit Workflow

Before committing changes:

```bash
# Check everything is working
make test              # All tests pass
make lint              # No linting issues
make typecheck         # Type checking passes
make format            # Code is properly formatted
```

## API Reference

### CLI Commands

CinchDB CLI provides comprehensive database management through intuitive commands:

- `cinch init` - Initialize new project
- `cinch db` - Database management (list, create, delete, info, switch)
- `cinch branch` - Branch operations (list, create, delete, switch, merge)
- `cinch tenant` - Tenant management (list, create, delete, rename, copy)
- `cinch table` - Table operations (list, create, delete, copy, info)
- `cinch column` - Column management (list, add, drop, rename, info) 
- `cinch view` - View operations (list, create, update, delete, info)
- `cinch query` - Execute SQL queries with multiple output formats
- `cinch codegen` - Generate models from database schemas
- `cinch-server serve` - Start the API server

Use `cinch --help` or `cinch <command> --help` for detailed usage information.

### Python SDK

The Python SDK provides a clean, unified interface for all database operations:

#### Connection Functions
- `cinchdb.connect()` - Connect to local database
- `cinchdb.connect_api()` - Connect to remote CinchDB API

#### Database Interface
The `CinchDB` class (returned by connect functions) provides:
- **Query execution**: `db.query()` for SQL queries
- **Data operations**: `db.insert()`, `db.update()`, `db.delete()`
- **Schema management**: `db.create_table()` (local only)
- **Context switching**: `db.switch_branch()`, `db.switch_tenant()`
- **Type safety**: Full type hints and IDE support

### REST API

The FastAPI server provides endpoints for remote CinchDB operations:

- **Authentication**: UUID-based API keys with read/write permissions
- **Documentation**: Interactive API docs at `/docs` and `/redoc`
- **Health Check**: System status at `/health`

Start the server with `cinch-server serve` and visit `http://localhost:8000/docs` for interactive documentation.

## Contributing

We welcome contributions! Please see our contributing guidelines and code of conduct.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make test lint`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Full documentation](https://cinchdb.readthedocs.io) (coming soon)
- **Issues**: [GitHub Issues](https://github.com/yourusername/cinchdb/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cinchdb/discussions)

## Roadmap

- [ ] Enhanced frontend
- [ ] TypeScript SDK with full feature parity
- [ ] Cloud deployment templates (Docker, Kubernetes)
- [ ] Backup and restore functionality

---

**CinchDB** - Making database management as easy as version control.
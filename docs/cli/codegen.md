# Code Generation - Your ORM Replacement

CinchDB's code generation replaces traditional ORMs with type-safe models that perfectly match your database schema. Since CinchDB doesn't expose raw SQLite connections, generated models are **the primary way** to interact with your database programmatically.

## Why Use Generated Models Instead of ORMs?

**🚫 Traditional ORMs Don't Work**: CinchDB abstracts SQLite connections for security and multi-tenancy, so SQLAlchemy, Tortoise ORM, etc. can't be used.

**✅ Perfect Type Safety**: Generated models match your exact schema - no generic ORM abstractions that might be wrong.

**✅ Always In Sync**: Regenerate models when your schema changes. No more runtime errors from schema mismatches.

**✅ Full CRUD Operations**: Create, read, update, delete operations generated for every table.

**✅ Framework Agnostic**: Use with FastAPI, Flask, Express.js, Next.js - works anywhere.

## languages

List supported code generation languages.

```bash
cinch codegen languages
```

### Example Output
```
Supported languages:
• python - Python dataclasses with type hints
• typescript - TypeScript interfaces and types
```

## generate

Generate model code for tables and views. For Python, this creates a complete SDK with type-safe CRUD operations.

```bash
cinch codegen generate LANGUAGE [OPTIONS]
```

### Arguments
- `LANGUAGE` - Target language (python, typescript)

### Options
- `--output DIR` - Output directory (default: `./generated`)
- `--tables/--no-tables` - Include tables (default: true)
- `--views/--no-views` - Include views (default: true)

### Examples

#### Python Generation
```bash
# Generate Python models
cinch codegen generate python

# Custom output directory
cinch codegen generate python --output ./src/models

# Tables only
cinch codegen generate python --no-views
```

#### TypeScript Generation
```bash
# Generate TypeScript interfaces
cinch codegen generate typescript

# Custom output
cinch codegen generate typescript --output ./src/types
```

## Generated Code Examples

### Python Models

For a table:
```sql
CREATE TABLE users (
  name TEXT,
  email TEXT,
  active BOOLEAN
)
```

Generates:
```python
# generated/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    """Model for users table"""
    id: str
    name: Optional[str]
    email: Optional[str]
    active: Optional[bool]
    created_at: datetime
    updated_at: datetime
    
    __tablename__ = "users"
```

### TypeScript Interfaces

Generates:
```typescript
// generated/models.ts
export interface User {
  id: string;
  name: string | null;
  email: string | null;
  active: boolean | null;
  created_at: string;
  updated_at: string;
}

export type UserInput = Omit<User, 'id' | 'created_at' | 'updated_at'>;
```

## Using Generated Code

### Python SDK with CRUD Operations

The Python code generation creates a complete SDK with type-safe CRUD operations:

```python
# generated/__init__.py provides everything you need
from generated import cinch_models

# Connect to your database
db = cinchdb.connect("myapp")
models = cinch_models(db)

# Access your models with full CRUD operations
User = models.User

# Create
new_user = User.create(name="Alice", email="alice@example.com", active=True)

# Read
user = User.get(new_user["id"])
all_users = User.get_all()
active_users = User.filter(active=True)

# Update
User.update(user["id"], email="newemail@example.com")

# Delete
User.delete(user["id"])

# Advanced queries
users_named_alice = User.filter(name="Alice")
users_with_email = User.filter(email__like="%@example.com")
```

### Traditional Python Usage
```python
from generated.models import User
import cinchdb

# Type-safe operations
db = cinchdb.connect("myapp")

# Insert with type checking
user = User(
    id="123",
    name="Alice",
    email="alice@example.com",
    active=True,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Query returns typed results
users: List[User] = db.query("SELECT * FROM users")
```

### TypeScript Usage
```typescript
import { User, UserInput } from './generated/models';
import { CinchDB } from '@cinchdb/client';

const db = new CinchDB({
  url: 'https://api.example.com',
  apiKey: 'your-key'
});

// Type-safe insert
const newUser: UserInput = {
  name: 'Alice',
  email: 'alice@example.com',
  active: true
};

// Typed query results
const users: User[] = await db.query<User>('SELECT * FROM users');
```

## Advanced Features

### Custom Templates

Create `.cinchdb/templates/` for custom generation:

```bash
mkdir -p .cinchdb/templates/python
# Add custom Jinja2 templates
```

### Include/Exclude Patterns

```bash
# Generate only specific tables
cinch codegen generate python --include users,products

# Exclude tables
cinch codegen generate python --exclude temp_*
```

## Multi-Branch Codegen

Generate from different branches:

```bash
# Generate from feature branch
cinch branch switch feature.new-schema
cinch codegen generate python --output ./src/models/feature

# Generate from main
cinch branch switch main  
cinch codegen generate python --output ./src/models/main
```

## Integration Patterns

### Python Project Structure
```
myproject/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── generated.py  # Generated by CinchDB
│   └── app.py
├── .cinchdb/
└── pyproject.toml
```

### TypeScript Project Structure
```
myproject/
├── src/
│   ├── types/
│   │   └── generated.ts  # Generated by CinchDB
│   ├── api/
│   └── app.ts
├── .cinchdb/
└── package.json
```

## Regeneration Workflow

```bash
# Make schema changes
cinch table create orders user_id:TEXT total:REAL
cinch column add users phone:TEXT

# Regenerate models
cinch codegen generate python

# Diff shows changes
git diff generated/
```

## Best Practices

1. **Version Control**
   - Commit generated files
   - Review changes in PRs
   - Regenerate after schema changes

2. **CI/CD Integration**
   ```yaml
   # .github/workflows/codegen.yml
   - name: Generate models
     run: cinch codegen generate python
   
   - name: Check for changes
     run: git diff --exit-code generated/
   ```

3. **Type Safety**
   - Use generated types everywhere
   - Enable strict type checking
   - Avoid type assertions

4. **Organization**
   - Keep generated code separate
   - Don't edit generated files
   - Use clear output paths

## Remote Codegen

Generate from remote databases:

```bash
```

## Customization Options

### Python Options
- `--dataclass` - Use dataclasses (default)
- `--pydantic` - Generate Pydantic models
- `--sqlalchemy` - Generate SQLAlchemy models

### TypeScript Options
- `--interfaces` - Generate interfaces (default)
- `--classes` - Generate classes
- `--zod` - Include Zod schemas

## Troubleshooting

### Common Issues

1. **Missing tables/views**
   - Check current branch
   - Verify table exists: `cinch table list`

2. **Import errors**
   - Ensure output path is in Python path
   - Check generated `__init__.py`

3. **Type mismatches**
   - Regenerate after schema changes
   - Check nullable fields

## Next Steps

- [Python SDK](../python-sdk/index.md) - Use generated models
- [Python SDK API Reference](../python-sdk/api-reference.md) - Complete API documentation
- [Branching](../concepts/branching.md) - Multi-branch development
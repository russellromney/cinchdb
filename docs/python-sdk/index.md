# Python SDK

Connect to databases, manage schema, run queries.

```bash
pip install cinchdb
```

## Basic Usage

```python
import cinchdb
from cinchdb.models import Column

db = cinchdb.connect("myapp")

# Create table
db.create_table("users", [
    Column(name="name", type="TEXT"),
    Column(name="email", type="TEXT", unique=True)
])

# Insert data
user = db.insert("users", {"name": "Alice", "email": "alice@example.com"})

# Query data
users = db.query("SELECT * FROM users WHERE name = ?", ["Alice"])

# Update/delete
db.update("users", user["id"], {"name": "Alice Smith"})
db.delete("users", user["id"])
```

## Common Tasks

### Connect to Different Contexts
```python
# Different database
db = cinchdb.connect("analytics") 

# Different branch  
dev_db = cinchdb.connect("myapp", branch="development")

# Different tenant
customer_db = cinchdb.connect("myapp", tenant="customer_a")

# Specific project directory
db = cinchdb.connect("myapp", project_dir="/path/to/project")
```

### Batch Operations
```python
# Insert multiple records
users = db.insert("users",
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Carol", "email": "carol@example.com"},
    {"name": "Dave", "email": "dave@example.com"}
)

# Create table with indexes
db.create_table("products", [
    Column(name="name", type="TEXT"),
    Column(name="price", type="REAL"),
    Column(name="category", type="TEXT")
])
db.create_index("products", ["category", "price"])
```

### Error Handling
```python
try:
    db.create_table("users", columns)
    db.insert("users", {"name": "John", "email": "john@example.com"})
except Exception as e:
    print(f"Error: {e}")
```

## Quick Reference

| Task | Method |
|------|--------|
| Connect | `cinchdb.connect("db", branch="main", tenant="main")` |
| Create table | `db.create_table(name, columns)` |
| Insert | `db.insert(table, data1, data2, ...)` |
| Update | `db.update(table, id, data)` |
| Delete | `db.delete(table, id)` |
| Query | `db.query(sql, params)` |
| Index | `db.create_index(table, columns, unique=False)` |

## Column Types

- `"TEXT"` - String data
- `"INTEGER"` - Whole numbers  
- `"REAL"` - Decimal numbers
- `"BOOLEAN"` - True/false values
- `"BLOB"` - Binary data

Every table automatically gets `id`, `created_at`, and `updated_at` fields.

## More Information

- [Connection Details](connection.md)  
- [Table Operations](tables.md)
- [Query Examples](queries.md)
- [Complete API](api-reference.md)
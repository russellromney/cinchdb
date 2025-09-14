# Naming Conventions

CinchDB enforces consistent naming conventions across all entities to ensure compatibility, security, and maintainability.

## General Rules

All names in CinchDB must:
- Be between 1 and 63 characters long
- Use only lowercase letters
- Not contain null bytes or control characters
- Not use Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)

## Entity-Specific Rules

### Projects, Databases, Branches, and Tenants

These entities can use:
- **Allowed characters**: lowercase letters (a-z), numbers (0-9), hyphens (-), underscores (_)
- **Start/End**: Must start and end with alphanumeric characters (letter or number)
- **Special rules**: Cannot contain consecutive special characters (e.g., `--`, `__`, `-_`, `_-`)

✅ Valid examples:
- `my-database`
- `feature-123`
- `test_db_v2`
- `db123`
- `2024-backup`

❌ Invalid examples:
- `My-Database` (uppercase not allowed)
- `-database` (cannot start with hyphen)
- `database-` (cannot end with hyphen)
- `my--database` (consecutive special characters)
- `my.database` (periods not allowed)

### Tables and Columns

Tables and columns have stricter rules to avoid SQL quoting issues:
- **Allowed characters**: lowercase letters (a-z), numbers (0-9), underscores (_)
- **Start**: Must start with a lowercase letter (a-z)
- **End**: Must end with a letter or number
- **No hyphens**: Hyphens are not allowed in table or column names

✅ Valid examples:
- `users`
- `user_profiles`
- `order_items_2024`
- `col123`
- `created_at`

❌ Invalid examples:
- `123_table` (cannot start with number)
- `_private` (cannot start with underscore)
- `user-profiles` (hyphens not allowed)
- `table_` (cannot end with underscore)
- `User_Profiles` (uppercase not allowed)

### Protected Names

The following naming patterns are reserved and cannot be used:

#### Protected Prefixes
- `__` (double underscore) - Reserved for system tables
- `sqlite_` - Reserved for SQLite internal tables

#### Protected Column Names
- `id` - Auto-generated primary key
- `created_at` - Auto-generated timestamp
- `updated_at` - Auto-generated timestamp

## Security Considerations

Names are validated to prevent:
- **Path traversal attacks**: Names containing `..`, `/`, `\`, or `~` are rejected
- **SQL injection**: Special characters that could break SQL syntax are not allowed
- **Filesystem issues**: Names are limited to 63 characters to ensure compatibility across all filesystems

## Best Practices

1. **Be descriptive**: Use clear, meaningful names like `customer_orders` instead of `co`
2. **Be consistent**: Follow a naming pattern throughout your project
3. **Use underscores for separation**: `user_profiles` is preferred over `userprofiles`
4. **Include version info when needed**: `schema_v2` or `backup_2024`
5. **Keep it simple**: Avoid overly complex names that are hard to type

## Error Messages

When a name validation fails, CinchDB provides helpful error messages:
- Suggests lowercase version for uppercase names
- Explains which characters are not allowed
- Indicates if a name is reserved
- Warns about security violations (path traversal attempts)

## Examples

```python
from cinchdb import Database

# Valid database and table names
db = Database("my-app-db")  # Hyphens OK for databases
table = db.create_table("user_accounts")  # Underscores for tables

# Invalid names will raise errors
db.create_table("user-accounts")  # Error: hyphens not allowed in tables
db.create_table("123users")  # Error: must start with letter
db.create_table("__system")  # Error: __ prefix is reserved
```
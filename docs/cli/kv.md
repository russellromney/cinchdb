# KV Store Commands

Redis-like key-value storage for fast unstructured data access with TTL support and atomic operations.

## Overview

CinchDB's built-in key-value store provides high-performance storage for unstructured data alongside your relational tables. Perfect for sessions, caching, feature flags, and counters.

### Key Features
- ⚡ **Sub-millisecond operations** - < 1ms single operations
- 🔄 **Atomic operations** - Thread-safe increment/decrement
- ⏰ **TTL support** - Automatic expiration for temporary data
- 🔍 **Pattern matching** - Redis-style glob patterns
- 📦 **Multi-type storage** - Preserves booleans, numbers, JSON, binary
- 🏢 **Multi-tenant isolation** - Each tenant has separate KV store
- 🚫 **CDC excluded** - KV operations not tracked by change capture

## Commands

### `cinch kv set`

Set a key-value pair with optional TTL.

#### Basic Usage

```bash
$ cinch kv set user:123 '{"name": "Alice", "role": "admin"}'
```
**Expected output:**
```
✓ Key 'user:123' set successfully
```

#### With TTL (Auto-expiration)

```bash
$ cinch kv set session:abc "session_data" --ttl 3600
```
**Expected output:**
```
✓ Key 'session:abc' set with TTL of 3600 seconds
```

#### Different Value Types

```bash
# Number (preserved as integer or float)
$ cinch kv set counter 42
✓ Key 'counter' set successfully

# Boolean (returns as true/false, not 1/0)
$ cinch kv set feature:enabled true
✓ Key 'feature:enabled' set successfully

# JSON object
$ cinch kv set config '{"timeout": 30, "retries": 3}'
✓ Key 'config' set successfully

# Keys with spaces (quote them!)
$ cinch kv set "user settings" "dark mode"
✓ Key 'user settings' set successfully
```

#### Options

| Option | Description | Default |
|--------|-------------|----------|
| `--ttl INTEGER` | Time-to-live in seconds | None (permanent) |
| `--database TEXT` | Database name | From context |
| `--branch TEXT` | Branch name | main |
| `--tenant TEXT` | Tenant name | main |

#### Common Errors

```bash
$ cinch kv set "" value
✗ Error: Key must be a non-empty string

$ cinch kv set __system value
✗ Error: Keys cannot start with '__' (reserved for system use)

$ cinch kv set "key\nwith\nnewline" value
✗ Error: Key cannot contain newlines, tabs, or null bytes
```

**Performance:** < 1ms for single set operation

### `cinch kv get`

Retrieve a value by key.

```bash
cinch kv get user:123
# Output: {"name": "Alice", "role": "admin"}

cinch kv get "user settings"  # Keys with spaces need quotes
# Output: preferences

cinch kv get nonexistent
# Output: null (key doesn't exist or is expired)
```

### `cinch kv delete`

Delete one or more keys.

```bash
# Single key
cinch kv delete session:old

# Multiple keys
cinch kv delete key1 key2 key3

# Pattern-based deletion
cinch kv keys "temp:*" | xargs cinch kv delete
```

**Output:** Number of keys deleted

### `cinch kv exists`

Check if a key exists and is not expired.

```bash
cinch kv exists user:123
# Output: true

cinch kv exists nonexistent
# Output: false
```

### `cinch kv keys`

List keys matching a pattern.

```bash
# List all keys
cinch kv keys

# Pattern matching (Redis-style glob)
cinch kv keys "user:*"        # All user keys
cinch kv keys "*:session"      # All session keys
cinch kv keys "cache:api:*"    # Nested namespace
```

**Pattern syntax:**
- `*` matches any sequence of characters
- `?` matches a single character
- `[abc]` matches any character in the set

### `cinch kv ttl`

Get remaining TTL for a key.

```bash
cinch kv ttl session:abc
# Output: 3542 (seconds remaining)

cinch kv ttl permanent_key
# Output: null (no expiration set)

cinch kv ttl expired_key
# Output: -1 (expired or doesn't exist)
```

### `cinch kv expire`

Set or update TTL for an existing key.

```bash
# Set key to expire in 1 hour
cinch kv expire important_data 3600
# Output: true (TTL set)

cinch kv expire nonexistent 3600
# Output: false (key doesn't exist)
```

### `cinch kv persist`

Remove TTL from a key, making it permanent.

```bash
cinch kv persist session:abc
# Output: true (TTL removed)

cinch kv persist permanent_key
# Output: false (no TTL to remove)
```

### `cinch kv increment`

Atomically increment a numeric value.

```bash
# Increment by 1 (default)
cinch kv increment page:views
# Output: 1 (if new) or current value + 1

# Increment by specific amount
cinch kv increment api:calls --by 5
# Output: new value after increment

# Create and set initial value if doesn't exist
cinch kv increment new:counter
# Output: 1
```

**Options:**
- `--by INTEGER`: Amount to increment (default: 1, can be negative)

### `cinch kv mset`

Set multiple key-value pairs atomically.

```bash
# From JSON file
cat > data.json << EOF
{
  "config:debug": true,
  "config:timeout": 30,
  "config:url": "https://api.example.com"
}
EOF

cinch kv mset --file data.json

# With TTL for all keys
cinch kv mset --file data.json --ttl 3600
```

### `cinch kv mget`

Get multiple values at once.

```bash
cinch kv mget key1 key2 key3
# Output: JSON object with all key-value pairs

cinch kv mget config:debug config:timeout
# Output: {"config:debug": true, "config:timeout": 30}
```

**Note:** Raises error if any key doesn't exist.

### `cinch kv count`

Count keys matching a pattern.

```bash
cinch kv count           # Total key count
# Output: 42

cinch kv count "user:*"  # Count matching pattern
# Output: 15
```

### `cinch kv size`

Get storage size information.

```bash
cinch kv size            # Total storage size
# Output: {"total": 10240} (bytes)

cinch kv size key1 key2  # Size of specific keys
# Output: {"key1": 512, "key2": 1024}
```

### `cinch kv cleanup`

Delete all expired keys from storage.

```bash
cinch kv cleanup
# Output: 5 (number of expired keys removed)
```

## Key Naming Rules

- **Maximum 255 characters**
- **Must contain only printable characters**
- **Cannot contain newlines, tabs, or null bytes**
- **Cannot start with `__` (reserved for system use)**
- **Spaces ARE allowed** (use quotes in CLI)

### Valid Key Examples

```bash
# Natural language (use quotes for spaces)
cinch kv set "shopping cart" '["item1", "item2"]'
cinch kv set "user profile" '{"name": "John"}'

# Namespace patterns
cinch kv set user:123:profile "data"
cinch kv set api/v2/response "cached"
cinch kv set feature.flags.dark-mode true

# Special characters
cinch kv set "email@domain.com" "user_id"
cinch kv set "price_in_$USD" 99.99
cinch kv set "50%_discount" true

# Even emojis work
cinch kv set "status_🚀" "launched"
```

## Common Use Cases

### Session Management

```bash
# Create session with 1-hour TTL
cinch kv set session:abc123 '{"user_id": 42, "ip": "192.168.1.1"}' --ttl 3600

# Check if session exists
cinch kv exists session:abc123

# Extend session
cinch kv expire session:abc123 3600

# End session
cinch kv delete session:abc123
```

### Rate Limiting

```bash
# Track API calls per minute
cinch kv set "rate:user:123" 0 --ttl 60
cinch kv increment "rate:user:123"

# Check current count
cinch kv get "rate:user:123"
```

### Feature Flags

```bash
# Set feature flags
cinch kv set feature:dark-mode true
cinch kv set feature:beta-ui false

# List all features
cinch kv keys "feature:*"

# Check specific feature
cinch kv get feature:dark-mode
```

### Caching

```bash
# Cache API response for 5 minutes
cinch kv set "cache:api:/users/123" '{"id": 123, "name": "Alice"}' --ttl 300

# Check if cached
cinch kv exists "cache:api:/users/123"

# Clear cache pattern
cinch kv keys "cache:api:*" | xargs cinch kv delete
```

## Performance Characteristics

- **Single operations**: < 1ms
- **Batch operations**: ~1ms per 100 items
- **Pattern matching**: O(n) where n = total keys
- **Storage overhead**: ~100 bytes per key

## Important Notes

1. **CDC Exclusion**: KV operations are NOT tracked by Change Data Capture
2. **Multi-tenant**: Each tenant has its own isolated KV store
3. **Branch-independent**: KV data is not affected by branch operations
4. **Persistence**: KV data is stored in the `__kv` system table
5. **Type preservation**: Values maintain their type (boolean, number, etc.)

## Troubleshooting

### "Key must be a non-empty string"
Ensure your key is not empty and is a valid string.

### "Key cannot start with '__'"
Keys starting with double underscore are reserved for system use.

### "Key cannot contain newlines, tabs, or null bytes"
Use only printable characters in keys.

### "Keys not found" (mget)
When using `mget`, all requested keys must exist. Use individual `get` commands if keys might be missing.
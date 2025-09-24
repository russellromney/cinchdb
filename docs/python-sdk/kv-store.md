# Key-Value Store

High-performance Redis-like key-value storage with TTL support, atomic operations, and type preservation.

## Overview

The KV store provides a fast, unstructured data storage layer alongside your relational tables. It's perfect for:

- 🔐 **Session management** - Store user sessions with auto-expiration
- ⚡ **Caching** - Speed up responses with cached data
- 🎛️ **Feature flags** - Toggle features without deployments
- 📊 **Counters & metrics** - Atomic increments for analytics
- 🔄 **Temporary data** - Auto-cleanup with TTL support

## Getting Started

```python
import cinchdb

# Connect to database
db = cinchdb.connect("myapp")

# Store and retrieve data
db.kv.set("user:123", {"name": "Alice", "role": "admin"})
user = db.kv.get("user:123")
print(user)  # {'name': 'Alice', 'role': 'admin'}
```

## Core Operations

### Setting Values

Store any JSON-serializable data with optional TTL.

#### Basic Usage

```python
# Store different data types
db.kv.set("string_key", "Hello World")
db.kv.set("number_key", 42)
db.kv.set("bool_key", True)  # Stored as boolean, not 1
db.kv.set("json_key", {"nested": {"data": [1, 2, 3]}})
db.kv.set("binary_key", b"raw bytes")
```

**Expected behavior:**
- Values are stored with type preservation
- Booleans return as `True`/`False`, not `1`/`0`
- Binary data stored without base64 encoding

#### With TTL (Time-To-Live)

```python
# Session expires in 1 hour
db.kv.set("session:abc", {"user_id": 123}, ttl=3600)

# Cache API response for 5 minutes
db.kv.set("cache:users", user_list, ttl=300)
```

**Expected output:**
```python
# After TTL expires
result = db.kv.get("session:abc")
print(result)  # None (automatically cleaned up)
```

### Getting Values

Retrieve values with automatic type preservation.

```python
# Get existing key
user = db.kv.get("user:123")
print(user)  # {'name': 'Alice', 'role': 'admin'}

# Get with proper type
count = db.kv.get("counter")
print(count, type(count))  # 42 <class 'int'>

enabled = db.kv.get("feature:enabled")
print(enabled, type(enabled))  # True <class 'bool'>

# Non-existent or expired keys return None
result = db.kv.get("missing_key")
print(result)  # None
```

### Deleting Keys

```python
# Delete single key
deleted = db.kv.delete("old_session")
print(f"Deleted {deleted} key(s)")  # Deleted 1 key(s)

# Delete multiple keys
deleted = db.kv.delete("key1", "key2", "key3")
print(f"Deleted {deleted} key(s)")  # Returns actual count

# Delete from list
keys_to_delete = ["temp1", "temp2", "temp3"]
deleted = db.kv.delete(*keys_to_delete)
```

## Batch Operations

### Multiple Set (mset)

Set multiple key-value pairs atomically.

```python
# All keys set in single transaction
db.kv.mset({
    "config:debug": True,
    "config:timeout": 30,
    "config:api_url": "https://api.example.com",
    "config:features": ["auth", "api", "webhooks"]
})
```

**Performance:** ~2ms for 100 items

#### With TTL for all keys

```python
# All keys expire together
db.kv.mset({
    "cache:user:1": user1_data,
    "cache:user:2": user2_data,
    "cache:user:3": user3_data
}, ttl=300)  # 5-minute cache
```

### Multiple Get (mget)

Get multiple values in one operation.

```python
# Get multiple keys at once
configs = db.kv.mget(["config:debug", "config:timeout", "config:api_url"])
print(configs)
# {
#   "config:debug": True,
#   "config:timeout": 30,
#   "config:api_url": "https://api.example.com"
# }
```

**Important:** `mget` raises `ValueError` if any key is missing:

```python
try:
    result = db.kv.mget(["exists", "missing"])
except ValueError as e:
    print(e)  # "Keys not found: ['missing']"
```

## Atomic Operations

### Increment

Thread-safe atomic increments without race conditions.

```python
# Increment by 1 (default)
views = db.kv.increment("page:views")
print(views)  # 1 (if new) or current + 1

# Increment by specific amount
views = db.kv.increment("page:views", 5)
print(views)  # 6

# Decrement using negative values
stock = db.kv.increment("inventory:item123", -1)
print(stock)  # Decreased by 1
```

**Type Safety:**
```python
# Can't increment non-numeric values
db.kv.set("text_key", "hello")
try:
    db.kv.increment("text_key")
except ValueError as e:
    print(e)  # "Cannot increment non-numeric value"

# Booleans can't be incremented (they're not numbers!)
db.kv.set("bool_key", True)
try:
    db.kv.increment("bool_key")
except ValueError as e:
    print(e)  # "Cannot increment non-numeric value"
```

## Pattern Matching

### List Keys

Find keys using Redis-style glob patterns.

```python
# Set some example keys
db.kv.set("user:1:profile", {"name": "Alice"})
db.kv.set("user:2:profile", {"name": "Bob"})
db.kv.set("user:1:settings", {"theme": "dark"})
db.kv.set("session:abc", {"user": 1})

# List all keys
all_keys = db.kv.keys()
print(all_keys)  # ['session:abc', 'user:1:profile', 'user:1:settings', 'user:2:profile']

# Pattern matching
user_profiles = db.kv.keys("user:*:profile")
print(user_profiles)  # ['user:1:profile', 'user:2:profile']

user1_keys = db.kv.keys("user:1:*")
print(user1_keys)  # ['user:1:profile', 'user:1:settings']
```

**Pattern Syntax:**
- `*` matches any sequence of characters
- `?` matches single character
- `[abc]` matches any character in set

### Count Keys

```python
# Count all keys
total = db.kv.key_count()
print(f"Total keys: {total}")

# Count matching pattern
user_count = db.kv.key_count("user:*")
print(f"User keys: {user_count}")
```

## TTL Management

### Check TTL

```python
# Set key with TTL
db.kv.set("temp_data", "value", ttl=300)

# Check remaining TTL
remaining = db.kv.ttl("temp_data")
print(f"Expires in {remaining} seconds")  # e.g., 298

# Permanent key (no TTL)
ttl = db.kv.ttl("permanent_key")
print(ttl)  # None

# Expired or non-existent
ttl = db.kv.ttl("expired_key")
print(ttl)  # -1
```

### Update TTL

```python
# Add/update expiration
success = db.kv.expire("important_data", 86400)  # 24 hours
print(success)  # True if key exists

# Remove expiration (make permanent)
success = db.kv.persist("session:abc")
print(success)  # True if TTL was removed
```

## Advanced Features

### Set If Not Exists (setnx)

Perfect for distributed locks and race condition prevention.

```python
# Only sets if key doesn't exist
acquired = db.kv.setnx("lock:resource", "locked", ttl=30)
if acquired:
    try:
        # Do work with exclusive access
        process_resource()
    finally:
        db.kv.delete("lock:resource")
else:
    print("Resource is locked by another process")
```

### Storage Information

```python
# Get total storage size
size = db.kv.storage_size()
print(size)  # {'total': 10240} bytes

# Get size of specific keys
sizes = db.kv.storage_size("large_key1", "large_key2")
print(sizes)  # {'large_key1': 5120, 'large_key2': 3072}
```

### Cleanup Expired Keys

```python
# Remove all expired keys
deleted = db.kv.delete_expired()
print(f"Cleaned up {deleted} expired keys")
```

## Key Naming Rules

### Validation Rules

- ✅ **Maximum 255 characters**
- ✅ **Must contain only printable characters**
- ❌ **Cannot contain newlines, tabs, or null bytes**
- ❌ **Cannot start with `__` (reserved)**
- ✅ **Spaces ARE allowed** (Redis-compatible)

### Valid Examples

```python
# Natural language keys (spaces allowed!)
db.kv.set("shopping cart", ["item1", "item2"])
db.kv.set("user preferences", {"theme": "dark"})

# Hierarchical namespaces
db.kv.set("app:module:component:key", "value")
db.kv.set("tenant/123/settings", {})

# Special characters
db.kv.set("email@domain.com", "user_123")
db.kv.set("price_in_$USD", 99.99)
db.kv.set("50%_discount!", True)

# Even emojis work
db.kv.set("status_🚀", "launched")
```

### Invalid Examples

```python
# These will raise ValueError
db.kv.set("", "value")           # Empty key
db.kv.set("__system", "value")   # Starts with __
db.kv.set("key\nwith\nnewline", "value")  # Contains newline
db.kv.set("k" * 256, "value")    # Exceeds 255 chars
```

## Common Use Cases

### Session Management

```python
import secrets
import json
from datetime import datetime

class SessionManager:
    def __init__(self, db, ttl=3600):
        self.db = db
        self.ttl = ttl

    def create_session(self, user_id, ip_address):
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "user_id": user_id,
            "ip": ip_address,
            "created": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }

        self.db.kv.set(f"session:{session_id}", session_data, ttl=self.ttl)
        return session_id

    def get_session(self, session_id):
        return self.db.kv.get(f"session:{session_id}")

    def refresh_session(self, session_id):
        session = self.get_session(session_id)
        if session:
            session["last_activity"] = datetime.now().isoformat()
            self.db.kv.set(f"session:{session_id}", session, ttl=self.ttl)
            return True
        return False

    def end_session(self, session_id):
        return self.db.kv.delete(f"session:{session_id}") > 0

# Usage
sessions = SessionManager(db, ttl=7200)  # 2-hour sessions
session_id = sessions.create_session(user_id=123, ip_address="192.168.1.1")
```

### Rate Limiting

```python
def check_rate_limit(db, user_id, limit=100, window=60):
    """Check if user exceeded rate limit."""
    key = f"rate:{user_id}"

    # Get current count
    current = db.kv.get(key)

    if current is None:
        # First request in window
        db.kv.set(key, 1, ttl=window)
        return True, 1

    if current >= limit:
        # Rate limit exceeded
        ttl = db.kv.ttl(key)
        return False, ttl

    # Increment counter
    new_count = db.kv.increment(key)
    return True, new_count

# Usage
allowed, info = check_rate_limit(db, user_id=123, limit=100, window=60)
if not allowed:
    print(f"Rate limit exceeded. Try again in {info} seconds")
else:
    print(f"Request {info}/100")
```

### Feature Flags

```python
class FeatureFlags:
    def __init__(self, db):
        self.db = db
        self.prefix = "feature:"

    def enable(self, feature_name, metadata=None):
        """Enable a feature flag."""
        data = {
            "enabled": True,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.db.kv.set(f"{self.prefix}{feature_name}", data)

    def disable(self, feature_name):
        """Disable a feature flag."""
        data = self.db.kv.get(f"{self.prefix}{feature_name}")
        if data:
            data["enabled"] = False
            self.db.kv.set(f"{self.prefix}{feature_name}", data)

    def is_enabled(self, feature_name):
        """Check if feature is enabled."""
        data = self.db.kv.get(f"{self.prefix}{feature_name}")
        return data and data.get("enabled", False)

    def list_features(self):
        """List all feature flags."""
        keys = self.db.kv.keys(f"{self.prefix}*")
        features = {}
        for key in keys:
            feature_name = key[len(self.prefix):]
            features[feature_name] = self.db.kv.get(key)
        return features

# Usage
flags = FeatureFlags(db)
flags.enable("dark-mode", {"rollout_percentage": 50})
if flags.is_enabled("dark-mode"):
    render_dark_theme()
```

### Distributed Cache

```python
import hashlib
import json

class Cache:
    def __init__(self, db, default_ttl=300):
        self.db = db
        self.default_ttl = default_ttl

    def _make_key(self, *args, **kwargs):
        """Generate cache key from function arguments."""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"cache:{key_hash}"

    def get_or_compute(self, func, *args, ttl=None, **kwargs):
        """Get from cache or compute and cache result."""
        cache_key = self._make_key(*args, **kwargs)

        # Try cache first
        cached = self.db.kv.get(cache_key)
        if cached is not None:
            return cached["result"]

        # Compute and cache
        result = func(*args, **kwargs)
        self.db.kv.set(
            cache_key,
            {"result": result, "computed_at": datetime.now().isoformat()},
            ttl=ttl or self.default_ttl
        )
        return result

    def invalidate_pattern(self, pattern):
        """Clear cache entries matching pattern."""
        keys = self.db.kv.keys(f"cache:{pattern}")
        if keys:
            return self.db.kv.delete(*keys)
        return 0

# Usage
cache = Cache(db, default_ttl=600)

def expensive_calculation(x, y):
    # Simulate expensive operation
    import time
    time.sleep(2)
    return x * y

# First call: slow (computes)
result = cache.get_or_compute(expensive_calculation, 10, 20)

# Second call: fast (cached)
result = cache.get_or_compute(expensive_calculation, 10, 20)
```

## Performance Characteristics

| Operation | Performance | Notes |
|-----------|-------------|-------|
| Single set/get | < 1ms | Direct SQLite operation |
| Batch operations | ~1ms per 100 items | Transaction-wrapped |
| Pattern matching | O(n) | Where n = total keys |
| Increment | < 1ms | Atomic SQL UPDATE |
| Storage overhead | ~100 bytes/key | Metadata included |

## Important Notes

### Multi-Tenant Isolation

Each tenant has its own isolated KV store:

```python
# Different tenants, different data
db_tenant1 = cinchdb.connect("myapp", tenant="customer1")
db_tenant2 = cinchdb.connect("myapp", tenant="customer2")

db_tenant1.kv.set("key", "tenant1_data")
db_tenant2.kv.set("key", "tenant2_data")

print(db_tenant1.kv.get("key"))  # "tenant1_data"
print(db_tenant2.kv.get("key"))  # "tenant2_data"
```

### CDC Exclusion

KV operations are NOT tracked by Change Data Capture:

```python
# Regular table operations are tracked
db.insert("users", {"name": "Alice"})  # Tracked by CDC

# KV operations are not tracked
db.kv.set("user:cache", {"name": "Alice"})  # NOT tracked by CDC
```

### Type Preservation

Values maintain their exact type:

```python
# What you store is what you get
db.kv.set("bool", True)
db.kv.set("int", 42)
db.kv.set("float", 3.14)

assert db.kv.get("bool") is True  # Not 1
assert type(db.kv.get("int")) is int  # Not float
assert type(db.kv.get("float")) is float
```

## Troubleshooting

### Common Issues

#### "Key must be a non-empty string"
```python
# Wrong
db.kv.set("", "value")  # Empty key
db.kv.set(None, "value")  # None key
db.kv.set(123, "value")  # Non-string key

# Right
db.kv.set("my_key", "value")
```

#### "Keys not found" (mget)
```python
# Wrong - raises error if any key missing
configs = db.kv.mget(["exists", "missing"])  # ValueError!

# Right - check existence first
keys = ["key1", "key2", "key3"]
existing = [k for k in keys if db.kv.exists(k)]
if existing:
    values = db.kv.mget(existing)
```

#### "Cannot increment non-numeric value"
```python
# Wrong
db.kv.set("counter", "10")  # String, not number
db.kv.increment("counter")  # ValueError!

# Right
db.kv.set("counter", 10)  # Store as number
db.kv.increment("counter")  # Works: returns 11
```

## Related Topics

- [Multi-Tenancy](../concepts/multi-tenancy.md) - Tenant isolation for KV stores
- [Python SDK Reference](./api-reference.md) - Complete API documentation
- [Performance Guide](../production/performance.md) - Optimization tips
- [CLI KV Commands](../cli/kv.md) - Command-line KV operations
"""Tests for KV store functionality."""

import json
import time
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from cinchdb.core.database import CinchDB
from cinchdb.core.initializer import ProjectInitializer


class TestKVStore:
    """Test the KVStore class."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Initialize project
            initializer = ProjectInitializer(project_dir)
            initializer.init_project("testdb")

            yield project_dir

    @pytest.fixture
    def db(self, temp_project):
        """Create a CinchDB instance for testing."""
        db = CinchDB(database="testdb", project_dir=temp_project)

        # Create a table to ensure the tenant database is materialized
        # This triggers the creation of the __empty__ tenant template with __kv table
        from cinchdb.models import Column
        db.create_table("testtable", [Column(name="testcol", type="INTEGER")])

        return db

    def test_basic_set_get(self, db):
        """Test basic set and get operations."""
        # Set a simple value
        db.kv.set("test_key", "test_value")

        # Get the value
        result = db.kv.get("test_key")
        assert result == "test_value"

    def test_set_get_complex_values(self, db):
        """Test setting and getting complex JSON-serializable values."""
        # Test dict
        data = {"name": "Alice", "age": 30, "active": True}
        db.kv.set("user", data)
        assert db.kv.get("user") == data

        # Test list
        items = [1, 2, "three", {"four": 4}]
        db.kv.set("items", items)
        assert db.kv.get("items") == items

        # Test numbers
        db.kv.set("number", 42.5)
        assert db.kv.get("number") == 42.5

        # Test boolean - stored as numbers (0/1)
        db.kv.set("flag", False)
        assert db.kv.get("flag") == 0  # Booleans stored as numbers

        # Test None
        db.kv.set("none_value", None)
        assert db.kv.get("none_value") is None

    def test_type_preservation(self, db):
        """Test that native types are preserved (multi-type storage)."""
        # Integer should stay integer
        db.kv.set("int_val", 42)
        result = db.kv.get("int_val")
        assert result == 42
        assert isinstance(result, int)

        # Float should stay float
        db.kv.set("float_val", 3.14159)
        result = db.kv.get("float_val")
        assert result == 3.14159
        assert isinstance(result, float)

        # String should stay string
        db.kv.set("str_val", "hello")
        result = db.kv.get("str_val")
        assert result == "hello"
        assert isinstance(result, str)

        # Bytes should stay bytes
        binary_data = b"\x00\x01\x02\x03\xFF\xFE\xFD"
        db.kv.set("bytes_val", binary_data)
        result = db.kv.get("bytes_val")
        assert result == binary_data
        assert isinstance(result, bytes)

        # Boolean type properly preserved
        db.kv.set("bool_true", True)
        assert db.kv.get("bool_true") is True
        assert isinstance(db.kv.get("bool_true"), bool)

        db.kv.set("bool_false", False)
        assert db.kv.get("bool_false") == 0

        # Complex types stored as JSON
        db.kv.set("list_val", [1, 2, 3])
        result = db.kv.get("list_val")
        assert result == [1, 2, 3]
        assert isinstance(result, list)

    def test_binary_data(self, db):
        """Test binary data handling."""
        # Test various binary patterns
        test_cases = [
            b"simple",
            b"\x00\x00\x00",  # null bytes
            b"\xFF\xFE\xFD",  # high bytes
            bytes(range(256)),  # all byte values
            b"",  # empty bytes
        ]

        for i, binary_data in enumerate(test_cases):
            key = f"binary_{i}"
            db.kv.set(key, binary_data)
            result = db.kv.get(key)
            assert result == binary_data
            assert isinstance(result, bytes)

    def test_setnx_positive(self, db):
        """Test setnx when key doesn't exist (positive case)."""
        # Key doesn't exist, should set successfully
        result = db.kv.setnx("new_key", "new_value")
        assert result is True
        assert db.kv.get("new_key") == "new_value"

        # Test with TTL
        result = db.kv.setnx("temp_new", "temp_value", ttl=2)
        assert result is True
        assert db.kv.get("temp_new") == "temp_value"
        ttl = db.kv.ttl("temp_new")
        assert 1 <= ttl <= 2

        # Test with different types
        assert db.kv.setnx("int_nx", 123) is True
        assert db.kv.get("int_nx") == 123

        assert db.kv.setnx("bytes_nx", b"data") is True
        assert db.kv.get("bytes_nx") == b"data"

    def test_setnx_negative(self, db):
        """Test setnx when key already exists (negative case)."""
        # Set an existing key
        db.kv.set("existing", "original")

        # Try to set with setnx - should fail
        result = db.kv.setnx("existing", "new_value")
        assert result is False
        # Original value should be unchanged
        assert db.kv.get("existing") == "original"

        # Test with different types - existing key shouldn't change
        db.kv.set("typed_key", 42)
        assert db.kv.setnx("typed_key", "string_value") is False
        assert db.kv.get("typed_key") == 42

        # Test expired key can be set
        db.kv.set("expired", "old", ttl=0.03)
        time.sleep(0.05)
        assert db.kv.setnx("expired", "new") is True
        assert db.kv.get("expired") == "new"

    def test_setnx_validation(self, db):
        """Test setnx validation."""
        # Invalid key
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.setnx("", "value")

        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.setnx(None, "value")

        # Invalid TTL
        with pytest.raises(ValueError, match="TTL must be positive"):
            db.kv.setnx("key", "value", ttl=-1)

    def test_persist_positive(self, db):
        """Test persist removes TTL successfully."""
        # Set key with TTL
        db.kv.set("temp_key", "value", ttl=2)
        ttl = db.kv.ttl("temp_key")
        assert 1 <= ttl <= 2

        # Remove TTL with persist
        result = db.kv.persist("temp_key")
        assert result is True

        # Key should now be permanent
        assert db.kv.ttl("temp_key") is None
        assert db.kv.get("temp_key") == "value"

        # Wait a bit - key should still exist (no TTL anymore)
        time.sleep(0.05)
        assert db.kv.get("temp_key") == "value"

    def test_persist_negative(self, db):
        """Test persist negative cases."""
        # Non-existent key
        result = db.kv.persist("nonexistent")
        assert result is False

        # Key without TTL (already permanent)
        db.kv.set("permanent", "value")
        result = db.kv.persist("permanent")
        assert result is False  # No TTL to remove

        # Expired key
        db.kv.set("expired", "value", ttl=0.03)
        time.sleep(0.05)
        result = db.kv.persist("expired")
        assert result is False  # Key is already expired

    def test_persist_validation(self, db):
        """Test persist validation."""
        # Invalid key returns False
        assert db.kv.persist("") is False
        assert db.kv.persist(None) is False

    def test_type_updates(self, db):
        """Test updating keys with different types."""
        # Start with string
        db.kv.set("changing_key", "string_value")
        assert db.kv.get("changing_key") == "string_value"

        # Update to number
        db.kv.set("changing_key", 42)
        assert db.kv.get("changing_key") == 42

        # Update to binary
        db.kv.set("changing_key", b"bytes")
        assert db.kv.get("changing_key") == b"bytes"

        # Update to JSON
        db.kv.set("changing_key", {"type": "json"})
        assert db.kv.get("changing_key") == {"type": "json"}

        # Update to None
        db.kv.set("changing_key", None)
        assert db.kv.get("changing_key") is None

    def test_empty_values(self, db):
        """Test edge cases with empty values."""
        # Empty string
        db.kv.set("empty_str", "")
        assert db.kv.get("empty_str") == ""

        # Empty bytes
        db.kv.set("empty_bytes", b"")
        assert db.kv.get("empty_bytes") == b""

        # Empty list
        db.kv.set("empty_list", [])
        assert db.kv.get("empty_list") == []

        # Empty dict
        db.kv.set("empty_dict", {})
        assert db.kv.get("empty_dict") == {}

    def test_large_values(self, db):
        """Test handling of large values."""
        # Large string
        large_string = "x" * 100000
        db.kv.set("large_str", large_string)
        assert db.kv.get("large_str") == large_string

        # Large binary
        large_binary = bytes(range(256)) * 1000
        db.kv.set("large_binary", large_binary)
        assert db.kv.get("large_binary") == large_binary

        # Large JSON
        large_json = {"items": list(range(10000))}
        db.kv.set("large_json", large_json)
        assert db.kv.get("large_json") == large_json

    def test_unicode_handling(self, db):
        """Test Unicode string handling."""
        test_strings = [
            "Hello 世界",
            "Emoji: 😀🎉🚀",
            "Math: ∑∏∫∞",
            "Mixed: café ñoño €",
            "\u0000\u0001\u0002",  # Control characters
        ]

        for i, text in enumerate(test_strings):
            key = f"unicode_{i}"
            db.kv.set(key, text)
            assert db.kv.get(key) == text

    def test_special_numeric_values(self, db):
        """Test special numeric values."""
        # Zero
        db.kv.set("zero", 0)
        assert db.kv.get("zero") == 0

        # Negative numbers
        db.kv.set("negative", -42)
        assert db.kv.get("negative") == -42

        # Very large numbers
        db.kv.set("large_int", 10**15)
        assert db.kv.get("large_int") == 10**15

        # Very small float
        db.kv.set("small_float", 1e-10)
        assert db.kv.get("small_float") == 1e-10

    def test_mset_type_preservation(self, db):
        """Test that mset preserves types correctly."""
        items = {
            "mset_int": 42,
            "mset_float": 3.14,
            "mset_str": "hello",
            "mset_bool_true": True,
            "mset_bool_false": False,
            "mset_bytes": b"data",
            "mset_list": [1, 2, 3],
            "mset_dict": {"a": 1},
            "mset_none": None,
        }

        db.kv.mset(items)

        # Verify types are preserved
        assert db.kv.get("mset_int") == 42
        assert isinstance(db.kv.get("mset_int"), int)

        assert db.kv.get("mset_float") == 3.14
        assert isinstance(db.kv.get("mset_float"), float)

        assert db.kv.get("mset_str") == "hello"
        assert isinstance(db.kv.get("mset_str"), str)

        assert db.kv.get("mset_bool_true") is True
        assert isinstance(db.kv.get("mset_bool_true"), bool)

        assert db.kv.get("mset_bool_false") is False
        assert isinstance(db.kv.get("mset_bool_false"), bool)

        assert db.kv.get("mset_bytes") == b"data"
        assert isinstance(db.kv.get("mset_bytes"), bytes)

        assert db.kv.get("mset_list") == [1, 2, 3]
        assert db.kv.get("mset_dict") == {"a": 1}
        assert db.kv.get("mset_none") is None

    def test_boolean_logic(self, db):
        """Test comprehensive boolean logic and type preservation."""
        # Test basic boolean storage and retrieval
        db.kv.set("bool_true", True)
        db.kv.set("bool_false", False)

        # Verify exact boolean return (not 0/1)
        assert db.kv.get("bool_true") is True
        assert db.kv.get("bool_false") is False

        # Verify type is preserved
        assert isinstance(db.kv.get("bool_true"), bool)
        assert isinstance(db.kv.get("bool_false"), bool)

        # Test that booleans are distinct types from integers
        # Note: In Python, True == 1 and False == 0, but they are different types
        assert type(db.kv.get("bool_true")) is not int
        assert type(db.kv.get("bool_false")) is not int
        assert type(db.kv.get("bool_true")) is bool
        assert type(db.kv.get("bool_false")) is bool

        # Test boolean in mset/mget
        db.kv.mset({
            "config:enabled": True,
            "config:debug": False,
            "config:verbose": True
        })

        configs = db.kv.mget(["config:enabled", "config:debug", "config:verbose"])
        assert configs["config:enabled"] is True
        assert configs["config:debug"] is False
        assert configs["config:verbose"] is True

        # Test boolean with TTL
        db.kv.set("temp_flag", True, ttl=2)
        assert db.kv.get("temp_flag") is True

        # Test setnx with boolean
        assert db.kv.setnx("new_flag", False) is True
        assert db.kv.get("new_flag") is False
        assert db.kv.setnx("new_flag", True) is False  # Already exists
        assert db.kv.get("new_flag") is False  # Value unchanged

        # Test updating from boolean to other type
        db.kv.set("type_change", True)
        assert db.kv.get("type_change") is True

        db.kv.set("type_change", "now a string")
        assert db.kv.get("type_change") == "now a string"

        db.kv.set("type_change", 42)
        assert db.kv.get("type_change") == 42

        # Test pattern matching with boolean values
        db.kv.set("feature:login", True)
        db.kv.set("feature:signup", False)
        db.kv.set("feature:payment", True)

        feature_keys = db.kv.keys("feature:*")
        assert len(feature_keys) == 3

        # Verify all features return proper booleans
        for key in feature_keys:
            value = db.kv.get(key)
            assert isinstance(value, bool)

    def test_get_nonexistent_key(self, db):
        """Test getting a key that doesn't exist."""
        result = db.kv.get("nonexistent")
        assert result is None

    def test_key_validation(self, db):
        """Test key validation."""
        # Empty key should raise ValueError
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.set("", "value")

        # Non-string key should raise ValueError
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.set(123, "value")

        # None key should raise ValueError
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.set(None, "value")

        # Key exceeding 255 characters should raise ValueError
        long_key = "k" * 256
        with pytest.raises(ValueError, match="Key length cannot exceed 255 characters"):
            db.kv.set(long_key, "value")

        # Keys starting with __ should raise ValueError (reserved)
        with pytest.raises(ValueError, match="Keys cannot start with '__'"):
            db.kv.set("__system_key", "value")

        # Keys with control characters should raise ValueError
        with pytest.raises(ValueError, match="Key cannot contain newlines, tabs, or null bytes"):
            db.kv.set("key\nwith\nnewlines", "value")

        with pytest.raises(ValueError, match="Key cannot contain newlines, tabs, or null bytes"):
            db.kv.set("key\twith\ttabs", "value")

        with pytest.raises(ValueError, match="Key cannot contain newlines, tabs, or null bytes"):
            db.kv.set("key\0with\0nulls", "value")

        # Valid keys should work - now supports more characters
        valid_keys = [
            "simple_key",
            "key-with-hyphens",
            "key:with:colons",
            "user:123:session",
            "path/to/resource",
            "email@domain.com",
            "feature#enabled",
            "price$USD",
            "array[0]",
            "object{field}",
            "function(param)",
            "list,separated",
            "semi;colon",
            "plus+minus",
            "equals=value",
            "key.with.dots",
            "key with spaces",  # Now allowed!
            "shopping cart items",
            "user profile settings",
            "email@domain.com",
            "key!with@special#chars$allowed%now",
            "(parentheses) and [brackets]",
            "emoji_🚀_works",  # Even emojis work if they're printable
            "MixedCaseKey123",
            "k" * 255  # Max length key
        ]
        for key in valid_keys:
            db.kv.set(key, "test_value")
            assert db.kv.get(key) == "test_value"

    def test_value_serialization_errors(self, db):
        """Test handling of non-serializable values."""
        # Function object (not JSON serializable)
        with pytest.raises(ValueError, match="Value is not JSON serializable"):
            db.kv.set("func", lambda x: x)

        # Complex object
        class CustomClass:
            pass

        with pytest.raises(ValueError, match="Value is not JSON serializable"):
            db.kv.set("obj", CustomClass())

    def test_delete(self, db):
        """Test key deletion."""
        # Set a key
        db.kv.set("delete_me", "value")
        assert db.kv.get("delete_me") == "value"

        # Delete it
        result = db.kv.delete("delete_me")
        assert result == 1

        # Verify it's gone
        assert db.kv.get("delete_me") is None

        # Delete non-existent key
        result = db.kv.delete("nonexistent")
        assert result == 0

        # Delete multiple keys
        db.kv.set("key1", "value1")
        db.kv.set("key2", "value2")
        db.kv.set("key3", "value3")
        result = db.kv.delete("key1", "key2", "key3")
        assert result == 3

        # Verify all are gone
        assert db.kv.get("key1") is None
        assert db.kv.get("key2") is None
        assert db.kv.get("key3") is None

    def test_exists(self, db):
        """Test key existence checking."""
        # Non-existent key
        assert db.kv.exists("test") is False

        # Set a key
        db.kv.set("test", "value")
        assert db.kv.exists("test") is True

        # Delete the key
        db.kv.delete("test")
        assert db.kv.exists("test") is False

    @pytest.mark.xdist_group(name="kv_ttl")
    def test_ttl_basic(self, db):
        """Test TTL functionality."""
        # Set with 0.03 second TTL
        db.kv.set("temp", "value", ttl=0.03)

        # Should exist immediately
        assert db.kv.get("temp") == "value"
        assert db.kv.exists("temp") is True

        # Wait for expiry
        time.sleep(0.05)

        # Should be expired
        assert db.kv.get("temp") is None
        assert db.kv.exists("temp") is False

    def test_ttl_validation(self, db):
        """Test TTL validation."""
        # Negative TTL should raise error
        with pytest.raises(ValueError, match="TTL must be positive"):
            db.kv.set("key", "value", ttl=-1)

        # Zero TTL should raise error
        with pytest.raises(ValueError, match="TTL must be positive"):
            db.kv.set("key", "value", ttl=0)

    def test_ttl_method(self, db):
        """Test the ttl() method."""
        # Non-existent key
        assert db.kv.ttl("nonexistent") == -1

        # Key without TTL
        db.kv.set("permanent", "value")
        assert db.kv.ttl("permanent") is None

        # Key with TTL
        db.kv.set("temp", "value", ttl=2)
        ttl = db.kv.ttl("temp")
        assert isinstance(ttl, (int, float))
        assert 1 <= ttl <= 2  # Allow for small timing differences

        # Expired key
        db.kv.set("expired", "value", ttl=0.03)
        time.sleep(0.05)
        assert db.kv.ttl("expired") == -1

    def test_expire_method(self, db):
        """Test the expire() method."""
        # Set TTL on existing key
        db.kv.set("test", "value")
        result = db.kv.expire("test", 5)
        assert result is True

        ttl = db.kv.ttl("test")
        assert 3 <= ttl <= 5

        # Try to set TTL on non-existent key
        result = db.kv.expire("nonexistent", 5)
        assert result is False

        # Invalid TTL
        result = db.kv.expire("test", -1)
        assert result is False

    def test_keys_listing(self, db):
        """Test keys listing and pattern matching."""
        # Set some keys
        db.kv.set("user:1", "alice")
        db.kv.set("user:2", "bob")
        db.kv.set("admin:1", "charlie")
        db.kv.set("config", "settings")

        # List all keys
        all_keys = db.kv.keys()
        assert len(all_keys) == 4
        assert "user:1" in all_keys
        assert "user:2" in all_keys
        assert "admin:1" in all_keys
        assert "config" in all_keys

        # Pattern matching
        user_keys = db.kv.keys("user:*")
        assert len(user_keys) == 2
        assert "user:1" in user_keys
        assert "user:2" in user_keys

        admin_keys = db.kv.keys("admin:*")
        assert len(admin_keys) == 1
        assert "admin:1" in admin_keys

        # No matches
        empty_keys = db.kv.keys("nonexistent:*")
        assert len(empty_keys) == 0

    def test_batch_operations(self, db):
        """Test batch set and get operations."""
        # mset
        items = {
            "key1": "value1",
            "key2": {"nested": "data"},
            "key3": [1, 2, 3]
        }
        db.kv.mset(items)

        # Verify all were set
        assert db.kv.get("key1") == "value1"
        assert db.kv.get("key2") == {"nested": "data"}
        assert db.kv.get("key3") == [1, 2, 3]

        # mget
        result = db.kv.mget(["key1", "key2", "key3"])
        assert result == items

        # mget with some non-existent keys should raise
        with pytest.raises(ValueError, match="Keys not found"):
            db.kv.mget(["key1", "nonexistent", "key3"])

    @pytest.mark.xdist_group(name="kv_ttl")
    def test_mset_with_ttl(self, db):
        """Test batch set with TTL."""
        items = {"temp1": "value1", "temp2": "value2"}
        db.kv.mset(items, ttl=0.03)

        # Should exist immediately
        assert db.kv.get("temp1") == "value1"
        assert db.kv.get("temp2") == "value2"

        # Wait for expiry
        time.sleep(0.05)

        # Should be expired
        assert db.kv.get("temp1") is None
        assert db.kv.get("temp2") is None

    def test_mset_validation(self, db):
        """Test mset validation."""
        # Invalid key
        with pytest.raises(ValueError, match="Invalid key"):
            db.kv.mset({"": "value"})

        # Non-serializable value
        with pytest.raises(ValueError, match="not JSON serializable"):
            db.kv.mset({"key": lambda x: x})

        # Empty dict is fine
        db.kv.mset({})  # Should not raise

    def test_delete_pattern_workflow(self, db):
        """Test pattern-based deletion workflow using keys() + delete()."""
        # Set some keys
        db.kv.set("user:1", "alice")
        db.kv.set("user:2", "bob")
        db.kv.set("admin:1", "charlie")
        db.kv.set("config", "settings")

        # Test unpacking from list (pattern-based workflow)
        user_keys = db.kv.keys("user:*")
        deleted = db.kv.delete(*user_keys)
        assert deleted == 2

        # Verify deletions
        assert db.kv.get("user:1") is None
        assert db.kv.get("user:2") is None
        assert db.kv.get("admin:1") == "charlie"
        assert db.kv.get("config") == "settings"

        # Test with mixed operations
        db.kv.set("temp:1", "data1")
        db.kv.set("temp:2", "data2")
        temp_keys = db.kv.keys("temp:*")
        deleted = db.kv.delete("admin:1", *temp_keys, "config")
        assert deleted == 4

        # Verify all are gone
        assert db.kv.get("admin:1") is None
        assert db.kv.get("temp:1") is None
        assert db.kv.get("temp:2") is None
        assert db.kv.get("config") is None

    def test_increment(self, db):
        """Test atomic increment operations."""
        # Increment non-existent key (should start at increment value)
        result = db.kv.increment("counter")
        assert result == 1

        # Increment existing numeric key
        result = db.kv.increment("counter", 5)
        assert result == 6

        # Increment with float
        result = db.kv.increment("counter", 0.5)
        assert result == 6.5

        # Set non-numeric value and try to increment
        db.kv.set("text", "hello")
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("text")

    def test_increment_type_conflicts(self, db):
        """Test increment with various type conflicts."""
        # String value
        db.kv.set("string_key", "not a number")
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("string_key")

        # JSON object
        db.kv.set("json_key", {"count": 5})
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("json_key")

        # List
        db.kv.set("list_key", [1, 2, 3])
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("list_key")

        # Binary data
        db.kv.set("binary_key", b"bytes")
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("binary_key")

        # Null value
        db.kv.set("null_key", None)
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("null_key")

        # Boolean (now stored as boolean type) should fail to increment
        db.kv.set("bool_key", True)
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("bool_key", 1)

        # Also test with False
        db.kv.set("bool_key_false", False)
        with pytest.raises(ValueError, match="Cannot increment non-numeric value"):
            db.kv.increment("bool_key_false", 1)

    def test_increment_atomicity(self, db):
        """Test that increment is truly atomic."""
        # Set initial value
        db.kv.set("atomic_counter", 0)

        # Increment should return new value atomically
        result1 = db.kv.increment("atomic_counter", 10)
        assert result1 == 10

        result2 = db.kv.increment("atomic_counter", -5)
        assert result2 == 5

        # Verify final value
        assert db.kv.get("atomic_counter") == 5

    def test_increment_validation(self, db):
        """Test increment validation."""
        # Invalid key
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.increment("")

        # Invalid amount
        with pytest.raises(ValueError, match="Amount must be numeric"):
            db.kv.increment("counter", "invalid")

        # Non-string key
        with pytest.raises(ValueError, match="Key must be a non-empty string"):
            db.kv.increment(123)

    def test_count_and_size(self, db):
        """Test count and size methods."""
        # Empty store
        assert db.kv.key_count() == 0
        assert db.kv.storage_size() == {'total': 0}

        # Add some keys
        db.kv.set("key1", "value1")
        db.kv.set("key2", "value2")
        db.kv.set("user:1", "alice")

        assert db.kv.key_count() == 3
        storage = db.kv.storage_size()
        assert storage['total'] > 0

        # Count with pattern
        assert db.kv.key_count("user:*") == 1
        assert db.kv.key_count("key*") == 2

    def test_clear(self, db):
        """Test clearing all keys."""
        # Add some keys
        db.kv.set("key1", "value1")
        db.kv.set("key2", "value2")
        db.kv.set("key3", "value3")

        assert db.kv.key_count() == 3

        # Clear all using delete with keys
        all_keys = db.kv.keys()
        deleted = db.kv.delete(*all_keys)
        assert deleted == 3
        assert db.kv.key_count() == 0

    def test_cleanup_expired(self, db):
        """Test manual cleanup of expired keys."""
        # Set keys with short TTL
        db.kv.set("temp1", "value1", ttl=0.03)
        db.kv.set("temp2", "value2", ttl=0.03)
        db.kv.set("permanent", "value")

        # Wait for expiry
        time.sleep(0.05)

        # Keys should be logically expired but still in DB
        assert db.kv.get("temp1") is None
        assert db.kv.get("temp2") is None
        assert db.kv.get("permanent") == "value"

        # Cleanup should remove expired keys
        removed = db.kv.delete_expired()
        assert removed == 2


    def test_integration_with_cinchdb(self, temp_project):
        """Test KV store integration with CinchDB."""
        # Create CinchDB instance
        db = CinchDB(database="testdb", project_dir=temp_project)

        # Access KV store through CinchDB
        db.kv.set("integration_test", {"status": "success"})
        result = db.kv.get("integration_test")
        assert result == {"status": "success"}

    def test_boolean_persistence_across_sessions(self, temp_project):
        """Test that boolean values persist correctly across database sessions."""
        # First session - set various types including booleans
        db1 = CinchDB(database="testdb", project_dir=temp_project)

        # Set different types
        db1.kv.set("bool_true", True)
        db1.kv.set("bool_false", False)
        db1.kv.set("int_zero", 0)
        db1.kv.set("int_one", 1)
        db1.kv.set("str_true", "true")
        db1.kv.set("str_false", "false")

        # Verify in first session
        assert db1.kv.get("bool_true") is True
        assert db1.kv.get("bool_false") is False

        # Close first session
        del db1

        # Second session - verify persistence and type preservation
        db2 = CinchDB(database="testdb", project_dir=temp_project)

        # Booleans should come back as exact booleans
        assert db2.kv.get("bool_true") is True
        assert db2.kv.get("bool_false") is False
        assert type(db2.kv.get("bool_true")) is bool
        assert type(db2.kv.get("bool_false")) is bool

        # Integers should remain integers
        assert db2.kv.get("int_zero") == 0
        assert db2.kv.get("int_one") == 1
        assert type(db2.kv.get("int_zero")) is int
        assert type(db2.kv.get("int_one")) is int

        # Strings should remain strings
        assert db2.kv.get("str_true") == "true"
        assert db2.kv.get("str_false") == "false"
        assert type(db2.kv.get("str_true")) is str

        # Verify types are preserved distinctly
        # Note: In Python True == 1 and False == 0, but types are different
        assert type(db2.kv.get("bool_false")) != type(db2.kv.get("int_zero"))
        assert type(db2.kv.get("bool_true")) != type(db2.kv.get("int_one"))
        assert db2.kv.get("bool_true") != db2.kv.get("str_true")  # True != "true"


class TestKVStoreMultiTenant:
    """Test KV store multi-tenant isolation."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)

            # Initialize project
            initializer = ProjectInitializer(project_dir)
            initializer.init_project("testdb")

            yield project_dir

    def test_tenant_isolation(self, temp_project):
        """Test that tenants are properly isolated."""
        # First materialize the main tenant to create __empty__ template
        db_setup = CinchDB(database="testdb", project_dir=temp_project)
        from cinchdb.models import Column
        db_setup.create_table("testtable", [Column(name="test_id", type="INTEGER")])

        # Create CinchDB instances for different tenants
        db_main = CinchDB(database="testdb", project_dir=temp_project, tenant="main")
        db_tenant1 = CinchDB(database="testdb", project_dir=temp_project, tenant="tenant1")
        db_tenant2 = CinchDB(database="testdb", project_dir=temp_project, tenant="tenant2")

        # Set same key in different tenants
        db_main.kv.set("shared_key", "main_value")
        db_tenant1.kv.set("shared_key", "tenant1_value")
        db_tenant2.kv.set("shared_key", "tenant2_value")

        # Verify isolation
        assert db_main.kv.get("shared_key") == "main_value"
        assert db_tenant1.kv.get("shared_key") == "tenant1_value"
        assert db_tenant2.kv.get("shared_key") == "tenant2_value"

        # Delete from one tenant shouldn't affect others
        db_tenant1.kv.delete("shared_key")
        assert db_tenant1.kv.get("shared_key") is None
        assert db_main.kv.get("shared_key") == "main_value"
        assert db_tenant2.kv.get("shared_key") == "tenant2_value"

    def test_tenant_operations_dont_interfere(self, temp_project):
        """Test that operations on one tenant don't affect others."""
        # First materialize the main tenant to create __empty__ template
        db_setup = CinchDB(database="testdb", project_dir=temp_project)
        from cinchdb.models import Column
        db_setup.create_table("testtable", [Column(name="test_id", type="INTEGER")])

        db_main = CinchDB(database="testdb", project_dir=temp_project, tenant="main")
        db_tenant1 = CinchDB(database="testdb", project_dir=temp_project, tenant="tenant1")

        # Set keys in both tenants
        db_main.kv.set("key1", "main1")
        db_main.kv.set("key2", "main2")
        db_tenant1.kv.set("key1", "tenant1")
        db_tenant1.kv.set("key3", "tenant3")

        # Verify counts are separate
        assert db_main.kv.key_count() == 2
        assert db_tenant1.kv.key_count() == 2

        # Delete all keys from one tenant
        for key in db_main.kv.keys():
            db_main.kv.delete(key)
        assert db_main.kv.key_count() == 0
        assert db_tenant1.kv.key_count() == 2
        assert db_tenant1.kv.get("key1") == "tenant1"
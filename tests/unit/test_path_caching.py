"""Tests for path caching with write-through invalidation."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from cinchdb.core import path_utils
from cinchdb.core.path_utils import (
    get_context_root,
    calculate_shard,
    invalidate_cache,
    clear_all_caches,
    get_cache_stats,
    _path_cache,
    _shard_cache,
)


class TestPathCaching:
    """Test path caching functionality."""
    
    @pytest.fixture(autouse=True)
    def clear_caches(self):
        """Clear caches before and after each test."""
        clear_all_caches()
        yield
        clear_all_caches()
    
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir)
        (project_root / ".cinchdb").mkdir(parents=True)
        yield project_root
        shutil.rmtree(temp_dir)
    
    def test_context_root_caching(self, temp_project):
        """Test that context root paths are cached."""
        # First call should cache the result
        path1 = get_context_root(temp_project, "testdb", "main")
        assert len(_path_cache) == 1
        
        # Second call should use cached result
        path2 = get_context_root(temp_project, "testdb", "main")
        assert path1 == path2
        assert len(_path_cache) == 1  # Still only one entry
        
        # Different parameters should create new cache entry
        path3 = get_context_root(temp_project, "testdb", "dev")
        assert path3 != path1
        assert len(_path_cache) == 2
    
    def test_shard_calculation_caching(self):
        """Test that shard calculations are cached."""
        # First call should cache the result
        shard1 = calculate_shard("tenant1")
        assert len(_shard_cache) == 1
        assert shard1 == _shard_cache["tenant1"]
        
        # Second call should use cached result
        shard2 = calculate_shard("tenant1")
        assert shard1 == shard2
        assert len(_shard_cache) == 1  # Still only one entry
        
        # Different tenant should create new cache entry
        shard3 = calculate_shard("tenant2")
        assert len(_shard_cache) == 2
        assert shard3 == _shard_cache["tenant2"]
    
    def test_cache_invalidation_database(self, temp_project):
        """Test cache invalidation when database is deleted."""
        # Create some cached paths
        get_context_root(temp_project, "db1", "main")
        get_context_root(temp_project, "db1", "dev")
        get_context_root(temp_project, "db2", "main")
        assert len(_path_cache) == 3
        
        # Invalidate all entries for db1
        invalidate_cache(database="db1")
        assert len(_path_cache) == 1
        
        # Only db2 entry should remain
        remaining_key = list(_path_cache.keys())[0]
        assert remaining_key[1] == "db2"
    
    def test_cache_invalidation_branch(self, temp_project):
        """Test cache invalidation for specific branch."""
        # Create some cached paths
        get_context_root(temp_project, "db1", "main")
        get_context_root(temp_project, "db1", "dev")
        get_context_root(temp_project, "db1", "staging")
        assert len(_path_cache) == 3
        
        # Invalidate only the dev branch
        invalidate_cache(database="db1", branch="dev")
        assert len(_path_cache) == 2
        
        # main and staging should remain
        keys = list(_path_cache.keys())
        branches = [key[2] for key in keys]
        assert "main" in branches
        assert "staging" in branches
        assert "dev" not in branches
    
    def test_cache_invalidation_tenant(self):
        """Test cache invalidation for tenant shard."""
        # Create some cached shards
        calculate_shard("tenant1")
        calculate_shard("tenant2")
        calculate_shard("tenant3")
        assert len(_shard_cache) == 3
        
        # Invalidate only tenant2
        invalidate_cache(tenant="tenant2")
        assert len(_shard_cache) == 2
        assert "tenant1" in _shard_cache
        assert "tenant3" in _shard_cache
        assert "tenant2" not in _shard_cache
    
    def test_clear_all_caches(self, temp_project):
        """Test clearing all caches."""
        # Populate caches
        get_context_root(temp_project, "db1", "main")
        get_context_root(temp_project, "db2", "dev")
        calculate_shard("tenant1")
        calculate_shard("tenant2")
        
        assert len(_path_cache) == 2
        assert len(_shard_cache) == 2
        
        # Clear all caches
        clear_all_caches()
        
        assert len(_path_cache) == 0
        assert len(_shard_cache) == 0
    
    def test_cache_stats(self, temp_project):
        """Test cache statistics."""
        # Start with empty caches
        stats = get_cache_stats()
        assert stats["path_cache_size"] == 0
        assert stats["shard_cache_size"] == 0
        assert stats["max_cache_size"] == path_utils._MAX_CACHE_SIZE
        
        # Add some entries
        get_context_root(temp_project, "db1", "main")
        calculate_shard("tenant1")
        
        stats = get_cache_stats()
        assert stats["path_cache_size"] == 1
        assert stats["shard_cache_size"] == 1
    
    def test_cache_size_limit(self, temp_project):
        """Test that cache respects size limits."""
        # Temporarily set a small cache size for testing
        original_max = path_utils._MAX_CACHE_SIZE
        path_utils._MAX_CACHE_SIZE = 3
        
        try:
            # Fill the cache to the limit
            get_context_root(temp_project, "db1", "main")
            get_context_root(temp_project, "db2", "main")
            get_context_root(temp_project, "db3", "main")
            assert len(_path_cache) == 3
            
            # Adding one more should clear the cache and add the new entry
            get_context_root(temp_project, "db4", "main")
            assert len(_path_cache) == 1
            # The new entry should be present
            assert list(_path_cache.keys())[0][1] == "db4"
            
        finally:
            # Restore original max size
            path_utils._MAX_CACHE_SIZE = original_max
    
    def test_cache_hit_performance(self, temp_project):
        """Test that cached lookups are faster than uncached."""
        import time
        
        # Clear cache
        clear_all_caches()
        
        # Time uncached call
        start = time.perf_counter()
        for _ in range(1000):
            get_context_root(temp_project, "testdb", "main")
            clear_all_caches()  # Force cache miss
        uncached_time = time.perf_counter() - start
        
        # Time cached calls
        clear_all_caches()
        get_context_root(temp_project, "testdb", "main")  # Prime cache
        start = time.perf_counter()
        for _ in range(1000):
            get_context_root(temp_project, "testdb", "main")
        cached_time = time.perf_counter() - start
        
        # Cached should be significantly faster
        assert cached_time < uncached_time / 2  # At least 2x faster
    
    def test_shard_deterministic(self):
        """Test that shard calculation is deterministic."""
        # Same tenant should always produce same shard
        shard1 = calculate_shard("my-tenant")
        clear_all_caches()
        shard2 = calculate_shard("my-tenant")
        assert shard1 == shard2
        
        # Shard should be 2 characters
        assert len(shard1) == 2
        # Should be hexadecimal
        assert all(c in "0123456789abcdef" for c in shard1)
    
    def test_cache_thread_safety(self, temp_project):
        """Test cache operations are thread-safe."""
        import threading
        import random
        
        errors = []
        
        def worker():
            try:
                for _ in range(100):
                    db_num = random.randint(1, 10)
                    branch_num = random.randint(1, 3)
                    
                    # Perform cache operations
                    get_context_root(temp_project, f"db{db_num}", f"branch{branch_num}")
                    calculate_shard(f"tenant{db_num}")
                    
                    # Occasionally invalidate
                    if random.random() < 0.1:
                        invalidate_cache(database=f"db{db_num}")
                    
                    if random.random() < 0.05:
                        clear_all_caches()
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # No errors should have occurred
        assert len(errors) == 0
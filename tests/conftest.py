"""Pytest configuration and shared fixtures."""

import os
import pytest

# Set environment variable to skip maintenance mode delays in tests
os.environ["CINCHDB_SKIP_MAINTENANCE_DELAY"] = "1"


@pytest.fixture(autouse=True)
def ensure_fast_tests():
    """Ensure tests run without artificial delays."""
    # This runs before each test
    assert os.getenv("CINCHDB_SKIP_MAINTENANCE_DELAY") == "1"
    yield
    # This runs after each test


@pytest.fixture(autouse=True)
def cleanup_connections():
    """Clean up connection pools after each test to prevent file descriptor leaks."""
    yield
    # This runs after each test
    try:
        from cinchdb.infrastructure.metadata_connection_pool import MetadataConnectionPool
        MetadataConnectionPool.close_all()
    except ImportError:
        # Connection pool not available, skip cleanup
        pass

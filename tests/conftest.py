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
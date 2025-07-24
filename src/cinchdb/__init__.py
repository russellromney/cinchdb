"""CinchDB - A Git-like SQLite database management system."""

from cinchdb.core.database import connect, connect_api

__version__ = "0.1.0"

__all__ = ["connect", "connect_api"]

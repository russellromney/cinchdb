"""CinchDB - A Git-like SQLite database management system."""

from cinchdb.core.database import connect, connect_api

try:
    from importlib.metadata import version
    __version__ = version("cinchdb")
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import version
    __version__ = version("cinchdb")
except Exception:
    # Final fallback if package metadata is not available
    __version__ = "0.1.13"

__all__ = ["connect", "connect_api"]

"""
Simple Plugin System for CinchDB

Easy-to-use plugin architecture for CinchDB.
"""

from .base import Plugin
from .manager import PluginManager
from .decorators import database_method, auto_extend

__all__ = [
    "Plugin",
    "PluginManager",
    "database_method", 
    "auto_extend",
]
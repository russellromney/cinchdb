"""
CinchDB Plugin System

Extensible plugin architecture for CinchDB.
"""

from .base import BasePlugin, PluginHook
from .manager import PluginManager
from .decorators import hook, plugin_method

__all__ = [
    "BasePlugin",
    "PluginHook", 
    "PluginManager",
    "hook",
    "plugin_method",
]
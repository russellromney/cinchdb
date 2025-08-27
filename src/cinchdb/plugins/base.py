"""
Base classes for CinchDB plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable
from enum import Enum


class PluginHook(Enum):
    """Available plugin hooks."""
    # Database lifecycle hooks
    DATABASE_INIT = "database_init"
    DATABASE_CONNECT = "database_connect"
    DATABASE_DISCONNECT = "database_disconnect"
    
    # Query hooks
    QUERY_BEFORE = "query_before"
    QUERY_AFTER = "query_after"
    QUERY_ERROR = "query_error"
    
    # Table hooks
    TABLE_CREATE = "table_create"
    TABLE_DROP = "table_drop"
    TABLE_ALTER = "table_alter"
    
    # Tenant hooks
    TENANT_CREATE = "tenant_create"
    TENANT_DROP = "tenant_drop"
    
    # Branch hooks
    BRANCH_CREATE = "branch_create"
    BRANCH_SWITCH = "branch_switch"
    BRANCH_MERGE = "branch_merge"
    
    # CLI hooks
    CLI_COMMAND_BEFORE = "cli_command_before"
    CLI_COMMAND_AFTER = "cli_command_after"


class BasePlugin(ABC):
    """Base class for all CinchDB plugins."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self.description = ""
        self._hooks: Dict[PluginHook, List[Callable]] = {}
        self._methods: Dict[str, Callable] = {}
        
    @abstractmethod
    def initialize(self, cinchdb_instance) -> None:
        """Initialize the plugin with a CinchDB instance."""
        pass
    
    def register_hook(self, hook: PluginHook, callback: Callable) -> None:
        """Register a callback for a specific hook."""
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
    
    def register_method(self, method_name: str, method: Callable) -> None:
        """Register a new method to be added to CinchDB instances."""
        self._methods[method_name] = method
    
    def get_hooks(self) -> Dict[PluginHook, List[Callable]]:
        """Get all registered hooks."""
        return self._hooks.copy()
    
    def get_methods(self) -> Dict[str, Callable]:
        """Get all registered methods."""
        return self._methods.copy()
    
    def call_hook(self, hook: PluginHook, *args, **kwargs) -> Any:
        """Call all callbacks for a specific hook."""
        results = []
        for callback in self._hooks.get(hook, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                # Log error but don't break other plugins
                print(f"Plugin {self.name} hook {hook} failed: {e}")
        return results
    
    def cleanup(self) -> None:
        """Cleanup when plugin is unloaded."""
        pass
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "hooks": list(self._hooks.keys()),
            "methods": list(self._methods.keys()),
        }
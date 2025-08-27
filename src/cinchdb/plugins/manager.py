"""
Plugin manager for CinchDB.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
try:
    from importlib.metadata import entry_points
except ImportError:
    # Fallback for Python < 3.8
    from importlib_metadata import entry_points

from .base import BasePlugin, PluginHook

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin lifecycle and hooks for CinchDB."""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self._cinchdb_instance = None
        
    def set_cinchdb_instance(self, instance):
        """Set the CinchDB instance for plugins."""
        self._cinchdb_instance = instance
        
        # Initialize any already loaded plugins
        for plugin in self.plugins.values():
            try:
                plugin.initialize(instance)
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin.name}: {e}")
    
    def register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin instance."""
        plugin_name = plugin.name
        
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} already registered, replacing")
        
        self.plugins[plugin_name] = plugin
        
        # Initialize with CinchDB instance if available
        if self._cinchdb_instance:
            try:
                plugin.initialize(self._cinchdb_instance)
                self._apply_plugin_methods(plugin)
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
        
        logger.info(f"Plugin {plugin_name} registered successfully")
    
    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin_name}: {e}")
            
            del self.plugins[plugin_name]
            logger.info(f"Plugin {plugin_name} unregistered")
    
    def load_plugin_from_module(self, module_name: str) -> None:
        """Load a plugin from a module name."""
        try:
            module = importlib.import_module(module_name)
            
            # Look for plugin classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    
                    plugin_instance = attr()
                    self.register_plugin(plugin_instance)
                    return
            
            logger.warning(f"No plugin class found in module {module_name}")
            
        except ImportError as e:
            logger.error(f"Failed to import plugin module {module_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_name}: {e}")
    
    def load_plugin_from_file(self, file_path: Path) -> None:
        """Load a plugin from a Python file."""
        try:
            spec = importlib.util.spec_from_file_location("plugin_module", file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for plugin classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BasePlugin) and 
                        attr != BasePlugin):
                        
                        plugin_instance = attr()
                        self.register_plugin(plugin_instance)
                        return
                
                logger.warning(f"No plugin class found in file {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to load plugin from file {file_path}: {e}")
    
    def discover_plugins(self) -> None:
        """Discover plugins using entry points."""
        try:
            eps = entry_points()
            # Handle both old and new entry_points API
            if hasattr(eps, 'select'):
                # New API (Python 3.10+)
                plugin_eps = eps.select(group='cinchdb.plugins')
            else:
                # Old API
                plugin_eps = eps.get('cinchdb.plugins', [])
            
            for entry_point in plugin_eps:
                try:
                    plugin_class = entry_point.load()
                    if issubclass(plugin_class, BasePlugin):
                        plugin_instance = plugin_class()
                        self.register_plugin(plugin_instance)
                except Exception as e:
                    logger.error(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            logger.error(f"Failed to discover plugins: {e}")
    
    def _apply_plugin_methods(self, plugin: BasePlugin) -> None:
        """Apply plugin methods to the CinchDB instance."""
        if not self._cinchdb_instance:
            return
            
        for method_name, method in plugin.get_methods().items():
            # Bind method to the instance
            bound_method = method.__get__(self._cinchdb_instance, type(self._cinchdb_instance))
            setattr(self._cinchdb_instance, method_name, bound_method)
    
    def call_hook(self, hook: PluginHook, *args, **kwargs) -> List[Any]:
        """Call all plugin hooks for a specific event."""
        results = []
        
        for plugin in self.plugins.values():
            try:
                plugin_results = plugin.call_hook(hook, *args, **kwargs)
                results.extend(plugin_results)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} hook {hook} failed: {e}")
        
        return results
    
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all registered plugins with their metadata."""
        return [plugin.metadata for plugin in self.plugins.values()]
    
    def plugin_exists(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self.plugins
    
    def cleanup_all(self) -> None:
        """Cleanup all plugins."""
        for plugin_name in list(self.plugins.keys()):
            self.unregister_plugin(plugin_name)
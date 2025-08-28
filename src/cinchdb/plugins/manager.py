"""
Simple plugin manager for CinchDB.
"""

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from .base import Plugin

logger = logging.getLogger(__name__)


class PluginManager:
    """Simple plugin manager for CinchDB."""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self._database_instances: List[Any] = []
        
    def register_plugin(self, plugin: Union[Plugin, type]) -> None:
        """Register a plugin instance or class."""
        # If it's a class, instantiate it
        if isinstance(plugin, type):
            plugin = plugin()
            
        plugin_name = plugin.name
        
        if plugin_name in self.plugins:
            logger.warning(f"Plugin {plugin_name} already registered, replacing")
        
        self.plugins[plugin_name] = plugin
        
        # Apply to existing database instances
        for db_instance in self._database_instances:
            try:
                plugin.extend_database(db_instance)
            except Exception as e:
                logger.error(f"Failed to extend database with plugin {plugin_name}: {e}")
        
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
            
            # Look for Plugin class first
            if hasattr(module, 'Plugin'):
                plugin_instance = module.Plugin()
                self.register_plugin(plugin_instance)
                return
            
            # Fallback: look for any Plugin subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, Plugin) and 
                    attr != Plugin):
                    
                    plugin_instance = attr()
                    self.register_plugin(plugin_instance)
                    return
            
            logger.warning(f"No Plugin class found in module {module_name}")
            
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
                
                # Look for Plugin class
                if hasattr(module, 'Plugin'):
                    plugin_instance = module.Plugin()
                    self.register_plugin(plugin_instance)
                    return
                
                logger.warning(f"No Plugin class found in file {file_path}")
        
        except Exception as e:
            logger.error(f"Failed to load plugin from file {file_path}: {e}")
    
    def load_plugins_from_directory(self, plugins_dir: Path) -> None:
        """Load all plugins from a directory."""
        if not plugins_dir.exists():
            logger.info(f"Plugins directory {plugins_dir} does not exist")
            return
            
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name == "__init__.py":
                continue
            self.load_plugin_from_file(plugin_file)
    
    def discover_plugins(self) -> None:
        """Discover plugins using entry points and plugins directory."""
        # Try entry points for installed plugins
        try:
            try:
                from importlib.metadata import entry_points
            except ImportError:
                from importlib_metadata import entry_points
                
            eps = entry_points()
            if hasattr(eps, 'select'):
                plugin_eps = eps.select(group='cinchdb.plugins')
            else:
                plugin_eps = eps.get('cinchdb.plugins', [])
            
            for entry_point in plugin_eps:
                try:
                    plugin_class = entry_point.load()
                    self.register_plugin(plugin_class)
                except Exception as e:
                    logger.error(f"Failed to load plugin {entry_point.name}: {e}")
        except Exception as e:
            logger.debug(f"Entry points not available: {e}")
        
        # Also check for local plugins directory
        plugins_dir = Path("plugins")
        if plugins_dir.exists():
            self.load_plugins_from_directory(plugins_dir)
    
    def register_database(self, db_instance) -> None:
        """Register a database instance with all plugins."""
        self._database_instances.append(db_instance)
        
        # Apply all plugins to this database instance
        for plugin in self.plugins.values():
            try:
                plugin.extend_database(db_instance)
            except Exception as e:
                logger.error(f"Failed to extend database with plugin {plugin.name}: {e}")
    
    def unregister_database(self, db_instance) -> None:
        """Unregister a database instance."""
        if db_instance in self._database_instances:
            self._database_instances.remove(db_instance)
    
    def before_query(self, sql: str, params: Optional[tuple] = None) -> tuple:
        """Call before_query on all plugins."""
        for plugin in self.plugins.values():
            try:
                sql, params = plugin.before_query(sql, params)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} before_query failed: {e}")
        return sql, params
    
    def after_query(self, sql: str, params: Optional[tuple], result: Any) -> Any:
        """Call after_query on all plugins."""
        for plugin in self.plugins.values():
            try:
                result = plugin.after_query(sql, params, result)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} after_query failed: {e}")
        return result
    
    def on_connect(self, db_path: str, connection) -> None:
        """Call on_connect on all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.on_connect(db_path, connection)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} on_connect failed: {e}")
    
    def on_disconnect(self, db_path: str) -> None:
        """Call on_disconnect on all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.on_disconnect(db_path)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} on_disconnect failed: {e}")
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
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
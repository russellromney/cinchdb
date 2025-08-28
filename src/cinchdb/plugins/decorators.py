"""
Simple decorators for plugin development.
"""

from typing import Callable


def database_method(method_name: str):
    """Decorator to mark a method for database extension.
    
    Usage:
        class Plugin:
            @database_method("my_method")
            def my_custom_method(self, db):
                return "Hello from plugin!"
    """
    def decorator(func: Callable) -> Callable:
        func._database_method_name = method_name
        return func
    return decorator


def auto_extend(plugin_class):
    """Class decorator to automatically extend databases with decorated methods.
    
    Usage:
        @auto_extend
        class Plugin:
            @database_method("custom_query")
            def custom_query_method(self, db, query):
                # Method will be added to db instances as db.custom_query()
                return "Custom result"
    """
    original_extend = getattr(plugin_class, 'extend_database', None)
    
    def new_extend_database(self, db):
        # Call original extend_database if it exists
        if original_extend:
            original_extend(self, db)
        
        # Auto-add decorated methods
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and hasattr(attr, '_database_method_name'):
                method_name = attr._database_method_name
                setattr(db, method_name, lambda *args, **kwargs: attr(db, *args, **kwargs))
    
    plugin_class.extend_database = new_extend_database
    return plugin_class
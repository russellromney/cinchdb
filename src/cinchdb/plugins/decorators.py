"""
Decorators for plugin development.
"""

from typing import Callable

from .base import PluginHook


def hook(hook_type: PluginHook):
    """Decorator to register a method as a hook callback."""
    def decorator(func: Callable) -> Callable:
        func._plugin_hook = hook_type
        return func
    return decorator


def plugin_method(method_name: str):
    """Decorator to register a method to be added to CinchDB instances."""
    def decorator(func: Callable) -> Callable:
        func._plugin_method_name = method_name
        return func
    return decorator


class PluginDecorators:
    """Helper class to collect decorated methods from a plugin class."""
    
    @staticmethod
    def collect_hooks(plugin_instance) -> None:
        """Collect and register hook methods from a plugin instance."""
        for attr_name in dir(plugin_instance):
            attr = getattr(plugin_instance, attr_name)
            if callable(attr) and hasattr(attr, '_plugin_hook'):
                hook_type = attr._plugin_hook
                plugin_instance.register_hook(hook_type, attr)
    
    @staticmethod
    def collect_methods(plugin_instance) -> None:
        """Collect and register plugin methods from a plugin instance."""
        for attr_name in dir(plugin_instance):
            attr = getattr(plugin_instance, attr_name)
            if callable(attr) and hasattr(attr, '_plugin_method_name'):
                method_name = attr._plugin_method_name
                plugin_instance.register_method(method_name, attr)
"""
Simple base class for CinchDB plugins.
"""

from typing import Any, Dict, Optional


class Plugin:
    """Simple base class for CinchDB plugins."""
    
    # Plugin metadata - override in subclass
    name: str = "unnamed_plugin"
    version: str = "1.0.0"
    description: str = ""
    
    def extend_database(self, db) -> None:
        """Add methods or modify the database instance.
        
        Override this method to add custom methods to database instances:
        
        Example:
            def extend_database(self, db):
                db.my_custom_method = self.my_custom_method
        """
        pass
    
    def before_query(self, sql: str, params: Optional[tuple] = None) -> tuple:
        """Called before executing any SQL query.
        
        Args:
            sql: The SQL statement to be executed
            params: Parameters for the SQL statement
            
        Returns:
            Tuple of (modified_sql, modified_params)
        """
        return sql, params
    
    def after_query(self, sql: str, params: Optional[tuple], result: Any) -> Any:
        """Called after executing any SQL query.
        
        Args:
            sql: The SQL statement that was executed
            params: Parameters that were used
            result: The query result
            
        Returns:
            Modified result (or original result)
        """
        return result
    
    def on_connect(self, db_path: str, connection) -> None:
        """Called when a database connection is established.
        
        Args:
            db_path: Path to the database file
            connection: SQLite connection object
        """
        pass
    
    def on_disconnect(self, db_path: str) -> None:
        """Called when a database connection is closed.
        
        Args:
            db_path: Path to the database file
        """
        pass
    
    def cleanup(self) -> None:
        """Called when plugin is being unloaded."""
        pass
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get plugin metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
"""Code generation manager for creating models from database schemas."""

from pathlib import Path
from typing import List, Dict, Any, Literal
from ..core.connection import DatabaseConnection
from ..core.path_utils import get_tenant_db_path
from ..models import Table, Column, View
from ..managers.table import TableManager
from ..managers.view import ViewModel


LanguageType = Literal["python", "typescript"]


class CodegenManager:
    """Manages code generation for database schemas."""
    
    SUPPORTED_LANGUAGES = ["python", "typescript"]
    
    def __init__(self, project_root: Path, database: str, branch: str, tenant: str = "main"):
        """Initialize codegen manager.
        
        Args:
            project_root: Path to project root
            database: Database name
            branch: Branch name  
            tenant: Tenant name (defaults to main)
        """
        self.project_root = Path(project_root)
        self.database = database
        self.branch = branch
        self.tenant = tenant
        self.db_path = get_tenant_db_path(
            project_root, database, branch, tenant
        )
        
        # Initialize managers for data access
        self.table_manager = TableManager(
            project_root, database, branch, tenant
        )
        self.view_manager = ViewModel(
            project_root, database, branch, tenant  
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported code generation languages.
        
        Returns:
            List of supported language names
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    def generate_models(
        self, 
        language: LanguageType, 
        output_dir: Path,
        include_tables: bool = True,
        include_views: bool = True
    ) -> Dict[str, Any]:
        """Generate model files for the specified language.
        
        Args:
            language: Target language for generation
            output_dir: Directory to write generated files
            include_tables: Whether to generate table models
            include_views: Whether to generate view models
            
        Returns:
            Dictionary with generation results
            
        Raises:
            ValueError: If language not supported or output directory invalid
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{language}' not supported. Available: {self.SUPPORTED_LANGUAGES}")
        
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "language": language,
            "output_dir": str(output_path),
            "files_generated": [],
            "tables_processed": [],
            "views_processed": []
        }
        
        if language == "python":
            return self._generate_python_models(output_path, include_tables, include_views, results)
        elif language == "typescript":
            return self._generate_typescript_models(output_path, include_tables, include_views, results)
        
        return results
    
    def _generate_python_models(
        self, 
        output_dir: Path, 
        include_tables: bool, 
        include_views: bool,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate Python Pydantic models."""
        
        # Generate __init__.py
        init_content = ['"""Generated CinchDB models."""\n']
        model_imports = []
        
        if include_tables:
            # Get all tables
            tables = self.table_manager.list_tables()
            
            for table in tables:
                # Generate model for each table
                model_content = self._generate_python_table_model(table)
                model_filename = f"{self._to_snake_case(table.name)}.py"
                model_path = output_dir / model_filename
                
                with open(model_path, 'w') as f:
                    f.write(model_content)
                
                results["files_generated"].append(model_filename)
                results["tables_processed"].append(table.name)
                
                # Add to imports
                class_name = self._to_pascal_case(table.name)
                model_imports.append(f"from .{self._to_snake_case(table.name)} import {class_name}")
        
        if include_views:
            # Get all views
            views = self.view_manager.list_views()
            
            for view in views:
                # Generate model for each view (read-only)
                model_content = self._generate_python_view_model(view)
                model_filename = f"{self._to_snake_case(view.name)}_view.py"
                model_path = output_dir / model_filename
                
                with open(model_path, 'w') as f:
                    f.write(model_content)
                
                results["files_generated"].append(model_filename)
                results["views_processed"].append(view.name)
                
                # Add to imports
                class_name = f"{self._to_pascal_case(view.name)}View"
                model_imports.append(f"from .{self._to_snake_case(view.name)}_view import {class_name}")
        
        # Write __init__.py with all imports
        if model_imports:
            init_content.extend(model_imports)
            init_content.append("")  # Empty line
            
            # Add __all__ export
            all_exports = []
            if include_tables:
                for table_name in results["tables_processed"]:
                    all_exports.append(f'"{self._to_pascal_case(table_name)}"')
            if include_views:
                for view_name in results["views_processed"]:
                    all_exports.append(f'"{self._to_pascal_case(view_name)}View"')
            
            init_content.append(f"__all__ = [{', '.join(all_exports)}]")
        
        init_path = output_dir / "__init__.py"
        with open(init_path, 'w') as f:
            f.write("\n".join(init_content))
        
        results["files_generated"].append("__init__.py")
        
        return results
    
    def _generate_python_table_model(self, table: Table) -> str:
        """Generate Python Pydantic model for a table."""
        class_name = self._to_pascal_case(table.name)
        
        content = [
            f'"""Generated model for {table.name} table."""',
            "",
            "from typing import Optional",
            "from datetime import datetime",
            "from pydantic import BaseModel, Field",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f'    """Model for {table.name} table."""',
            ""
        ]
        
        # Generate fields for each column
        for column in table.columns:
            field_content = self._generate_python_field(column)
            content.append(f"    {field_content}")
        
        content.append("")
        content.append("    class Config:")
        content.append("        from_attributes = True")
        content.append(f'        json_schema_extra = {{"table_name": "{table.name}"}}')
        
        return "\n".join(content)
    
    def _generate_python_view_model(self, view: View) -> str:
        """Generate Python Pydantic model for a view (read-only)."""
        class_name = f"{self._to_pascal_case(view.name)}View"
        
        # Get view schema by inspecting the view
        columns = self._get_view_columns(view.name)
        
        content = [
            f'"""Generated model for {view.name} view."""',
            "",
            "from typing import Optional, Any",
            "from pydantic import BaseModel, Field",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f'    """Read-only model for {view.name} view."""',
            ""
        ]
        
        # Generate fields for each column (all Optional since we can't know schema exactly)
        for column_name, column_type in columns.items():
            python_type = self._sqlite_to_python_type(column_type)
            content.append(f"    {column_name}: Optional[{python_type}] = Field(default=None)")
        
        content.append("")
        content.append("    class Config:")
        content.append("        from_attributes = True")
        content.append(f'        json_schema_extra = {{"view_name": "{view.name}", "readonly": True}}')
        
        return "\n".join(content)
    
    def _generate_python_field(self, column: Column) -> str:
        """Generate Python field definition for a column."""
        python_type = self._sqlite_to_python_type(column.type, column.name)
        
        # Handle nullable columns
        if column.nullable and column.name not in ["id"]:  # id is never nullable
            python_type = f"Optional[{python_type}]"
        
        # Create field definition
        field_parts = []
        
        # Add description
        field_parts.append(f'description="{column.name} field"')
        
        # Add default for nullable columns
        if column.nullable and column.name not in ["id", "created_at"]:
            field_parts.append("default=None")
        elif column.name == "created_at":
            field_parts.append("default_factory=datetime.utcnow")
        elif column.name == "updated_at":
            field_parts.append("default=None")
        
        field_def = f"Field({', '.join(field_parts)})" if field_parts else "Field()"
        
        return f"{column.name}: {python_type} = {field_def}"
    
    def _generate_typescript_models(
        self, 
        output_dir: Path, 
        include_tables: bool, 
        include_views: bool,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate TypeScript interface models."""
        # TODO: Implement TypeScript generation
        # For now, return placeholder
        results["files_generated"].append("typescript_generation_todo.md")
        
        placeholder_path = output_dir / "typescript_generation_todo.md"
        with open(placeholder_path, 'w') as f:
            f.write("# TypeScript Generation\n\nTypeScript model generation will be implemented in a future update.\n")
        
        return results
    
    def _get_view_columns(self, view_name: str) -> Dict[str, str]:
        """Get column information for a view by querying PRAGMA."""
        columns = {}
        
        with DatabaseConnection(self.db_path) as conn:
            try:
                # Try to get view column info
                cursor = conn.execute(f"PRAGMA table_info('{view_name}')")
                for row in cursor.fetchall():
                    column_name = row["name"]
                    column_type = row["type"] or "TEXT"  # Default to TEXT if type is empty
                    columns[column_name] = column_type.upper()
            except Exception:
                # If we can't get schema, use generic approach
                columns = {"data": "TEXT"}  # Fallback
        
        return columns
    
    def _sqlite_to_python_type(self, sqlite_type: str, column_name: str = "") -> str:
        """Convert SQLite type to Python type string."""
        sqlite_type = sqlite_type.upper()
        
        # Special case for timestamp fields
        if column_name in ["created_at", "updated_at"]:
            return "datetime"
        
        if "INT" in sqlite_type:
            return "int"
        elif sqlite_type in ["REAL", "FLOAT", "DOUBLE"]:
            return "float"
        elif sqlite_type == "BLOB":
            return "bytes"
        elif "NUMERIC" in sqlite_type:
            return "float"  # Could be Decimal, but float is simpler
        else:
            # TEXT, VARCHAR, etc.
            return "str"
    
    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case."""
        import re
        # Insert underscore before uppercase letters (except first)
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters preceded by lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        # If already PascalCase, return as-is
        if name and name[0].isupper() and '_' not in name and '-' not in name:
            return name
        
        # Split on underscores and capitalize each part
        parts = name.replace('-', '_').split('_')
        return ''.join(word.capitalize() for word in parts if word)
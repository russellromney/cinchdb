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

    def __init__(
        self, project_root: Path, database: str, branch: str, tenant: str = "main"
    ):
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
        self.db_path = get_tenant_db_path(project_root, database, branch, tenant)

        # Initialize managers for data access
        self.table_manager = TableManager(project_root, database, branch, tenant)
        self.view_manager = ViewModel(project_root, database, branch, tenant)

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
        include_views: bool = True,
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
            raise ValueError(
                f"Language '{language}' not supported. Available: {self.SUPPORTED_LANGUAGES}"
            )

        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        results = {
            "language": language,
            "output_dir": str(output_path),
            "files_generated": [],
            "tables_processed": [],
            "views_processed": [],
        }

        if language == "python":
            return self._generate_python_models(
                output_path, include_tables, include_views, results
            )
        elif language == "typescript":
            return self._generate_typescript_models(
                output_path, include_tables, include_views, results
            )

        return results

    def _generate_python_models(
        self,
        output_dir: Path,
        include_tables: bool,
        include_views: bool,
        results: Dict[str, Any],
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

                with open(model_path, "w") as f:
                    f.write(model_content)

                results["files_generated"].append(model_filename)
                results["tables_processed"].append(table.name)

                # Add to imports
                class_name = self._to_pascal_case(table.name)
                model_imports.append(
                    f"from .{self._to_snake_case(table.name)} import {class_name}"
                )

        if include_views:
            # Get all views
            views = self.view_manager.list_views()

            for view in views:
                # Generate model for each view (read-only)
                model_content = self._generate_python_view_model(view)
                model_filename = f"{self._to_snake_case(view.name)}_view.py"
                model_path = output_dir / model_filename

                with open(model_path, "w") as f:
                    f.write(model_content)

                results["files_generated"].append(model_filename)
                results["views_processed"].append(view.name)

                # Add to imports
                class_name = f"{self._to_pascal_case(view.name)}View"
                model_imports.append(
                    f"from .{self._to_snake_case(view.name)}_view import {class_name}"
                )

        # Generate CinchModels container class
        cinch_models_content = self._generate_cinch_models_class()
        cinch_models_path = output_dir / "cinch_models.py"
        with open(cinch_models_path, "w") as f:
            f.write(cinch_models_content)
        results["files_generated"].append("cinch_models.py")

        # Write __init__.py with all imports and factory function
        if model_imports:
            # Import CinchModels
            init_content.append("from .cinch_models import CinchModels")
            init_content.extend(model_imports)
            init_content.append("")  # Empty line

            # Create model registry
            init_content.append("# Model registry for dynamic loading")
            init_content.append("_MODEL_REGISTRY = {")
            if include_tables:
                for table_name in results["tables_processed"]:
                    class_name = self._to_pascal_case(table_name)
                    init_content.append(f"    '{class_name}': {class_name},")
            if include_views:
                for view_name in results["views_processed"]:
                    class_name = f"{self._to_pascal_case(view_name)}View"
                    init_content.append(f"    '{class_name}': {class_name},")
            init_content.append("}")
            init_content.append("")

            # Add factory function
            init_content.extend(
                [
                    "def create_models(connection) -> CinchModels:",
                    '    """Create unified models interface.',
                    "",
                    "    Args:",
                    "        connection: CinchDB instance (local or remote)",
                    "",
                    "    Returns:",
                    "        CinchModels container with all generated models",
                    '    """',
                    "    models = CinchModels(connection)",
                    "    models._model_registry = _MODEL_REGISTRY",
                    "    return models",
                    "",
                ]
            )

            # Add __all__ export
            all_exports = ["'CinchModels'", "'create_models'"]
            if include_tables:
                for table_name in results["tables_processed"]:
                    all_exports.append(f'"{self._to_pascal_case(table_name)}"')
            if include_views:
                for view_name in results["views_processed"]:
                    all_exports.append(f'"{self._to_pascal_case(view_name)}View"')

            init_content.append(f"__all__ = [{', '.join(all_exports)}]")

        init_path = output_dir / "__init__.py"
        with open(init_path, "w") as f:
            f.write("\n".join(init_content))

        results["files_generated"].append("__init__.py")

        return results

    def _generate_python_table_model(self, table: Table) -> str:
        """Generate Python Pydantic model for a table."""
        class_name = self._to_pascal_case(table.name)

        content = [
            f'"""Generated model for {table.name} table."""',
            "",
            "from typing import Optional, List, ClassVar, Union",
            "from datetime import datetime",
            "from pathlib import Path",
            "from pydantic import BaseModel, Field, ConfigDict",
            "",
            "from cinchdb.managers.data import DataManager",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f'    """Model for {table.name} table with CRUD operations."""',
            "    model_config = ConfigDict(",
            "        from_attributes=True,",
            f'        json_schema_extra={{"table_name": "{table.name}"}}',
            "    )",
            "",
            "    # Class variables for database connection info",
            "    _data_manager: ClassVar[Optional[DataManager]] = None",
            "",
        ]

        # Generate fields for each column
        for column in table.columns:
            field_content = self._generate_python_field(column)
            content.append(f"    {field_content}")

        content.extend(
            [
                "",
                "    @classmethod",
                "    def _get_data_manager(cls) -> DataManager:",
                '        """Get data manager instance (set by CinchModels container)."""',
                "        if cls._data_manager is None:",
                '            raise RuntimeError("Model not initialized. Access models through CinchModels container.")',
                "        return cls._data_manager",
                "",
                "    @classmethod",
                f"    def select(cls, limit: Optional[int] = None, offset: Optional[int] = None, **filters) -> List['{class_name}']:",
                '        """Select records with optional filtering."""',
                "        return cls._get_data_manager().select(cls, limit=limit, offset=offset, **filters)",
                "",
                "    @classmethod",
                f"    def find_by_id(cls, record_id: str) -> Optional['{class_name}']:",
                '        """Find a single record by ID."""',
                "        return cls._get_data_manager().find_by_id(cls, record_id)",
                "",
                "    @classmethod",
                f"    def create(cls, **data) -> '{class_name}':",
                '        """Create a new record."""',
                "        instance = cls(**data)",
                "        return cls._get_data_manager().create(instance)",
                "",
                "    @classmethod",
                f"    def bulk_create(cls, records: List[dict]) -> List['{class_name}']:",
                '        """Create multiple records in a single transaction."""',
                "        instances = [cls(**record) for record in records]",
                "        return cls._get_data_manager().bulk_create(instances)",
                "",
                "    @classmethod",
                "    def count(cls, **filters) -> int:",
                '        """Count records with optional filtering."""',
                "        return cls._get_data_manager().count(cls, **filters)",
                "",
                "    @classmethod",
                "    def delete_records(cls, **filters) -> int:",
                '        """Delete records matching filters."""',
                "        return cls._get_data_manager().delete(cls, **filters)",
                "",
                f"    def save(self) -> '{class_name}':",
                '        """Save (upsert) this record."""',
                "        return self._get_data_manager().save(self)",
                "",
                f"    def update(self) -> '{class_name}':",
                '        """Update this existing record."""',
                "        return self._get_data_manager().update(self)",
                "",
                "    def delete(self) -> bool:",
                '        """Delete this record."""',
                "        if not self.id:",
                '            raise ValueError("Cannot delete record without ID")',
                "        return self._get_data_manager().delete_by_id(type(self), self.id)",
            ]
        )

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
            "from pydantic import BaseModel, Field, ConfigDict",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f'    """Read-only model for {view.name} view."""',
            "    model_config = ConfigDict(",
            "        from_attributes=True,",
            f'        json_schema_extra={{"view_name": "{view.name}", "readonly": True}}',
            "    )",
            "",
        ]

        # Generate fields for each column (all Optional since we can't know schema exactly)
        for column_name, column_type in columns.items():
            python_type = self._sqlite_to_python_type(column_type)
            content.append(
                f"    {column_name}: Optional[{python_type}] = Field(default=None)"
            )

        return "\n".join(content)

    def _generate_python_field(self, column: Column) -> str:
        """Generate Python field definition for a column."""
        python_type = self._sqlite_to_python_type(column.type, column.name)

        # Handle nullable columns - all fields should be Optional except required business fields
        # ID is always optional (auto-generated), timestamps are optional for model creation
        if column.nullable or column.name in ["id", "created_at", "updated_at"]:
            python_type = f"Optional[{python_type}]"

        # Create field definition
        field_parts = []

        # Add description
        field_parts.append(f'description="{column.name} field"')

        # Add default values
        if column.name == "id":
            field_parts.append("default=None")  # Auto-generated by DataManager
        elif column.name == "created_at":
            field_parts.append("default=None")  # Set by DataManager on create
        elif column.name == "updated_at":
            field_parts.append("default=None")  # Set by DataManager on create/update
        elif column.nullable:
            field_parts.append("default=None")

        field_def = f"Field({', '.join(field_parts)})" if field_parts else "Field()"

        return f"{column.name}: {python_type} = {field_def}"

    def _generate_typescript_models(
        self,
        output_dir: Path,
        include_tables: bool,
        include_views: bool,
        results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate TypeScript interface models."""
        # Generate interfaces for tables
        if include_tables:
            tables = self.table_manager.list_tables()
            for table in tables:
                interface_content = self._generate_typescript_table_interface(table)
                file_name = f"{self._to_pascal_case(table.name)}.ts"
                file_path = output_dir / file_name
                
                with open(file_path, "w") as f:
                    f.write(interface_content)
                
                results["tables_processed"].append(table.name)
                results["files_generated"].append(file_name)
        
        # Generate interfaces for views
        if include_views:
            views = self.view_manager.list_views()
            for view in views:
                interface_content = self._generate_typescript_view_interface(view)
                file_name = f"{self._to_pascal_case(view.name)}View.ts"
                file_path = output_dir / file_name
                
                with open(file_path, "w") as f:
                    f.write(interface_content)
                
                results["views_processed"].append(view.name)
                results["files_generated"].append(file_name)
        
        # Generate main index file
        index_content = self._generate_typescript_index(
            results["tables_processed"], 
            results["views_processed"]
        )
        index_path = output_dir / "index.ts"
        with open(index_path, "w") as f:
            f.write(index_content)
        results["files_generated"].append("index.ts")
        
        # Generate API client
        client_content = self._generate_typescript_client()
        client_path = output_dir / "client.ts"
        with open(client_path, "w") as f:
            f.write(client_content)
        results["files_generated"].append("client.ts")
        
        # Generate types file
        types_content = self._generate_typescript_types()
        types_path = output_dir / "types.ts"
        with open(types_path, "w") as f:
            f.write(types_content)
        results["files_generated"].append("types.ts")
        
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
                    column_type = (
                        row["type"] or "TEXT"
                    )  # Default to TEXT if type is empty
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
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        # Insert underscore before uppercase letters preceded by lowercase
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase."""
        # If already PascalCase, return as-is
        if name and name[0].isupper() and "_" not in name and "-" not in name:
            return name

        # Split on underscores and capitalize each part
        parts = name.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in parts if word)
    
    def _sqlite_to_typescript_type(self, sqlite_type: str, column_name: str = "") -> str:
        """Convert SQLite type to TypeScript type string."""
        sqlite_type = sqlite_type.upper()
        
        # Special case for timestamp fields
        if column_name in ["created_at", "updated_at"]:
            return "string"  # ISO date strings
        
        if "INT" in sqlite_type:
            return "number"
        elif sqlite_type in ["REAL", "FLOAT", "DOUBLE", "NUMERIC"]:
            return "number"
        elif sqlite_type == "BLOB":
            return "Uint8Array"
        elif sqlite_type == "BOOLEAN":
            return "boolean"
        else:
            # TEXT, VARCHAR, etc.
            return "string"
    
    def _generate_typescript_table_interface(self, table: Table) -> str:
        """Generate TypeScript interface for a table."""
        interface_name = self._to_pascal_case(table.name)
        
        content = [
            f"/**",
            f" * Generated interface for {table.name} table",
            f" */",
            f"export interface {interface_name} {{",
        ]
        
        # Generate properties for each column
        for column in table.columns:
            ts_type = self._sqlite_to_typescript_type(column.type, column.name)
            optional = "?" if column.nullable and column.name not in ["id", "created_at"] else ""
            content.append(f"  {column.name}{optional}: {ts_type};")
        
        content.append("}")
        content.append("")
        
        # Generate input interface (for create/update operations)
        content.extend([
            f"/**",
            f" * Input interface for creating/updating {table.name} records",
            f" */",
            f"export interface {interface_name}Input {{",
        ])
        
        for column in table.columns:
            # Skip auto-generated fields in input
            if column.name in ["id", "created_at", "updated_at"]:
                continue
            ts_type = self._sqlite_to_typescript_type(column.type, column.name)
            optional = "?" if column.nullable else ""
            content.append(f"  {column.name}{optional}: {ts_type};")
        
        content.append("}")
        content.append("")
        
        return "\n".join(content)
    
    def _generate_typescript_view_interface(self, view: View) -> str:
        """Generate TypeScript interface for a view."""
        interface_name = f"{self._to_pascal_case(view.name)}View"
        
        # Get view columns from PRAGMA
        columns = self._get_view_columns(view.name)
        
        content = [
            f"/**",
            f" * Generated interface for {view.name} view (read-only)",
            f" */",
            f"export interface {interface_name} {{",
        ]
        
        # Generate properties for each column
        for column_name, column_type in columns.items():
            ts_type = self._sqlite_to_typescript_type(column_type, column_name)
            content.append(f"  {column_name}: {ts_type};")
        
        content.append("}")
        content.append("")
        
        return "\n".join(content)
    
    def _generate_typescript_index(self, tables: List[str], views: List[str]) -> str:
        """Generate TypeScript index file exporting all interfaces."""
        content = [
            "/**",
            " * Generated TypeScript models for CinchDB",
            " */",
            "",
        ]
        
        # Export tables
        for table_name in tables:
            interface_name = self._to_pascal_case(table_name)
            content.append(f"export {{ {interface_name}, {interface_name}Input }} from './{interface_name}';")
        
        # Export views
        for view_name in views:
            interface_name = f"{self._to_pascal_case(view_name)}View"
            content.append(f"export {{ {interface_name} }} from './{interface_name}';")
        
        # Export client and types
        content.extend([
            "",
            "export { CinchDBClient } from './client';",
            "export * from './types';",
            "",
        ])
        
        return "\n".join(content)
    
    def _generate_typescript_client(self) -> str:
        """Generate TypeScript API client class."""
        content = [
            "/**",
            " * CinchDB TypeScript API Client",
            " */",
            "",
            "import { QueryResult, CreateResult, UpdateResult, DeleteResult } from './types';",
            "",
            "export class CinchDBClient {",
            "  private baseUrl: string;",
            "  private headers: HeadersInit;",
            "",
            "  constructor(baseUrl: string, apiKey: string) {",
            "    this.baseUrl = baseUrl;",
            "    this.headers = {",
            "      'Content-Type': 'application/json',",
            "      'X-API-Key': apiKey,",
            "    };",
            "  }",
            "",
            "  /**",
            "   * Execute a query against the database",
            "   */",
            "  async query<T = any>(sql: string, params?: any[]): Promise<QueryResult<T>> {",
            "    const response = await fetch(`${this.baseUrl}/api/v1/query`, {",
            "      method: 'POST',",
            "      headers: this.headers,",
            "      body: JSON.stringify({ sql, params }),",
            "    });",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Query failed: ${response.statusText}`);",
            "    }",
            "",
            "    return response.json();",
            "  }",
            "",
            "  /**",
            "   * Select records from a table",
            "   */",
            "  async select<T = any>(",
            "    table: string,",
            "    filters?: Record<string, any>,",
            "    limit?: number,",
            "    offset?: number",
            "  ): Promise<T[]> {",
            "    const params = new URLSearchParams();",
            "    if (filters) {",
            "      Object.entries(filters).forEach(([key, value]) => {",
            "        params.append(key, String(value));",
            "      });",
            "    }",
            "    if (limit !== undefined) params.append('limit', String(limit));",
            "    if (offset !== undefined) params.append('offset', String(offset));",
            "",
            "    const response = await fetch(",
            "      `${this.baseUrl}/api/v1/tables/${table}/records?${params}`,",
            "      {",
            "        method: 'GET',",
            "        headers: this.headers,",
            "      }",
            "    );",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Select failed: ${response.statusText}`);",
            "    }",
            "",
            "    const result = await response.json();",
            "    return result.records;",
            "  }",
            "",
            "  /**",
            "   * Create a new record",
            "   */",
            "  async create<T = any>(table: string, data: Partial<T>): Promise<CreateResult<T>> {",
            "    const response = await fetch(`${this.baseUrl}/api/v1/tables/${table}/records`, {",
            "      method: 'POST',",
            "      headers: this.headers,",
            "      body: JSON.stringify(data),",
            "    });",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Create failed: ${response.statusText}`);",
            "    }",
            "",
            "    return response.json();",
            "  }",
            "",
            "  /**",
            "   * Update a record by ID",
            "   */",
            "  async update<T = any>(",
            "    table: string,",
            "    id: string,",
            "    data: Partial<T>",
            "  ): Promise<UpdateResult<T>> {",
            "    const response = await fetch(",
            "      `${this.baseUrl}/api/v1/tables/${table}/records/${id}`,",
            "      {",
            "        method: 'PUT',",
            "        headers: this.headers,",
            "        body: JSON.stringify(data),",
            "      }",
            "    );",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Update failed: ${response.statusText}`);",
            "    }",
            "",
            "    return response.json();",
            "  }",
            "",
            "  /**",
            "   * Delete a record by ID",
            "   */",
            "  async delete(table: string, id: string): Promise<DeleteResult> {",
            "    const response = await fetch(",
            "      `${this.baseUrl}/api/v1/tables/${table}/records/${id}`,",
            "      {",
            "        method: 'DELETE',",
            "        headers: this.headers,",
            "      }",
            "    );",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Delete failed: ${response.statusText}`);",
            "    }",
            "",
            "    return response.json();",
            "  }",
            "",
            "  /**",
            "   * Bulk create multiple records",
            "   */",
            "  async bulkCreate<T = any>(",
            "    table: string,",
            "    records: Partial<T>[]",
            "  ): Promise<CreateResult<T>[]> {",
            "    const response = await fetch(",
            "      `${this.baseUrl}/api/v1/tables/${table}/records/bulk`,",
            "      {",
            "        method: 'POST',",
            "        headers: this.headers,",
            "        body: JSON.stringify({ records }),",
            "      }",
            "    );",
            "",
            "    if (!response.ok) {",
            "      throw new Error(`Bulk create failed: ${response.statusText}`);",
            "    }",
            "",
            "    return response.json();",
            "  }",
            "}",
            "",
        ]
        
        return "\n".join(content)
    
    def _generate_typescript_types(self) -> str:
        """Generate TypeScript type definitions."""
        content = [
            "/**",
            " * Common TypeScript type definitions for CinchDB",
            " */",
            "",
            "export interface QueryResult<T = any> {",
            "  success: boolean;",
            "  data: T[];",
            "  rowCount: number;",
            "  error?: string;",
            "}",
            "",
            "export interface CreateResult<T = any> {",
            "  success: boolean;",
            "  data: T;",
            "  error?: string;",
            "}",
            "",
            "export interface UpdateResult<T = any> {",
            "  success: boolean;",
            "  data: T;",
            "  rowsAffected: number;",
            "  error?: string;",
            "}",
            "",
            "export interface DeleteResult {",
            "  success: boolean;",
            "  rowsAffected: number;",
            "  error?: string;",
            "}",
            "",
            "export interface PaginationParams {",
            "  limit?: number;",
            "  offset?: number;",
            "}",
            "",
            "export interface FilterParams {",
            "  [key: string]: any;",
            "}",
            "",
        ]
        
        return "\n".join(content)

    def _generate_cinch_models_class(self) -> str:
        """Generate the CinchModels container class."""
        content = [
            '"""CinchModels container class for unified model access."""',
            "",
            "from typing import Dict, Any, Optional",
            "from cinchdb.core.database import CinchDB",
            "from cinchdb.managers.data import DataManager",
            "",
            "",
            "class CinchModels:",
            '    """Unified interface for generated models."""',
            "",
            "    def __init__(self, connection: CinchDB):",
            '        """Initialize with a CinchDB connection.',
            "",
            "        Args:",
            "            connection: CinchDB instance (local or remote)",
            '        """',
            "        if not isinstance(connection, CinchDB):",
            '            raise TypeError("CinchModels requires a CinchDB connection instance")',
            "",
            "        self._connection = connection",
            "        self._models = {}  # Lazy loaded model cache",
            "        self._model_registry = {}  # Map of model names to classes",
            "        self._tenant_override = None  # Optional tenant override",
            "",
            "    def __getattr__(self, name: str):",
            '        """Lazy load and return model class with connection set."""',
            "        if name not in self._models:",
            "            if name not in self._model_registry:",
            "                raise AttributeError(f\"Model '{name}' not found\")",
            "",
            "            model_class = self._model_registry[name]",
            "",
            "            # Determine tenant to use (override or connection default)",
            "            tenant = self._tenant_override or self._connection.tenant",
            "",
            "            # Initialize model with connection context",
            "            if self._connection.is_local:",
            "                # Create DataManager for local connections",
            "                data_manager = DataManager(",
            "                    self._connection.project_dir,",
            "                    self._connection.database,",
            "                    self._connection.branch,",
            "                    tenant",
            "                )",
            "                model_class._data_manager = data_manager",
            "            else:",
            "                # Remote connections not yet supported in codegen",
            '                raise NotImplementedError("Remote connections not yet supported in generated models")',
            "",
            "            self._models[name] = model_class",
            "",
            "        return self._models[name]",
            "",
            "    def with_tenant(self, tenant: str) -> 'CinchModels':",
            '        """Create models interface for a specific tenant with connection context override."""',
            "        # Create a new CinchModels with same connection but different tenant context",
            "        new_models = CinchModels(self._connection)",
            "        new_models._tenant_override = tenant",
            "        new_models._model_registry = self._model_registry",
            "        return new_models",
        ]

        return "\n".join(content)

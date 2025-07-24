"""Code generation router for CinchDB API."""

import tempfile
from typing import List, Dict
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from cinchdb.core.database import CinchDB
from cinchdb.api.auth import AuthContext, require_read_permission


router = APIRouter()


class CodegenLanguage(BaseModel):
    """Supported language for code generation."""
    name: str
    description: str


class GenerateModelsRequest(BaseModel):
    """Request to generate models."""
    language: str
    include_tables: bool = True
    include_views: bool = True


@router.get("/languages", response_model=List[CodegenLanguage])
async def list_supported_languages():
    """List supported code generation languages."""
    # Using a temporary CinchDB to get supported languages
    # This doesn't require specific database/branch so we use dummy values
    temp_project = Path(tempfile.mkdtemp())
    try:
        db = CinchDB(database="dummy", branch="dummy", tenant="dummy", project_dir=temp_project)
        languages = db.codegen.get_supported_languages()
        
        # Map languages to descriptions
        language_info = {
            "python": "Python Pydantic models with full CRUD operations",
            "typescript": "TypeScript interfaces and classes (planned)"
        }
        
        return [
            CodegenLanguage(
                name=lang, 
                description=language_info.get(lang, f"{lang.title()} models")
            ) 
            for lang in languages
        ]
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_project, ignore_errors=True)






@router.post("/generate/files", response_model=Dict[str, str])
async def generate_model_files_content(
    request: GenerateModelsRequest,
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Generate model files and return their content as JSON (alternative to ZIP download)."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Create temporary directory for generation
        temp_dir = Path(tempfile.mkdtemp())
        output_dir = temp_dir / "generated_models"
        
        # Initialize CinchDB and get codegen manager
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        codegen_mgr = db.codegen
        
        # Generate models
        results = codegen_mgr.generate_models(
            language=request.language,
            output_dir=output_dir,
            include_tables=request.include_tables,
            include_views=request.include_views
        )
        
        # Read generated files and return their content
        file_contents = {}
        
        for file_name in results["files_generated"]:
            file_path = output_dir / file_name
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_contents[file_name] = f.read()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return file_contents
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.get("/info")
async def get_codegen_info(
    database: str = Query(..., description="Database name"),
    branch: str = Query(..., description="Branch name"),
    auth: AuthContext = Depends(require_read_permission)
):
    """Get information about what can be generated for the current database/branch."""
    db_name = database
    branch_name = branch
    
    # Check branch permissions
    await require_read_permission(auth, branch_name)
    
    try:
        # Initialize CinchDB and get codegen manager
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        codegen_mgr = db.codegen
        
        # Get available tables and views using CinchDB
        db = CinchDB(database=db_name, branch=branch_name, tenant="main", project_dir=auth.project_dir)
        tables = db.tables.list_tables()
        views = db.views.list_views()
        
        return {
            "database": db_name,
            "branch": branch_name,
            "tenant": "main",
            "supported_languages": codegen_mgr.get_supported_languages(),
            "available_tables": [table.name for table in tables],
            "available_views": [view.name for view in views],
            "total_entities": len(tables) + len(views)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))